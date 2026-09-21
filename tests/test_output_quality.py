from __future__ import annotations

from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

from workflow.graph import ask
from memory.conversation_memory import ConversationMemory


TEST_CASES = [
    {
        "name": "East men's clothing",
        "query": "What traditional clothing is common for men in Dammam?",
    },
    {
        "name": "East women's clothing",
        "query": "What traditional clothing is common for women in Dammam?",
    },
    {
        "name": "Western clothing",
        "query": "What traditional clothing is common for men in Jeddah?",
    },
    {
        "name": "Central clothing",
        "query": "What traditional clothing is common for men in Riyadh?",
    },
    {
        "name": "Northern clothing",
        "query": "What traditional clothing is common for people in Tabuk?",
    },
    {
        "name": "Southern clothing",
        "query": "What traditional clothing is common in Faifa?",
    },
    {
        "name": "Food",
        "query": "What traditional food is associated with the Eastern Region?",
    },
    {
        "name": "Wedding",
        "query": "What cultural practices are common at Saudi weddings?",
    },
    {
        "name": "Social etiquette",
        "query": "What is appropriate etiquette when visiting a Saudi family?",
    },
    {
        "name": "Follow-up",
        "follow_up": True,
        "first_query": (
            "What traditional clothing is common for men in Dammam?"
        ),
        "query": "What about women?",
    },
]


def _evaluate_result(query: str, result: dict):
    test_case = LLMTestCase(
        input=query,
        actual_output=result.get("answer", ""),
        retrieval_context=[
            str(source)
            for source in result.get("sources", [])
        ],
    )

    metrics = [
        AnswerRelevancyMetric(threshold=0.7),
        FaithfulnessMetric(threshold=0.7),
    ]

    return test_case, metrics


def test_output_quality_dataset():
    test_cases = []
    metrics = []

    for case in TEST_CASES:
        if case.get("follow_up"):
            memory = ConversationMemory()

            ask(
                case["first_query"],
                memory=memory,
            )

            result = ask(
                case["query"],
                memory=memory,
            )
        else:
            result = ask(case["query"])

        test_case, case_metrics = _evaluate_result(
            case["query"],
            result,
        )

        test_cases.append(test_case)
        metrics.extend(case_metrics)

    evaluate(
        test_cases,
        [
            AnswerRelevancyMetric(threshold=0.7),
            FaithfulnessMetric(threshold=0.7),
        ],
    )