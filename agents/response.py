from __future__ import annotations

import json

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
    # Never pass evidence from another region to the response model.
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
            == normalized_requested_region
        ]

    if not records:
        return json.dumps(
            {
                "status": "no_region_matched_evidence",
                "message": (
                    "No validated evidence matches the requested region."
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


def generate_response(state: AseelState) -> dict:
    facts = state.get("validated", [])
    confidence = state.get("confidence_score", 0.0)
    requested_region = state.get("region") or ""

    # Final safety check before calling the LLM.
    # Only validated evidence from the requested region may reach the model.
    # Normalized for the same reason as in prepare_cultural_evidence above.
    if requested_region:
        normalized_requested_region = CulturalVectorStore.normalize_region(
            requested_region
        )

        facts = [
            record
            for record in facts
            if CulturalVectorStore.normalize_region(record.get("region"))
            == normalized_requested_region
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

Use the evidence tool exactly once and then provide the final answer.
""",
                }
            ]
        }
    )

    messages = result.get("messages", [])

    answer = ""

    for message in reversed(messages):
        if getattr(message, "type", None) == "ai":
            content = message.content

            if isinstance(content, str):
                answer = content
            elif isinstance(content, list):
                answer = " ".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )

            if answer:
                break

    if not answer:
        answer = (
            "I could not generate a response from the available evidence."
        )

    return {
        "answer": answer,
        "status": "grounded",
        "sources": facts,
    }