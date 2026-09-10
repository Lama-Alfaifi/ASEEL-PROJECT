from __future__ import annotations
from config.settings import MIN_RELEVANCE

def validate_evidence(records: list[dict], requested_region: str | None) -> tuple[list[dict], str]:
    """Return records meeting the relevance threshold and regional scope."""
    valid = [record for record in records if record["relevance"] >= MIN_RELEVANCE and (not requested_region or record["region"] in (requested_region, "General"))]
    if not valid:
        return [], "No sufficiently relevant, region-compatible knowledge record was found."
    return valid, "Retrieved evidence meets relevance and regional-scope requirements."