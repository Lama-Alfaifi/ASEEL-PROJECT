from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from agents.state import AseelState
from config.settings import OPENAI_MODEL_TOOL
from tools.cultural_search import search_cultural_knowledge
from tools.metadata_filter import filter_by_metadata
from utils.region_override import normalize_region_override

log = logging.getLogger(__name__)

MAX_RESULTS = 5
MAX_PLANNED_QUERIES = 3

# ---------------------------------------------------------------------------
# Design
#
# Pass 1 (attempts == 0): deterministic vector search over the rewritten
#   query and the user's original wording, merged. Cheap, fast, and the
#   region filter is applied inside the store, never by an LLM.
#
# Pass 2 (attempts > 0, i.e. validation found the evidence too weak):
#   an LLM *diagnoses* why the first search failed and plans 1-3 new queries
#   (alternative spellings, a generic descriptor for unfamiliar terms, or a
#   split of a compound question). Each query is searched, and the results
#   are merged with the evidence from pass 1.
#
# The LLM only ever decides WHAT TO SEARCH FOR. It never sees or edits the
# evidence, and the region filter stays inside CulturalVectorStore.search(),
# so a bad plan can at worst retrieve nothing - never cross-region evidence.
# ---------------------------------------------------------------------------


class QueryPlan(BaseModel):
    diagnosis: str = Field(
        description="One short sentence: why the previous retrieval was weak."
    )
    queries: list[str] = Field(
        description="1 to 3 alternative search queries, each meaningfully different."
    )


PLANNER_PROMPT = """
You are ASEEL's Retrieval Planner. A semantic search over a Saudi cultural
knowledge base returned weak evidence. Write better SEARCH QUERIES.

Rules:
- You only write search queries. Do NOT answer the question and do NOT state
  cultural facts.
- Keep the user's intent and keep any city/region exactly as in the original
  query. Never introduce a different location.
- If the question contains an unfamiliar or transliterated Arabic term, keep
  its original spelling, add plausible alternative transliterations, and add
  a generic descriptor as a search hint (e.g. "traditional dish", "traditional
  garment", "heritage site").
- If the question has two parts, write one focused query per part.
- Use the retrieved titles to see what was found and aim at what is missing.
- Write plain natural-language queries of at most 12 words. No quotation
  marks, no parentheses, and no lists of guesses inside one query: use one
  concrete descriptor per query and put different guesses in different queries.
- Return 1-3 queries. No duplicates.
"""

_planner = None


def _get_planner():
    global _planner
    if _planner is None:
        _planner = ChatOpenAI(
            model=OPENAI_MODEL_TOOL,
            temperature=0,
        ).with_structured_output(QueryPlan)
    return _planner


def plan_queries(state: AseelState) -> list[str]:
    """LLM-planned follow-up queries. Returns [] on any failure."""
    previous = state.get("retrieval_query") or state.get("query", "")

    found = [
        f"- ({r.get('relevance', 0):.2f}) {r.get('question', '')}"
        for r in (state.get("retrieved") or state.get("raw_semantic_results") or [])[:3]
    ]

    user = (
        f"Original question: {state.get('query', '')}\n"
        f"Previous search query: {previous}\n"
        f"Region: {state.get('region') or 'not specified'}\n"
        f"Category: {state.get('category') or 'not specified'}\n"
        f"Why validation failed: {state.get('validation_reason') or 'low relevance'}\n"
        "Best records found so far:\n"
        f"{chr(10).join(found) if found else '- none'}"
    )

    try:
        plan = _get_planner().invoke(
            [("system", PLANNER_PROMPT), ("human", user)]
        )
    except Exception as exc:  # network, schema, quota ... fail safe
        log.warning("Retrieval planner failed: %r", exc)
        return []

    log.info("Retrieval plan: %s | %s", plan.diagnosis, plan.queries)

    queries, seen = [], {previous.strip().lower()}

    for q in plan.queries:
        q = (q or "").strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            queries.append(q)

    return queries[:MAX_PLANNED_QUERIES]


def _search(query: str, region: str) -> list[dict]:
    try:
        payload = json.loads(
            search_cultural_knowledge.invoke({"query": query, "region": region})
        )
        return payload.get("results", [])
    except (json.JSONDecodeError, TypeError):
        return []


def _merge(result_lists: list[list[dict]]) -> list[dict]:
    """Deduplicate by question text, keeping the best relevance for each."""
    best: dict[str, dict] = {}

    for records in result_lists:
        for record in records:
            key = (record.get("question") or "").strip().lower()

            if not key:
                continue

            current = best.get(key)

            if current is None or (record.get("relevance") or 0) > (
                current.get("relevance") or 0
            ):
                best[key] = record

    return sorted(
        best.values(),
        key=lambda r: r.get("relevance") or 0,
        reverse=True,
    )


def retrieve_knowledge(state: AseelState) -> dict:
    query = state["retrieval_query"]

    # An explicit UI selection (including "General") is authoritative.
    region = (
        normalize_region_override(state.get("region_override"))
        or state.get("region")
        or ""
    )

    if state.get("attempts", 0) == 0:
        # Search the rewritten query AND the user's original wording. The
        # rewrite often appends region text ("... in the South region of
        # Saudi Arabia"), which can drag generic region-trivia records above
        # the exact match. The region filter already lives in the store, so
        # the bare question is always worth searching too (embedding only,
        # no LLM call).
        queries = [query]
        original = (state.get("query") or "").strip()

        if original and original.lower() != query.strip().lower():
            queries.append(original)

        result_lists = [_search(q, region) for q in queries]
    else:
        # Keep what pass 1 found, then add the LLM-planned searches.
        result_lists = [state.get("raw_semantic_results") or []]

        for planned in plan_queries(state):
            result_lists.append(_search(planned, region))

    records = _merge(result_lists)[:MAX_RESULTS]

    filtered_records = filter_by_metadata(
        records,
        state.get("region"),
        state.get("category"),
    )

    return {
        "raw_semantic_results": records,
        "retrieved": filtered_records,
    }