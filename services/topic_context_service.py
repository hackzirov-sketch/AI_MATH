import hashlib
import json
import logging
import os
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Sequence
from urllib.parse import quote
import urllib.request

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from services.knowledge_retriever import knowledge_retriever


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TopicContext:
    topic: str
    queries: tuple[str, ...]
    snippets: tuple[str, ...]
    sources: tuple[str, ...]

    def to_prompt_text(self) -> str:
        if not self.snippets:
            return ""
        merged = " | ".join(self.snippets[:4])
        return f"INTERNETDAN OLGAN KONTEKST: {merged}\n"


class TopicContextService:
    def __init__(self):
        self._stopwords = {
            "va",
            "yoki",
            "bilan",
            "uchun",
            "ham",
            "shu",
            "nega",
            "qanday",
            "necha",
            "toping",
            "topiladi",
            "hisoblang",
            "bo'lsa",
            "bolsa",
            "ekan",
            "faqat",
            "mavzu",
            "savol",
            "javob",
            "soni",
            "qiymati",
            "uzunligi",
            "yig'indisi",
            "farqi",
            "gacha",
            "sm",
            "cm",
            "mm",
            "dm",
            "ga",
            "ni",
            "ning",
            "lar",
            "lari",
            "haqida",
            "misol",
            "misollar",
            "masala",
            "masalalar",
            "sodda",
            "qisqa",
        }
        self._geometry_keywords = {
            "geometriya",
            "burchak",
            "uchburchak",
            "tortburchak",
            "to'rtburchak",
            "aylana",
            "doira",
            "radius",
            "diametr",
            "perimetr",
            "yuza",
            "pifagor",
            "kesma",
            "parallel",
            "trapetsiya",
            "romb",
        }
        self._logic_keywords = {
            "mantiq",
            "mantiqiy",
            "boshqotirma",
            "analogiya",
            "kodlash",
            "ketma",
            "qonuniyat",
            "xulosa",
            "tahlil",
            "iq",
        }
        self._critical_keywords = {
            "iq",
            "tanqidiy",
            "tahlil",
            "dalil",
            "xulosa",
            "analitik",
        }
        self._president_keywords = {
            "prezident",
            "president",
            "saralash",
            "maktab",
        }

    def normalize(self, value: str | None) -> str:
        text = str(value or "").lower()
        text = (
            text.replace("â€™", "'")
            .replace("’", "'")
            .replace("‘", "'")
            .replace("ʻ", "'")
            .replace("ʼ", "'")
            .replace("`", "'")
            .replace("—", " ")
            .replace("–", " ")
        )
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def topic_tokens(self, value: str | None) -> set[str]:
        normalized = self.normalize(value)
        normalized = re.sub(r"[^a-z0-9'/% ]+", " ", normalized)
        tokens = set()
        for token in re.findall(r"[a-z0-9'/%]+", normalized):
            if len(token) < 3:
                continue
            if token in self._stopwords:
                continue
            tokens.add(token[:16])
        return tokens

    def infer_quiz_type(self, subject: str | None, topic: str | None = None) -> str:
        subject_text = self.normalize(subject)
        topic_text = self.normalize(topic)
        combined = f"{subject_text} {topic_text}".strip()
        tokens = self.topic_tokens(combined)

        if any(keyword in combined for keyword in self._president_keywords):
            return "Prezident maktabi"
        if subject_text == "iq" or any(keyword in combined for keyword in self._critical_keywords):
            return "IQ / Tanqidiy fikrlash"
        if subject_text in {"mantiq", "mantiqiy fikrlash"} or tokens & self._logic_keywords:
            return "Mantiqiy fikrlash"
        if subject_text in {"boshqotirma", "puzzle"}:
            return "Boshqotirma"
        if subject_text == "geometriya" or tokens & self._geometry_keywords:
            return "Geometriya"
        return "Algebra / Matematika"

    def topic_matches(
        self,
        requested_topic: str | None,
        candidate_topic: str | None = None,
        question_text: str | None = None,
    ) -> bool:
        requested = self.normalize(requested_topic)
        if not requested:
            return True

        haystack = self.normalize(" ".join(filter(None, [candidate_topic, question_text])))
        if not haystack:
            return False

        requested_tokens = self.topic_tokens(requested)
        haystack_tokens = self.topic_tokens(haystack)

        if requested in haystack or haystack in requested:
            return True
        if requested_tokens and requested_tokens <= haystack_tokens:
            return True
        overlap = requested_tokens & haystack_tokens
        if not overlap:
            return False
        minimum = 1 if len(requested_tokens) <= 2 else 2
        return len(overlap) >= minimum

    def filter_matching_questions(self, questions: Sequence[Dict], requested_topic: str | None) -> List[Dict]:
        if not requested_topic:
            return list(questions)
        matched = []
        for question in questions:
            if self.topic_matches(
                requested_topic,
                question.get("topic"),
                question.get("question") or question.get("question_text"),
            ):
                matched.append(question)
        return matched

    def build_generation_notes(
        self,
        topic: str | None,
        age_group: str | None,
        difficulty: str | None,
        quiz_type: str,
    ) -> str:
        topic_text = self.normalize(topic)
        notes = [
            "Savol 1-2 gapdan oshmasin.",
            "Variantlar juda qisqa bo'lsin.",
            "Mavzudan chetga chiqma.",
        ]

        if difficulty == "oson" or age_group == "6-9":
            notes.extend(
                [
                    "Bir qadamli yoki ikki qadamli sodda misol tuz.",
                    "Kichik va toza sonlardan foydalan.",
                    "Izoh ham sodda bo'lsin.",
                ]
            )
        elif difficulty == "o'rta":
            notes.extend(
                [
                    "Ortiqcha matn ishlatma.",
                    "Amallar soni 2 tadan oshmasin.",
                ]
            )
        else:
            notes.extend(
                [
                    "Mavzuga mos, lekin baribir aniq va ixcham bo'lsin.",
                ]
            )

        if "kasr" in topic_text:
            notes.append("Kasrlarda maxrajlar juda murakkab bo'lmasin.")
        if "foiz" in topic_text:
            notes.append("Foiz savolida 10%, 20%, 25%, 50% kabi sodda foizlardan foydalan.")
        if "tenglama" in topic_text:
            notes.append("Tenglama bir noma'lumli va sodda bo'lsin.")
        if "perimetr" in topic_text or "yuza" in topic_text:
            notes.append("Shakl o'lchamlari kichik butun sonlar bo'lsin.")
        if quiz_type == "Geometriya":
            notes.append("Geometriya so'zlari savolning o'zida aniq ko'rinsin.")

        return " ".join(dict.fromkeys(notes))

    def build_search_queries(self, topic: str, subject: str | None = None) -> List[str]:
        topic_text = topic.strip()
        quiz_type = self.infer_quiz_type(subject, topic)
        queries = [f"{topic_text} matematika sodda misollar"]
        if quiz_type == "Geometriya":
            queries.append(f"{topic_text} geometry simple examples")
        else:
            queries.append(f"{topic_text} example problem")
        queries.append(f"{topic_text} wikipedia")
        return queries

    def fetch_internet_context(self, topic: str, subject: str | None = None) -> TopicContext:
        if not topic:
            return TopicContext(topic="", queries=(), snippets=(), sources=())
        return self._fetch_internet_context_cached(topic.strip(), (subject or "").strip())

    @lru_cache(maxsize=128)
    def _fetch_internet_context_cached(self, topic: str, subject: str) -> TopicContext:
        retrieval = knowledge_retriever.retrieve(topic=topic, subject=subject)
        queries = tuple(self.build_search_queries(topic, subject))
        snippets: List[str] = []
        sources: List[str] = []

        for source in retrieval.sources:
            if source.metadata.get("snippet"):
                snippet = self._clean_snippet(str(source.metadata["snippet"]))
                if snippet and snippet not in snippets:
                    snippets.append(snippet)
                    sources.append(source.source_type)
            if len(snippets) >= 4:
                break

        if len(snippets) < 4:
            for bucket in (
                retrieval.structured.definitions,
                retrieval.structured.formulas,
                retrieval.structured.rules,
                retrieval.structured.important_facts,
            ):
                for text in bucket:
                    snippet = self._clean_snippet(text)
                    if snippet and snippet not in snippets:
                        snippets.append(snippet)
                        sources.append("retrieval")
                    if len(snippets) >= 4:
                        break
                if len(snippets) >= 4:
                    break

        return TopicContext(
            topic=topic,
            queries=queries,
            snippets=tuple(snippets[:4]),
            sources=tuple(sources[:4]),
        )

    def _fetch_serper_snippets(self, queries: Sequence[str]) -> List[str]:
        api_key = os.getenv("SERPER_API_KEY", "").strip()
        if not api_key:
            return []

        snippets: List[str] = []
        for query in queries[:2]:
            try:
                response = requests.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json",
                    },
                    data=json.dumps({"q": query, "gl": "uz", "hl": "uz"}),
                    timeout=6,
                )
                payload = response.json()
            except Exception as exc:
                logger.warning("Serper qidiruvi ishlamadi: %s", exc)
                continue

            for section in ("answerBox", "knowledgeGraph"):
                data = payload.get(section) or {}
                for key in ("snippet", "answer", "description"):
                    value = self._clean_snippet(data.get(key))
                    if value:
                        snippets.append(value)

            for item in payload.get("organic", [])[:4]:
                title = self._clean_snippet(item.get("title"))
                body = self._clean_snippet(item.get("snippet"))
                merged = " - ".join(part for part in (title, body) if part)
                if merged:
                    snippets.append(merged)

            if snippets:
                break

        return snippets

    def _fetch_duckduckgo_snippets(self, queries: Sequence[str]) -> List[str]:
        snippets: List[str] = []
        for query in queries[:2]:
            try:
                request = urllib.request.Request(
                    f"https://html.duckduckgo.com/html/?q={quote(query)}",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                html = urllib.request.urlopen(request, timeout=6).read().decode("utf-8", errors="ignore")
            except Exception as exc:
                logger.warning("DuckDuckGo qidiruvi ishlamadi: %s", exc)
                continue

            for raw in re.findall(
                r'<a class="result__snippet[^>]*>(.*?)</a>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            ):
                text = self._clean_snippet(raw)
                if text:
                    snippets.append(text)
                if len(snippets) >= 4:
                    break
            if snippets:
                break
        return snippets

    def _fetch_wikipedia_snippets(self, topic: str) -> List[str]:
        candidates = [
            topic.replace(" ", "_"),
            topic.title().replace(" ", "_"),
        ]
        snippets: List[str] = []
        for lang in ("uz", "en"):
            for candidate in candidates:
                try:
                    response = requests.get(
                        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(candidate)}",
                        timeout=6,
                    )
                except Exception as exc:
                    logger.warning("Wikipedia so'rovi ishlamadi: %s", exc)
                    continue

                if response.status_code != 200:
                    continue

                data = response.json()
                text = self._clean_snippet(data.get("extract"))
                if text:
                    snippets.append(text)
                    return snippets
        return snippets

    def _clean_snippet(self, value: str | None) -> str:
        text = str(value or "").strip()
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" |.-")
        if len(text) < 20:
            return ""
        if len(text) > 220:
            text = text[:217].rstrip() + "..."
        return text

    def build_local_topic_question(
        self,
        topic: str,
        grade: int,
        difficulty: str,
        quiz_type: str,
        seed: str,
    ) -> Dict:
        rng = random.Random(f"{topic}|{grade}|{difficulty}|{quiz_type}|{seed}")
        topic_text = self.normalize(topic)
        hint = "null"
        validation = {"type": "exact_option_match", "value": topic.strip()}
        variant_key = self._variant_index(seed, topic_text, difficulty, quiz_type, 19)

        if "kasr" in topic_text:
            if difficulty == "oson":
                variant = variant_key % 3
                if variant == 0:
                    denominator = rng.choice([2, 3, 4, 5, 6, 8, 10])
                    numerator = rng.randint(1, max(1, denominator - 1))
                    factor = rng.choice([2, 3])
                    raw_num = numerator * factor
                    raw_den = denominator * factor
                    question = f"{raw_num}/{raw_den} kasrni qisqartiring."
                    correct = f"{numerator}/{denominator}"
                    options = [correct, f"{raw_num}/{denominator}", f"{numerator}/{raw_den}", f"{raw_num - 1}/{raw_den}"]
                    validation = {
                        "type": "fraction_simplify",
                        "numerator": raw_num,
                        "denominator": raw_den,
                    }
                elif variant == 1:
                    denominator = rng.choice([3, 4, 5, 6, 8, 10])
                    numerator = rng.randint(1, denominator - 1)
                    factor = rng.choice([2, 3, 4])
                    eq_num = numerator * factor
                    eq_den = denominator * factor
                    question = f"Quyidagilardan qaysi biri {numerator}/{denominator} ga teng?"
                    correct = f"{eq_num}/{eq_den}"
                    options = [
                        correct,
                        f"{numerator + 1}/{denominator}",
                        f"{numerator}/{denominator + 1}",
                        f"{max(1, eq_num - factor)}/{eq_den}",
                    ]
                    validation = {
                        "type": "exact_option_match",
                        "value": correct,
                    }
                else:
                    denominator = rng.choice([4, 5, 6, 8, 10])
                    left_num = rng.randint(1, denominator - 2)
                    right_num = rng.randint(left_num + 1, denominator - 1)
                    question = f"Qaysi kasr kattaroq?"
                    correct = f"{right_num}/{denominator}"
                    options = [
                        correct,
                        f"{left_num}/{denominator}",
                        f"{max(1, left_num - 1)}/{denominator}",
                        f"{min(denominator - 1, right_num - 1)}/{denominator}",
                    ]
                    validation = {
                        "type": "exact_option_match",
                        "value": correct,
                    }
            elif difficulty == "o'rta":
                variant = variant_key % 4
                if variant == 0:
                    denominator = rng.choice([4, 5, 6, 8, 10, 12])
                    a_num = rng.randint(1, denominator - 2)
                    b_num = rng.randint(1, denominator - a_num - 1)
                    numerator = a_num + b_num
                    question = f"{a_num}/{denominator} + {b_num}/{denominator} ni hisoblang."
                    correct = f"{numerator}/{denominator}"
                    options = [
                        correct,
                        f"{numerator}/{max(2, denominator // 2)}",
                        f"{abs(a_num - b_num)}/{denominator}",
                        f"{a_num + b_num}/{denominator + 1}",
                    ]
                    validation = {
                        "type": "fraction_simplify",
                        "numerator": numerator,
                        "denominator": denominator,
                    }
                elif variant == 1:
                    denominator = rng.choice([5, 6, 8, 10, 12])
                    b_num = rng.randint(1, denominator // 2)
                    a_num = rng.randint(b_num + 1, denominator - 1)
                    numerator = a_num - b_num
                    question = f"{a_num}/{denominator} - {b_num}/{denominator} ni hisoblang."
                    correct = f"{numerator}/{denominator}"
                    options = [
                        correct,
                        f"{a_num + b_num}/{denominator}",
                        f"{numerator}/{denominator + 1}",
                        f"{max(1, numerator + 1)}/{denominator}",
                    ]
                    validation = {
                        "type": "fraction_simplify",
                        "numerator": numerator,
                        "denominator": denominator,
                    }
                elif variant == 2:
                    denominator = rng.choice([6, 8, 10, 12, 15])
                    numerator = rng.randint(1, denominator - 1)
                    compare_num = rng.randint(1, denominator - 1)
                    relation = "katta" if numerator > compare_num else "kichik"
                    correct = f"{numerator}/{denominator}"
                    question = f"Quyidagi kasrlardan qaysi biri {compare_num}/{denominator} dan {relation}?"
                    options = [
                        correct,
                        f"{compare_num}/{denominator}",
                        f"{max(1, numerator - 1)}/{denominator}",
                        f"{min(denominator - 1, numerator + 1)}/{denominator}",
                    ]
                    validation = {
                        "type": "exact_option_match",
                        "value": correct,
                    }
                else:
                    numerator = rng.choice([1, 2, 3, 4])
                    denominator = rng.choice([2, 3, 4, 5, 6])
                    factor = rng.choice([2, 3, 4])
                    question = f"{numerator}/{denominator} kasrining surat va maxrajini {factor} ga ko'paytiring."
                    correct = f"{numerator * factor}/{denominator * factor}"
                    options = [
                        correct,
                        f"{numerator + factor}/{denominator * factor}",
                        f"{numerator * factor}/{denominator + factor}",
                        f"{numerator + factor}/{denominator + factor}",
                    ]
                    validation = {
                        "type": "exact_option_match",
                        "value": correct,
                    }
            else:
                variant = variant_key % 4
                if variant == 0:
                    a_den = rng.choice([4, 5, 6, 8, 10, 12])
                    b_den = rng.choice([2, 3, 4, 5, 6])
                    a_num = rng.randint(1, max(1, a_den - 1))
                    b_num = rng.randint(1, max(1, b_den - 1))
                    numerator = a_num * b_den + b_num * a_den
                    denominator = a_den * b_den
                    gcd_value = self._gcd(numerator, denominator)
                    correct = f"{numerator // gcd_value}/{denominator // gcd_value}"
                    question = f"{a_num}/{a_den} + {b_num}/{b_den} ni hisoblang."
                    options = [
                        correct,
                        f"{numerator}/{denominator}",
                        f"{a_num + b_num}/{max(a_den, b_den)}",
                        f"{abs(a_num * b_den - b_num * a_den)}/{denominator}",
                    ]
                    validation = {
                        "type": "fraction_simplify",
                        "numerator": numerator,
                        "denominator": denominator,
                    }
                elif variant == 1:
                    a_den = rng.choice([3, 4, 5, 6, 8, 10])
                    b_den = rng.choice([2, 3, 4, 5, 6])
                    a_num = rng.randint(1, max(1, a_den - 1))
                    b_num = rng.randint(1, max(1, b_den - 1))
                    numerator = a_num * b_num
                    denominator = a_den * b_den
                    gcd_value = self._gcd(numerator, denominator)
                    correct = f"{numerator // gcd_value}/{denominator // gcd_value}"
                    question = f"{a_num}/{a_den} × {b_num}/{b_den} ni hisoblang."
                    options = [
                        correct,
                        f"{numerator}/{denominator}",
                        f"{a_num + b_num}/{a_den + b_den}",
                        f"{abs(a_num - b_num)}/{max(a_den, b_den)}",
                    ]
                    validation = {
                        "type": "fraction_simplify",
                        "numerator": numerator,
                        "denominator": denominator,
                    }
                elif variant == 2:
                    a_den = rng.choice([4, 5, 6, 8, 10, 12])
                    b_den = rng.choice([2, 3, 4, 5, 6])
                    a_num = rng.randint(1, max(1, a_den - 1))
                    b_num = rng.randint(1, max(1, b_den - 1))
                    numerator = a_num * b_den
                    denominator = a_den * b_num
                    gcd_value = self._gcd(numerator, denominator)
                    correct = f"{numerator // gcd_value}/{denominator // gcd_value}"
                    question = f"{a_num}/{a_den} ÷ {b_num}/{b_den} ni hisoblang."
                    options = [
                        correct,
                        f"{a_num * b_num}/{a_den * b_den}",
                        f"{numerator}/{denominator}",
                        f"{a_den * b_num}/{a_num * b_den}",
                    ]
                    validation = {
                        "type": "fraction_simplify",
                        "numerator": numerator,
                        "denominator": denominator,
                    }
                else:
                    denominator = rng.choice([8, 10, 12, 15])
                    left_num = rng.randint(1, denominator - 2)
                    right_num = rng.randint(left_num + 1, denominator - 1)
                    question = f"Quyidagi kasrlardan eng kattasini toping."
                    correct = f"{right_num}/{denominator}"
                    options = [
                        correct,
                        f"{left_num}/{denominator}",
                        f"{max(1, left_num - 1)}/{denominator}",
                        f"{max(1, right_num - 2)}/{denominator}",
                    ]
                    validation = {
                        "type": "exact_option_match",
                        "value": correct,
                    }
        elif "foiz" in topic_text:
            if difficulty == "oson":
                variant = variant_key % 3
                if variant == 0:
                    percent = rng.choice([10, 20, 25, 50])
                    base = rng.choice([20, 40, 60, 80, 100, 120])
                    correct = str(base * percent // 100)
                    question = f"{base} sonining {percent} foizini toping."
                    options = self._numeric_options(int(correct), rng)
                    validation = {
                        "type": "percentage_of",
                        "percent": percent,
                        "whole": base,
                    }
                elif variant == 1:
                    total = rng.choice([40, 60, 80, 100, 120])
                    part_percent = rng.choice([10, 20, 25, 50])
                    part = total * part_percent // 100
                    correct = str(part)
                    question = f"{total} ning {part_percent}% qismi nechaga teng?"
                    options = self._numeric_options(part, rng)
                    validation = {
                        "type": "percentage_of",
                        "percent": part_percent,
                        "whole": total,
                    }
                else:
                    total = rng.choice([20, 40, 50, 80, 100])
                    part = rng.choice([5, 10, 20, 25, 40, 50])
                    percent = int(part * 100 / total)
                    part = total * percent // 100
                    correct = str(percent)
                    question = f"{part} soni {total} ning necha foiziga teng?"
                    options = self._numeric_options(percent, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"({part}*100)/{total}",
                    }
            elif difficulty == "o'rta":
                variant = variant_key % 4
                if variant == 0:
                    base = rng.choice([80, 100, 120, 160, 200])
                    percent = rng.choice([10, 15, 20, 25])
                    result = base + (base * percent // 100)
                    correct = str(result)
                    question = f"Son {percent}% ga oshirilsa va boshlang'ich qiymat {base} bo'lsa, yangi qiymatni toping."
                    options = self._numeric_options(result, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"{base} + ({base}*{percent}/100)",
                    }
                elif variant == 1:
                    base = rng.choice([60, 80, 100, 120, 150])
                    percent = rng.choice([10, 20, 25, 30])
                    result = base - (base * percent // 100)
                    correct = str(result)
                    question = f"{base} soni {percent}% ga kamaytirilsa, natija nechaga teng bo'ladi?"
                    options = self._numeric_options(result, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"{base} - ({base}*{percent}/100)",
                    }
                elif variant == 2:
                    percent = rng.choice([10, 20, 25, 40, 50])
                    part = rng.choice([12, 15, 18, 20, 24, 30, 36, 45])
                    result = int(part * 100 / percent)
                    correct = str(result)
                    question = f"Agar sonning {percent} foizi {part} ga teng bo'lsa, sonning o'zini toping."
                    options = self._numeric_options(result, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"({part}*100)/{percent}",
                    }
                else:
                    old_value = rng.choice([50, 60, 80, 100, 120])
                    percent = rng.choice([10, 20, 25, 50])
                    new_value = old_value + (old_value * percent // 100)
                    correct = str(percent)
                    question = f"Son {old_value} dan {new_value} ga oshdi. Bu necha foizlik o'sish?"
                    options = self._numeric_options(percent, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"(({new_value}-{old_value})*100)/{old_value}",
                    }
            else:
                variant = variant_key % 4
                if variant == 0:
                    percent = rng.choice([20, 25, 40, 50])
                    part = rng.choice([18, 20, 24, 30, 36, 45, 50])
                    result = int(part * 100 / percent)
                    correct = str(result)
                    question = f"Agar sonning {percent} foizi {part} ga teng bo'lsa, sonning o'zini toping."
                    options = self._numeric_options(result, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"({part}*100)/{percent}",
                    }
                elif variant == 1:
                    old_value = rng.choice([40, 60, 80, 100, 120])
                    percent = rng.choice([20, 25, 50])
                    new_value = old_value + (old_value * percent // 100)
                    correct = str(percent)
                    question = f"Son {old_value} dan {new_value} ga oshdi. Bu necha foizlik o'sish?"
                    options = self._numeric_options(percent, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"(({new_value}-{old_value})*100)/{old_value}",
                    }
                elif variant == 2:
                    total = rng.choice([80, 100, 120, 160, 200])
                    percent = rng.choice([15, 20, 25, 30, 40])
                    remain = total - (total * percent // 100)
                    correct = str(remain)
                    question = f"{total} soni {percent}% ga kamaytirilgandan keyin nechaga teng bo'ladi?"
                    options = self._numeric_options(remain, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"{total} - ({total}*{percent}/100)",
                    }
                else:
                    new_value = rng.choice([72, 90, 96, 108, 125, 150])
                    percent = rng.choice([20, 25, 50])
                    old_value = int(new_value * 100 / (100 - percent))
                    if old_value * (100 - percent) // 100 != new_value:
                        old_value = rng.choice([80, 100, 120, 160])
                        new_value = old_value - (old_value * percent // 100)
                    correct = str(old_value)
                    question = f"Narx {percent}% ga kamaygach {new_value} bo'ldi. Dastlabki narxni toping."
                    options = self._numeric_options(old_value, rng)
                    validation = {
                        "type": "expression_value",
                        "expression": f"({new_value}*100)/(100-{percent})",
                    }
        elif "nisbat" in topic_text or "proporsiya" in topic_text:
            variant = variant_key % 3
            if variant == 0:
                left = rng.randint(2, 6)
                scale = rng.randint(2, 5)
                right = left * scale
                missing = rng.randint(2, 8)
                result = missing * scale
                question = f"{left}:{right} = {missing}:x proporsiyada x ni toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "proportion",
                    "a": left,
                    "b": right,
                    "c": missing,
                }
            elif variant == 1:
                left = rng.randint(2, 12)
                right = rng.randint(2, 12)
                gcd_value = self._gcd(left, right)
                correct = f"{left // gcd_value}:{right // gcd_value}"
                question = f"{left}:{right} nisbatni sodda ko'rinishga keltiring."
                options = [
                    correct,
                    f"{left}:{right}",
                    f"{left + gcd_value}:{right + gcd_value}",
                    f"{max(1, left - gcd_value)}:{max(1, right - gcd_value)}",
                ]
                validation = {
                    "type": "exact_option_match",
                    "value": correct,
                }
            else:
                left = rng.randint(2, 5)
                right = rng.randint(3, 8)
                items = rng.randint(2, 6)
                result = items * right // left
                question = (
                    f"Agar {left} daftar narxi {right} ming so'm bo'lsa, "
                    f"{items} ta daftar necha ming so'm turadi?"
                )
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "expression_value",
                    "expression": f"({items}*{right})/{left}",
                }
        elif "tenglama" in topic_text or "ifoda" in topic_text:
            if difficulty == "oson":
                variant = variant_key % 3
                if variant == 0:
                    x = rng.randint(3, 15)
                    add = rng.randint(2, 9)
                    total = x + add
                    question = f"x + {add} = {total}. x ni toping."
                    equation = f"x + {add} = {total}"
                elif variant == 1:
                    x = rng.randint(3, 15)
                    sub = rng.randint(2, min(9, x - 1))
                    total = x - sub
                    question = f"x - {sub} = {total}. x ni toping."
                    equation = f"x - {sub} = {total}"
                else:
                    x = rng.randint(2, 12)
                    mul = rng.randint(2, 5)
                    total = mul * x
                    question = f"{mul}x = {total}. x ni toping."
                    equation = f"{mul}*x = {total}"
                correct = str(x)
                options = self._numeric_options(x, rng)
                validation = {
                    "type": "equation_solution",
                    "equation": equation,
                    "variable": "x",
                }
            elif difficulty == "o'rta":
                variant = variant_key % 3
                if variant == 0:
                    x = rng.randint(3, 12)
                    mul = rng.randint(2, 5)
                    add = rng.randint(2, 11)
                    total = mul * x + add
                    question = f"{mul}x + {add} = {total}. x ni toping."
                    equation = f"{mul}*x + {add} = {total}"
                elif variant == 1:
                    x = rng.randint(4, 16)
                    div = rng.randint(2, 4)
                    total = x // div
                    x = total * div
                    question = f"x/{div} = {total}. x ni toping."
                    equation = f"x/{div} = {total}"
                else:
                    x = rng.randint(3, 12)
                    mul = rng.randint(2, 4)
                    sub = rng.randint(1, 5)
                    total = mul * (x - sub)
                    question = f"{mul}(x - {sub}) = {total}. x ni toping."
                    equation = f"{mul}*(x - {sub}) = {total}"
                correct = str(x)
                options = self._numeric_options(x, rng)
                validation = {
                    "type": "equation_solution",
                    "equation": equation,
                    "variable": "x",
                }
            else:
                variant = variant_key % 4
                if variant == 0:
                    x = rng.randint(2, 12)
                    left_mul = rng.randint(2, 5)
                    right_mul = rng.randint(1, left_mul - 1)
                    left_add = rng.randint(3, 12)
                    right_add = left_mul * x + left_add - right_mul * x
                    question = f"{left_mul}x + {left_add} = {right_mul}x + {right_add}. x ni toping."
                    equation = f"{left_mul}*x + {left_add} = {right_mul}*x + {right_add}"
                elif variant == 1:
                    x = rng.randint(3, 12)
                    mul = rng.randint(2, 4)
                    div = rng.randint(2, 5)
                    total = (mul * x) // div
                    x = (total * div) // mul
                    total = (mul * x) // div
                    question = f"{mul}x/{div} = {total}. x ni toping."
                    equation = f"{mul}*x/{div} = {total}"
                elif variant == 2:
                    x = rng.randint(3, 12)
                    mul = rng.randint(2, 4)
                    add = rng.randint(2, 7)
                    total = mul * (x + add)
                    question = f"{mul}(x + {add}) = {total}. x ni toping."
                    equation = f"{mul}*(x + {add}) = {total}"
                else:
                    x = rng.randint(4, 14)
                    denom = rng.randint(2, 4)
                    add = rng.randint(2, 6)
                    total = (x + add) // denom
                    x = total * denom - add
                    total = (x + add) // denom
                    question = f"(x + {add})/{denom} = {total}. x ni toping."
                    equation = f"(x + {add})/{denom} = {total}"
                correct = str(x)
                options = self._numeric_options(x, rng)
                validation = {
                    "type": "equation_solution",
                    "equation": equation,
                    "variable": "x",
                }
        elif "perimetr" in topic_text:
            variant = variant_key % 4
            if variant == 0:
                a = rng.randint(3, 12)
                b = rng.randint(2, 9)
                result = 2 * (a + b)
                question = f"Tomonlari {a} sm va {b} sm bo'lgan to'rtburchak perimetrini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                hint = f"rectangle|bottom={a}|left={b}|perimeter=x"
                validation = {
                    "type": "geometry_formula",
                    "formula": "2*(a+b)",
                    "values": {"a": a, "b": b},
                }
            elif variant == 1:
                side = rng.randint(3, 14)
                result = 4 * side
                question = f"Tomoni {side} sm bo'lgan kvadrat perimetrini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                hint = f"rectangle|bottom={side}|left={side}|perimeter=x"
                validation = {
                    "type": "geometry_formula",
                    "formula": "4*a",
                    "values": {"a": side},
                }
            elif variant == 2:
                a = rng.randint(3, 12)
                b = rng.randint(3, 12)
                c = rng.randint(3, 12)
                result = a + b + c
                question = f"Tomonlari {a} sm, {b} sm va {c} sm bo'lgan uchburchak perimetrini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "expression_value",
                    "expression": f"{a}+{b}+{c}",
                }
            else:
                perimeter = rng.choice([20, 24, 28, 32, 36, 40])
                side = rng.randint(3, perimeter // 2 - 1)
                other = perimeter // 2 - side
                question = (
                    f"To'rtburchakning perimetri {perimeter} sm. "
                    f"Bir tomoni {side} sm bo'lsa, ikkinchi tomoni nechaga teng?"
                )
                correct = str(other)
                options = self._numeric_options(other, rng)
                hint = f"rectangle|bottom={side}|left=x|perimeter={perimeter}"
                validation = {
                    "type": "expression_value",
                    "expression": f"({perimeter}/2)-{side}",
                }
        elif "yuza" in topic_text or "maydon" in topic_text:
            variant = variant_key % 4
            if variant == 0:
                a = rng.randint(3, 12)
                b = rng.randint(2, 9)
                result = a * b
                question = f"Tomonlari {a} sm va {b} sm bo'lgan to'rtburchak yuzini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                hint = f"rectangle|bottom={a}|left={b}|area=x"
                validation = {
                    "type": "geometry_formula",
                    "formula": "a*b",
                    "values": {"a": a, "b": b},
                }
            elif variant == 1:
                side = rng.randint(3, 12)
                result = side * side
                question = f"Tomoni {side} sm bo'lgan kvadrat yuzini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                hint = f"rectangle|bottom={side}|left={side}|area=x"
                validation = {
                    "type": "geometry_formula",
                    "formula": "a*a",
                    "values": {"a": side},
                }
            elif variant == 2:
                base = rng.randint(4, 14)
                height = rng.randint(2, 10)
                result = base * height // 2
                question = f"Asosi {base} sm va balandligi {height} sm bo'lgan uchburchak yuzini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "expression_value",
                    "expression": f"({base}*{height})/2",
                }
            else:
                area = rng.choice([24, 30, 36, 40, 48, 56])
                side = rng.choice([3, 4, 5, 6, 7, 8])
                while area % side != 0:
                    side = rng.choice([3, 4, 5, 6, 7, 8])
                other = area // side
                question = f"To'rtburchakning yuzi {area} sm². Bir tomoni {side} sm bo'lsa, ikkinchi tomoni nechaga teng?"
                correct = str(other)
                options = self._numeric_options(other, rng)
                hint = f"rectangle|bottom={side}|left=x|area={area}"
                validation = {
                    "type": "expression_value",
                    "expression": f"{area}/{side}",
                }
        elif "pifagor" in topic_text:
            a, b, c = rng.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)])
            pythagoras_variant = variant_key % 5
            if pythagoras_variant == 0:
                question = f"Katetlari {a} va {b} bo'lgan to'g'ri burchakli uchburchakda gipotenuzani toping."
                correct = str(c)
                options = self._numeric_options(c, rng)
                hint = f"right_triangle|bottom={a}|left={b}|right=x"
                validation = {
                    "type": "geometry_formula",
                    "formula": "sqrt(a**2 + b**2)",
                    "values": {"a": a, "b": b},
                }
            elif pythagoras_variant == 1:
                if rng.choice([True, False]):
                    known_leg = a
                    missing_leg = b
                else:
                    known_leg = b
                    missing_leg = a
                question = (
                    f"Gipotenuzasi {c} va bir kateti {known_leg} bo'lgan "
                    "to'g'ri burchakli uchburchakda ikkinchi katetni toping."
                )
                correct = str(missing_leg)
                options = self._numeric_options(missing_leg, rng)
                hint = f"right_triangle|bottom={known_leg}|left=x|right={c}"
                validation = {
                    "type": "geometry_formula",
                    "formula": "sqrt(c**2 - a**2)",
                    "values": {"c": c, "a": known_leg},
                }
            elif pythagoras_variant == 2:
                question = (
                    f"Tomonlari {a}, {b} va {c} bo'lgan uchburchakning to'g'ri burchakli "
                    "ekanini ko'rsatuvchi tenglikni toping."
                )
                correct = f"{a}² + {b}² = {c}²"
                options = [
                    correct,
                    f"{a}² + {c}² = {b}²",
                    f"{b}² + {c}² = {a}²",
                    f"{a} + {b} = {c}",
                ]
                hint = f"right_triangle|bottom={a}|left={b}|right={c}"
                validation = {
                    "type": "exact_option_match",
                    "value": correct,
                }
            elif pythagoras_variant == 3:
                question = f"Tomonlari {a} sm va {b} sm bo'lgan to'g'ri to'rtburchak diagonalini toping."
                correct = str(c)
                options = self._numeric_options(c, rng)
                hint = f"rectangle|bottom={a}|left={b}|diagonal=x"
                validation = {
                    "type": "geometry_formula",
                    "formula": "sqrt(a**2 + b**2)",
                    "values": {"a": a, "b": b},
                }
            else:
                square_area = c * c
                question = (
                    f"Katetlari {a} va {b} bo'lgan to'g'ri burchakli uchburchakda "
                    "gipotenuzaga qurilgan kvadrat yuzini toping."
                )
                correct = str(square_area)
                options = self._numeric_options(square_area, rng)
                hint = f"right_triangle|bottom={a}|left={b}|right={c}"
                validation = {
                    "type": "expression_value",
                    "expression": f"{a}**2 + {b}**2",
                }
        elif "burchak" in topic_text:
            variant = variant_key % 3
            if variant == 0:
                angle1 = rng.choice([30, 40, 50, 60, 70])
                angle2 = rng.choice([40, 50, 60, 70])
                result = 180 - angle1 - angle2
                question = f"Uchburchak burchaklari {angle1}° va {angle2}° bo'lsa, uchinchi burchakni toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "expression_value",
                    "expression": f"180 - {angle1} - {angle2}",
                }
            elif variant == 1:
                angle = rng.choice([25, 35, 45, 55, 65, 75])
                result = 180 - angle
                question = f"Bir chiziq ustida yotgan qo'shni burchaklardan biri {angle}° bo'lsa, ikkinchi burchakni toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "expression_value",
                    "expression": f"180 - {angle}",
                }
            else:
                angle = rng.choice([10, 15, 20, 25, 30, 35, 40])
                result = 90 - angle
                question = f"To'g'ri burchakning bir qismi {angle}° bo'lsa, qolgan qismi nechaga teng?"
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "expression_value",
                    "expression": f"90 - {angle}",
                }
        elif "ildiz" in topic_text or "daraja" in topic_text:
            prefers_root = "ildiz" in topic_text and "daraja" not in topic_text
            prefers_power = "daraja" in topic_text and "ildiz" not in topic_text
            if difficulty == "oson":
                variant = variant_key % 3
                if prefers_root or (not prefers_power and variant != 2):
                    root = rng.choice([3, 4, 5, 6, 7, 8, 9])
                    square = root * root
                    if variant == 0:
                        question = f"{square} ning kvadrat ildizini toping."
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt({square})",
                        }
                    else:
                        question = f"Qaysi sonning kvadrati {square} ga teng?"
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt({square})",
                        }
                else:
                    base = rng.choice([2, 3, 4, 5, 6, 7])
                    if variant == 2:
                        question = f"{base} ning kubini toping."
                        correct = str(base ** 3)
                        options = self._numeric_options(base ** 3, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"{base}**3",
                        }
                    else:
                        question = f"{base} ning kvadratini toping."
                        correct = str(base * base)
                        options = self._numeric_options(base * base, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"{base}**2",
                        }
            elif difficulty == "o'rta":
                variant = variant_key % 4
                if prefers_power or (not prefers_root and variant in {0, 3}):
                    base = rng.choice([2, 3, 4, 5, 6, 7])
                    if variant == 3:
                        plus = rng.choice([1, 2, 3, 4, 5])
                        question = f"{base}² + {plus} ifodaning qiymatini toping."
                        correct = str(base * base + plus)
                        options = self._numeric_options(base * base + plus, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"{base}**2 + {plus}",
                        }
                    else:
                        question = f"{base} ning kvadratini toping."
                        correct = str(base * base)
                        options = self._numeric_options(base * base, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"{base}**2",
                        }
                else:
                    root = rng.choice([5, 6, 7, 8, 9, 10])
                    square = root * root
                    if variant == 1:
                        question = f"{square} ning kvadrat ildizini toping."
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt({square})",
                        }
                    elif variant == 2:
                        delta = rng.choice([4, 9, 16])
                        question = f"{square + delta} - {delta} ifodaning kvadrat ildizini toping."
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt(({square + delta}) - {delta})",
                        }
                    else:
                        question = f"Qaysi sonning kvadrati {square} ga teng?"
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt({square})",
                        }
            else:
                variant = variant_key % 4
                if prefers_root or (not prefers_power and variant in {0, 1, 2}):
                    root = rng.choice([6, 7, 8, 9, 10, 11, 12])
                    square = root * root
                    if variant == 0:
                        delta = rng.choice([5, 9, 16])
                        question = f"{square + delta} - {delta} ifodaning kvadrat ildizini toping."
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt(({square + delta}) - {delta})",
                        }
                    elif variant == 1:
                        question = f"{square} ning kvadrat ildizini toping."
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt({square})",
                        }
                    else:
                        question = f"Qaysi sonning kvadrati {square} ga teng?"
                        correct = str(root)
                        options = self._numeric_options(root, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"sqrt({square})",
                        }
                else:
                    base = rng.choice([3, 4, 5, 6, 7, 8])
                    if variant == 3:
                        power = base ** 3
                        minus = rng.choice([1, 2, 3, 4, 5])
                        question = f"{base}³ - {minus} ifodaning qiymatini toping."
                        correct = str(power - minus)
                        options = self._numeric_options(power - minus, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"{base}**3 - {minus}",
                        }
                    else:
                        power = base * base
                        plus = rng.choice([1, 2, 3, 4])
                        question = f"{base}² + {plus} ifodaning qiymatini toping."
                        correct = str(power + plus)
                        options = self._numeric_options(power + plus, rng)
                        validation = {
                            "type": "expression_value",
                            "expression": f"{base}**2 + {plus}",
                        }
        elif "aylana" in topic_text or "doira" in topic_text or "radius" in topic_text or "diametr" in topic_text:
            variant = variant_key % 4
            if variant == 0:
                radius = rng.randint(2, 10)
                diameter = radius * 2
                question = f"Aylana radiusi {radius} sm. Diametri nechaga teng?"
                correct = str(diameter)
                options = self._numeric_options(diameter, rng)
                hint = f"circle|radius_1={radius}|diameter=x"
                validation = {
                    "type": "expression_value",
                    "expression": f"2 * {radius}",
                }
            elif variant == 1:
                diameter = rng.choice([6, 8, 10, 12, 14, 16, 18, 20])
                radius = diameter // 2
                question = f"Aylana diametri {diameter} sm. Radiusini toping."
                correct = str(radius)
                options = self._numeric_options(radius, rng)
                hint = f"circle|radius_1=x|diameter={diameter}"
                validation = {
                    "type": "expression_value",
                    "expression": f"{diameter}/2",
                }
            elif variant == 2:
                radius = rng.randint(2, 8)
                circumference = 2 * 3 * radius
                question = f"π=3 deb olib, radiusi {radius} sm bo'lgan aylana uzunligini toping."
                correct = str(circumference)
                options = self._numeric_options(circumference, rng)
                hint = f"circle|radius_1={radius}|circumference=x"
                validation = {
                    "type": "expression_value",
                    "expression": f"2*3*{radius}",
                }
            else:
                radius = rng.randint(2, 7)
                area = 3 * radius * radius
                question = f"π=3 deb olib, radiusi {radius} sm bo'lgan doira yuzini toping."
                correct = str(area)
                options = self._numeric_options(area, rng)
                hint = f"circle|radius_1={radius}|area=x"
                validation = {
                    "type": "expression_value",
                    "expression": f"3*{radius}*{radius}",
                }
        elif "tub" in topic_text:
            variant = variant_key % 3
            if variant == 0:
                prime = rng.choice([11, 13, 17, 19, 23, 29])
                composite = rng.sample([12, 14, 15, 18, 21, 27], 3)
                question = "Quyidagi sonlardan qaysi biri tub son?"
                options = [str(prime), *(str(value) for value in composite)]
                rng.shuffle(options)
                correct = str(prime)
                validation = {
                    "type": "direct_value",
                    "value": prime,
                }
            elif variant == 1:
                composite = rng.choice([12, 14, 15, 18, 21, 24, 27, 30])
                primes = rng.sample([11, 13, 17, 19, 23, 29], 3)
                question = "Quyidagi sonlardan qaysi biri murakkab son?"
                options = [str(composite), *(str(value) for value in primes)]
                rng.shuffle(options)
                correct = str(composite)
                validation = {
                    "type": "direct_value",
                    "value": composite,
                }
            else:
                base = rng.choice([30, 42, 45, 66, 70, 78])
                prime_factors = []
                for candidate in [2, 3, 5, 7, 11, 13]:
                    if base % candidate == 0:
                        prime_factors.append(candidate)
                correct_value = rng.choice(prime_factors)
                wrong_values = [value for value in [4, 6, 8, 9, 10, 12, 14, 15] if value not in prime_factors]
                options = [str(correct_value)] + [str(value) for value in rng.sample(wrong_values, 3)]
                rng.shuffle(options)
                question = f"{base} sonining tub bo'luvchilaridan birini toping."
                correct = str(correct_value)
                validation = {
                    "type": "exact_option_match",
                    "value": correct,
                }
        elif "bo'luv" in topic_text or "karrali" in topic_text or "ekub" in topic_text or "ekuk" in topic_text:
            variant = variant_key % 4
            if variant == 0:
                a = rng.choice([12, 18, 24, 30])
                b = rng.choice([6, 8, 9, 10, 12])
                result = self._gcd(a, b)
                question = f"{a} va {b} sonlarining EKUB ini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "direct_value",
                    "value": result,
                }
            elif variant == 1:
                a = rng.choice([6, 8, 9, 10, 12])
                b = rng.choice([12, 15, 18, 20, 24])
                result = self._lcm(a, b)
                question = f"{a} va {b} sonlarining EKUK ini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "direct_value",
                    "value": result,
                }
            elif variant == 2:
                target = rng.choice([2, 3, 4, 6])
                correct_pair = rng.choice([(target, target * 2), (target * 2, target * 3), (target * 3, target * 4)])
                wrong_pairs = [("4", "9"), ("5", "10"), ("7", "14"), ("8", "12")]
                rendered_correct = f"{correct_pair[0]} va {correct_pair[1]}"
                rendered_wrongs = []
                for left, right in wrong_pairs:
                    pair_text = f"{left} va {right}"
                    if self._gcd(int(left), int(right)) != target and pair_text != rendered_correct:
                        rendered_wrongs.append(pair_text)
                options = [rendered_correct] + rendered_wrongs[:3]
                rng.shuffle(options)
                question = f"Qaysi juftlikning EKUB i {target} ga teng?"
                correct = rendered_correct
                validation = {
                    "type": "exact_option_match",
                    "value": correct,
                }
            else:
                target = rng.choice([12, 18, 24, 30])
                candidate_pairs = [(3, 4), (6, 9), (6, 8), (4, 6), (5, 6), (2, 15), (3, 10)]
                valid_pairs = [pair for pair in candidate_pairs if self._lcm(pair[0], pair[1]) == target]
                if not valid_pairs:
                    valid_pairs = [(3, 4)] if target == 12 else [(6, 8)]
                correct_pair = rng.choice(valid_pairs)
                rendered_correct = f"{correct_pair[0]} va {correct_pair[1]}"
                rendered_wrongs = []
                for left, right in candidate_pairs:
                    pair_text = f"{left} va {right}"
                    if self._lcm(left, right) != target and pair_text != rendered_correct:
                        rendered_wrongs.append(pair_text)
                options = [rendered_correct] + rendered_wrongs[:3]
                rng.shuffle(options)
                question = f"Qaysi juftlikning EKUK i {target} ga teng?"
                correct = rendered_correct
                validation = {
                    "type": "exact_option_match",
                    "value": correct,
                }
        elif "ehtimol" in topic_text:
            variant = variant_key % 3
            red = rng.randint(1, 4)
            blue = rng.randint(2, 6)
            green = rng.randint(1, 4)
            if variant == 0:
                total = red + blue
                question = f"Qutida {red} ta qizil va {blue} ta ko'k shar bor. Tasodifiy olingan shar qizil bo'lish ehtimoli nechaga teng?"
                correct = f"{red}/{total}"
                options = [correct, f"{blue}/{total}", f"{red}/{blue}", f"1/{total}"]
                validation = {
                    "type": "fraction_simplify",
                    "numerator": red,
                    "denominator": total,
                }
            elif variant == 1:
                total = red + blue
                question = f"Qutida {red} ta qizil va {blue} ta ko'k shar bor. Tasodifiy olingan shar ko'k bo'lish ehtimoli nechaga teng?"
                correct = f"{blue}/{total}"
                options = [correct, f"{red}/{total}", f"{blue}/{red}", f"1/{total}"]
                validation = {
                    "type": "fraction_simplify",
                    "numerator": blue,
                    "denominator": total,
                }
            else:
                total = red + blue + green
                non_red = blue + green
                question = (
                    f"Qutida {red} ta qizil, {blue} ta ko'k va {green} ta yashil shar bor. "
                    "Tasodifiy olingan shar qizil bo'lmaslik ehtimoli nechaga teng?"
                )
                correct = f"{non_red}/{total}"
                options = [correct, f"{red}/{total}", f"{blue}/{total}", f"{green}/{total}"]
                validation = {
                    "type": "fraction_simplify",
                    "numerator": non_red,
                    "denominator": total,
                }
        elif "progressiya" in topic_text or "ketma" in topic_text or "qonuniyat" in topic_text:
            variant = variant_key % 3
            start = rng.randint(2, 7)
            step = rng.randint(2, 5)
            if variant == 0:
                seq = [start + step * idx for idx in range(4)]
                result = start + step * 4
                question = f"Qatorni davom ettiring: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, x."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "sequence_next_term",
                    "sequence": seq,
                    "strategy": "arithmetic",
                }
            elif variant == 1:
                seq = [start + step * idx for idx in range(5)]
                missing_index = rng.choice([1, 2, 3])
                result = seq[missing_index]
                display = [str(value) for value in seq]
                display[missing_index] = "x"
                question = f"Ketma-ketlikdagi x ni toping: {', '.join(display)}."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "sequence_next_term",
                    "sequence": seq,
                    "strategy": "arithmetic",
                }
            else:
                seq = [start + step * idx for idx in range(4)]
                result = step
                question = f"{seq[0]}, {seq[1]}, {seq[2]}, {seq[3]} ketma-ketlikning ayirmasini toping."
                correct = str(result)
                options = self._numeric_options(result, rng)
                validation = {
                    "type": "sequence_next_term",
                    "sequence": seq,
                    "strategy": "arithmetic",
                }
        else:
            a = rng.randint(5, 30)
            b = rng.randint(2, 15)
            result = a + b if difficulty == "oson" else a - min(a - 1, b)
            if difficulty == "oson":
                question = f"{topic} mavzusidan kirish savoli: {a} + {b} = ?"
                validation = {
                    "type": "expression_value",
                    "expression": f"{a} + {b}",
                }
            else:
                question = f"{topic} mavzusidan sodda savol: {a} - {min(a - 1, b)} = ?"
                validation = {
                    "type": "expression_value",
                    "expression": f"{a} - {min(a - 1, b)}",
                }
            correct = str(result)
            options = self._numeric_options(result, rng)

        if correct not in options:
            options[0] = correct

        options = self._finalize_options(correct, options, rng)
        rng.shuffle(options)
        correct_index = options.index(correct)
        return {
            "question": question,
            "topic": topic.strip(),
            "options": options[:4],
            "correct_index": correct_index,
            "explanation": f"Qisqa yechim: kerakli amal bajariladi. Javob: {correct}",
            "geometry_hint": hint,
            "source_type": "local_topic_fallback",
            "source": "Local Topic Builder",
            "metadata": {
                "validation": validation,
                "option_labels": ["A", "B", "C", "D"],
                "correct_label": chr(65 + correct_index),
            },
        }

    def _numeric_options(self, correct: int, rng: random.Random) -> List[str]:
        values = [correct]
        deltas = [-10, -5, -3, -2, -1, 1, 2, 3, 5, 10]
        rng.shuffle(deltas)
        for delta in deltas:
            candidate = correct + delta
            if candidate > 0 and candidate not in values:
                values.append(candidate)
            if len(values) == 4:
                break
        while len(values) < 4:
            candidate = correct + len(values) + 1
            if candidate not in values:
                values.append(candidate)
        return [str(value) for value in values[:4]]

    def _finalize_options(self, correct: str, options: List[str], rng: random.Random) -> List[str]:
        unique: List[str] = []
        for option in options:
            value = str(option)
            if value and value not in unique:
                unique.append(value)
        if correct not in unique:
            unique.insert(0, correct)

        while len(unique) < 4:
            if "/" in correct:
                candidate = f"{rng.randint(1, 9)}/{rng.randint(2, 12)}"
            elif str(correct).isdigit():
                candidate = str(int(correct) + len(unique) + 1)
            else:
                candidate = f"Variant {len(unique) + 1}"
            if candidate not in unique:
                unique.append(candidate)

        return unique[:4]

    def _variant_index(self, seed: str, topic_text: str, difficulty: str, quiz_type: str, modulo: int) -> int:
        raw = f"{seed}|{topic_text}|{difficulty}|{quiz_type}".encode("utf-8")
        digest = hashlib.sha1(raw).hexdigest()
        return int(digest[:8], 16) % max(1, modulo)

    def _gcd(self, a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    def _lcm(self, a: int, b: int) -> int:
        return a * b // self._gcd(a, b)


topic_context_service = TopicContextService()
