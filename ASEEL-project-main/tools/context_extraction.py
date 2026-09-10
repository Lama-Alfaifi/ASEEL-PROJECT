from __future__ import annotations

import re

ROLES = ("tourist", "visitor", "resident", "student", "expat")
OCCASIONS = ("majlis", "wedding", "restaurant", "meal", "dinner", "meeting", "campus", "celebration", "social gathering", "gathering", "visit")
CATEGORIES = {
    "Food": ("food", "dish", "eat", "meal", "dinner", "lunch", "restaurant"),
    "Clothes": ("clothes", "clothing", "dress", "wear"),
    "Celebration": ("wedding", "celebration", "festival", "occasion", "social gathering", "social event", "gathering"),
    "Language & Communication": ("language", "speak", "greeting", "communication"),
}

def _match(options: tuple[str, ...], text: str) -> str | None:
    return next((item.title() for item in options if re.search(rf"\b{re.escape(item)}\b", text, re.IGNORECASE)), None)

def extract_context(query: str, conversation_context: str = "") -> dict[str, str | None]:
    """Extract non-cultural user context for the shared workflow state."""
    text = f"{conversation_context} {query}"
    category = next((name for name, terms in CATEGORIES.items() if any(re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE) for term in terms)), None)
    return {"user_role": _match(ROLES, text), "occasion": _match(OCCASIONS, text), "category": category, "intent": "cultural etiquette guidance", "retrieval_query": query}