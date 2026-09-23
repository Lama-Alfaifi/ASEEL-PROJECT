from __future__ import annotations

from typing import Literal, TypedDict


class AseelState(TypedDict, total=False):
    query: str
    conversation_context: str

    city: str | None
    region: str | None

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