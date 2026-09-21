from tools.evidence_validation import validate_evidence


def test_validate_evidence_keeps_only_strongest_three():
    records = [
        {
            "question": "Strong evidence",
            "answer": "Answer 1",
            "region": "West",
            "relevance": 0.8348,
        },
        {
            "question": "Medium evidence",
            "answer": "Answer 2",
            "region": "West",
            "relevance": 0.4135,
        },
        {
            "question": "Weak evidence",
            "answer": "Answer 3",
            "region": "West",
            "relevance": 0.3448,
        },
        {
            "question": "Too weak",
            "answer": "Answer 4",
            "region": "West",
            "relevance": 0.3228,
        },
        {
            "question": "Very weak",
            "answer": "Answer 5",
            "region": "West",
            "relevance": 0.2884,
        },
    ]

    validated, reason, confidence = validate_evidence(
        records,
        "West",
    )

    # Only records >= MIN_RELEVANCE should survive.
    # Then only the strongest 3 should be returned.
    assert len(validated) == 3

    # Strongest evidence should come first.
    assert validated[0]["relevance"] == 0.8348
    assert validated[1]["relevance"] == 0.4135
    assert validated[2]["relevance"] == 0.3448

    # Weak evidence should be excluded.
    assert all(
        record["relevance"] >= 0.33
        for record in validated
    )

    # Confidence should come from the strongest evidence.
    assert confidence == 0.83

    assert "relevance" in reason