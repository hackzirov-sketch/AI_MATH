from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np

from services.serialization import dumps, loads

try:
    import faiss
except Exception:
    faiss = None


@dataclass
class VectorMatch:
    score: float
    payload: Dict[str, object]


class FaissVectorStore:
    def __init__(self, index_dir: Path, dimension: int = 384):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self._index = None
        self._payloads: List[Dict[str, object]] = []
        self._vectors = np.zeros((0, self.dimension), dtype=np.float32)
        self._index_path = self.index_dir / "rag.index"
        self._metadata_path = self.index_dir / "rag_metadata.json"
        self._vectors_path = self.index_dir / "rag_vectors.json"
        self._load()

    def add(self, vectors: np.ndarray, payloads: Sequence[Dict[str, object]]) -> None:
        if len(vectors) == 0 or not payloads:
            return
        normalized = self._normalize_vectors(vectors)
        self._payloads.extend(dict(payload) for payload in payloads)
        if faiss is not None:
            index = self._get_index()
            index.add(normalized)
        else:
            self._vectors = np.vstack([self._vectors, normalized]).astype(np.float32)
        self._save()

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[VectorMatch]:
        if not self._payloads:
            return []
        normalized_query = self._normalize_vectors(np.asarray([query_vector], dtype=np.float32))
        if faiss is not None:
            index = self._get_index()
            scores, indices = index.search(normalized_query, min(top_k, len(self._payloads)))
            matches: List[VectorMatch] = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self._payloads):
                    continue
                matches.append(VectorMatch(score=float(score), payload=dict(self._payloads[idx])))
            return matches
        scores = np.dot(self._vectors, normalized_query[0])
        order = np.argsort(scores)[::-1][:top_k]
        return [VectorMatch(score=float(scores[index]), payload=dict(self._payloads[index])) for index in order]

    def _get_index(self):
        if self._index is None and faiss is not None:
            self._index = faiss.IndexFlatIP(self.dimension)
            if len(self._vectors):
                self._index.add(self._vectors)
        return self._index

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        normalized = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(normalized, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return normalized / norms

    def _load(self) -> None:
        if self._metadata_path.exists():
            try:
                self._payloads = list(loads(self._metadata_path.read_bytes()) or [])
            except Exception:
                self._payloads = []
        if faiss is not None and self._index_path.exists():
            try:
                self._index = faiss.read_index(str(self._index_path))
            except Exception:
                self._index = None
        elif self._vectors_path.exists():
            try:
                raw = loads(self._vectors_path.read_bytes())
                self._vectors = np.asarray(raw or [], dtype=np.float32)
            except Exception:
                self._vectors = np.zeros((0, self.dimension), dtype=np.float32)

    def _save(self) -> None:
        self._metadata_path.write_bytes(dumps(self._payloads))
        if faiss is not None:
            index = self._get_index()
            if index is not None:
                faiss.write_index(index, str(self._index_path))
            return
        self._vectors_path.write_bytes(dumps(self._vectors.tolist()))
