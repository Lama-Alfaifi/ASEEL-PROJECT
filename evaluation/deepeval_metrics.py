"""
evaluation/deepeval_metrics.py

Wraps DeepEval's RAG metrics around end-to-end samples produced by the
ASEEL graph:

- Faithfulness         -> is the answer supported by the retrieval context?
- Answer Relevancy     -> does the answer address the question?
- Contextual Relevancy -> is the retrieved context relevant to the question?
- Contextual Recall    -> does the retrieved context cover what the
                           ground-truth answer needed? (requires expected_output)

The metrics themselves (type, threshold, judge model) are unchanged from
the original version of this module. This revision only adds two
robustness measures, both scoped to what gets *sent to the judge model*:

1. Input caps (`MAX_CONTEXT_ITEM_CHARS` / `MAX_CONTEXT_ITEMS` /
   `MAX_ANSWER_CHARS`). Faithfulness's verdict-generation step scales
   with how much text it's asked to reason over (claims x truths). If a
   sample happens to carry an unusually large validated-evidence list or
   a very long answer, the judge model can get stuck trying to enumerate
   verdicts for it and run past its own max output tokens -- which
   surfaces as `openai.LengthFinishReasonError` ("could not parse
   response content as the length limit was reached"). Capping the size
   of what's scored prevents this without changing what the production
   graph actually retrieves or answers with.

2. Per-batch resilience (`_safe_evaluate`). `deepeval.evaluate()` scores
   a whole list of test cases in one call; if any single one blows up
   (even after the caps above -- e.g. a genuinely pathological answer),
   the exception was taking the *entire batch* down with it. Now the
   batch is tried as-is first; on failure it falls back to scoring each
   test case individually, logging and skipping only the one(s) that
   fail, so the rest of the batch isn't lost.

Requires: pip install deepeval
Requires OPENAI_API_KEY (or whatever provider you configure DeepEval's
judge model with) to be set in the environment, since these are
LLM-as-judge metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from deepeval import evaluate as deepeval_evaluate
from deepeval.evaluate.configs import AsyncConfig
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

# NOTE: use a judge model independent from the one that generates the
# answers (config.settings.OPENAI_MODEL) where possible -- grading your
# own generations with the same model biases the scores. Override via
# the `model` argument below (e.g. "gpt-4o") if you have access.
DEFAULT_JUDGE_MODEL = "gpt-4o-mini"
DEFAULT_THRESHOLD = 0.5

# Caps applied only to what is sent to the judge model for scoring --
# they do not change what the production graph retrieves or answers
# with, only what's fed into these metrics. See module docstring.
MAX_CONTEXT_ITEMS = 10
MAX_CONTEXT_ITEM_CHARS = 1000
MAX_ANSWER_CHARS = 3000


@dataclass
class GenerationSample:
    """One end-to-end sample: a question, what the system answered, what
    context it actually used, and (optionally) the ground-truth answer."""

    question: str
    actual_output: str
    retrieval_context: list[str] = field(default_factory=list)
    expected_output: str | None = None


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + " …[truncated for evaluation]"


def build_test_case(sample: GenerationSample) -> LLMTestCase:
    context = sample.retrieval_context or [""]
    truncated_item_count = len(context) > MAX_CONTEXT_ITEMS
    context = context[:MAX_CONTEXT_ITEMS]

    capped_context = []
    truncated_chars = False
    for chunk in context:
        capped = _truncate(chunk, MAX_CONTEXT_ITEM_CHARS)
        truncated_chars = truncated_chars or (capped != chunk)
        capped_context.append(capped)

    answer = sample.actual_output or ""
    capped_answer = _truncate(answer, MAX_ANSWER_CHARS)

    if truncated_item_count or truncated_chars or capped_answer != answer:
        print(
            f"[evaluation.deepeval_metrics] Truncated evaluation inputs for "
            f"{sample.question!r} before scoring (retrieval_context or "
            f"actual_output was unusually large). This only affects what's "
            f"sent to the judge model -- worth checking why this question's "
            f"validated evidence or answer got so large in the first place."
        )

    return LLMTestCase(
        input=sample.question,
        actual_output=capped_answer,
        retrieval_context=capped_context or [""],
        expected_output=sample.expected_output or "",
    )


def _default_async_config() -> AsyncConfig:
    return AsyncConfig(run_async=True, throttle_value=0, max_concurrent=2)


def _safe_evaluate(test_cases: list[LLMTestCase], metrics: list, label: str):
    """
    Scores the whole list of test cases in one call first (fast path,
    same as before). If that raises -- most commonly
    openai.LengthFinishReasonError from one sample's judge-model call
    overflowing -- falls back to evaluating each test case individually
    so a single bad sample doesn't discard the rest of the batch.
    Individual failures are logged with the offending question and
    skipped, not silently dropped.
    """
    try:
        return deepeval_evaluate(
            test_cases=test_cases,
            metrics=metrics,
            async_config=_default_async_config(),
        )
    except Exception as exc:
        print(
            f"[evaluation.deepeval_metrics] Batch evaluation failed for {label} "
            f"({type(exc).__name__}: {exc}). Falling back to evaluating "
            f"{len(test_cases)} test case(s) one at a time so the rest of the "
            f"batch isn't lost ..."
        )

    all_test_results = []
    for i, test_case in enumerate(test_cases, start=1):
        try:
            result = deepeval_evaluate(
                test_cases=[test_case],
                metrics=metrics,
                async_config=AsyncConfig(run_async=False),
            )
            all_test_results.extend(result.test_results)
        except Exception as exc:
            print(
                f"[evaluation.deepeval_metrics] Skipping test case {i}/{len(test_cases)} "
                f"({test_case.input!r}) for {label} after it failed to score: "
                f"{type(exc).__name__}: {exc}"
            )

    return SimpleNamespace(test_results=all_test_results)


def run_core_rag_metrics(
    samples: list[GenerationSample],
    model: str = DEFAULT_JUDGE_MODEL,
    threshold: float = DEFAULT_THRESHOLD,
):
    """Faithfulness, Answer Relevancy, Contextual Relevancy -- run on
    every sample, since none of these require a ground-truth answer."""
    test_cases = [build_test_case(s) for s in samples]

    metrics = [
        FaithfulnessMetric(threshold=threshold, model=model, include_reason=True),
        AnswerRelevancyMetric(threshold=threshold, model=model, include_reason=True),
        ContextualRelevancyMetric(threshold=threshold, model=model, include_reason=True),
    ]

    return _safe_evaluate(test_cases, metrics, label="core RAG metrics")


def run_contextual_recall(
    samples: list[GenerationSample],
    model: str = DEFAULT_JUDGE_MODEL,
    threshold: float = DEFAULT_THRESHOLD,
):
    """Contextual Recall requires a ground-truth `expected_output`.
    Samples without one (see evaluation/dataset.py's warning about
    unresolved ground truth) are skipped rather than scored on an
    empty string, which would be meaningless."""
    scoreable = [s for s in samples if s.expected_output]

    if not scoreable:
        print(
            "[evaluation.deepeval_metrics] No samples had a resolvable "
            "ground-truth answer -- skipping Contextual Recall."
        )
        return None

    if len(scoreable) < len(samples):
        print(
            f"[evaluation.deepeval_metrics] Contextual Recall computed on "
            f"{len(scoreable)}/{len(samples)} samples (others had no "
            f"ground-truth answer)."
        )

    test_cases = [build_test_case(s) for s in scoreable]
    metrics = [ContextualRecallMetric(threshold=threshold, model=model, include_reason=True)]

    return _safe_evaluate(test_cases, metrics, label="Contextual Recall")
