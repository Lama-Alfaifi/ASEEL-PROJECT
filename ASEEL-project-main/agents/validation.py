from __future__ import annotations
from agents.state import AseelState
from tools.evidence_validation import validate_evidence

def validate_cultural_knowledge(state: AseelState) -> dict:
    valid, evidence_reason = validate_evidence(state.get("retrieved", []), state.get("region"))
    return {"validated": valid, "status": "grounded" if valid else "pending", "validation_reason": evidence_reason}

def refine_query(state: AseelState) -> dict:
    # A deliberately conservative retry: expands terminology but never adds cultural facts.
    query = state["query"]
    if state.get("occasion"):
        query = f"{query} {state['occasion']} etiquette customs"
    return {"retrieval_query": query, "attempts": state.get("attempts", 0) + 1}