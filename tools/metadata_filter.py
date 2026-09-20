from __future__ import annotations

from retrieval.vector_store import CulturalVectorStore


def filter_by_metadata(
    records: list[dict],
    region: str | None,
    category: str | None = None,
    city: str | None = None,
) -> list[dict]:
    """Apply deterministic region/category filtering after semantic search."""

    filtered = records

    if region:
        normalized_region = CulturalVectorStore.normalize_region(region)

        filtered = [
            record
            for record in filtered
            if (
                CulturalVectorStore.normalize_region(record.get("region"))
                == normalized_region
                or record.get("region") == "General"
            )
        ]

    if category:
        category_matches = [
            record
            for record in filtered
            if record.get("category") == category
        ]

        if category_matches:
            filtered = category_matches

    return filtered