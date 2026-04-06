from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str
    source_type: str
    rank_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source_type": self.source_type,
            "rank_score": self.rank_score,
        }


@dataclass
class SourceDocument:
    title: str
    url: str
    content: str
    source_type: str
    rank_score: float
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "source_type": self.source_type,
            "rank_score": self.rank_score,
            "metadata": dict(self.metadata),
        }


@dataclass
class StructuredKnowledge:
    definitions: List[str] = field(default_factory=list)
    formulas: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    important_facts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "definitions": list(self.definitions),
            "formulas": list(self.formulas),
            "rules": list(self.rules),
            "examples": list(self.examples),
            "important_facts": list(self.important_facts),
        }


@dataclass
class RetrievalResult:
    content: str
    sources: List[SourceDocument]
    confidence: float
    structured: StructuredKnowledge
    query: str

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "sources": [source.to_dict() for source in self.sources],
            "confidence": self.confidence,
            "structured": self.structured.to_dict(),
            "query": self.query,
        }
