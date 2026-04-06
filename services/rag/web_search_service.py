from __future__ import annotations

import html
import os
import re
from typing import Iterable, List
from urllib.parse import parse_qs, quote, unquote, urlparse

try:
    import httpx
except Exception:
    httpx = None

from services.rag.models import SearchHit

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None


class WebSearchService:
    def __init__(self, timeout_seconds: int = 8):
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, topic: str, subject: str, max_results: int = 4) -> List[SearchHit]:
        hits: List[SearchHit] = []
        hits.extend(await self._search_serper(query))
        hits.extend(await self._search_duckduckgo_html(query))
        hits.extend(await self._search_wikipedia(topic, subject))
        ranked = self._rank_hits(query, hits)
        deduped: List[SearchHit] = []
        seen = set()
        for hit in ranked:
            normalized = hit.url.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(hit)
            if len(deduped) >= max_results * 2:
                break
        return deduped

    async def _search_serper(self, query: str) -> List[SearchHit]:
        api_key = os.getenv("SERPER_API_KEY", "").strip()
        if not api_key or httpx is None:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "gl": "uz", "hl": "uz"},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []
        hits: List[SearchHit] = []
        for item in payload.get("organic", [])[:5]:
            title = self._normalize_text(item.get("title", ""))
            url = str(item.get("link") or "").strip()
            snippet = self._normalize_text(item.get("snippet", ""))
            if title and url:
                hits.append(SearchHit(title=title, url=url, snippet=snippet, source_type="serper"))
        return hits

    async def _search_duckduckgo_html(self, query: str) -> List[SearchHit]:
        if httpx is None:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers={"User-Agent": "Mozilla/5.0"}) as client:
                response = await client.get(f"https://html.duckduckgo.com/html/?q={quote(query)}")
                response.raise_for_status()
                body = response.text
        except Exception:
            return []
        titles = re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', body, flags=re.IGNORECASE | re.DOTALL)
        snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', body, flags=re.IGNORECASE | re.DOTALL)
        hits: List[SearchHit] = []
        for index, (url, title) in enumerate(titles[:5]):
            snippet = snippets[index] if index < len(snippets) else ""
            hits.append(
                SearchHit(
                    title=self._normalize_text(self._strip_tags(title)),
                    url=self._normalize_duckduckgo_url(html.unescape(url)),
                    snippet=self._normalize_text(self._strip_tags(snippet)),
                    source_type="duckduckgo",
                )
            )
        return hits

    async def _search_wikipedia(self, topic: str, subject: str) -> List[SearchHit]:
        if httpx is None:
            return []
        candidates = [topic.strip()]
        if subject and subject.lower() not in topic.lower():
            candidates.append(f"{topic.strip()} {subject.strip()}")
        hits: List[SearchHit] = []
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers={"User-Agent": "Mozilla/5.0"}) as client:
            for lang in ("uz", "en"):
                for candidate in candidates:
                    try:
                        response = await client.get(
                            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(candidate.replace(' ', '_'))}"
                        )
                    except Exception:
                        continue
                    if response.status_code != 200:
                        continue
                    payload = response.json()
                    title = self._normalize_text(payload.get("title", candidate))
                    url = (
                        payload.get("content_urls", {})
                        .get("desktop", {})
                        .get("page", f"https://{lang}.wikipedia.org/wiki/{quote(candidate.replace(' ', '_'))}")
                    )
                    snippet = self._normalize_text(payload.get("extract", ""))
                    if title and url and snippet:
                        hits.append(SearchHit(title=title, url=url, snippet=snippet, source_type="wikipedia"))
                        return hits
        return hits

    def _rank_hits(self, query: str, hits: Iterable[SearchHit]) -> List[SearchHit]:
        query_tokens = self._tokenize(query)
        ranked: List[SearchHit] = []
        for hit in hits:
            text = f"{hit.title} {hit.snippet}"
            tokens = self._tokenize(text)
            overlap = len(query_tokens & tokens) / max(len(query_tokens), 1)
            fuzzy = 0.0
            if fuzz is not None:
                fuzzy = fuzz.token_set_ratio(query, text) / 100.0
            score = overlap * 0.65 + fuzzy * 0.2
            domain = urlparse(hit.url).netloc.lower()
            if "wikipedia.org" in domain:
                score += 0.25
            if ".edu" in domain or "khanacademy" in domain or "byjus" in domain:
                score += 0.15
            hit.rank_score = round(score, 4)
            ranked.append(hit)
        ranked.sort(key=lambda item: item.rank_score, reverse=True)
        return ranked

    def _normalize_text(self, value: str) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"\s+", " ", text)
        return text.strip(" |.-")

    def _strip_tags(self, value: str) -> str:
        return re.sub(r"(?is)<[^>]+>", " ", value)

    def _tokenize(self, value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9']+", self._normalize_text(value).lower())
            if len(token) >= 3
        }

    def _normalize_duckduckgo_url(self, raw_url: str) -> str:
        if raw_url.startswith("//"):
            raw_url = f"https:{raw_url}"
        parsed = urlparse(raw_url)
        query = parse_qs(parsed.query)
        if "uddg" in query and query["uddg"]:
            return unquote(query["uddg"][0])
        return raw_url


web_search_service = WebSearchService()
