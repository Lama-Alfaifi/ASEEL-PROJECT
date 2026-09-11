from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.state import AseelState
from agents.understanding import understand_context
from agents.retrieval_agent import retrieve_knowledge
from agents.validation import validate_cultural_knowledge, refine_query
from agents.response import generate_response


def route_after_validation(state: AseelState) -> str:
    confidence = state.get("confidence_score", 0.0)

    if confidence >= 0.5:
        return "respond"

    return "refine" if state.get("attempts", 0) < 1 else "respond"


def build_workflow():
    graph = StateGraph(AseelState)

    graph.add_node("understand", understand_context)
    graph.add_node("retrieve", retrieve_knowledge)
    graph.add_node("validate", validate_cultural_knowledge)
    graph.add_node("refine", refine_query)
    graph.add_node("respond", generate_response)

    graph.add_edge(START, "understand")
    graph.add_edge("understand", "retrieve")
    graph.add_edge("retrieve", "validate")

    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "respond": "respond",
            "refine": "refine",
        },
    )

    graph.add_edge("refine", "retrieve")
    graph.add_edge("respond", END)

    return graph.compile()


def ask(query: str, conversation_context: str = "") -> dict:
    return build_workflow().invoke(
        {
            "query": query,
            "conversation_context": conversation_context,
            "attempts": 0,
        }
    )