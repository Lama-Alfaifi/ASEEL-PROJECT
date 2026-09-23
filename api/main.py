from __future__ import annotations

import uuid

from fastapi import FastAPI
from pydantic import BaseModel, Field

from workflow.graph import ask
from memory.conversation_memory import ConversationMemory
from utils.monitoring import get_metrics, get_failure_patterns

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config.settings import ROOT_DIR
from utils.region_geography import load_regions
from utils.user_location import normalize_user_location, resolve_coordinates

from utils.feedback_store import (
    save_feedback,
    list_feedback,
    get_feedback,
    set_status,
)



app = FastAPI(
    title="ASEEL API",
    description="Saudi cultural etiquette guidance API",
    version="1.0.0",
)



# Session memory store

# Without this, ask() would receive memory=None on every call and build a
# fresh ConversationMemory that gets discarded as soon as the request ends —
# follow-up questions ("what about women?") would never have context.
#
# NOTE: this is a process-local, in-memory dict. It resets on restart and is
# NOT shared across multiple workers/instances. Fine for a single-process
# dev/demo deployment. For production (multiple workers, autoscaling), swap
# this for a shared store (e.g. Redis: session_id -> serialized context via
# memory.get_context() / memory.update_context()) without changing the
# /chat logic below.
_session_memories: dict[str, ConversationMemory] = {}


class UserLocation(BaseModel):
    # Coordinates are optional: the web client resolves them via POST /locate and
    # then sends only city/region. If coordinates ARE sent they are resolved and
    # discarded before the workflow runs.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    city: str | None = None
    region: str | None = None


class ChatRequest(BaseModel):
    message: str
    conversation_context: str = ""
    session_id: str | None = None
    user_location: UserLocation | None = None
    # Explicit region chip from the UI (central/west/east/south/north/general).
    # Omitted / null = "Auto". Without this field FastAPI silently dropped the
    # `region` the frontend sends, so the selection never reached the workflow.
    region: str | None = None


class ChatResponse(BaseModel):
    answer: str
    status: str
    confidence_score: float
    sources: list[dict]
    session_id: str
    city: str | None = None
    region: str | None = None


@app.get("/")
def root():
    return {
        "message": "ASEEL API is running"
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # First message of a new conversation: client sends no session_id,
    # we mint one and hand it back so the client can reuse it for follow-ups.
    session_id = request.session_id or str(uuid.uuid4())

    memory = _session_memories.setdefault(session_id, ConversationMemory())

    # Lowest-priority location fallback. Reduced to {city, region}; coordinates
    # never reach the workflow state or monitoring.
    raw_location = None
    if request.user_location is not None:
        loc = request.user_location
        raw_location = loc.model_dump() if hasattr(loc, "model_dump") else loc.dict()

    result = ask(
        request.message,
        request.conversation_context,
        memory=memory,
        user_location=normalize_user_location(raw_location),
        region_override=request.region,
    )

    return {
        "answer": result.get("answer", ""),
        "status": result.get("status", "fallback"),
        "confidence_score": result.get("confidence_score", 0.0),
        "sources": result.get("sources", []),
        "session_id": session_id,
        "city": result.get("city"),
        "region": result.get("region"),
    }


class LocateRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@app.post("/locate")
def locate(request: LocateRequest):
    """
    Browser coordinates -> {"city", "region"} using the project's own region
    data. Coordinates are used for this lookup only: not stored, not logged,
    not echoed back. Both fields are null outside Saudi Arabia.
    """
    return resolve_coordinates(request.latitude, request.longitude)


@app.delete("/chat/{session_id}")
def reset_session(session_id: str):
    """Clear a conversation's remembered context (e.g. user starts a new chat)."""
    if session_id in _session_memories:
        _session_memories[session_id].clear_context()

    return {
        "message": "Session memory cleared",
        "session_id": session_id,
    }



# Monitoring endpoints
# Surfaces what utils/monitoring.py is already recording in monitoring.jsonl.


@app.get("/metrics")
def metrics():
    return get_metrics()


@app.get("/metrics/failures")
def failure_patterns():
    return get_failure_patterns()

@app.get("/regions-geojson")
def regions_geojson():
    """Serves the raw region boundaries for the frontend map."""
    path = ROOT_DIR / "data" / "regions.geojson"

    if not path.exists():
        return {"error": "regions.geojson not found"}

    return FileResponse(path, media_type="application/json")


@app.get("/regions-mapping")
def regions_mapping():
    """
    Serves the same administrative-region -> planning-region mapping used
    internally (utils/region_geography.py), so the frontend colors the map
    using the exact same logic as the backend rather than duplicating it
    in JavaScript.
    """
    _, mapping = load_regions()
    return mapping

class FeedbackRequest(BaseModel):
    type: str
    message: str
    city: str | None = None
    region: str | None = None
    category: str | None = None
    original_query: str | None = None
    original_answer: str | None = None


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    record = save_feedback(
        feedback_type=request.type,
        message=request.message,
        city=request.city,
        region=request.region,
        category=request.category,
        original_query=request.original_query,
        original_answer=request.original_answer,
    )

    return record


@app.get("/feedback")
def get_all_feedback(status: str | None = None):
    return list_feedback(status=status)


@app.post("/feedback/{feedback_id}/approve")
def approve_feedback(feedback_id: str):
    record = set_status(feedback_id, "approved")
    return record if record else {"error": "not found"}


@app.post("/feedback/{feedback_id}/reject")
def reject_feedback(feedback_id: str):
    record = set_status(feedback_id, "rejected")
    return record if record else {"error": "not found"}

# Serves the static frontend at http://localhost:8000/ui/
app.mount(
    "/ui",
    StaticFiles(directory=str(ROOT_DIR / "web"), html=True),
    name="ui",
)










# from __future__ import annotations

# from fastapi import FastAPI
# from pydantic import BaseModel

# from workflow.graph import ask


# app = FastAPI(
#     title="ASEEL API",
#     description="Saudi cultural etiquette guidance API",
#     version="1.0.0",
# )


# class ChatRequest(BaseModel):
#     message: str
#     conversation_context: str = ""


# class ChatResponse(BaseModel):
#     answer: str
#     status: str
#     confidence_score: float
#     sources: list[dict]


# @app.get("/")
# def root():
#     return {
#         "message": "ASEEL API is running"
#     }


# @app.post("/chat", response_model=ChatResponse)
# def chat(request: ChatRequest):
#     result = ask(
#         request.message,
#         request.conversation_context,
#     )

#     return {
#         "answer": result.get("answer", ""),
#         "status": result.get("status", "fallback"),
#         "confidence_score": result.get("confidence_score", 0.0),
#         "sources": result.get("sources", []),
#     }