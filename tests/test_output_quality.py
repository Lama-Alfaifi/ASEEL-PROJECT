from __future__ import annotations

import pytest
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
    {
        "name": "Multi-turn follow-up chain",
        "follow_up_chain": True,
        "queries": [
            "What traditional clothing is common for men in Dammam?",
            "What about women?",
            "And what about children?",
        ],
    },
    {
        "name": "Follow-up changes city mid-conversation",
        "follow_up_chain": True,
        "queries": [
            "What traditional clothing is common for men in Dammam?",
            "What about in Jeddah instead?",
        ],
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
        if case.get("follow_up_chain"):
            memory = ConversationMemory()
            result = None

            for query in case["queries"]:
                result = ask(query, memory=memory)

            # Only the final turn in the chain is scored — it's the one
            # that depends on every prior turn's memory being carried
            # forward correctly.
            evaluated_query = case["queries"][-1]

        elif case.get("follow_up"):
            memory = ConversationMemory()

            ask(
                case["first_query"],
                memory=memory,
            )

            result = ask(
                case["query"],
                memory=memory,
            )

            evaluated_query = case["query"]

        else:
            result = ask(case["query"])
            evaluated_query = case["query"]

        test_case, case_metrics = _evaluate_result(
            evaluated_query,
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

# ============================================================
# Grounding / safety tests — NOT scored with DeepEval.
#
# The correct behavior for these cases is REFUSING to answer
# ("insufficient evidence"), which AnswerRelevancyMetric can penalize as
# "not relevant to the question" even though it's exactly the safe,
# grounded response we want. These use direct assertions on the workflow's
# own status field instead, so a passing refusal never shows up as a
# failure in the DeepEval summary above.
# ============================================================

def test_fallback_when_topic_has_no_evidence():
    """A question with no matching knowledge-base coverage must refuse,
    not hallucinate a plausible-sounding cultural claim."""

    result = ask(
        "What is the traditional etiquette for visiting a Saudi space station?"
    )

    assert result["status"] == "fallback"
    assert result["confidence_score"] < 0.50


def test_fallback_when_region_is_unresolvable():
    """A location outside the supported regions must not silently fall
    back to an unrelated region's evidence."""

    result = ask(
        "What is the traditional clothing custom in Antarctica?"
    )

    assert result["status"] == "fallback"


# ============================================================
# Known current limitation — documented, not silently broken.
#
# ASEEL has no translation layer yet (planned separately). The knowledge
# base and the region/city/category resolvers are all English-only today,
# so an Arabic-language question is expected to fail to resolve region/
# category and to retrieve weak evidence via the English-only embedding
# model. This test records that current behavior explicitly so it turns
# into a clear, intentional regression signal once the translation layer
# (see project notes, section 3.5) is implemented — at that point this
# test should be updated to assert success instead of xfail.
# ============================================================

def test_arabic_query_grounded():
    """Section 3.5 acceptance test: Arabic question about a Saudi city
    must resolve region correctly and answer in Arabic, grounded in
    evidence — no more xfail now that the translation layer exists."""
    result = ask("ما هو اللباس التقليدي للرجال في الدمام؟")

    assert result["status"] == "grounded"
    assert result["confidence_score"] >= 0.50
    assert result.get("language") == "Arabic"
    assert result.get("region") == "East"
    # The answer itself should actually be in Arabic, not English.
    assert any(
        "\u0600" <= ch <= "\u06FF"
        for ch in result["answer"]
    )


def test_french_query_grounded():
    """French → English internally → French answer, per section 3.5's
    explicit French example."""
    result = ask(
        "Quels vêtements traditionnels les hommes portent-ils à Djeddah?"
    )

    assert result["status"] == "grounded"
    assert result.get("language") == "French"
    assert result.get("region") == "West"


def test_chinese_query_grounded():
    """China is consistently among Saudi tourism's top international
    source markets (see connectingtravel.com / gulfnews.com reporting on
    2025 arrivals)."""
    result = ask("利雅得男士传统服装是什么?")

    assert result["status"] == "grounded"
    assert result.get("language") == "Chinese"
    assert result.get("region") == "Central"


def test_urdu_query_grounded():
    """Pakistan is among the fastest-growing inbound markets in 2025
    (Umrah + leisure travel combined)."""
    result = ask("دمام میں مردوں کا روایتی لباس کیا ہے؟")

    assert result["status"] == "grounded"
    assert result.get("language") == "Urdu"
    assert result.get("region") == "East"


def test_indonesian_query_grounded():
    """Indonesia is a major source of Umrah-driven visitors to Saudi
    Arabia."""
    result = ask("Apa pakaian tradisional pria di Jeddah?")

    assert result["status"] == "grounded"
    assert result.get("language") == "Indonesian"
    assert result.get("region") == "West"


def test_arabic_follow_up_keeps_language_and_context():
    """A follow-up in the same language must keep both the resolved
    region/category from memory AND the response language — this is the
    translation layer working together with the memory layer, not either
    one in isolation."""
    memory = ConversationMemory()

    ask(
        "ما هو اللباس التقليدي للرجال في الدمام؟",
        memory=memory,
    )

    result = ask(
        "ماذا عن النساء؟",
        memory=memory,
    )

    assert result["status"] == "grounded"
    assert result.get("region") == "East"
    assert any(
        "\u0600" <= ch <= "\u06FF"
        for ch in result["answer"]
    )