from __future__ import annotations

import json

from langchain_core.tools import tool

from config.settings import TOP_K
from retrieval.vector_store import CulturalVectorStore
from utils.location_resolver import location_resolver


store = CulturalVectorStore()


@tool
def search_cultural_knowledge(query: str, region: str = "") -> str:
    """Search the Saudi cultural knowledge base for relevant cultural evidence."""

    # ---------------------------------------------------------
    # 1. Detect a city/place from the user's question
    # ---------------------------------------------------------
    location = location_resolver.find_in_query(query)

    # ---------------------------------------------------------
    # 2. Use the detected planning region
    # ---------------------------------------------------------
    resolved_region = region or ""

    if location:
        resolved_region = location["planning_region"]

    # ---------------------------------------------------------
    # 3. Search the existing cultural knowledge base
    # ---------------------------------------------------------
    results = store.search(
        query=query,
        region=resolved_region or None,
        limit=TOP_K,
    )

    # Remove duplicate knowledge records
    unique_results = []
    seen_questions = set()

    for result in results:
        question_key = result.record.question.strip().lower()

        if question_key not in seen_questions:
            seen_questions.add(question_key)
            unique_results.append(result)

    results = unique_results

    # ---------------------------------------------------------
    # 4. No results
    # ---------------------------------------------------------
    if not results:
        return json.dumps(
            {
                "results": [],
                "message": "No relevant cultural knowledge was found.",
                "location": location,
                "resolved_region": resolved_region or None,
            },
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # 5. Format retrieved knowledge
    # ---------------------------------------------------------
    records = [
        {
            "question": result.record.question,
            "answer": result.record.answer,
            "choices": result.record.choices,
            "region": result.record.region,
            "domain": result.record.domain,
            "category": result.record.category,
            "relevance": result.relevance,
            "distance": result.distance,
        }
        for result in results
    ]

    return json.dumps(
        {
            "results": records,
            "location": location,
            "resolved_region": resolved_region or None,
        },
        ensure_ascii=False,
    )