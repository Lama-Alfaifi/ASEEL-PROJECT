from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from workflow.graph import ask


app = FastAPI(
    title="ASEEL API",
    description="Saudi cultural etiquette guidance API",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str
    conversation_context: str = ""


class ChatResponse(BaseModel):
    answer: str
    status: str
    confidence_score: float
    sources: list[dict]


@app.get("/")
def root():
    return {
        "message": "ASEEL API is running"
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = ask(
        request.message,
        request.conversation_context,
    )

    return {
        "answer": result.get("answer", ""),
        "status": result.get("status", "fallback"),
        "confidence_score": result.get("confidence_score", 0.0),
        "sources": result.get("sources", []),
    }