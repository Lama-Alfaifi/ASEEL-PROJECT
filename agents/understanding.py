from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.tools import tool

from agents.state import AseelState
from config.settings import OPENAI_MODEL
from tools.context_extraction import extract_context
from tools.region_resolution import resolve_region


@tool
def extract_user_context(query: str, conversation_context: str = "") -> dict:
    """Extract cultural context such as occasion, user role, category, and intent from the user's query."""
    return extract_context(query, conversation_context)


@tool
def resolve_user_region(query: str) -> str | None:
    """Resolve the Saudi region mentioned or implied by the user's query."""
    return resolve_region(query)


understanding_agent = create_agent(
    model=OPENAI_MODEL,
    tools=[
        extract_user_context,
        resolve_user_region,
    ],
    system_prompt="""
You are ASEEL's Understanding Agent.

Your job is to understand the user's cultural question before retrieval.

You must:
- Use the context extraction tool to identify relevant context.
- Use the region resolution tool to identify the Saudi region when possible.
- Do not invent missing information.
- Preserve the user's original intent.
- Return the extracted context clearly.
""",
)


def understand_context(state: AseelState) -> dict:
    query = state["query"]
    conversation_context = state.get("conversation_context", "")

    result = understanding_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Understand this ASEEL user request.

User query:
{query}

Conversation context:
{conversation_context or "None"}

Use the available tools to extract the context and resolve the region.
""",
                }
            ]
        }
    )

    messages = result.get("messages", [])

    extracted_context = {}
    region = None

    for message in messages:
        if getattr(message, "type", None) != "tool":
            continue

        tool_name = getattr(message, "name", "")

        if tool_name == "extract_user_context":
            content = message.content

            if isinstance(content, dict):
                extracted_context = content
            else:
                try:
                    import json
                    extracted_context = json.loads(content)
                except (TypeError, ValueError):
                    pass

        elif tool_name == "resolve_user_region":
            content = message.content
            region = content if content else None

    return {
        **extracted_context,
        "region": region,
        "attempts": state.get("attempts", 0),
        "retrieval_query": query,
    }