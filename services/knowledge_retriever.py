from __future__ import annotations

from pathlib import Path
from typing import Optional

from services.rag.content_cleaner import content_cleaner
from services.rag.fact_extractor import fact_extractor
from services.rag.models import RetrievalResult, SearchHit, SourceDocument, StructuredKnowledge
from services.rag.pipeline import RAGPipeline


_BASE_DIR = Path(__file__).resolve().parent.parent
_CACHE_DIR = _BASE_DIR / "data" / "rag" / "cache"


class KnowledgeRetriever:
    def __init__(self, cache_dir: Path = _CACHE_DIR, timeout_seconds: int = 8):
        self.cache_dir = Path(cache_dir)
        self.timeout_seconds = timeout_seconds
        self.pipeline = RAGPipeline(root_dir=self.cache_dir.parent, timeout_seconds=timeout_seconds)

    def retrieve(
        self,
        topic: str,
        subject: str = "",
        grade: Optional[int] = None,
        max_results: int = 4,
    ) -> RetrievalResult:
        return self.pipeline.retrieve(topic=topic, subject=subject, grade=grade, max_results=max_results)

    def _build_query(self, topic: str, subject: str, grade: Optional[int]) -> str:
        return self.pipeline.build_query(topic, subject, grade)

    def _clean_html_content(self, raw_html: str, fallback: str = "") -> str:
        return content_cleaner.clean(raw_html, fallback=fallback)

    def _structure_content(self, content: str) -> StructuredKnowledge:
        return fact_extractor.extract(content)

    def _compute_confidence(self, sources, structured: StructuredKnowledge) -> float:
        return self.pipeline.compute_confidence(sources, structured)


knowledge_retriever = KnowledgeRetriever()
