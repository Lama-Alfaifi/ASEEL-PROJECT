from __future__ import annotations

import uuid

from fastapi import FastAPI
from pydantic import BaseModel

from workflow.graph import ask
from memory.conversation_memory import ConversationMemory
from utils.monitoring import (
    get_metrics,
    get_failure_patterns,
)


app = FastAPI(
    title="ASEEL API",
    description="Saudi cultural etiquette guidance API",
    version="1.0.0",
)


_session_memories: dict[str, ConversationMemory] = {}


class ChatRequest(BaseModel):
    message: str
    conversation_context: str = ""
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    status: str
    confidence_score: float
    sources: list[dict]
    session_id: str


@app.get("/")
def root():
    return {
        "message": "ASEEL API is running"
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):

    session_id = (
        request.session_id
        or str(uuid.uuid4())
    )

    memory = _session_memories.setdefault(
        session_id,
        ConversationMemory(),
    )

    result = ask(
        request.message,
        request.conversation_context,
        memory=memory,
    )

    return {
        "answer": result.get(
            "answer",
            "",
        ),
        "status": result.get(
            "status",
            "fallback",
        ),
        "confidence_score": result.get(
            "confidence_score",
            0.0,
        ),
        "sources": result.get(
            "sources",
            [],
        ),
        "session_id": session_id,
    }


@app.delete(
    "/chat/{session_id}"
)
def reset_session(session_id: str):

    if session_id in _session_memories:
        _session_memories[
            session_id
        ].clear_context()

    return {
        "message": "Session memory cleared",
        "session_id": session_id,
    }


@app.get("/metrics")
def metrics():
    return get_metrics()


@app.get("/metrics/failures")
def failure_patterns():
    return get_failure_patterns()
