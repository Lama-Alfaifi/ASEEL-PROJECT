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

    location = location_resolver.find_in_query(query)

    # An explicitly-provided region (e.g. resolved earlier by the
    # Understanding Agent from conversation memory on a follow-up question)
    # always wins. We only fall back to a city detected in THIS query's
    # text when no region was provided at all. Previously a detected city
    # silently overwrote an already-correct region, and on follow-ups with
    # no city mention ("What about women?") the region could end up unset,
    # causing an unfiltered, noisy search.
    resolved_region = region or ""

    if not resolved_region and location:
        resolved_region = location["planning_region"]

    # Normalize once, here, so every downstream comparison (metadata
    # filter, evidence validation) works against the same canonical
    # region names regardless of whether the region came from the
    # regex-based resolver ("East") or the CSV-based one ("Eastern").
    resolved_region = CulturalVectorStore.normalize_region(resolved_region) or ""

    # 3. Search the existing cultural knowledge base
    results = store.search(
        query=query,
        region=resolved_region or None,
        limit=TOP_K,
    )

    # 4. No results
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

    # 5. Format retrieved knowledge
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