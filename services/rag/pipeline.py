from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import List, Optional

from services.redis_store import redis_store
from services.runtime import run_async_blocking
from services.serialization import dumps, loads
from services.rag.content_cleaner import content_cleaner
from services.rag.embedding_service import embedding_service
from services.rag.fact_extractor import fact_extractor
from services.rag.local_search import LocalSearchIndex
from services.rag.models import RetrievalResult, SearchHit, SourceDocument, StructuredKnowledge
from services.rag.vector_store import FaissVectorStore
from services.rag.web_fetcher import web_fetcher
from services.rag.web_search_service import web_search_service


class RAGPipeline:
    def __init__(self, root_dir: Optional[Path] = None, timeout_seconds: int = 8):
        self.root_dir = Path(root_dir or Path(__file__).resolve().parent.parent.parent / "data" / "rag")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = self.root_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.local_search = LocalSearchIndex(self.root_dir / "whoosh")
        self.vector_store = FaissVectorStore(self.root_dir / "vector_store", dimension=embedding_service.dimension)
        self.timeout_seconds = timeout_seconds

    def retrieve(self, topic: str, subject: str = "", grade: Optional[int] = None, max_results: int = 4) -> RetrievalResult:
        query = self.build_query(topic, subject, grade)
        cache_key = self.cache_key(query, max_results)
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        result = run_async_blocking(self._retrieve_async(topic=topic, subject=subject, grade=grade, max_results=max_results))
        self._save_cache(cache_key, result)
        return result

    def build_query(self, topic: str, subject: str, grade: Optional[int]) -> str:
        parts = [topic.strip()]
        if subject:
            parts.append(subject.strip())
        if grade:
            parts.append(f"{grade}-sinf")
        parts.append("matematika")
        return " ".join(part for part in parts if part)

    async def _retrieve_async(self, topic: str, subject: str, grade: Optional[int], max_results: int) -> RetrievalResult:
        query = self.build_query(topic, subject, grade)
        hits = await web_search_service.search(query, topic=topic, subject=subject, max_results=max_results)
        raw_documents = await web_fetcher.fetch_many(hits)
        documents = self._collect_documents(hits, raw_documents, max_results=max_results)
        combined_content = "\n\n".join(document.content for document in documents if document.content).strip()
        structured = fact_extractor.extract(combined_content)
        confidence = self.compute_confidence(documents, structured)
        self._index_documents(documents)
        return RetrievalResult(
            content=combined_content,
            sources=documents,
            confidence=confidence,
            structured=structured,
            query=query,
        )

    def clean_html_content(self, raw_html: str, fallback: str = "", url: str = "") -> str:
        return content_cleaner.clean(raw_html, fallback=fallback, url=url)

    def structure_content(self, content: str) -> StructuredKnowledge:
        return fact_extractor.extract(content)

    def compute_confidence(self, sources: List[SourceDocument], structured: StructuredKnowledge) -> float:
        if not sources:
            return 0.0
        avg_rank = sum(source.rank_score for source in sources) / max(len(sources), 1)
        structure_signal = (
            len(structured.definitions)
            + len(structured.formulas)
            + len(structured.rules)
            + len(structured.examples)
            + len(structured.important_facts)
        )
        confidence = min(0.98, 0.35 + avg_rank * 0.45 + min(structure_signal, 12) * 0.02)
        return round(confidence, 3)

    def _collect_documents(self, hits: List[SearchHit], raw_documents: dict[str, str], max_results: int) -> List[SourceDocument]:
        documents: List[SourceDocument] = []
        for hit in hits[: max_results * 2]:
            cleaned = self.clean_html_content(raw_documents.get(hit.url, ""), fallback=hit.snippet, url=hit.url)
            if not cleaned:
                continue
            content = cleaned
            snippet = str(hit.snippet or "").strip()
            if snippet and snippet.lower() not in cleaned.lower():
                content = f"{snippet}\n{cleaned}".strip()
            documents.append(
                SourceDocument(
                    title=hit.title,
                    url=hit.url,
                    content=content,
                    source_type=hit.source_type,
                    rank_score=hit.rank_score,
                    metadata={"snippet": hit.snippet},
                )
            )
            if len(documents) >= max_results:
                break
        return documents

    def _index_documents(self, documents: List[SourceDocument]) -> None:
        if not documents:
            return
        payloads = [document.to_dict() for document in documents]
        self.local_search.index_documents(payloads)
        vectors = embedding_service.embed_texts([document.content for document in documents])
        self.vector_store.add(vectors, payloads)

    def cache_key(self, query: str, max_results: int) -> str:
        return hashlib.sha1(f"{query}|{max_results}".encode("utf-8")).hexdigest()

    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def _load_cache(self, cache_key: str) -> Optional[RetrievalResult]:
        redis_payload = redis_store.get_json(f"rag:{cache_key}")
        if redis_payload:
            return self._payload_to_result(redis_payload)
        path = self._cache_path(cache_key)
        if not path.exists():
            return None
        try:
            payload = loads(path.read_bytes())
        except Exception:
            return None
        if time.time() - float(payload.get("created_at", 0)) > 3600 * 12:
            return None
        return self._payload_to_result(payload)

    def _save_cache(self, cache_key: str, result: RetrievalResult) -> None:
        payload = result.to_dict()
        payload["created_at"] = time.time()
        redis_store.set_json(f"rag:{cache_key}", payload, ttl_seconds=3600 * 12)
        self._cache_path(cache_key).write_bytes(dumps(payload))

    def _payload_to_result(self, payload: dict) -> RetrievalResult:
        return RetrievalResult(
            content=payload.get("content", ""),
            sources=[
                SourceDocument(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    source_type=item.get("source_type", ""),
                    rank_score=float(item.get("rank_score", 0.0)),
                    metadata=dict(item.get("metadata") or {}),
                )
                for item in payload.get("sources", [])
            ],
            confidence=float(payload.get("confidence", 0.0)),
            structured=StructuredKnowledge(**dict(payload.get("structured") or {})),
            query=payload.get("query", ""),
        )
