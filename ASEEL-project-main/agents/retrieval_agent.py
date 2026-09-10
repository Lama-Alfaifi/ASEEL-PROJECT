from __future__ import annotations
from agents.state import AseelState
from retrieval.vector_store import CulturalVectorStore
from tools.cultural_search import search_cultural_knowledge
from tools.metadata_filter import filter_by_metadata

def retrieve_knowledge(store: CulturalVectorStore):
    def node(state: AseelState) -> dict:
        results = search_cultural_knowledge(store, state["retrieval_query"], state.get("region"), limit=5)
        records = [{"question": x.record.question, "answer": x.record.answer, "choices": x.record.choices, "region": x.record.region, "domain": x.record.domain, "category": x.record.category, "relevance": x.relevance, "distance": x.distance} for x in results]
        return {"raw_semantic_results": records, "retrieved": filter_by_metadata(records, state.get("region"), state.get("category"))}
    return node