from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from config.settings import ROOT_DIR

FEEDBACK_FILE = ROOT_DIR / "data" / "feedback.jsonl"

VALID_STATUSES = {"pending", "approved", "rejected", "needs_review"}


def _ensure_file():
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_FILE.touch(exist_ok=True)


def _load_all() -> list[dict]:
    if not FEEDBACK_FILE.exists():
        return []

    records = []
    with FEEDBACK_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _save_all(records: list[dict]) -> None:
    _ensure_file()
    with FEEDBACK_FILE.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_feedback(
    *,
    feedback_type: str,
    message: str,
    city: str | None = None,
    region: str | None = None,
    category: str | None = None,
    original_query: str | None = None,
    original_answer: str | None = None,
) -> dict:
    """
    Append a new feedback item with status=pending.
    Deterministic, no LLM — mirrors utils/monitoring.py's JSONL-append
    convention so the project has one consistent pattern for append-only
    logs.
    """
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": feedback_type,
        "message": message,
        "city": city,
        "region": region,
        "category": category,
        "original_query": original_query,
        "original_answer": original_answer,
        "status": "pending",
        "validation": None,
    }

    _ensure_file()
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def list_feedback(status: str | None = None) -> list[dict]:
    records = _load_all()
    if status:
        records = [r for r in records if r.get("status") == status]
    return sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)


def get_feedback(feedback_id: str) -> dict | None:
    for record in _load_all():
        if record.get("id") == feedback_id:
            return record
    return None


def update_feedback(feedback_id: str, updates: dict) -> dict | None:
    records = _load_all()
    updated = None
    for record in records:
        if record.get("id") == feedback_id:
            record.update(updates)
            updated = record
            break
    if updated is not None:
        _save_all(records)
    return updated


def set_validation_result(feedback_id: str, validation: dict) -> dict | None:
    """
    Attach the validation agent's classification to a feedback item.

    CRITICAL RULE: this never sets status to "approved" or "rejected" —
    those require an explicit human action (set_status below). The agent's
    recommended_action can only move a record to "needs_review", which is
    still a pending-for-human state, not a publishing decision.
    """
    recommended = validation.get("recommended_action")
    updates = {"validation": validation}

    if recommended == "needs_review":
        updates["status"] = "needs_review"

    return update_feedback(feedback_id, updates)


def set_status(feedback_id: str, status: str) -> dict | None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    return update_feedback(
        feedback_id,
        {
            "status": status,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        },
    )