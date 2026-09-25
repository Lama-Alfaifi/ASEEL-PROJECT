from __future__ import annotations


def build_decision_summary(state: dict) -> dict:
    """Short, displayable summary of how ASEEL reached its answer.
    Built only from final structured fields, never from raw LLM reasoning."""

    context_parts = [
        state.get("occasion"),
        state.get("situation"),
        state.get("category"),
    ]
    context = " · ".join(str(p) for p in context_parts if p) or None

    # Evidence actually used for the answer = validated records
    evidence = state.get("validated") or []

    return {
        "detected_region": state.get("region"),
        "city": state.get("city"),
        "context": context,
        "evidence_count": len(evidence),
        "location_source": state.get("location_source"),
    }