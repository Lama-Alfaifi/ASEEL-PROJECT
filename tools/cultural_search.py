from __future__ import annotations

import json

from langchain_core.tools import tool

from config.settings import TOP_K
from retrieval.vector_store import CulturalVectorStore


store = CulturalVectorStore()


@tool
def search_cultural_knowledge(query: str, region: str = "") -> str:
    """Search the Saudi cultural knowledge base for relevant cultural evidence."""

    results = store.search(
        query=query,
        region=region or None,
        limit=TOP_K,
    )

    if not results:
        return json.dumps({
            "results": [],
            "message": "No relevant cultural knowledge was found."
        })

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

    return json.dumps({
        "results": records
    }, ensure_ascii=False)