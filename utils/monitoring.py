from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from config.settings import ROOT_DIR


# Anchored to the project root (not the process's working directory), so it
# resolves correctly no matter where the app/tests/Docker container is
# launched from.
MONITORING_FILE = ROOT_DIR / "data" / "monitoring.jsonl"


def start_timer() -> float:
    """Start a timer for measuring workflow latency."""
    return time.perf_counter()


def _ensure_file():
    MONITORING_FILE.parent.mkdir(parents=True, exist_ok=True)
    MONITORING_FILE.touch(exist_ok=True)


def detect_failure_pattern(
    confidence_score: float,
    status: str,
    error: str | None = None,
) -> str:
    """Classify the main monitoring outcome."""

    if error:
        return "workflow_error"

    if status == "success":
        return "none"

    if confidence_score == 0:
        return "no_relevant_evidence"

    if confidence_score < 0.50:
        return "low_confidence"

    return "unknown"


def record_run(
    *,
    query: str,
    result: dict | None = None,
    latency_seconds: float = 0.0,
    error: str | None = None,
):
    """Record one ASEEL workflow run."""

    result = result or {}

    confidence_score = float(
        result.get("confidence_score", 0.0) or 0.0
    )

    attempts = int(
        result.get("attempts", 0) or 0
    )

    if error:
        status = "error"
    elif confidence_score >= 0.50:
        status = "success"
    else:
        status = "retry_or_insufficient"

    failure_pattern = detect_failure_pattern(
        confidence_score,
        status,
        error,
    )

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "region": result.get("region", ""),
        "language": result.get("language", ""),
        "confidence_score": confidence_score,
        "attempts": attempts,
        "validation_status": result.get("status", ""),
        "latency_seconds": round(latency_seconds, 3),
        "status": status,
        "failure_pattern": failure_pattern,
        "error": error,
    }

    _ensure_file()

    with MONITORING_FILE.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )


def load_runs() -> list[dict]:
    """Load all monitoring records."""

    if not MONITORING_FILE.exists():
        return []

    runs = []

    with MONITORING_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return runs


def get_metrics() -> dict:
    """Calculate aggregate monitoring metrics."""

    runs = load_runs()

    if not runs:
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "retries": 0,
            "errors": 0,
            "average_latency": 0.0,
            "average_confidence": 0.0,
        }

    successful = [
        run for run in runs
        if run["status"] == "success"
    ]

    retries = [
        run for run in runs
        if run["status"] == "retry_or_insufficient"
    ]

    errors = [
        run for run in runs
        if run["status"] == "error"
    ]

    confidence_values = [
        run["confidence_score"]
        for run in runs
        if run.get("confidence_score") is not None
    ]

    latency_values = [
        run["latency_seconds"]
        for run in runs
    ]

    return {
        "total_requests": len(runs),
        "successful_requests": len(successful),
        "retries": len(retries),
        "errors": len(errors),
        "average_latency": round(
            sum(latency_values) / len(latency_values),
            3,
        ),
        "average_confidence": round(
            sum(confidence_values) / len(confidence_values),
            2,
        ),
    }


def get_failure_patterns() -> dict:
    """Count failure patterns."""

    runs = load_runs()

    patterns = {}

    for run in runs:
        pattern = run.get(
            "failure_pattern",
            "unknown",
        )

        if pattern == "none":
            continue

        patterns[pattern] = patterns.get(
            pattern,
            0,
        ) + 1

    return patterns