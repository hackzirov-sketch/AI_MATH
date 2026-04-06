from __future__ import annotations

import hashlib
import os
from typing import Iterable

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class EmbeddingService:
    def __init__(self, model_name: str | None = None, dimension: int = 384):
        self.model_name = model_name or os.getenv("SENTENCE_TRANSFORMER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.dimension = dimension
        self._model = None

    def embed_texts(self, texts: Iterable[str]) -> np.ndarray:
        items = [str(text or "") for text in texts]
        if not items:
            return np.zeros((0, self.dimension), dtype=np.float32)
        model = self._get_model()
        if model is not None:
            vectors = model.encode(items, convert_to_numpy=True, normalize_embeddings=True)
            return np.asarray(vectors, dtype=np.float32)
        return np.vstack([self._hash_embedding(text) for text in items]).astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        vectors = self.embed_texts([text])
        return vectors[0] if len(vectors) else np.zeros((self.dimension,), dtype=np.float32)

    def _get_model(self):
        if SentenceTransformer is None:
            return None
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                self._model = None
        return self._model

    def _hash_embedding(self, text: str) -> np.ndarray:
        vector = np.zeros((self.dimension,), dtype=np.float32)
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimension
            vector[index] += 1.0
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector


embedding_service = EmbeddingService()
