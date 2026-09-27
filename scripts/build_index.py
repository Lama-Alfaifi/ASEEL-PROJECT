from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from config.settings import RAW_DATA_DIR
from retrieval.ingestion import load_directory
from retrieval.models import KnowledgeRecord
from retrieval.vector_store import CulturalVectorStore
from utils.feedback_store import list_feedback


def load_approved_feedback() -> list[KnowledgeRecord]:
    records: list[KnowledgeRecord] = []

    # Only human-approved feedback that was successfully
    # published to the knowledge base is included.
    feedback_items = list_feedback(status="approved")

    for item in feedback_items:
        message = (item.get("message") or "").strip()
        region = CulturalVectorStore.normalize_region(item.get("region"))

        if not message or not region:
            continue

        if item.get("knowledge_base_status") != "added":
            continue

        feedback_id = item.get("id")
        if not feedback_id:
            continue

        # Preserve the same ID created by feedback_service.py.
        kb_id = item.get("knowledge_base_id")

        if not kb_id:
            kb_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"feedback:{feedback_id}",
                )
            )

        question = (
            item.get("original_query")
            or f"Community contribution — "
            f"{item.get('category') or 'General'}"
        )

        records.append(
            KnowledgeRecord(
                id=kb_id,
                question=question,
                answer=message,
                choices="",
                region=region,
                domain="Community",
                category=item.get("category") or "Unspecified",
                question_type="Community contribution",
            )
        )

    return records


if __name__ == "__main__":
    # Main knowledge base from the regional CSV files.
    csv_records = load_directory(RAW_DATA_DIR)

    # Human-approved feedback that was previously added to the KB.
    feedback_records = load_approved_feedback()

    # ONE knowledge base.
    all_records = csv_records + feedback_records

    store = CulturalVectorStore()
    store.replace(all_records)

    print(f"CSV records: {len(csv_records)}")
    print(f"Approved feedback: {len(feedback_records)}")
    print(f"Total indexed in ChromaDB: {len(all_records)}")