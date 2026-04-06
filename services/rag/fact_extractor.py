from __future__ import annotations

import re
from typing import List

from services.rag.models import StructuredKnowledge

try:
    import spacy
except Exception:
    spacy = None


class FactExtractor:
    def __init__(self):
        self._nlp = None

    def extract(self, content: str) -> StructuredKnowledge:
        structured = StructuredKnowledge()
        if not content:
            return structured

        seen = set()
        for sentence in self.split_sentences(content):
            normalized = sentence.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            lowered = normalized.lower()
            if len(structured.examples) < 8 and self.looks_like_example(lowered):
                structured.examples.append(normalized)
            elif len(structured.formulas) < 8 and self.looks_like_formula(normalized):
                structured.formulas.append(normalized)
            elif len(structured.definitions) < 8 and self.looks_like_definition(lowered):
                structured.definitions.append(normalized)
            elif len(structured.rules) < 8 and self.looks_like_rule(lowered):
                structured.rules.append(normalized)
            elif len(structured.important_facts) < 12:
                structured.important_facts.append(normalized)
        return structured

    def split_sentences(self, content: str) -> List[str]:
        text = content.replace("\n", ". ")
        if spacy is not None:
            try:
                if self._nlp is None:
                    self._nlp = spacy.blank("xx")
                    if "sentencizer" not in self._nlp.pipe_names:
                        self._nlp.add_pipe("sentencizer")
                doc = self._nlp(text)
                sentences = [self._normalize_text(sentence.text) for sentence in doc.sents]
                sentences = [sentence for sentence in sentences if sentence]
                if sentences:
                    return sentences
            except Exception:
                pass
        chunks = re.split(r"(?<=[.!?])\s+", text)
        return [self._normalize_text(chunk) for chunk in chunks if self._normalize_text(chunk)]

    def looks_like_definition(self, text: str) -> bool:
        return " bu " in text or " deyiladi" in text or " is defined as " in text

    def looks_like_formula(self, text: str) -> bool:
        return "=" in text and bool(re.search(r"[0-9a-zA-Z]+\s*=\s*[^=]+", text))

    def looks_like_rule(self, text: str) -> bool:
        keywords = ("qoida", "theorem", "teorema", "xossa", "property", "rule", "if ", "agar ")
        return any(keyword in text for keyword in keywords)

    def looks_like_example(self, text: str) -> bool:
        keywords = ("masalan", "example", "misol", "for example", "e.g.")
        return any(keyword in text for keyword in keywords)

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip(" |.-")


fact_extractor = FactExtractor()
