from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agents.state import AseelState
from config.settings import OPENAI_MODEL
from tools.evidence_validation import validate_evidence


class EvidenceRecord(BaseModel):
    question: str
    answer: str
    region: str
    domain: str = ""
    category: str = ""
    relevance: float
    distance: float | None = None


class ValidationInput(BaseModel):
    records: list[EvidenceRecord] = Field(default_factory=list)
    requested_region: str = ""


@tool(args_schema=ValidationInput)
def validate_evidence_tool(
    records: list[EvidenceRecord],
    requested_region: str = "",
) -> str:
    """Validate retrieved cultural evidence and calculate confidence."""

    record_dicts = [record.model_dump() for record in records]

    valid, reason, confidence_score = validate_evidence(
        record_dicts,
        requested_region or None,
    )

    return json.dumps(
        {
            "valid": valid,
            "reason": reason,
            "confidence_score": confidence_score,
            "passed": confidence_score >= 0.50,
        },
        ensure_ascii=False,
    )


validation_agent = create_agent(
    model=OPENAI_MODEL,
    tools=[validate_evidence_tool],
    system_prompt="""
You are ASEEL's Validation Agent.

Your job is to validate retrieved Saudi cultural evidence.

IMPORTANT:
- Call the validation tool exactly ONCE.
- Pass all retrieved records to the tool without changing their values.
- After receiving the tool result, STOP.
- Do not call the tool again.
- Do not retry the tool yourself.
- Do not recalculate the confidence score.
- Do not modify the evidence.
- PASS if the returned confidence_score is 0.50 or higher.
- RETRY if the returned confidence_score is below 0.50.
- Your final response must contain only PASS or RETRY.
""",
)


def validate_cultural_knowledge(state: AseelState) -> dict:
    records = state.get("retrieved", [])
    region = state.get("region") or ""

    # Deterministic validation.
    # Region matching must never depend on the LLM.
    validated, reason, confidence_score = validate_evidence(
        records,
        region or None,
    )

    passed = confidence_score >= 0.50

    return {
        "validated": validated,
        "status": "grounded" if passed else "pending",
        "validation_reason": reason,
        "confidence_score": confidence_score,
    }


def refine_query(state: AseelState) -> dict:
    query = state["query"]

    if state.get("occasion"):
        query = f"{query} {state['occasion']} etiquette customs"

    return {
        "retrieval_query": query,
        "attempts": state.get("attempts", 0) + 1,
    }