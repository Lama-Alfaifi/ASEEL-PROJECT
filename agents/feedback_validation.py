from __future__ import annotations

import json

from langchain.agents import create_agent

from config.settings import OPENAI_MODEL_UNDERSTANDING


feedback_validation_agent = create_agent(
    model=OPENAI_MODEL_UNDERSTANDING,
    tools=[],
    system_prompt="""
You are ASEEL's Feedback Validation Agent.

Your job is to analyze user-submitted feedback about a Saudi cultural
answer and CLASSIFY it — you do NOT decide whether it gets published.

CRITICAL RULE: You must never cause the knowledge base to be changed.
Your output is only a recommendation for a human reviewer. You never
recommend "approved" — only a human approves feedback.

Analyze the feedback for:
- Is it relevant to Saudi culture at all?
- Is it a factual cultural claim, or just an opinion/preference?
- Is it a correction of something ASEEL said, or new information?
- Does it reference a specific city/region?
- Would it need supporting evidence/source before being trusted?
- Does it look like it might contradict existing knowledge?

Return ONLY valid JSON, no other text, in this exact shape:
{
  "classification": "correction" | "clarification" | "missing_information" | "additional_information" | "wrong_region" | "opinion" | "other",
  "relevance": <float 0.0-1.0>,
  "contains_cultural_claim": <true or false>,
  "needs_source_verification": <true or false>,
  "recommended_action": "needs_review" | "reject_low_relevance"
}
""",
)


def _clean_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def validate_feedback(feedback: dict) -> dict:
    """
    Classify a feedback item. On any failure (LLM error, bad JSON), returns
    a safe default that routes to human review rather than silently
    dropping or auto-rejecting the feedback.
    """
    prompt = f"""
Feedback type (user-selected): {feedback.get("type")}
Message: {feedback.get("message")}
City: {feedback.get("city") or "Not specified"}
Region: {feedback.get("region") or "Not specified"}
Category: {feedback.get("category") or "Not specified"}
Original question asked to ASEEL: {feedback.get("original_query") or "Not specified"}
ASEEL's original answer: {feedback.get("original_answer") or "Not specified"}
"""

    try:
        result = feedback_validation_agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        for message in reversed(result.get("messages", [])):
            content = getattr(message, "content", "")
            if not content:
                continue
            try:
                return json.loads(_clean_json(content))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

    except Exception:
        pass

    return {
        "classification": "other",
        "relevance": 0.0,
        "contains_cultural_claim": False,
        "needs_source_verification": True,
        "recommended_action": "needs_review",
    }