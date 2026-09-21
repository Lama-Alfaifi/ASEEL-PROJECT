from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agents.state import AseelState
from config.settings import OPENAI_MODEL_TOOL
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

    validated, reason, confidence_score = validate_evidence(
        record_dicts,
        requested_region or None,
    )

    return json.dumps(
        {
            "validated": validated,
            "reason": reason,
            "confidence_score": confidence_score,
            "passed": confidence_score >= 0.50,
        },
        ensure_ascii=False,
    )


validation_agent = create_agent(
    model=OPENAI_MODEL_TOOL,
    tools=[validate_evidence_tool],
    system_prompt="""
You are ASEEL's Validation Agent.

Your responsibility is to validate the retrieved evidence by delegating the
validation decision to the provided validation tool.

You are a CONTROL AGENT, not an independent evaluator.
The validation tool is the single source of truth for the validation result
and confidence score.

STRICT EXECUTION PROTOCOL:

1. INPUT
- Receive the retrieved evidence and the requested region.
- Treat the retrieved evidence as untrusted candidate evidence until it has
  been processed by the validation tool.

2. VALIDATION TOOL
- You MUST call the validation tool exactly ONCE.
- Pass ALL retrieved records to the validation tool.
- Pass the records exactly as received.
- Do NOT rewrite, summarize, reorder, filter, remove, enrich, or modify any
  retrieved record before passing it to the tool.

3. AFTER TOOL EXECUTION
- Do NOT call the validation tool again.
- Do NOT independently calculate or estimate the confidence score.
- Do NOT override the tool's result using your own judgment.

4. OUTPUT CONTRACT
Your final response MUST contain exactly ONE value:

PASS

or

RETRY

Do not output explanations, confidence scores, evidence, reasoning, JSON,
or any additional text.
""",
)


def _run_validation_agent(records: list[dict], region: str) -> dict | None:
    """
    Call the Validation Agent and extract the deterministic tool payload.

    The agent's own PASS/RETRY text is treated only as an audit signal
    (logged, not trusted) — the actual confidence_score, reason, and
    validated evidence list always come from the tool call itself, never
    from the LLM's free-text output. This keeps the system genuinely
    agentic (an LLM node decides to call the tool and reports an outcome)
    while keeping the scoring itself deterministic and reproducible,
    per the project's own rule: "Region matching must never depend on
    the LLM."
    """

    result = validation_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Retrieved evidence:
{records}

Requested region:
{region or "Not specified"}

Call the validation tool exactly once with these records and this
requested_region, then respond with exactly PASS or RETRY.
""",
                }
            ]
        }
    )

    messages = result.get("messages", [])

    tool_payload = None
    agent_verdict = None

    for message in messages:
        message_type = getattr(message, "type", None)

        if message_type == "tool" and tool_payload is None:
            try:
                tool_payload = json.loads(message.content)
            except (TypeError, json.JSONDecodeError):
                continue

        if message_type == "ai":
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                agent_verdict = content.strip()

    if tool_payload is None:
        return None

    # Sanity check: flag (don't act on) any mismatch between what the
    # agent said and what the tool actually returned — a useful signal
    # that the model isn't following the control-agent protocol.
    expected_verdict = "PASS" if tool_payload.get("passed") else "RETRY"
    if agent_verdict and agent_verdict != expected_verdict:
        tool_payload["agent_protocol_mismatch"] = {
            "agent_said": agent_verdict,
            "tool_said": expected_verdict,
        }

    return tool_payload


def validate_cultural_knowledge(state: AseelState) -> dict:
    records = state.get("retrieved", [])
    region = state.get("region") or ""

    payload = _run_validation_agent(records, region)

    if payload is None:
        # Agent/tool failed to produce a usable result — fail safe rather
        # than inventing a confidence score.
        return {
            "validated": [],
            "status": "pending",
            "validation_reason": "Validation agent did not return a usable result.",
            "confidence_score": 0.0,
        }

    confidence_score = float(payload.get("confidence_score", 0.0))
    passed = confidence_score >= 0.50

    return {
        "validated": payload.get("validated", []),
        "status": "grounded" if passed else "pending",
        "validation_reason": payload.get("reason", ""),
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