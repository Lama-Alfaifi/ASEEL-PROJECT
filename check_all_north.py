import csv
from retrieval.ingestion import _resolve_mcq_answer

with open("data/raw/NORTH.csv", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for row in rows:
    original = row.get("Answer", "").strip()
    if len(original) <= 3:
        fixed = _resolve_mcq_answer(original, row.get("Choices", ""))
        print(f"{original!r:>6} -> {fixed!r}")
