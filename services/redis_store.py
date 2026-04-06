from __future__ import annotations

import os
from typing import Any, Optional

from services.serialization import dumps, loads

try:
    import redis
except Exception:
    redis = None


class RedisStore:
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None

    def is_available(self) -> bool:
        return redis is not None

    def _get_client(self):
        if redis is None:
            return None
        if self._client is None:
            self._client = redis.Redis.from_url(self.url, decode_responses=False)
        return self._client

    def get_json(self, key: str) -> Optional[Any]:
        client = self._get_client()
        if client is None:
            return None
        try:
            payload = client.get(key)
        except Exception:
            return None
        if payload is None:
            return None
        return loads(payload)

    def set_json(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            payload = dumps(value)
            if ttl_seconds:
                client.setex(key, int(ttl_seconds), payload)
            else:
                client.set(key, payload)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.delete(key)
            return True
        except Exception:
            return False


redis_store = RedisStore()
