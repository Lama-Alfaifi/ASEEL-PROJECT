from __future__ import annotations

import csv
import statistics
from pathlib import Path

from retrieval.vector_store import CulturalVectorStore


# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

OUTPUT_FILE = BASE_DIR / "data" / "relevance_results.csv"

TOP_K = 5


# ============================================================
# Region mapping
# ============================================================

REGION_MAP = {
    "CENTERAL": "Central",
    "CENTRAL": "Central",
    "EAST": "East",
    "WEST": "West",
    "NORTH": "North",
    "SOUTH": "South",
}


# ============================================================
# Load benchmark questions
# ============================================================

def load_questions() -> list[dict]:
    questions = []

    for file in sorted(RAW_DATA_DIR.glob("*.csv")):
        name = file.stem.upper()

        region = None

        for key, value in REGION_MAP.items():
            if key in name:
                region = value
                break

        if not region:
            print(f"Skipping unknown region file: {file.name}")
            continue

        print(f"Loading: {file.name} -> {region}")

        with file.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:
                question = (row.get("Question") or "").strip()

                if not question:
                    continue

                questions.append(
                    {
                        "question": question,
                        "expected_region": region,
                        "file": file.name,
                        "question_type": (
                            row.get("Question Type") or ""
                        ).strip(),
                        "domain": (
                            row.get("Domain") or ""
                        ).strip(),
                        "category": (
                            row.get("Category") or ""
                        ).strip(),
                    }
                )

    return questions


# ============================================================
# Analyze retrieval
# ============================================================

def analyze():

    print("\nLoading benchmark...")
    questions = load_questions()

    print(f"\nTotal questions: {len(questions)}")

    store = CulturalVectorStore()

    results = []

    print("\nRunning retrieval...\n")

    for i, item in enumerate(questions, start=1):

        question = item["question"]
        region = item["expected_region"]

        retrieved = store.search(
            query=question,
            region=region,
            limit=TOP_K,
        )

        scores = [
            float(result.relevance)
            for result in retrieved
        ]

        if scores:
            max_score = max(scores)
            avg_score = statistics.mean(scores)
            top_score = scores[0]
        else:
            max_score = 0.0
            avg_score = 0.0
            top_score = 0.0

        results.append(
            {
                **item,
                "top_score": round(top_score, 4),
                "max_score": round(max_score, 4),
                "average_score": round(avg_score, 4),
                "num_results": len(scores),
            }
        )

        if i % 25 == 0 or i == len(questions):
            print(f"Processed {i}/{len(questions)}")


    # ========================================================
    # Save detailed results
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "question",
        "expected_region",
        "file",
        "question_type",
        "domain",
        "category",
        "top_score",
        "max_score",
        "average_score",
        "num_results",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)


    # ========================================================
    # Statistics
    # ========================================================

    max_scores = [
        r["max_score"]
        for r in results
        if r["num_results"] > 0
    ]

    if not max_scores:
        print("\nNo retrieval results found.")
        return


    print("\n" + "=" * 60)
    print("RELEVANCE SCORE ANALYSIS")
    print("=" * 60)

    print(f"\nQuestions: {len(results)}")
    print(f"Questions with results: {len(max_scores)}")

    print(f"\nMinimum: {min(max_scores):.4f}")
    print(f"Maximum: {max(max_scores):.4f}")
    print(f"Mean:    {statistics.mean(max_scores):.4f}")
    print(f"Median:  {statistics.median(max_scores):.4f}")


    # ========================================================
    # Percentiles
    # ========================================================

    sorted_scores = sorted(max_scores)

    def percentile(p: float) -> float:
        index = int((len(sorted_scores) - 1) * p)
        return sorted_scores[index]

    print(f"P25:     {percentile(0.25):.4f}")
    print(f"P75:     {percentile(0.75):.4f}")
    print(f"P90:     {percentile(0.90):.4f}")


    # ========================================================
    # Threshold analysis
    # ========================================================

    thresholds = [
        0.30,
        0.33,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
    ]

    print("\n" + "-" * 60)
    print("THRESHOLD ANALYSIS")
    print("-" * 60)

    print(
        f"{'Threshold':<12}"
        f"{'Passing':<12}"
        f"{'Percentage':<12}"
    )

    for threshold in thresholds:

        passing = sum(
            score >= threshold
            for score in max_scores
        )

        percentage = (
            passing / len(max_scores) * 100
        )

        print(
            f"{threshold:<12.2f}"
            f"{passing:<12}"
            f"{percentage:<12.2f}%"
        )


    # ========================================================
    # Weakest questions
    # ========================================================

    print("\n" + "-" * 60)
    print("10 WEAKEST RETRIEVALS")
    print("-" * 60)

    weakest = sorted(
        results,
        key=lambda x: x["max_score"],
    )[:10]

    for item in weakest:

        print(
            f"\nScore: {item['max_score']:.4f}"
        )
        print(
            f"Region: {item['expected_region']}"
        )
        print(
            f"Question: {item['question']}"
        )


    # ========================================================
    # Strongest questions
    # ========================================================

    print("\n" + "-" * 60)
    print("10 STRONGEST RETRIEVALS")
    print("-" * 60)

    strongest = sorted(
        results,
        key=lambda x: x["max_score"],
        reverse=True,
    )[:10]

    for item in strongest:

        print(
            f"\nScore: {item['max_score']:.4f}"
        )
        print(
            f"Region: {item['expected_region']}"
        )
        print(
            f"Question: {item['question']}"
        )


    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    print(
        f"\nDetailed results saved to:\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    analyze()