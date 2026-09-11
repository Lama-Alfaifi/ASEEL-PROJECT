from agents.understanding import understand_context
from agents.response import generate_response
from agents.validation import validate_cultural_knowledge
from workflow.graph import route_after_validation

def test_understanding_extracts_region_and_role():
    result = understand_context({"query": "As a tourist visiting the East, what should I eat?"})
    assert result["region"] == "East"
    assert result["user_role"] == "Tourist"

def test_validation_rejects_irrelevant_knowledge(monkeypatch):
    monkeypatch.setattr("tools.evidence_validation.MIN_RELEVANCE", 0.7)
    state = {"region": "East", "retrieved": [{"region": "East", "relevance": 0.2}]}
    result = validate_cultural_knowledge(state)
    assert result["validated"] == []
    assert route_after_validation({**state, **result, "attempts": 1}) == "respond"

def test_validation_rejects_wrong_region(monkeypatch):
    monkeypatch.setattr("tools.evidence_validation.MIN_RELEVANCE", 0.1)
    result = validate_cultural_knowledge({"region": "East", "retrieved": [{"region": "West", "relevance": 0.9}]})
    assert result["validated"] == []

def test_fallback_when_no_knowledge_is_available():
    result = generate_response({"query": "What is the etiquette on Mars?", "validated": []})
    assert result["status"] == "fallback"
    assert "could not find" in result["answer"]

def test_grounded_response_uses_validated_facts():
    result = generate_response(
        {
            "query": "Question",
            "region": "East",
            "validated": [
                {
                    "region": "East",
                    "answer": "Dataset answer",
                    "question": "Dataset question",
                    "category": "Food",
                    "relevance": 0.9,
                }
            ],
            "confidence_score": 0.9,
        }
    )

    assert result["status"] == "grounded"
    assert result["answer"]
    assert result["answer"] != (
        "I could not find enough reliable cultural evidence "
        "in the ASEEL knowledge base to answer this question confidently."
    )

def test_route_to_refine_when_validation_fails():
    state = {
        "confidence_score": 0.4,
        "attempts": 0,
    }

    assert route_after_validation(state) == "refine"


def test_route_to_respond_after_retry_fails():
    state = {
        "confidence_score": 0.4,
        "attempts": 1,
    }

    assert route_after_validation(state) == "respond"