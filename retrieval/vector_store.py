from __future__ import annotations

from pathlib import Path
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config.settings import COLLECTION_NAME, VECTOR_DB_DIR
from retrieval.models import KnowledgeRecord, RetrievedKnowledge

class CulturalVectorStore:
    def __init__(self, directory: Path = VECTOR_DB_DIR, collection_name: str = COLLECTION_NAME):
        directory.mkdir(parents=True, exist_ok=True)
        self.client = PersistentClient(path=str(directory))
        embedding = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.collection = self.client.get_or_create_collection(collection_name, embedding_function=embedding, metadata={"hnsw:space": "cosine"})

    def replace(self, records: list[KnowledgeRecord]) -> None:
        if self.collection.count():
            self.client.delete_collection(self.collection.name)
            embedding = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            self.collection = self.client.get_or_create_collection(self.collection.name, embedding_function=embedding, metadata={"hnsw:space": "cosine"})
        self.collection.add(ids=[r.id for r in records], documents=[r.text for r in records], metadatas=[r.metadata | {"question": r.question, "answer": r.answer, "choices": r.choices} for r in records])

    def search(self, query: str, region: str | None = None, limit: int = 5) -> list[RetrievedKnowledge]:
        where = {"region": region} if region and region != "General" else None
        # Chroma raises when n_results exceeds the collection size, which is
        # common during small test/dev datasets.
        count = self.collection.count()
        if not count:
            return []
        if where:
            count = len(self.collection.get(where=where, include=[])["ids"])
            if not count:
                return []
        result = self.collection.query(query_texts=[query], n_results=min(limit, count), where=where, include=["documents", "metadatas", "distances"])
        found: list[RetrievedKnowledge] = []
        for metadata, distance in zip(result["metadatas"][0], result["distances"][0]):
            distance = float(distance)
            record = KnowledgeRecord(id="retrieved", question=metadata["question"], answer=metadata["answer"], choices=metadata.get("choices", ""), region=metadata["region"], domain=metadata["domain"], category=metadata["category"], question_type=metadata.get("question_type", "Unspecified"))
            # Chroma's cosine HNSW distance is a distance (lower is better),
            # so relevance is the derived similarity-like score: 1 - distance.
            found.append(RetrievedKnowledge(record, max(0.0, 1.0 - distance), distance))
        return found