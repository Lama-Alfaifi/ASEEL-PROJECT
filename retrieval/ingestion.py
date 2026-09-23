from __future__ import annotations
 
import argparse
import csv
import re
import shutil
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL
 
from config.settings import RAW_DATA_DIR
from retrieval.models import KnowledgeRecord
 
REGION_ALIASES = {"CENTERAL": "Central", "CENTRAL": "Central", "GENERAL": "General", "EAST": "East", "WEST": "West", "NORTH": "North", "SOUTH": "South"}
 
# Region names used inside the new "statement" CSV schema (region column),
# mapped to the same canonical region names used elsewhere in the project.
STATEMENT_REGION_ALIASES = {
    "all regions": "General",
    "central": "Central",
    "western": "West",
    "eastern": "East",
    "northern": "North",
    "southern": "South",
}


_MCQ_CHOICE_PATTERN = re.compile(r"([A-D])\.\s*(.*?)(?=(?:\s[A-D]\.\s)|$)")
_BARE_LETTER_PATTERN = re.compile(r"^[A-D]\.?$")


def _resolve_mcq_answer(answer: str, choices: str) -> str:
    """
    Some regional CSVs (e.g. NORTH.csv) store only the correct option's
    letter in the Answer column (e.g. "A"), leaving the actual answer
    text only inside the Choices column. Others (e.g. EAST.csv) already
    write the letter plus its text (e.g. "C. Al-Dishdasha"). Left as a
    bare letter, "A" becomes the entire knowledge-base answer record —
    meaningless on its own to both retrieval and the response LLM, which
    is exactly what caused a faithfulness failure on a NORTH-region
    question during DeepEval evaluation (the model had to reason from an
    answer field containing nothing but "A").

    Resolves a bare-letter answer to "Letter. Choice text" using the
    Choices column, so every regional file ends up with a genuinely
    informative answer regardless of which convention its source file
    used. Already-informative answers are left untouched (idempotent —
    running this on EAST.csv's "C. Al-Dishdasha" changes nothing).
    """
    stripped = answer.strip()

    if not _BARE_LETTER_PATTERN.match(stripped):
        return answer

    letter = stripped[0]

    for match_letter, text in _MCQ_CHOICE_PATTERN.findall(choices):
        if match_letter == letter:
            text = text.strip()
            if text:
                return f"{letter}. {text}"

    # Couldn't resolve from choices — fail safe, keep the original value
    # rather than guessing or dropping the row.
    return answer

 
def clean(value: str | None) -> str:
    value = (value or "").replace("\ufeff", "").strip()
    return re.sub(r"\s+", " ", value)
 
def region_from_filename(path: Path) -> str:
    key = path.stem.upper().replace(" ", "_").split("_")[0]
    if key not in REGION_ALIASES:
        raise ValueError(f"Cannot infer region from {path.name}; expected a regional CSV filename.")
    return REGION_ALIASES[key]
 
def _region_from_statement_value(value: str, path: Path) -> str:
    key = clean(value).lower()
    if key not in STATEMENT_REGION_ALIASES:
        raise ValueError(f"Unknown region '{value}' in {path.name}")
    return STATEMENT_REGION_ALIASES[key]


 
def _load_qa_rows(path: Path, rows: list[dict]) -> list[KnowledgeRecord]:
    # Original question/answer schema: region comes from the filename.
    region = region_from_filename(path)
    result: list[KnowledgeRecord] = []
    for row_number, row in enumerate(rows, start=2):
        normalized = {clean(k).lower(): clean(v) for k, v in row.items() if k}
        question, answer = normalized.get("question", ""), normalized.get("answer", "")
        if not question or not answer:
            continue
        answer = _resolve_mcq_answer(answer, normalized.get("choices", ""))
        stable_key = f"{path.name}:{row_number}:{question}:{answer}"
        result.append(KnowledgeRecord(
            id=str(uuid5(NAMESPACE_URL, stable_key)), question=question, answer=answer,
            choices=normalized.get("choices", ""), region=region,
            domain=normalized.get("domain", "Unspecified") or "Unspecified",
            category=normalized.get("category", "Unspecified") or "Unspecified",
            question_type=normalized.get("question type", "") or "Unspecified",
        ))
    return result


 
def _load_statement_rows(path: Path, rows: list[dict]) -> list[KnowledgeRecord]:
    # New "cultural statement" schema (id, source, region, region_areas,
    # scope, category, statement_type, topic, content, url): region comes
    # from a column inside the file rather than the filename, and
    # topic/content play the role of question/answer.
    result: list[KnowledgeRecord] = []
    for row_number, row in enumerate(rows, start=2):
        normalized = {clean(k).lower(): clean(v) for k, v in row.items() if k}
        question, answer = normalized.get("topic", ""), normalized.get("content", "")
        if not question or not answer:
            continue
        region = _region_from_statement_value(normalized.get("region", ""), path)
        stable_key = f"{path.name}:{row_number}:{question}:{answer}"
        result.append(KnowledgeRecord(
            id=str(uuid5(NAMESPACE_URL, stable_key)), question=question, answer=answer,
            choices="", region=region,
            domain=normalized.get("scope", "Unspecified") or "Unspecified",
            category=normalized.get("category", "Unspecified") or "Unspecified",
            question_type=normalized.get("statement_type", "") or "Unspecified",
        ))
    return result


 
def load_csv(path: Path) -> list[KnowledgeRecord]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"{path.name} has no header row")
        headers = {clean(h).lower() for h in reader.fieldnames if h}
        rows = list(reader)
 
    if {"topic", "content", "region"}.issubset(headers):
        return _load_statement_rows(path, rows)
    return _load_qa_rows(path, rows)


 
def load_directory(directory: Path) -> list[KnowledgeRecord]:
    records: list[KnowledgeRecord] = []
    for path in sorted(directory.glob("*.csv")):
        try:
            records.extend(load_csv(path))
        except ValueError as exc:
            # Dataset folders sometimes contain exports or application CSVs.
            # They are not ASEEL regional knowledge files and must not stop a
            # valid regional ingest.
            print(f"Skipping {path.name}: {exc}")
    if not records:
        raise ValueError(f"No usable CSV rows found in {directory}")
    return records


 
def stage_sources(source_dir: Path, destination: Path = RAW_DATA_DIR) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    for source in source_dir.glob("*.csv"):
        try:
            region_from_filename(source)
        except ValueError:
            print(f"Skipping unrelated CSV: {source.name}")
            continue
        target = destination / source.name
        shutil.copy2(source, target)
        staged.append(target)
    return staged
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate and optionally stage ASEEL regional CSV files.")
    parser.add_argument("--source-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--stage", action="store_true", help="Copy source CSV files into data/raw before loading.")
    args = parser.parse_args()
    source = args.source_dir
    if args.stage:
        stage_sources(source)
        source = RAW_DATA_DIR
    records = load_directory(source)
    print(f"Validated {len(records)} cultural knowledge records from {source}")