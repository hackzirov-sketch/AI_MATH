from __future__ import annotations

from pathlib import Path
from typing import Optional

from services.rag.models import RetrievalResult, SearchHit, SourceDocument, StructuredKnowledge


_BASE_DIR = Path(__file__).resolve().parent.parent
_CACHE_DIR = _BASE_DIR / "data" / "rag" / "cache"


class KnowledgeRetriever:
    def __init__(self, cache_dir: Path = _CACHE_DIR, timeout_seconds: int = 8):
        self.cache_dir = Path(cache_dir)
        self.timeout_seconds = timeout_seconds
        self._pipeline = None
        self._content_cleaner = None
        self._fact_extractor = None

    def retrieve(
        self,
        topic: str,
        subject: str = "",
        grade: Optional[int] = None,
        max_results: int = 4,
    ) -> RetrievalResult:
        return self._get_pipeline().retrieve(
            topic=topic,
            subject=subject,
            grade=grade,
            max_results=max_results,
        )

    def _build_query(self, topic: str, subject: str, grade: Optional[int]) -> str:
        return self._get_pipeline().build_query(topic, subject, grade)

    def _clean_html_content(self, raw_html: str, fallback: str = "") -> str:
        return self._get_content_cleaner().clean(raw_html, fallback=fallback)

    def _structure_content(self, content: str) -> StructuredKnowledge:
        return self._get_fact_extractor().extract(content)

    def _compute_confidence(self, sources, structured: StructuredKnowledge) -> float:
        return self._get_pipeline().compute_confidence(sources, structured)

    def _get_pipeline(self):
        if self._pipeline is None:
            from services.rag.pipeline import RAGPipeline

            self._pipeline = RAGPipeline(
                root_dir=self.cache_dir.parent,
                timeout_seconds=self.timeout_seconds,
            )
        return self._pipeline

    def _get_content_cleaner(self):
        if self._content_cleaner is None:
            from services.rag.content_cleaner import content_cleaner

            self._content_cleaner = content_cleaner
        return self._content_cleaner

    def _get_fact_extractor(self):
        if self._fact_extractor is None:
            from services.rag.fact_extractor import fact_extractor

            self._fact_extractor = fact_extractor
        return self._fact_extractor


knowledge_retriever = KnowledgeRetriever()
