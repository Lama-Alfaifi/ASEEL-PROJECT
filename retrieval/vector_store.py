from __future__ import annotations

from pathlib import Path

from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config.settings import COLLECTION_NAME, VECTOR_DB_DIR
from retrieval.models import KnowledgeRecord, RetrievedKnowledge


class CulturalVectorStore:

    REGION_ALIASES = {
        # South
        "south": "South",
        "southern": "South",
        "southern region": "South",
        "south region": "South",
        "south saudi arabia": "South",
        "southern saudi arabia": "South",
        "southern area": "South",
        "asir": "South",
        "jazan": "South",
        "najran": "South",
        "abha": "South",

        # North
        "north": "North",
        "northern": "North",
        "northern region": "North",
        "north region": "North",
        "north saudi arabia": "North",
        "northern saudi arabia": "North",
        "tabuk": "North",
        "hail": "North",
        "al jouf": "North",

        # East
        "east": "East",
        "eastern": "East",
        "eastern region": "East",
        "east region": "East",
        "eastern saudi arabia": "East",
        "east saudi arabia": "East",
        "dammam": "East",
        "khobar": "East",
        "al ahsa": "East",
        "ahsaa": "East",

        # West
        "west": "West",
        "western": "West",
        "western region": "West",
        "west region": "West",
        "western saudi arabia": "West",
        "west saudi arabia": "West",
        "hijaz": "West",
        "hejazi": "West",
        "makkah": "West",
        "mecca": "West",
        "madinah": "West",
        "medina": "West",
        "jeddah": "West",
        "taif": "West",

        # Central
        "central": "Central",
        "central region": "Central",
        "central saudi arabia": "Central",
        "central area": "Central",
        "riyadh": "Central",
        "najd": "Central",
    }

    def __init__(
        self,
        directory: Path = VECTOR_DB_DIR,
        collection_name: str = COLLECTION_NAME,
    ):
        directory.mkdir(parents=True, exist_ok=True)

        self.client = PersistentClient(path=str(directory))

        embedding = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        self.collection = self.client.get_or_create_collection(
            collection_name,
            embedding_function=embedding,
            metadata={"hnsw:space": "cosine"},
        )

    @classmethod
    def normalize_region(cls, region: str | None) -> str | None:
        """
        Convert different region names into the canonical
        region names used by the Chroma metadata.
        """

        if not region:
            return None

        region_key = region.strip().lower()

        return cls.REGION_ALIASES.get(
            region_key,
            region.strip(),
        )

    def replace(self, records: list[KnowledgeRecord]) -> None:
        if self.collection.count():
            self.client.delete_collection(self.collection.name)

            embedding = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            self.collection = self.client.get_or_create_collection(
                self.collection.name,
                embedding_function=embedding,
                metadata={"hnsw:space": "cosine"},
            )

        self.collection.add(
            ids=[r.id for r in records],
            documents=[r.text for r in records],
            metadatas=[
                r.metadata
                | {
                    "question": r.question,
                    "answer": r.answer,
                    "choices": r.choices,
                }
                for r in records
            ],
        )

    def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedKnowledge]:

        # Normalize region before searching Chroma.
        normalized_region = self.normalize_region(region)

        if normalized_region == "General":
            # General is nationwide: only General records are relevant.
            where = {"region": "General"}
        elif normalized_region:
            # Regional queries may use both region-specific and nationwide evidence.
            where = {
                "$or": [
                    {"region": normalized_region},
                    {"region": "General"},
                ]
            }
        else:
            # Auto / no resolved region: search the whole KB.
            where = None

        # Chroma raises when n_results exceeds the collection size.
        count = self.collection.count()

        if not count:
            return []

        # If a region filter exists, make sure that region
        # actually exists in the collection.
        if where:
            count = len(
                self.collection.get(
                    where=where,
                    include=[],
                )["ids"]
            )

            if not count:
                return []

        result = self.collection.query(
            query_texts=[query],
            n_results=min(limit, count),
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        found: list[RetrievedKnowledge] = []

        for metadata, distance in zip(
            result["metadatas"][0],
            result["distances"][0],
        ):
            distance = float(distance)

            record = KnowledgeRecord(
                id="retrieved",
                question=metadata["question"],
                answer=metadata["answer"],
                choices=metadata.get("choices", ""),
                region=metadata["region"],
                domain=metadata["domain"],
                category=metadata["category"],
                question_type=metadata.get(
                    "question_type",
                    "Unspecified",
                ),
            )

            # Cosine HNSW returns distance.
            # Lower distance = higher similarity.
            relevance = max(0.0, 1.0 - distance)

            found.append(
                RetrievedKnowledge(
                    record,
                    relevance,
                    distance,
                )
            )

        return found








# from __future__ import annotations

# from pathlib import Path
# from chromadb import PersistentClient
# from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# from config.settings import COLLECTION_NAME, VECTOR_DB_DIR
# from retrieval.models import KnowledgeRecord, RetrievedKnowledge

# class CulturalVectorStore:
#     def __init__(self, directory: Path = VECTOR_DB_DIR, collection_name: str = COLLECTION_NAME):
#         directory.mkdir(parents=True, exist_ok=True)
#         self.client = PersistentClient(path=str(directory))
#         embedding = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
#         self.collection = self.client.get_or_create_collection(collection_name, embedding_function=embedding, metadata={"hnsw:space": "cosine"})

#     def replace(self, records: list[KnowledgeRecord]) -> None:
#         if self.collection.count():
#             self.client.delete_collection(self.collection.name)
#             embedding = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
#             self.collection = self.client.get_or_create_collection(self.collection.name, embedding_function=embedding, metadata={"hnsw:space": "cosine"})
#         self.collection.add(ids=[r.id for r in records], documents=[r.text for r in records], metadatas=[r.metadata | {"question": r.question, "answer": r.answer, "choices": r.choices} for r in records])

#     def search(self, query: str, region: str | None = None, limit: int = 5) -> list[RetrievedKnowledge]:
#         where = {"region": region} if region and region != "General" else None
#         # Chroma raises when n_results exceeds the collection size, which is
#         # common during small test/dev datasets.
#         count = self.collection.count()
#         if not count:
#             return []
#         if where:
#             count = len(self.collection.get(where=where, include=[])["ids"])
#             if not count:
#                 return []
#         result = self.collection.query(query_texts=[query], n_results=min(limit, count), where=where, include=["documents", "metadatas", "distances"])
#         found: list[RetrievedKnowledge] = []
#         for metadata, distance in zip(result["metadatas"][0], result["distances"][0]):
#             distance = float(distance)
#             record = KnowledgeRecord(id="retrieved", question=metadata["question"], answer=metadata["answer"], choices=metadata.get("choices", ""), region=metadata["region"], domain=metadata["domain"], category=metadata["category"], question_type=metadata.get("question_type", "Unspecified"))
#             # Chroma's cosine HNSW distance is a distance (lower is better),
#             # so relevance is the derived similarity-like score: 1 - distance.
#             found.append(RetrievedKnowledge(record, max(0.0, 1.0 - distance), distance))
#         return found