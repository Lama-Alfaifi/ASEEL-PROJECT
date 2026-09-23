from __future__ import annotations

import json

from langchain_core.tools import tool

from config.settings import TOP_K
from retrieval.vector_store import CulturalVectorStore
from utils.location_resolver import location_resolver


store = CulturalVectorStore()


@tool
def search_cultural_knowledge(query: str, region: str = "") -> str:
    """Search the Saudi cultural knowledge base for relevant cultural evidence."""

    location = location_resolver.find_in_query(query)

    # An explicitly-provided region always wins over a city detected in
    # this query's text — see cultural_search.py history: a detected city
    # silently overwriting an already-correct region (e.g. from memory on
    # a follow-up question) was the root cause of the original retrieval
    # inconsistency bug.
    resolved_region = region or ""

    if not resolved_region and location:
        resolved_region = location["planning_region"]

    resolved_region = CulturalVectorStore.normalize_region(resolved_region) or ""

    results = store.search(
        query=query,
        region=resolved_region or None,
        limit=TOP_K,
    )

    # Remove duplicate knowledge records (same underlying question
    # appearing more than once in the source CSVs) so the top-K passed to
    # validation stays as diverse as possible instead of wasting slots on
    # near-identical repeats.
    unique_results = []
    seen_questions = set()

    for result in results:
        question_key = result.record.question.strip().lower()

        if question_key not in seen_questions:
            seen_questions.add(question_key)
            unique_results.append(result)

    results = unique_results

    if not results:
        return json.dumps(
            {
                "results": [],
                "message": "No relevant cultural knowledge was found.",
                "location": location,
                "resolved_region": resolved_region or None,
            },
            ensure_ascii=False,
        )

    records = [
        {
            "question": result.record.question,
            "answer": result.record.answer,
            "choices": result.record.choices,
            "region": result.record.region,
            "domain": result.record.domain,
            "category": result.record.category,
            "relevance": result.relevance,
            "distance": result.distance,
        }
        for result in results
    ]

    return json.dumps(
        {
            "results": records,
            "location": location,
            "resolved_region": resolved_region or None,
        },
        ensure_ascii=False,
    )