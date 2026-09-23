"""
evaluation/pipeline_integration.py

Runs the existing ASEEL graph end-to-end for each evaluation question
and packages the result into a GenerationSample for DeepEval.

This version adds checkpointing:
- Saves every completed sample to disk immediately.
- If the evaluation is interrupted or crashes, rerunning will resume
  from the saved samples instead of running ASEEL again for completed items.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.dataset import EvalItem
from evaluation.deepeval_metrics import GenerationSample

try:
    from workflow.graph import ask
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Could not import `ask` from `workflow.graph`."
    ) from exc


# ---------------------------------------------------------------------
# Checkpoint file
# ---------------------------------------------------------------------

CHECKPOINT_DIR = Path("evaluation/results")
CHECKPOINT_FILE = CHECKPOINT_DIR / "pipeline_samples.json"


# ---------------------------------------------------------------------
# Evidence formatting
# ---------------------------------------------------------------------

def _format_evidence(evidence: list[dict] | None) -> list[str]:
    """
    Turn the evidence dictionaries produced by ASEEL into plain strings
    that DeepEval can use as retrieval context.
    """
    formatted = []

    for record in evidence or []:
        question = record.get("question", "")
        answer = record.get("answer", "")
        region = record.get("region", "")

        formatted.append(
            f"[{region}] Q: {question} A: {answer}"
        )

    return formatted


# ---------------------------------------------------------------------
# Single item
# ---------------------------------------------------------------------

def run_pipeline_for_item(item: EvalItem) -> GenerationSample:
    """
    Runs the full ASEEL graph for one evaluation question.
    """

    state = ask(item.question)

    retrieval_context = (
        _format_evidence(state.get("sources"))
        or _format_evidence(state.get("retrieved"))
    )

    return GenerationSample(
        question=item.question,
        actual_output=state.get("answer", ""),
        retrieval_context=retrieval_context,
        expected_output=item.expected_answer,
    )


# ---------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------

def _sample_to_dict(sample: GenerationSample) -> dict:
    """
    Convert GenerationSample into JSON-serializable data.
    """

    return {
        "question": sample.question,
        "actual_output": sample.actual_output,
        "retrieval_context": sample.retrieval_context,
        "expected_output": sample.expected_output,
    }


def _dict_to_sample(data: dict) -> GenerationSample:
    """
    Convert saved JSON data back into GenerationSample.
    """

    return GenerationSample(
        question=data["question"],
        actual_output=data.get("actual_output", ""),
        retrieval_context=data.get("retrieval_context", []),
        expected_output=data.get("expected_output"),
    )


def _save_checkpoint(samples: list[GenerationSample]) -> None:
    """
    Save the current pipeline results.

    Uses a temporary file first so that an interruption while writing
    does not corrupt the main checkpoint.
    """

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    temp_file = CHECKPOINT_FILE.with_suffix(".tmp")

    data = [_sample_to_dict(sample) for sample in samples]

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    temp_file.replace(CHECKPOINT_FILE)


def _load_checkpoint() -> list[GenerationSample]:
    """
    Load previously completed pipeline samples if they exist.
    """

    if not CHECKPOINT_FILE.exists():
        return []

    try:
        with CHECKPOINT_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        samples = [_dict_to_sample(item) for item in data]

        print(
            f"[evaluation.pipeline_integration] "
            f"Loaded {len(samples)} saved pipeline result(s) "
            f"from {CHECKPOINT_FILE}"
        )

        return samples

    except Exception as exc:
        print(
            f"[evaluation.pipeline_integration] "
            f"Could not load checkpoint: {exc}"
        )
        return []


# ---------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------

def run_pipeline(items: list[EvalItem]) -> list[GenerationSample]:
    """
    Run ASEEL for all evaluation items with automatic checkpointing.

    Completed samples are saved after every question.

    If the process is interrupted, rerunning the evaluation will reuse
    the saved samples and continue from the first unfinished question.
    """

    samples = _load_checkpoint()

    # Make sure the checkpoint belongs to the same evaluation dataset.
    if samples:
        valid_count = min(len(samples), len(items))

        checkpoint_matches = all(
            samples[i].question == items[i].question
            for i in range(valid_count)
        )

        if not checkpoint_matches:
            print(
                "[evaluation.pipeline_integration] "
                "Checkpoint does not match the current evaluation dataset. "
                "Starting from scratch."
            )
            samples = []

    start_index = len(samples)

    if start_index >= len(items):
        print(
            "[evaluation.pipeline_integration] "
            f"All {len(items)} pipeline samples are already saved. "
            "Skipping ASEEL execution."
        )
        return samples

    if start_index > 0:
        print(
            "[evaluation.pipeline_integration] "
            f"Resuming from {start_index + 1}/{len(items)}. "
            f"{start_index} sample(s) already completed."
        )

    for i in range(start_index, len(items)):
        item = items[i]

        print(
            f"[evaluation.pipeline_integration] "
            f"Running {i + 1}/{len(items)}: {item.question!r}"
        )

        sample = run_pipeline_for_item(item)

        samples.append(sample)

        # Save immediately after every successful question.
        _save_checkpoint(samples)

        print(
            f"[evaluation.pipeline_integration] "
            f"Saved checkpoint: {len(samples)}/{len(items)}"
        )

    print(
        f"[evaluation.pipeline_integration] "
        f"Pipeline completed: {len(samples)}/{len(items)}"
    )

    return samples