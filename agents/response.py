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
Your job is to answer the user's Saudi cultural question 
using ONLY the validated evidence provided. STRICT GROUNDING RULES: 
- Use the prepare_cultural_evidence tool exactly once. 
- Do not invent, assume, or add cultural facts. 
- Do not use outside knowledge. 
- Do not transfer customs, traditions, or practices from one region to another. 
- Every cultural claim in your answer must be supported by the provided evidence. 
- Respect the requested regional scope. - If the evidence does not support a claim, do not make that claim. 
- If there is not enough evidence, clearly say that the knowledge base does not contain enough information. 
- Do not make absolute claims such as "always" or "never". - Keep the answer concise and useful.

CITY-TO-REGION RULE: 
- ASEEL's cultural knowledge base is organized by regional scope, not by individual cities. 
- When the user asks about a specific city, use the resolved region provided in the context. 
- Clearly mention the city and its corresponding region in the answer. 
- Make it clear that the cultural information comes from the broader region, not from city-specific data. 
- Do NOT claim that a tradition is unique to or specifically practiced in the city unless the provided evidence explicitly mentions that city. 
- You may answer a city question using evidence from its region, as long as you clearly frame it as regional cultural information.

Example: If the user asks about Dammam and the requested region is East, say: 
"Dammam is in the Eastern Region of Saudi Arabia. Based on the available regional evidence, some cultural traditions include..." 
Then continue with the supported cultural information.
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
