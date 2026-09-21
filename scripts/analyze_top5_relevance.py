from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean, median

from retrieval.vector_store import CulturalVectorStore


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"


REGION_MAP = {
    "CENTERAL.csv": "Central",
    "EAST.csv": "East",
    "NORTH.csv": "North",
    "SOUTH.csv": "South",
    "WEST.csv": "West",
}


def load_questions():
    questions = []

    for file_name, region in REGION_MAP.items():
        path = RAW_DATA_DIR / file_name

        if not path.exists():
            print(f"Missing file: {file_name}")
            continue

        print(f"Loading: {file_name} -> {region}")

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                question = (
                    row.get("question")
                    or row.get("Question")
                    or ""
                ).strip()

                if question:
                    questions.append(
                        {
                            "question": question,
                            "region": region,
                        }
                    )

    return questions


def main():
    print("\nLoading benchmark...")
    questions = load_questions()

    print(f"\nTotal questions: {len(questions)}")

    store = CulturalVectorStore()

    results = []

    for index, item in enumerate(questions, start=1):
        query = item["question"]
        region = item["region"]

        retrieved = store.search(
            query=query,
            region=region,
            limit=5,
        )

        scores = [round(r.relevance, 4) for r in retrieved]

        while len(scores) < 5:
            scores.append(None)

        results.append(
            {
                "question": query,
                "region": region,
                "score_1": scores[0],
                "score_2": scores[1],
                "score_3": scores[2],
                "score_4": scores[3],
                "score_5": scores[4],
            }
        )

        if index % 25 == 0:
            print(f"Processed {index}/{len(questions)}")


    # ---------------------------------------------------------
    # Save detailed results
    # ---------------------------------------------------------

    output_file = BASE_DIR / "data" / "top5_relevance_results.csv"

    with output_file.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        fieldnames = [
            "question",
            "region",
            "score_1",
            "score_2",
            "score_3",
            "score_4",
            "score_5",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)


    # ---------------------------------------------------------
    # Analyze every position
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TOP-5 RELEVANCE ANALYSIS")
    print("=" * 60)

    for position in range(1, 6):

        scores = [
            row[f"score_{position}"]
            for row in results
            if row[f"score_{position}"] is not None
        ]

        if not scores:
            continue

        print(f"\nTop-{position}")
        print(f"Count:  {len(scores)}")
        print(f"Min:    {min(scores):.4f}")
        print(f"Mean:   {mean(scores):.4f}")
        print(f"Median: {median(scores):.4f}")
        print(f"Max:    {max(scores):.4f}")


    # ---------------------------------------------------------
    # How many results are above each threshold?
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("RESULT DISTRIBUTION")
    print("=" * 60)

    all_scores = []

    for row in results:
        for position in range(1, 6):
            score = row[f"score_{position}"]

            if score is not None:
                all_scores.append(score)

    print(f"\nTotal retrieved results: {len(all_scores)}")

    for threshold in [0.30, 0.33, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:

        passed = sum(
            score >= threshold
            for score in all_scores
        )

        percentage = passed / len(all_scores) * 100

        print(
            f"{threshold:.2f} -> "
            f"{passed}/{len(all_scores)} "
            f"({percentage:.2f}%)"
        )


    # ---------------------------------------------------------
    # Questions where Top-1 is strong but Top-5 is weak
    # ---------------------------------------------------------

    suspicious = []

    for row in results:

        scores = [
            row[f"score_{i}"]
            for i in range(1, 6)
            if row[f"score_{i}"] is not None
        ]

        if len(scores) < 5:
            continue

        top1 = scores[0]
        top5 = scores[4]

        if top1 >= 0.80 and top5 < 0.50:
            suspicious.append(row)


    print("\n" + "=" * 60)
    print("STRONG TOP-1 / WEAK TOP-5")
    print("=" * 60)

    print(
        f"\nFound {len(suspicious)} questions "
        "where Top-1 >= 0.80 but Top-5 < 0.50."
    )

    for row in suspicious[:20]:

        scores = [
            row[f"score_{i}"]
            for i in range(1, 6)
        ]

        print("\nQuestion:")
        print(row["question"])
        print("Region:", row["region"])
        print("Scores:", scores)


    # ---------------------------------------------------------
    # Weakest Top-5 averages
    # ---------------------------------------------------------

    weakest = []

    for row in results:

        scores = [
            row[f"score_{i}"]
            for i in range(1, 6)
            if row[f"score_{i}"] is not None
        ]

        if scores:
            weakest.append(
                (
                    mean(scores),
                    row["question"],
                    row["region"],
                    scores,
                )
            )

    weakest.sort()

    print("\n" + "=" * 60)
    print("10 QUESTIONS WITH WEAKEST TOP-5 AVERAGE")
    print("=" * 60)

    for avg, question, region, scores in weakest[:10]:

        print(f"\nAverage: {avg:.4f}")
        print(f"Region:  {region}")
        print(f"Scores:  {scores}")
        print(f"Question: {question}")


    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    print(f"\nSaved detailed results to:")
    print(output_file)


if __name__ == "__main__":
    main()