from __future__ import annotations

from typing import Literal, TypedDict


class AseelState(TypedDict, total=False):
    query: str
    conversation_context: str
    region: str | None
    user_role: str | None
    occasion: str | None
    category: str | None
    intent: str
    retrieval_query: str
    attempts: int
    retrieved: list[dict]
    raw_semantic_results: list[dict]
    validated: list[dict]
    validation_reason: str
    confidence_score: float
    status: Literal["pending", "grounded", "fallback"]
    answer: str
    sources: list[dict]