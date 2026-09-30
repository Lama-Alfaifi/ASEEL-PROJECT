from __future__ import annotations

from retrieval.vector_store import CulturalVectorStore


def filter_by_metadata(
    records: list[dict],
    region: str | None,
    category: str | None = None,
) -> list[dict]:
    """Apply deterministic region filtering and optional category preference."""

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

    # Category is only a preference.
    # Do not remove semantically relevant General/Unspecified evidence
    # when the category classifier is uncertain or overly broad.
    if category:
        category_matches = [
            record
            for record in filtered
            if record.get("category") == category
        ]

        if category_matches:
            non_matches = [
                record
                for record in filtered
                if record.get("category") != category
            ]

            filtered = category_matches + non_matches

    return filtered