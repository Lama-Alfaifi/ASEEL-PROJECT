from retrieval.vector_store import CulturalVectorStore

store = CulturalVectorStore()

tests = [
    ("Central", "What traditional dish is associated with Riyadh?"),
    ("Central", "What is Al-Marqooq?"),

    ("East", "What traditional food is associated with Al-Ahsa?"),
    ("East", "What traditional food is common in the Eastern Province?"),

    ("West", "What traditional food is common in Jeddah?"),
    ("West", "What traditional dish is common in the western region of Saudi Arabia?"),

    ("South", "What traditional food is associated with Southern Saudi Arabia?"),
    ("South", "What traditional dish is associated with Jazan?"),

    ("North", "What traditional food is common in Northern Saudi Arabia?"),
    ("North", "What is the most common breakfast dish in Northern Saudi Arabia?"),
]

for region, question in tests:
    print("\n" + "=" * 60)
    print(f"Expected region: {region}")
    print(f"Question: {question}")

    results = store.search(question, region, 5)

    for i, result in enumerate(results, 1):
        print(
            f"{i}. [{result.record.region}] "
            f"relevance={result.relevance:.3f} | "
            f"{result.record.question}"
        )