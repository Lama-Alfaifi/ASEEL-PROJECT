"""
evaluation/report.py

Turns DeepEval metric outputs into a flat CSV + console summary so
results can be tracked over time / compared across runs.
"""

from __future__ import annotations

import csv
from pathlib import Path

from evaluation.deepeval_metrics import GenerationSample


def _metric_scores_by_input(deepeval_result) -> dict[str, dict[str, float]]:
    """Flatten DeepEval results into {input: {metric_name: score}}."""
    scores: dict[str, dict[str, float]] = {}
    if deepeval_result is None:
        return scores

    for test_result in getattr(deepeval_result, "test_results", []):
        question = test_result.input
        scores.setdefault(question, {})
        for metric_data in getattr(test_result, "metrics_data", []) or []:
            scores[question][metric_data.name] = metric_data.score
    return scores


def build_report_rows(
    samples: list[GenerationSample],
    core_rag_result,
    contextual_recall_result,
) -> list[dict]:
    """Build one report row per evaluated question."""
    core_scores = _metric_scores_by_input(core_rag_result)
    recall_scores = _metric_scores_by_input(contextual_recall_result)

    rows = []
    for sample in samples:
        row = {
            "question": sample.question,
            "actual_output": sample.actual_output,
            "expected_output": sample.expected_output or "",
        }
        row.update(core_scores.get(sample.question, {}))
        row.update(recall_scores.get(sample.question, {}))
        rows.append(row)

    return rows


def write_csv(rows: list[dict], out_path: Path | str) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        print(f"[evaluation.report] No rows to write to {out_path}")
        return

    preferred_order = [
        "question",
        "actual_output",
        "expected_output",
        "Faithfulness",
        "Answer Relevancy",
        "Contextual Relevancy",
        "Contextual Recall",
    ]
    all_fields = sorted({key for row in rows for key in row.keys()})
    fieldnames = [f for f in preferred_order if f in all_fields]
    fieldnames += [f for f in all_fields if f not in fieldnames]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[evaluation.report] Wrote {len(rows)} rows to {out_path}")


def print_summary(rows: list[dict]) -> None:
    print("\n=== ASEEL DeepEval Summary ===")
    print(f"Questions evaluated: {len(rows)}")

    metric_names = [
        "Faithfulness",
        "Answer Relevancy",
        "Contextual Relevancy",
        "Contextual Recall",
    ]

    for name in metric_names:
        values = [
            float(row[name])
            for row in rows
            if name in row and row[name] not in ("", None)
        ]
        if values:
            avg = sum(values) / len(values)
            print(f"{name:<24} {avg:.3f}  (n={len(values)})")
        else:
            print(f"{name:<24} n/a")

    print("================================\n")
