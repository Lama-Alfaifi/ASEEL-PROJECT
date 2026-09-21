from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.state import AseelState
from agents.understanding import understand_context
from agents.retrieval_agent import retrieve_knowledge
from agents.validation import validate_cultural_knowledge, refine_query
from agents.response import generate_response

from utils.monitoring import start_timer, record_run
from memory.conversation_memory import ConversationMemory


def route_after_validation(state: AseelState) -> str:
    confidence = state.get("confidence_score", 0.0)
    attempts = state.get("attempts", 0)

    if confidence >= 0.50:
        return "respond"

    if attempts < 1:
        return "refine"

    return "respond"


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


workflow = build_workflow()


def ask(
    query: str,
    conversation_context: str = "",
    memory: ConversationMemory | None = None,
) -> dict:

    start_time = start_timer()

    if memory is None:
        memory = ConversationMemory()

    try:
        memory_context = memory.to_prompt_context()

        combined_context = ""

        if memory_context:
            combined_context += (
                "Conversation memory:\n"
                f"{memory_context}\n\n"
            )

        if conversation_context:
            combined_context += (
                "Recent conversation:\n"
                f"{conversation_context}"
            )

        result = workflow.invoke(
            {
                "query": query,
                "conversation_context": combined_context,
                "attempts": 0,
            }
        )
        confidence = result.get(
            "confidence_score",
            0.0,
        )

        attempts = result.get(
            "attempts",
            0,
        )

        if confidence >= 0.50:
            agent_decision = "respond"

        elif attempts < 1:
            agent_decision = "refine"

        else:
            agent_decision = "fallback"

        result["decision_summary"] = {
            "region": result.get("region"),
            "city": result.get("city"),
            "intent": result.get("intent"),
            "occasion": result.get("occasion"),
            "retrieved_evidence": len(
                result.get("retrieved", [])
            ),
            "validated_evidence": len(
                result.get("validated", [])
            ),
            "confidence_score": confidence,
            "validation_status": result.get(
                "status",
                "pending",
            ),
            "decision": agent_decision,
        }

        memory_fields = {
            "city": result.get("city"),
            "destination": result.get("city"),
            "region": result.get("region"),
            "user_role": result.get("user_role"),
            "occasion": result.get("occasion"),
            "category": result.get("category"),
            "situation": result.get("situation"),
            "relationship": result.get("relationship"),
            "first_time": result.get("first_time"),
            "generation": result.get("generation"),
            "formality": result.get("formality"),
            "historical_or_contemporary": result.get(
                "historical_or_contemporary"
            ),
            "language": result.get("language"),
            "topics_discussed": result.get("category"),
        }
        memory.update_context(memory_fields)

        latency = start_timer() - start_time

        record_run(
            query=query,
            result=result,
            latency_seconds=latency,
        )

        return result

    except Exception as exc:
        latency = start_timer() - start_time

        record_run(
            query=query,
            result={},
            latency_seconds=latency,
            error=str(exc),
        )

        raise


# from __future__ import annotations

# from langgraph.graph import END, START, StateGraph

# from agents.state import AseelState
# from agents.understanding import understand_context
# from agents.retrieval_agent import retrieve_knowledge
# from agents.validation import validate_cultural_knowledge, refine_query
# from agents.response import generate_response

# from utils.monitoring import start_timer, record_run
# from memory.conversation_memory import ConversationMemory


# # ============================================================
# # ROUTING
# # ============================================================

# def route_after_validation(state: AseelState) -> str:
#     confidence = state.get("confidence_score", 0.0)
#     attempts = state.get("attempts", 0)

#     # PASS
#     if confidence >= 0.50:
#         return "respond"

#     # First failure → retry retrieval
#     if attempts < 1:
#         return "refine"

#     # Second failure → response safety fallback
#     return "respond"


# # ============================================================
# # BUILD WORKFLOW
# # ============================================================

# def build_workflow():
#     graph = StateGraph(AseelState)

#     graph.add_node("understand", understand_context)
#     graph.add_node("retrieve", retrieve_knowledge)
#     graph.add_node("validate", validate_cultural_knowledge)
#     graph.add_node("refine", refine_query)
#     graph.add_node("respond", generate_response)

#     # Main flow
#     graph.add_edge(START, "understand")
#     graph.add_edge("understand", "retrieve")
#     graph.add_edge("retrieve", "validate")

#     # Validation routing
#     graph.add_conditional_edges(
#         "validate",
#         route_after_validation,
#         {
#             "respond": "respond",
#             "refine": "refine",
#         },
#     )

#     # Retry flow
#     graph.add_edge("refine", "retrieve")

#     # End
#     graph.add_edge("respond", END)

#     return graph.compile()


# # Build the workflow once.
# workflow = build_workflow()


# # ============================================================
# # MAIN ENTRY POINT
# # ============================================================

# def ask(
#     query: str,
#     conversation_context: str = "",
#     memory: ConversationMemory | None = None,
# ) -> dict:

#     start_time = start_timer()

#     # Create memory if none was provided.
#     if memory is None:
#         memory = ConversationMemory()

#     try:

#         # ----------------------------------------------------
#         # 1. GET EXISTING MEMORY
#         # ----------------------------------------------------

#         memory_context = memory.to_prompt_context()

#         combined_context = ""

#         if memory_context:
#             combined_context += (
#                 "Conversation memory:\n"
#                 f"{memory_context}\n\n"
#             )

#         if conversation_context:
#             combined_context += (
#                 "Recent conversation:\n"
#                 f"{conversation_context}"
#             )

#         # ----------------------------------------------------
#         # 2. RUN ASEEL WORKFLOW
#         # ----------------------------------------------------

#         result = workflow.invoke(
#             {
#                 "query": query,
#                 "conversation_context": combined_context,
#                 "attempts": 0,
#             }
#         )

#         # ----------------------------------------------------
#         # 3. UPDATE CONVERSATION MEMORY
#         # ----------------------------------------------------

#         memory_fields = {
#             "city": result.get("city"),
#             "region": result.get("region"),
#             "occasion": result.get("occasion"),
#             "situation": result.get("situation"),
#             "relationship": result.get("relationship"),
#             "first_time": result.get("first_time"),
#             "formality": result.get("formality"),
#             "generation": result.get("generation"),
#             "historical_or_contemporary": result.get(
#                 "historical_or_contemporary"
#             ),
#             "language": result.get("language"),
#         }

#         memory.update_context(memory_fields)

#         # ----------------------------------------------------
#         # 4. MONITORING
#         # ----------------------------------------------------

#         latency = start_timer() - start_time

#         record_run(
#             query=query,
#             result=result,
#             latency_seconds=latency,
#         )

#         # ----------------------------------------------------
#         # 5. RETURN RESULT
#         # ----------------------------------------------------

#         return result

#     except Exception as exc:

#         # Measure failed request latency.
#         latency = start_timer() - start_time

#         record_run(
#             query=query,
#             result={},
#             latency_seconds=latency,
#             error=str(exc),
#         )

#         raise

