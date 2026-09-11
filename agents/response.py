from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain_core.tools import tool

from agents.state import AseelState
from config.settings import OPENAI_MODEL


@tool
def prepare_cultural_evidence(records: list[dict]) -> str:
    """Prepare validated cultural evidence for the final answer."""

    if not records:
        return json.dumps(
            {
                "status": "no_evidence",
                "message": "No validated cultural evidence is available.",
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
using ONLY the validated evidence provided.

Rules:
- Use the prepare_cultural_evidence tool exactly once.
- Do not invent cultural facts.
- Do not add information that is not supported by the evidence.
- Give a concise and useful answer.
- Mention the regional scope when available.
- If there is not enough evidence, clearly say that the knowledge base
  does not contain enough information.
- Do not make absolute claims such as "always" or "never".
"""
)


def generate_response(state: AseelState) -> dict:
    facts = state.get("validated", [])
    confidence = state.get("confidence_score", 0.0)

    # Final safety check before calling the LLM
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

Region:
{state.get("region") or "Not specified"}

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

    # Get the final AI response
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