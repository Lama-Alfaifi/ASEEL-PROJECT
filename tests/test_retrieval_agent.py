import json

from agents import retrieval_agent as retrieval_module
from agents.retrieval_agent import retrieve_knowledge


def test_retrieval_uses_query_and_region(monkeypatch):
    fake_result = {
        "messages": [
            type(
                "ToolMessage",
                (),
                {
                    "type": "tool",
                    "content": json.dumps(
                        {
                            "results": [
                                {
                                    "question": "What food?",
                                    "answer": "A dataset answer",
                                    "choices": "",
                                    "region": "East",
                                    "domain": "Common",
                                    "category": "Food",
                                    "relevance": 0.9,
                                    "distance": 0.1,
                                }
                            ]
                        }
                    ),
                },
            )()
        ]
    }

    class FakeAgent:
        def invoke(self, payload):
            return fake_result

    monkeypatch.setattr(retrieval_module, "retrieval_agent", FakeAgent())

    result = retrieve_knowledge(
        {
            "retrieval_query": "food",
            "region": "East",
            "category": "Food",
        }
    )

    assert result["retrieved"]
    assert result["retrieved"][0]["region"] == "East"