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

def clean(value: str | None) -> str:
    value = (value or "").replace("\ufeff", "").strip()
    return re.sub(r"\s+", " ", value)

def region_from_filename(path: Path) -> str:
    key = path.stem.upper().replace(" ", "_").split("_")[0]
    if key not in REGION_ALIASES:
        raise ValueError(f"Cannot infer region from {path.name}; expected a regional CSV filename.")
    return REGION_ALIASES[key]

def load_csv(path: Path) -> list[KnowledgeRecord]:
    region = region_from_filename(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"{path.name} has no header row")
        result: list[KnowledgeRecord] = []
        for row_number, row in enumerate(reader, start=2):
            normalized = {clean(k).lower(): clean(v) for k, v in row.items() if k}
            question, answer = normalized.get("question", ""), normalized.get("answer", "")
            if not question or not answer:
                continue
            stable_key = f"{path.name}:{row_number}:{question}:{answer}"
            result.append(KnowledgeRecord(
                id=str(uuid5(NAMESPACE_URL, stable_key)), question=question, answer=answer,
                choices=normalized.get("choices", ""), region=region,
                domain=normalized.get("domain", "Unspecified") or "Unspecified",
                category=normalized.get("category", "Unspecified") or "Unspecified",
                question_type=normalized.get("question type", "") or "Unspecified",
            ))
    return result

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