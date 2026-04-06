from __future__ import annotations

import html
import re
from typing import Iterable, List

try:
    import trafilatura
except Exception:
    trafilatura = None


class ContentCleaner:
    def __init__(self):
        self.noise_markers = (
            "cookie",
            "privacy policy",
            "all rights reserved",
            "advertisement",
            "subscribe",
            "sign in",
            "log in",
            "menu",
            "navigation",
            "breadcrumb",
            "share this",
            "related articles",
        )

    def clean(self, raw_content: str, fallback: str = "", url: str = "") -> str:
        extracted = self._extract_text(raw_content, url=url)
        lines = self._collect_candidates(extracted or raw_content)
        if not lines and fallback:
            lines = [self.normalize_text(fallback)]
        return "\n".join(lines).strip()

    def normalize_text(self, value: str) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"\s+", " ", text)
        return text.strip(" |.-")

    def strip_tags(self, value: str) -> str:
        return re.sub(r"(?is)<[^>]+>", " ", value)

    def _extract_text(self, raw_content: str, url: str = "") -> str:
        if trafilatura is not None:
            try:
                extracted = trafilatura.extract(
                    raw_content,
                    include_comments=False,
                    include_tables=False,
                    favor_recall=False,
                    url=url or None,
                )
                if extracted:
                    return extracted
            except Exception:
                pass
        document = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_content or "")
        document = re.sub(r"(?is)<style.*?>.*?</style>", " ", document)
        document = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", document)
        return self.strip_tags(document)

    def _collect_candidates(self, raw_text: str) -> List[str]:
        lines: List[str] = []
        seen = set()
        for candidate in self._split_into_chunks(raw_text):
            normalized = self.normalize_text(candidate)
            if len(normalized) < 40:
                continue
            lowered = normalized.lower()
            if any(marker in lowered for marker in self.noise_markers):
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            lines.append(normalized)
            if len(lines) >= 12:
                break
        return lines

    def _split_into_chunks(self, raw_text: str) -> Iterable[str]:
        if "<p" in raw_text.lower() or "<li" in raw_text.lower():
            paragraphs = re.findall(r"(?is)<p[^>]*>(.*?)</p>", raw_text)
            if not paragraphs:
                paragraphs = re.findall(r"(?is)<li[^>]*>(.*?)</li>", raw_text)
            if paragraphs:
                return paragraphs
        return re.split(r"[\r\n]+", raw_text)


content_cleaner = ContentCleaner()
