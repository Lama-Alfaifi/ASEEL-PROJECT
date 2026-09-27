"""
evaluation/raw_kb.py

Reads the raw per-region knowledge-base CSVs (data/raw/*.csv) directly,
to resolve ground-truth answers for the evaluation set. This is the
primary ground-truth source: it's static, doesn't require an embedding
model or a live Chroma collection, and a full join check against
relevance_results.csv matched 357/357 (100%) of the eval questions
verbatim.

Handles the two schema variants actually present across the raw files:
- GENERAL.csv:                        Question,Choices,Answer,Domain,Category
- NORTH/SOUTH/EAST/WEST/CENTERAL.csv: Question,Choices,Answer,Question Type,Domain,Category

Note the raw files have no `Region` column -- region is implied by
which file a row lives in, so it's attached here from the filename.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

# Matches the exact (misspelled, in the case of "CENTERAL") filenames
# used in this project. GENERAL.csv is cross-region knowledge and has
# no associated region.
FILE_TO_REGION: dict[str, str | None] = {
    "CENTERAL.csv": "Central",
    "EAST.csv": "East",
    "NORTH.csv": "North",
    "SOUTH.csv": "South",
    "WEST.csv": "West",
    "GENERAL.csv": None,
}


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


@dataclass
class RawKBRecord:
    question: str
    answer: str
    region: str | None
    domain: str | None
    category: str | None
    question_type: str | None
    source_file: str


def load_raw_kb(raw_dir: Path | str = "data/raw") -> dict[str, RawKBRecord]:
    """
    Returns {normalized_question: RawKBRecord}, built from every file in
    FILE_TO_REGION found under raw_dir. Missing files are skipped
    silently (so this degrades gracefully to the vector-store fallback
    in evaluation/dataset.py rather than hard failing).

    If the same (normalized) question shows up in more than one file,
    the first one encountered wins and a warning is printed -- that
    would indicate a genuine data issue worth checking.
    """
    raw_dir = Path(raw_dir)
    kb: dict[str, RawKBRecord] = {}
    duplicates: list[tuple[str, str, str]] = []  # (question, first_file, dupe_file)

    for filename, region in FILE_TO_REGION.items():
        path = raw_dir / filename
        if not path.exists():
            continue

        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                question = (row.get("Question") or "").strip()
                if not question:
                    continue

                key = normalize_text(question)
                if key in kb:
                    duplicates.append((question, kb[key].source_file, filename))
                    continue

                kb[key] = RawKBRecord(
                    question=question,
                    answer=(row.get("Answer") or "").strip(),
                    region=region,
                    domain=(row.get("Domain") or "").strip() or None,
                    category=(row.get("Category") or "").strip() or None,
                    question_type=(row.get("Question Type") or "").strip() or None,
                    source_file=filename,
                )

    if duplicates:
        same_file = sum(1 for _, a, b in duplicates if a == b)
        cross_file = len(duplicates) - same_file
        print(
            f"[evaluation.raw_kb] Found {len(duplicates)} duplicate question(s) across "
            f"the raw KB CSVs ({same_file} repeated within the same file, {cross_file} "
            f"duplicated across different region files) -- keeping the first occurrence "
            f"of each. Cross-file duplicates are worth checking, since they usually mean "
            f"a question got mis-filed into the wrong region's CSV:"
        )
        for question, first_file, dupe_file in duplicates:
            if first_file != dupe_file:
                print(f"    {question!r}  (kept from {first_file}, also found in {dupe_file})")

    return kb
