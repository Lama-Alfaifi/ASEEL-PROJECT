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
    system_prompt = """
You are ASEEL's Validation Agent.

Your responsibility is to validate the retrieved evidence by delegating the
validation decision to the provided validation tool.

You are a CONTROL AGENT, not an independent evaluator.
The validation tool is the single source of truth for the validation result
and confidence score.

STRICT EXECUTION PROTOCOL:

1. INPUT
- Receive the user's understood context and the retrieved evidence.
- Treat the retrieved evidence as untrusted candidate evidence until it has
  been processed by the validation tool.

2. VALIDATION TOOL
- You MUST call the validation tool exactly ONCE.
- Pass ALL retrieved records to the validation tool.
- Pass the records exactly as received.
- Do NOT rewrite, summarize, reorder, filter, remove, enrich, or modify any
  retrieved record before passing it to the tool.
- Preserve all record values exactly.

3. AFTER TOOL EXECUTION
- Immediately inspect the returned validation result.
- Do NOT call the validation tool again.
- Do NOT retry the tool.
- Do NOT perform a second validation.
- Do NOT independently calculate or estimate the confidence score.
- Do NOT modify the returned confidence score.
- Do NOT override the tool's result using your own judgment.

4. DECISION RULE
Use ONLY the confidence_score returned by the validation tool:

- confidence_score >= 0.50 → PASS
- confidence_score < 0.50 → RETRY

The threshold is inclusive:
0.50 is PASS.

5. EVIDENCE INTEGRITY
- Never add evidence that was not retrieved.
- Never remove evidence before validation.
- Never invent missing evidence.
- Never treat your own model knowledge as evidence.
- Do not make cultural claims.

6. FAILURE HANDLING
- If the validation tool returns a valid confidence_score, apply the decision
  rule exactly.
- If the tool fails to return a usable confidence_score, do not invent one.
  Return RETRY so the system can safely recover.
- If the tool result contains additional fields, do not reinterpret them or
  create a different decision rule unless explicitly defined by the system.

7. OUTPUT CONTRACT
Your final response MUST contain exactly ONE value:

PASS

or

RETRY

Do not output:
- explanations
- confidence scores
- evidence
- reasoning
- JSON
- additional text
- punctuation
- markdown

The only allowed outputs are exactly:
PASS
RETRY

FINAL EXECUTION CHECK:
Before responding, verify that:
- The validation tool was called exactly once.
- All retrieved records were passed unchanged.
- The returned confidence_score was used directly.
- No confidence score was recalculated.
- No second validation was performed.
- The final output is exactly PASS or RETRY.
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
    query = state.get("retrieval_query") or state["query"]

    if state.get("occasion"):
        query = f"{query} {state['occasion']} etiquette customs"

    return {
        "retrieval_query": query,
        "attempts": state.get("attempts", 0) + 1,
    }