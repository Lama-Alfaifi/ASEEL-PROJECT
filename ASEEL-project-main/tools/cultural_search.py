from __future__ import annotations
from retrieval.vector_store import CulturalVectorStore

def search_cultural_knowledge(store: CulturalVectorStore, query: str, region: str | None, limit: int = 5):
    """The retrieval agent's sole knowledge access tool."""
    return store.search(query=query, region=region, limit=limit)
