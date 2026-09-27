from __future__ import annotations

from typing import Literal, TypedDict


class AseelState(TypedDict, total=False):
    query: str
    conversation_context: str

    city: str | None
    region: str | None
    # Explicit UI region selection (canonical: Central/West/East/South/North/General).
    # None means "Auto". "General" is an explicit choice (nationwide records), NOT
    # "no region": like any other explicit selection it ignores memory, the
    # remembered city and the detected location for that request.
    region_override: str | None

    # Automatically detected user location, {"city", "region"} only (never
    # coordinates). Used by the Understanding Agent as the LOWEST-priority fallback.
    user_location: dict | None
    # Where city/region came from: "ui_selection" | "query" | "memory" | "user_location" | None
    location_source: str | None

    user_role: str | None
    occasion: str | None
    category: str | None
    situation: str | None
    relationship: str | None
    first_time: str | None
    generation: str | None
    formality: str | None
    historical_or_contemporary: str | None
    language: str | None

    intent: str | None
    retrieval_query: str

    attempts: int
    decision: str

    retrieved: list[dict]
    raw_semantic_results: list[dict]

    validated: list[dict]
    validation_reason: str
    confidence_score: float
    status: Literal["pending", "grounded", "fallback"]

    answer: str
    sources: list[dict]