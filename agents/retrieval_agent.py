from __future__ import annotations

from langchain.agents import create_agent
from agents.state import AseelState
from config.settings import OPENAI_MODEL
from tools.cultural_search import search_cultural_knowledge
from tools.metadata_filter import filter_by_metadata
import json


retrieval_agent = create_agent(
    model=OPENAI_MODEL,
    tools=[search_cultural_knowledge],
    system_prompt="""
You are ASEEL's Retrieval Agent.

Your job is to retrieve reliable Saudi cultural knowledge
from the cultural knowledge base.

Rules:
- Use the search_cultural_knowledge tool to find relevant evidence.
- Consider the user's region and category when available.
- Do not invent cultural facts.
- Prefer relevant and specific evidence.
- Return the retrieved evidence clearly.
"""
)


def retrieve_knowledge(state: AseelState) -> dict:
    query = state["retrieval_query"]
    region = state.get("region") or ""
    category = state.get("category")

    agent_input = f"""
User query: {query}
Region: {region}
Category: {category or "Not specified"}

Use the search_cultural_knowledge tool.

IMPORTANT:
- Use the User query EXACTLY as the search query.
- Do not rewrite or summarize the query.
- Pass the region exactly as provided.
- Search the knowledge base once.
- Return the retrieved evidence.
"""

    result = retrieval_agent.invoke(
        {
            "messages": [
                {"role": "user", "content": agent_input}
            ]
        }
    )

    messages = result.get("messages", [])

    records = []

    for message in messages:
        if getattr(message, "type", None) == "tool":
            try:
                tool_data = json.loads(message.content)
                records.extend(tool_data.get("results", []))
            except (json.JSONDecodeError, TypeError):
                continue

    filtered_records = filter_by_metadata(
        records,
        state.get("region"),
        state.get("category"),
    )

    return {
        "raw_semantic_results": records,
        "retrieved": filtered_records,
    }