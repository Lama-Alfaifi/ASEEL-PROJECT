from __future__ import annotations
from agents.state import AseelState
from tools.context_extraction import extract_context
from tools.region_resolution import resolve_region

def understand_context(state: AseelState) -> dict:
    context = extract_context(state["query"], state.get("conversation_context", ""))
    return {**context, "region": resolve_region(state["query"]), "attempts": state.get("attempts", 0)}