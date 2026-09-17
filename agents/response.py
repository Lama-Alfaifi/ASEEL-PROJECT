from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain_core.tools import tool

from agents.state import AseelState
from config.settings import OPENAI_MODEL


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
    if requested_region:
        records = [
            record
            for record in records
            if record.get("region") == requested_region
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
    model=OPENAI_MODEL,
    tools=[prepare_cultural_evidence],
    system_prompt="""
You are ASEEL's Response Agent.

Answer the user's Saudi cultural question using ONLY the validated evidence.

RULES:
- Use the prepare_cultural_evidence tool exactly once.
- Do not invent, assume, or use outside knowledge.
- Every cultural claim must be supported by the evidence.
- Do not transfer customs between regions.
- If evidence is insufficient, clearly say so.
- Keep the answer concise.
- Do not make absolute claims such as "always" or "never".

CITY-TO-REGION RULE:
- ASEEL's cultural knowledge base is organized by regional scope, not by
  individual cities.
- When the user asks about a specific city, use the resolved region provided
  in the context.
- You may use evidence from the city's broader region if it is relevant.
- If the evidence is regional only, do not mention the city in the same sentence
  as a cultural claim.
- City context may be used to identify the relevant region, but it must not be
  treated as evidence that the practice is specific to that city.
- Clearly mention the city and its corresponding region in the answer.
- Clearly state that the available cultural information comes from the broader
  region rather than city-specific data.
- Do NOT present regional evidence as if it were specifically practiced in,
  unique to, or characteristic of the requested city.
- Do NOT claim that a tradition is unique to or specifically practiced in the
  city unless the provided evidence explicitly mentions that city.
- Do NOT infer that a regional practice applies specifically to the city.
- When only regional evidence is available, use wording such as:
  "Based on the available regional evidence..."
  or
  "These practices are associated with the broader Southern Region and are not
  necessarily specific to Faifa."
- If the user asks for customs specifically associated with the city and the
  evidence is only regional, clearly state that the knowledge base does not
  provide city-specific evidence.

"""

)


def generate_response(state: AseelState) -> dict:
    facts = state.get("validated", [])
    confidence = state.get("confidence_score", 0.0)
    requested_region = state.get("region") or ""

    # Final safety check before calling the LLM.
    # Only validated evidence from the requested region may reach the model.
    if requested_region:
        facts = [
            record
            for record in facts
            if record.get("region") == requested_region
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
