from __future__ import annotations
from config.settings import MIN_RELEVANCE
from retrieval.vector_store import CulturalVectorStore


# Maximum number of evidence records passed to the Response Agent.
MAX_EVIDENCE = 3

# When no region is resolved for the query (region=None), the region filter
# in the comprehension below provides NO protection at all — any record in
# the entire knowledge base, regardless of topic, can pass just by clearing
# MIN_RELEVANCE. Empirically (see data/relevance_results.csv, a 357-question
# benchmark run with correct region filtering applied), even the WEAKEST
# genuine match against its correct region scores 0.58. A completely
# off-topic query ("Saudi space station etiquette") with no region scored
# 0.5885 — inside the normal range for real evidence — while genuine
# region-less questions ("Saudi wedding practices", "visiting a Saudi
# family") scored 0.65-0.72. NO_REGION_MIN_RELEVANCE sits between those two
# clusters, so it only blocks the unprotected, off-topic case without
# rejecting legitimate general questions that happen to have no city/region.
NO_REGION_MIN_RELEVANCE = 0.60


def validate_evidence(
    records: list[dict],
    requested_region: str | None,
) -> tuple[list[dict], str, float]:
    """
    Validate retrieved cultural evidence.

    Rules:
    - Evidence must match the requested region OR be General/nationwide when a region is provided,
      after normalization (see module docstring in cultural_search.py for
      why raw string comparison is unsafe here).
    - Evidence must clear MIN_RELEVANCE when a region was resolved (the
      region filter itself is the main defense against unrelated matches
      in that case), or the stricter NO_REGION_MIN_RELEVANCE when no
      region was resolved (there's no region filter to fall back on, so
      relevance alone has to do that job).
    - Only the strongest MAX_EVIDENCE records are returned.
    - Confidence is based on the strongest valid record.
    """

    normalized_requested_region = (
        CulturalVectorStore.normalize_region(requested_region)
        if requested_region
        else None
    )

    relevance_threshold = (
        MIN_RELEVANCE
        if normalized_requested_region
        else NO_REGION_MIN_RELEVANCE
    )

    valid = [
        record
        for record in records
        if (
            record["relevance"] >= relevance_threshold
            and (
                not normalized_requested_region
                or CulturalVectorStore.normalize_region(record.get("region"))
                in (normalized_requested_region, "General")
            )
        )
    ]

    if not valid:
        return (
            [],
            "No sufficiently relevant, region-compatible knowledge record was found.",
            0.0,
        )

    # Strongest evidence first.
    valid.sort(
        key=lambda record: record["relevance"],
        reverse=True,
    )

    # Keep only the strongest evidence.
    validated = valid[:MAX_EVIDENCE]

    # Confidence represents the strongest retrieved evidence.
    confidence_score = validated[0]["relevance"]

    return (
        validated,
        "Retrieved evidence meets relevance and regional-scope requirements.",
        round(confidence_score, 2),
    )

# from __future__ import annotations

# from config.settings import MIN_RELEVANCE


# def validate_evidence(
#     records: list[dict],
#     requested_region: str | None,
# ) -> tuple[list[dict], str, float]:
#     """Validate evidence and calculate a retrieval confidence score."""

#     valid = [
#         record
#         for record in records
#         if (
#             record["relevance"] >= MIN_RELEVANCE
#             and (
#                 not requested_region
#                 or record["region"] in (requested_region, "General")
#             )
#         )
#     ]

#     if not valid:
#         return (
#             [],
#             "No sufficiently relevant, region-compatible knowledge record was found.",
#             0.0,
#         )

#     confidence_score = max(
#         record["relevance"] for record in valid
#     )

#     return (
#         valid,
#         "Retrieved evidence meets relevance and regional-scope requirements.",
#         round(confidence_score, 2),
#     )