from __future__ import annotations

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from retrieval.models import KnowledgeRecord
from retrieval.vector_store import CulturalVectorStore
from utils.feedback_store import get_feedback, update_feedback, set_status

_store = CulturalVectorStore()

# Deterministic content gate — NOT a judgment on cultural truth, just a
# technical safeguard against empty/junk input ("hi", "aaaaaaaa") reaching
# ChromaDB. This runs only AFTER a human has already clicked Approve — it
# never makes the approve/reject decision itself. That decision belongs to
# the human reviewer alone, per the project's Human-in-the-Loop rule.
MIN_MESSAGE_LENGTH = 15

# Above this semantic-similarity score, an existing KB record is treated as
# already covering the same information, so nothing new is added.
DUPLICATE_RELEVANCE_THRESHOLD = 0.92


def _looks_like_junk(message: str) -> bool:
    text = message.strip()

    if len(text) < MIN_MESSAGE_LENGTH:
        return True

    words = text.split()
    distinct_words = {w.lower() for w in words}

    # "aaaaaaaa", "hi hi hi" etc. — real sentences use more than one
    # distinct word.
    if len(distinct_words) <= 1:
        return True

    return False


def _duplicate_match(answer_text: str, region: str | None) -> bool:
    if not answer_text.strip():
        return False

    results = _store.search(query=answer_text, region=region, limit=1)

    return bool(results) and results[0].relevance >= DUPLICATE_RELEVANCE_THRESHOLD


def _mark_failed(feedback_id: str, message: str) -> dict:
    update_feedback(
        feedback_id,
        {
            "status": "approved",
            "knowledge_base_status": "failed",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {
        "success": True,
        "status": "approved",
        "knowledge_base_updated": False,
        "message": message,
    }


def approve_and_publish(feedback_id: str) -> dict:
    """
    The ONLY path from a human's Approve click to ChromaDB.

    api/main.py's POST /feedback/{id}/approve is the sole caller, and that
    endpoint only ever runs when a human clicks Approve in the review
    dashboard — no automated process calls this function.

    Returns {success, status, knowledge_base_updated, message}.
    """
    print(f"DEBUG: approve_and_publish called with {feedback_id}")
    record = get_feedback(feedback_id)

    if record is None:
        return {
            "success": False,
            "status": "not_found",
            "knowledge_base_updated": False,
            "message": "Feedback item not found.",
        }

    message = record.get("message", "") or ""
    region = CulturalVectorStore.normalize_region(record.get("region"))
    print(f"DEBUG: message={message!r}")
    print(f"DEBUG: region={region!r}")

    # 1. Deterministic content gate.
    if _looks_like_junk(message):
        return _mark_failed(
            feedback_id,
            "Approved, but the message is too short or not informative "
            "enough to add to the knowledge base.",
        )

    # 2. Every knowledge-base record is region-tagged; without a
    #    resolvable region there is nowhere safe to file this entry.
    if not region:
        return _mark_failed(
            feedback_id,
            "Approved, but no region could be resolved for this "
            "feedback, so it cannot be added to the knowledge base.",
        )

    # 3. Duplicate check — semantic, reusing the existing search() method.
    print("DEBUG: before duplicate check")
    if _duplicate_match(message, region):
        update_feedback(
            feedback_id,
            {
                "status": "approved",
                "knowledge_base_status": "skipped_duplicate",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {
            "success": True,
            "status": "approved",
            "knowledge_base_updated": False,
            "message": "Approved. A very similar record already exists "
            "in the knowledge base, so nothing new was added.",
        }

    # 4. Convert to the existing KnowledgeRecord schema — no new schema.
    question = (
        record.get("original_query")
        or f"Community contribution \u2014 {record.get('category') or 'General'}"
    )

    # Deterministic id from the feedback_id itself: re-approving the same
    # feedback twice upserts the same document rather than duplicating it.
    kb_id = str(uuid5(NAMESPACE_URL, f"feedback:{feedback_id}"))
    print("DEBUG: creating KnowledgeRecord")

    kb_record = KnowledgeRecord(
        id=kb_id,
        question=question,
        answer=message,
        choices="",
        region=region,
        domain="Community",
        category=record.get("category") or "Unspecified",
        question_type="Community contribution",
    )

    # 5. Upsert only — never touches the existing 541 records.
    print("DEBUG: before Chroma upsert")
    try:
        _store.upsert_records([kb_record])
    except Exception as exc:
        print(f"FEEDBACK KB ERROR: {exc!r}")
        return _mark_failed(
            feedback_id,
            f"Approved, but updating the knowledge base failed: {exc}",
        )

    # 6. Success.
    now = datetime.now(timezone.utc).isoformat()
    update_feedback(
        feedback_id,
        {
            "status": "approved",
            "knowledge_base_status": "added",
            "knowledge_base_id": kb_id,
            "reviewed_at": now,
            "approved_at": now,
        },
    )

    return {
        "success": True,
        "status": "approved",
        "knowledge_base_updated": True,
        "message": "Approved and added to the knowledge base.",
    }


def reject(feedback_id: str) -> dict:
    record = set_status(feedback_id, "rejected")

    if record is None:
        return {
            "success": False,
            "status": "not_found",
            "knowledge_base_updated": False,
            "message": "Feedback item not found.",
        }

    return {
        "success": True,
        "status": "rejected",
        "knowledge_base_updated": False,
        "message": "Rejected. No changes were made to the knowledge base.",
    }