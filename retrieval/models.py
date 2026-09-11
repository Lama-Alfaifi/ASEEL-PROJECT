from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class KnowledgeRecord:
    id: str
    question: str
    answer: str
    choices: str
    region: str
    domain: str
    category: str
    question_type: str

    @property
    def text(self) -> str:
        return f"Region: {self.region}\nDomain: {self.domain}\nCategory: {self.category}\nQuestion: {self.question}\nAnswer: {self.answer}"

    @property
    def metadata(self) -> dict[str, str]:
        return {"region": self.region, "domain": self.domain, "category": self.category, "question_type": self.question_type}

@dataclass(frozen=True)
class RetrievedKnowledge:
    record: KnowledgeRecord
    relevance: float
    distance: float | None = None