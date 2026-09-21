from __future__ import annotations
from config.settings import MIN_RELEVANCE


# Maximum number of evidence records passed to the Response Agent.
MAX_EVIDENCE = 3


def validate_evidence(
    records: list[dict],
    requested_region: str | None,
) -> tuple[list[dict], str, float]:
    """
    Validate retrieved cultural evidence.

    Rules:
    - Evidence must meet MIN_RELEVANCE.
    - Evidence must match the requested region when a region is provided.
    - Only the strongest MAX_EVIDENCE records are returned.
    - Confidence is based on the strongest valid record.
    """

    valid = [
        record
        for record in records
        if (
            record["relevance"] >= MIN_RELEVANCE
            and (
                not requested_region
                or record["region"] == requested_region
            )
        )
    ]

    if not valid:
        return (
            [],
            "No sufficiently relevant, region-specific knowledge record was found.",
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