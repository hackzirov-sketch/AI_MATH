from __future__ import annotations

import asyncio
from typing import Dict, Iterable

try:
    import httpx
except Exception:
    httpx = None

from services.rag.models import SearchHit


class WebFetcher:
    def __init__(self, timeout_seconds: int = 8, concurrency: int = 4):
        self.timeout_seconds = timeout_seconds
        self.concurrency = max(1, concurrency)

    async def fetch_many(self, hits: Iterable[SearchHit]) -> Dict[str, str]:
        items = [hit for hit in hits if hit.url]
        if not items or httpx is None:
            return {}
        semaphore = asyncio.Semaphore(self.concurrency)
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            tasks = [self._fetch_hit(client, semaphore, hit) for hit in items]
            pairs = await asyncio.gather(*tasks, return_exceptions=True)
        payload: Dict[str, str] = {}
        for pair in pairs:
            if isinstance(pair, tuple):
                payload[pair[0]] = pair[1]
        return payload

    async def _fetch_hit(self, client, semaphore: asyncio.Semaphore, hit: SearchHit):
        async with semaphore:
            try:
                response = await client.get(hit.url)
                response.raise_for_status()
            except Exception:
                return hit.url, ""
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type and "text/plain" not in content_type:
                return hit.url, hit.snippet
            return hit.url, response.text


web_fetcher = WebFetcher()
