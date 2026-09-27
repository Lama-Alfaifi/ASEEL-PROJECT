"""
evaluation/dataset.py

Loads the ASEEL evaluation set (data/evaluation/relevance_results.csv)
and resolves a ground-truth answer for each question.

Design note
-----------
`relevance_results.csv` / `top5_relevance_results.csv` only contain
similarity *scores* -- they don't carry the ground-truth answer text.
Ground truth is resolved in two steps:

1. Primary: exact-match lookup against the raw per-region KB CSVs
   (data/raw/*.csv) via evaluation/raw_kb.py. This is static, requires
   no embedding model or live DB, and a full join check matched
   357/357 (100%) of the questions in relevance_results.csv verbatim.
2. Fallback: for any question that doesn't join against the raw CSVs
   (e.g. raw_dir not available in this environment, or the wording was
   edited since), fall back to an exact metadata match on `question`
   in the live Chroma collection. The vector store is only instantiated
   if this fallback path is actually needed.

This module only *reads* from CulturalVectorStore -- it never calls
`.replace()` or otherwise mutates the index.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from evaluation.raw_kb import load_raw_kb, normalize_text
from retrieval.vector_store import CulturalVectorStore

DEFAULT_DATASET_PATH = Path("data/evaluation/relevance_results.csv")
DEFAULT_RAW_DIR = Path("data/raw")


@dataclass
class EvalItem:
    question: str
    expected_region: str | None
    category: str | None
    domain: str | None
    question_type: str | None
    source_file: str | None
    expected_answer: str | None = None  # resolved from the vector store, may be None


def _load_ground_truth_answer(store: CulturalVectorStore, question: str) -> str | None:
    """
    Exact-match lookup of `question` against the collection metadata to
    retrieve its ground-truth answer. Returns None if the question isn't
    found verbatim in the index (e.g. index was rebuilt / edited since
    the eval CSV was generated).
    """
    try:
        result = store.collection.get(
            where={"question": question},
            include=["metadatas"],
        )
    except Exception:
        return None

    metadatas = result.get("metadatas") or []
    if not metadatas:
        return None

    return metadatas[0].get("answer")


def load_dataset(
    csv_path: Path | str = DEFAULT_DATASET_PATH,
    store: CulturalVectorStore | None = None,
    raw_dir: Path | str | None = DEFAULT_RAW_DIR,
    limit: int | None = None,
) -> list[EvalItem]:
    """
    Read the evaluation CSV and attach a ground-truth answer to each row.

    Parameters
    ----------
    csv_path: path to relevance_results.csv (or any CSV with the same
        `question,expected_region,file,question_type,domain,category`
        header).
    store: an existing CulturalVectorStore instance to reuse as the
        fallback ground-truth source (avoids re-loading the embedding
        model per call). Only instantiated (if not passed) when a
        question fails to join against the raw KB CSVs.
    raw_dir: directory containing the raw per-region KB CSVs
        (CENTERAL.csv, EAST.csv, NORTH.csv, SOUTH.csv, WEST.csv,
        GENERAL.csv). Pass None to skip this and go straight to the
        vector-store fallback for every row.
    limit: optional cap on number of rows, useful for smoke tests before
        running a full (costly) evaluation.
    """
    csv_path = Path(csv_path)
    raw_kb = load_raw_kb(raw_dir) if raw_dir else {}

    items: list[EvalItem] = []
    from_raw = 0
    from_store = 0
    missing_ground_truth = 0

    # utf-8-sig strips the BOM these exports were saved with.
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                break

            question = (row.get("question") or "").strip()
            if not question:
                continue

            raw_record = raw_kb.get(normalize_text(question))

            if raw_record is not None:
                expected_answer = raw_record.answer or None
                from_raw += 1
            else:
                # Fall back to the live vector store; only pay the cost
                # of instantiating it (embedding model + Chroma client)
                # if we actually need to.
                store = store or CulturalVectorStore()
                expected_answer = _load_ground_truth_answer(store, question)
                from_store += 1

            if expected_answer is None:
                missing_ground_truth += 1

            items.append(
                EvalItem(
                    question=question,
                    expected_region=(row.get("expected_region") or "").strip() or None,
                    category=(row.get("category") or "").strip() or None,
                    domain=(row.get("domain") or "").strip() or None,
                    question_type=(row.get("question_type") or "").strip() or None,
                    source_file=(row.get("file") or "").strip() or None,
                    expected_answer=expected_answer,
                )
            )

    print(
        f"[evaluation.dataset] Ground truth resolved for {len(items) - missing_ground_truth}/"
        f"{len(items)} questions ({from_raw} from raw KB CSVs, {from_store} via vector-store "
        f"fallback)."
    )
    if missing_ground_truth:
        print(
            f"[evaluation.dataset] Warning: {missing_ground_truth} question(s) had no "
            f"resolvable ground truth in either source. Contextual Recall will be "
            f"skipped for those rows."
        )

    return items
