"""
evaluation/run_evaluation.py

CLI entry point for the ASEEL DeepEval evaluation suite.

Usage
-----
    python -m evaluation.run_evaluation
    python -m evaluation.run_evaluation --dataset data/evaluation/relevance_results.csv --limit 10
    python -m evaluation.run_evaluation --judge-model gpt-4o-mini

The evaluation runs the existing graph end-to-end and scores the actual
answers and validated retrieval context with DeepEval. It does not modify
the production RAG pipeline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.dataset import DEFAULT_DATASET_PATH, load_dataset
from evaluation.deepeval_metrics import (
    DEFAULT_JUDGE_MODEL,
    run_contextual_recall,
    run_core_rag_metrics,
)
from evaluation.report import build_report_rows, print_summary, write_csv


# Number of questions evaluated in each DeepEval batch.
# Keeping this smaller prevents very large evaluation runs from timing out.
DEFAULT_BATCH_SIZE = 25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ASEEL DeepEval evaluation suite."
    )

    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="cap number of evaluation rows; useful for a small smoke test",
    )

    parser.add_argument(
        "--judge-model",
        default=DEFAULT_JUDGE_MODEL,
    )

    parser.add_argument(
        "--out",
        default="data/evaluation/eval_report.csv",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="number of questions evaluated per DeepEval batch",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be greater than 0")

    print(f"[run_evaluation] Loading dataset from {args.dataset} ...")

    items = load_dataset(
        Path(args.dataset),
        raw_dir=Path("data/raw"),
        limit=args.limit,
    )

    print(f"[run_evaluation] Loaded {len(items)} evaluation questions.")

    from evaluation.pipeline_integration import run_pipeline

    print(
        f"[run_evaluation] Running the existing graph for "
        f"{len(items)} questions ..."
    )

    samples = run_pipeline(items)

    total = len(samples)

    if total == 0:
        print("[run_evaluation] No samples to evaluate.")
        return

    # Split the samples into smaller batches.
    batches = [
        samples[i : i + args.batch_size]
        for i in range(0, total, args.batch_size)
    ]

    print(
        f"[run_evaluation] DeepEval batch size: {args.batch_size}"
    )
    print(
        f"[run_evaluation] Total batches: {len(batches)}"
    )

    all_rows: list[dict] = []

    for batch_number, batch_samples in enumerate(batches, start=1):
        start_index = (batch_number - 1) * args.batch_size + 1
        end_index = start_index + len(batch_samples) - 1

        print(
            "\n"
            f"[run_evaluation] ========================================\n"
            f"[run_evaluation] Evaluating batch "
            f"{batch_number}/{len(batches)} "
            f"(questions {start_index}-{end_index})\n"
            f"[run_evaluation] ========================================"
        )

        print(
            "[run_evaluation] Scoring with DeepEval: "
            "Faithfulness / Answer Relevancy / Contextual Relevancy ..."
        )

        core_result = run_core_rag_metrics(
            batch_samples,
            model=args.judge_model,
        )

        print(
            "[run_evaluation] Scoring Contextual Recall "
            "where ground truth is available ..."
        )

        recall_result = run_contextual_recall(
            batch_samples,
            model=args.judge_model,
        )

        batch_rows = build_report_rows(
            batch_samples,
            core_result,
            recall_result,
        )

        all_rows.extend(batch_rows)

        print(
            f"[run_evaluation] Completed batch "
            f"{batch_number}/{len(batches)} "
            f"({len(batch_rows)} questions)."
        )

    print(
        "\n"
        "[run_evaluation] All DeepEval batches completed successfully."
    )

    write_csv(
        all_rows,
        Path(args.out),
    )

    print_summary(all_rows)


if __name__ == "__main__":
    main()