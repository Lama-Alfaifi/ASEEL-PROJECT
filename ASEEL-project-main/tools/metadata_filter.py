from __future__ import annotations

def filter_by_metadata(records: list[dict], region: str | None, category: str | None = None) -> list[dict]:
    """Apply deterministic region/category filtering after semantic search."""
    filtered = records
    if region:
        filtered = [record for record in filtered if record["region"] == region or record["region"] == "General"]
    if category:
        category_matches = [record for record in filtered if record.get("category") == category]
        if category_matches:
            filtered = category_matches
    return filtered