from __future__ import annotations

import json

from langchain.agents import create_agent

from agents.state import AseelState
from config.settings import OPENAI_MODEL
from tools.cultural_search import search_cultural_knowledge
from tools.metadata_filter import filter_by_metadata


retrieval_agent = create_agent(
    model=OPENAI_MODEL,
    tools=[search_cultural_knowledge],
    system_prompt="""
You are ASEEL's Retrieval Agent.

Your job is to search the cultural knowledge base and select the most
relevant evidence for downstream validation and response generation.

You must NOT answer the user's question.

RETRIEVAL WORKFLOW:

1. Understand the Query
- Identify the main topic, intent, situation, and location.
- Pay attention to city-specific information.
- Preserve the meaning of the user's question.

2. Location Awareness
- Respect the requested city and region.
- If a city is provided, prefer evidence related to that city.
- If city-specific evidence is unavailable, relevant evidence from the
  corresponding region may be used.
- Do not use evidence from an unrelated region.

3. Search
- ALWAYS use the search_cultural_knowledge tool.
- Use the provided user query as the search query.
- Search up to TWO times.
- If the first search results are insufficient or unrelated, refine the
  query and perform one additional search.
- Review all results returned by the tool.

4. Evidence Selection
After receiving the search results, select the results that are relevant
to the user's question.

A result can be selected when:
- It directly answers the question, OR
- It provides useful supporting evidence for the question.

For example, if the user asks about traditional hospitality, relevant
evidence about guests, serving food, coffee, greetings, majalis, or
hospitality etiquette can be selected.
For hospitality questions:
- Prefer evidence explicitly related to hospitality, guests, hosting,
  serving food, coffee, greetings, majalis, or etiquette.
- Do NOT select clothing, crafts, tools, or other unrelated categories
  unless the user explicitly asks about them.
- Regional relevance alone is not enough to select an evidence record.
Do NOT select a result only because:
- It belongs to the same region.
- It contains a similar word.
- It is culturally interesting but unrelated to the question.

Do NOT select unrelated clothing, crafts, food, or other records unless
they meaningfully support the user's question.

5. Query Refinement
If the first search results are insufficient:
- Create a more specific query using important concepts from the user's question.
- Preserve the original intent, city, and region.
- For hospitality questions, concepts such as guests, serving food,
  coffee, greetings, hosting, or majalis may be used.
- Do not introduce unsupported cultural facts.

6. Grounding
- Use only evidence returned by the search tool.
- Never invent cultural information.
- Never use outside knowledge.
- Never create a new cultural claim by combining unrelated records.

7. Output
Return ONLY the selected result numbers.

Use 1-based numbering according to the order of the search results.

Example:

SELECTED: 1,3

If no result is relevant:

SELECTED: NONE

Do not return explanations.
Do not return the evidence.
Do not answer the user's question.
""",
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
- Search the knowledge base using the provided query.
- You may perform a second search only if the first search does not
  provide relevant evidence.
- Keep the original topic, city, and region.

First search query:
{query}

If the first search results are insufficient:
- Refine the query using important concepts from the user's question.
- Keep the city and region.
- Do not change the topic.
- Search again using the refined query.

After receiving the results:
- Review every result.
- Select results that directly answer the question OR provide meaningful
  supporting evidence.
- If the question is about hospitality, relevant evidence about guests,
  serving food, coffee, greetings, majalis, or etiquette may be selected.
- Do not select results merely because they belong to the same region.
- Do not select unrelated clothing or other cultural topics.
- Do not invent information.

Return ONLY:

SELECTED: 1,3

or:

SELECTED: NONE
"""

    result = retrieval_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": agent_input,
                }
            ]
        }
    )
   
    messages = result.get("messages", [])

    records = []

    # Collect results returned by the search tool
    for message in messages:
        if getattr(message, "type", None) == "tool":
            try:
                tool_data = json.loads(message.content)
                records.extend(tool_data.get("results", []))
            except (json.JSONDecodeError, TypeError):
                continue

    # Apply existing deterministic metadata filtering
    filtered_records = filter_by_metadata(
        records,
        state.get("region"),
        state.get("category"),
        state.get("city"),
    )

    # Read the Retrieval Agent's selection
    selected_indices = None

    for message in reversed(messages):
        if getattr(message, "type", None) == "tool":
            continue

        content = getattr(message, "content", "")

        if not content:
            continue

        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        content = str(content).strip()

        if "SELECTED:" not in content:
            continue

        selected_part = content.split(
            "SELECTED:",
            1,
        )[1].strip()

        if selected_part.upper() == "NONE":
            selected_indices = []
        else:
            try:
                selected_indices = [
                    int(index.strip()) - 1
                    for index in selected_part.split(",")
                    if index.strip().isdigit()
                ]
            except ValueError:
                selected_indices = []

        break

    # If the agent returned no selection, keep no records.
    if selected_indices is None:
        selected_indices = []

    # Keep only the records selected by the Retrieval Agent
    selected_records = [
        filtered_records[index]
        for index in selected_indices
        if 0 <= index < len(filtered_records)
    ]
    # Remove duplicate knowledge records from the final selection
    unique_selected_records = []
    seen_questions = set()

    for record in selected_records:
        question_key = record.get("question", "").strip().lower()

        if question_key and question_key not in seen_questions:
            seen_questions.add(question_key)
            unique_selected_records.append(record)

    selected_records = unique_selected_records
    return {
        "raw_semantic_results": records,
        "retrieved": selected_records,
    }