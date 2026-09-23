"""
Development stand-in for the ASEEL API (same contract as main.py).

Use it to work on the UI without an OpenAI key or a built vector store:

    pip install fastapi uvicorn
    uvicorn scripts.mock_api:app --port 8000

All text is clearly labelled placeholder content. It contains no cultural claims;
real answers only ever come from your ASEEL backend.
"""
from __future__ import annotations

import asyncio
import random

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ASEEL mock API")

REGION_WORDS = {
    "South": ["south", "abha", "jazan", "najran", "asir", "bahah"],
    "North": ["north", "tabuk", "hail", "sakaka", "jawf"],
    "East": ["east", "dammam", "ahsa", "hofuf", "khobar"],
    "West": ["west", "jeddah", "makkah", "mecca", "madinah", "medina", "hejaz"],
    "Central": ["central", "riyadh", "buraydah", "najd", "qassim"],
}
CATEGORIES = ["Hospitality", "Dining", "Greetings", "Occasions", "Dress", "Gifts"]


class ChatRequest(BaseModel):
    message: str
    conversation_context: str = ""


class ChatResponse(BaseModel):
    answer: str
    status: str
    confidence_score: float
    sources: list[dict]


def detect_region(text: str) -> str | None:
    low = text.lower()
    for region, words in REGION_WORDS.items():
        if any(w in low for w in words):
            return region
    return None


@app.get("/")
def root():
    return {"message": "ASEEL API is running (mock)"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    await asyncio.sleep(random.uniform(1.5, 3.0))
    q = req.message.strip()
    if "error500" in q.lower():
        raise RuntimeError("mock failure")
    region = detect_region(q)

    if "xyzzy" in q.lower() or (region is None and "general" not in q.lower() and "saudi" not in q.lower() and "how" not in q.lower() and "what" not in q.lower()):
        return {
            "answer": "I could not find enough reliable cultural evidence in the ASEEL knowledge base to answer this question confidently.",
            "status": "fallback",
            "confidence_score": 0.31,
            "sources": [],
        }

    region_name = region or "General"
    sources = [
        {
            "region": region_name,
            "domain": "etiquette",
            "category": CATEGORIES[i % len(CATEGORIES)],
            "question": f"[Mock entry {i + 1}] Sample knowledge-base question for {region_name}",
            "answer": (
                f"[Placeholder text] This stands in for a real knowledge-base entry #{i + 1} for the {region_name} region. "
                "It exists only so the interface can be developed offline. " + "Lorem ipsum dolor sit amet. " * (i + 1)
            ),
            "relevance": round(0.82 - i * 0.09, 2),
            "distance": round(0.35 + i * 0.1, 2),
        }
        for i in range(3)
    ]
    answer = (
        f"**[Mock answer]** You asked: _{q[:140]}_\n\n"
        f"This is placeholder text returned by the development mock, resolved to the **{region_name}** region.\n\n"
        "- The real ASEEL backend would summarise validated evidence here.\n"
        "- Each supporting entry appears under **Evidence**.\n"
        "- Context received: " + (f"{len(req.conversation_context)} characters" if req.conversation_context else "none")
    )
    return {"answer": answer, "status": "grounded", "confidence_score": round(random.uniform(0.58, 0.93), 2), "sources": sources}
