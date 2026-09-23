from __future__ import annotations

import json
import re

from langchain.agents import create_agent
from langchain_core.tools import tool

from agents.state import AseelState
from config.settings import OPENAI_MODEL_RESPONSE
from prompts.response import SYSTEM_PROMPT
from retrieval.vector_store import CulturalVectorStore


@tool
def prepare_cultural_evidence(
    records: list[dict],
    requested_region: str = "",
) -> str:
    """Prepare validated cultural evidence for the final answer."""

    if not records:
        return json.dumps(
            {
                "status": "no_evidence",
                "message": "No validated cultural evidence is available.",
            },
            ensure_ascii=False,
        )

    # Final region safety check.
    # Never pass incompatible regional evidence to the response model; General is nationwide.
    # Normalized before comparing — the same defensive fix applied in
    # tools/evidence_validation.py and tools/cultural_search.py, so a
    # differently-spelled but equivalent region (e.g. "Eastern" vs "East")
    # can never silently empty out valid evidence here.
    if requested_region:
        normalized_requested_region = CulturalVectorStore.normalize_region(
            requested_region
        )

        records = [
            record
            for record in records
            if CulturalVectorStore.normalize_region(record.get("region"))
            in (normalized_requested_region, "General")
        ]

    if not records:
        return json.dumps(
            {
                "status": "no_region_matched_evidence",
                "message": (
                    "No validated evidence matches the requested region or General scope."
                ),
            },
            ensure_ascii=False,
        )

    evidence = [
        {
            "region": record.get("region"),
            "question": record.get("question"),
            "answer": record.get("answer"),
            "category": record.get("category"),
            "relevance": record.get("relevance"),
        }
        for record in records
    ]

    return json.dumps(
        {
            "status": "evidence_available",
            "region": requested_region or None,
            "evidence": evidence,
        },
        ensure_ascii=False,
    )


response_agent = create_agent(
    model=OPENAI_MODEL_RESPONSE,
    tools=[prepare_cultural_evidence],
    system_prompt=SYSTEM_PROMPT,
)

# Tool-less agent used only to repair an answer that came back in the wrong
# language. Same model tier as the response agent: this is user-facing text.
_english_rewrite_agent = create_agent(
    model=OPENAI_MODEL_RESPONSE,
    tools=[],
    system_prompt="""
You rewrite an answer into English. Your ONLY job is translation.

- Preserve the meaning exactly. Do not add, remove, or soften anything.
- Keep every hedge and limitation.
- Keep Saudi cultural terms, names and places transliterated
  (e.g. Al-Kurta, Thobe Asiri). Do not output Arabic script.
- Return ONLY the English answer text.
""",
)

_ARABIC_CHAR = re.compile(r"[\u0600-\u06FF]")


def _arabic_ratio(text: str) -> float:
    """Share of alphabetic characters that are Arabic script."""
    letters = [c for c in text if c.isalpha()]

    if not letters:
        return 0.0

    return sum(1 for c in letters if _ARABIC_CHAR.match(c)) / len(letters)


def _last_ai_text(messages: list) -> str:
    """Text of the last AI message that has any."""
    for message in reversed(messages):
        if getattr(message, "type", None) != "ai":
            continue

        content = message.content
        text = ""

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        if text.strip():
            return text.strip()

    return ""


def _ensure_english(answer: str) -> str:
    """
    The pipeline invariant (graph.py) is that every agent works in English and
    the translation layer converts the final answer to the user's language.
    If the response model still answered in Arabic (e.g. because the evidence
    was Arabic), repair it here instead of letting it reach the user in the
    wrong language. Fails safe: returns the original answer on any error.
    """
    if _arabic_ratio(answer) <= 0.3:
        return answer

    try:
        result = _english_rewrite_agent.invoke(
            {"messages": [{"role": "user", "content": answer}]}
        )
        rewritten = _last_ai_text(result.get("messages", []))

        if rewritten and _arabic_ratio(rewritten) <= 0.3:
            return rewritten
    except Exception:
        pass

    return answer


def generate_response(state: AseelState) -> dict:
    facts = state.get("validated", [])
    confidence = state.get("confidence_score", 0.0)
    requested_region = state.get("region") or ""

    # Final safety check before calling the LLM.
    # Only validated evidence from the requested region or General scope may reach the model.
    # Normalized for the same reason as in prepare_cultural_evidence above.
    if requested_region:
        normalized_requested_region = CulturalVectorStore.normalize_region(
            requested_region
        )

        facts = [
            record
            for record in facts
            if CulturalVectorStore.normalize_region(record.get("region"))
            in (normalized_requested_region, "General")
        ]

    if not facts or confidence < 0.50:
        return {
            "answer": (
                "I could not find enough reliable cultural evidence "
                "in the ASEEL knowledge base to answer this question confidently."
            ),
            "status": "fallback",
            "sources": facts,
        }

    result = response_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
User question:
{state["query"]}

Requested region:
{requested_region or "Not specified"}

User role:
{state.get("user_role") or "Not specified"}

Occasion:
{state.get("occasion") or "Not specified"}

Retrieval confidence:
{confidence}

Validated evidence:
{facts}

Answer language (mandatory): English.
The evidence may contain Arabic. Read it, then write the entire answer in
English, keeping Saudi cultural terms transliterated (e.g. Al-Kurta).
Do not output Arabic script. The requested region affects which evidence
applies, never the language of the answer.

Use the evidence tool exactly once and then provide the final answer.
""",
                }
            ]
        }
    )

    answer = _last_ai_text(result.get("messages", []))

    if not answer:
        answer = (
            "I could not generate a response from the available evidence."
        )

    answer = _ensure_english(answer)

    return {
        "answer": answer,
        "status": "grounded",
        "sources": facts,
    }