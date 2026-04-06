import json
import logging
import os
import random
import re
import shutil
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_BASE_DIR, "config", "book_sources.json")
_CACHE_DIR = os.path.join(_BASE_DIR, "temp", "book_cache")
_PARSER_VERSION = 19
_PDFTOTEXT_CANDIDATES = (
    os.environ.get("PDFTOTEXT_PATH", ""),
    shutil.which("pdftotext") or "",
    r"C:\Program Files\Git\mingw64\bin\pdftotext.exe",
    r"C:\Program Files\Git\usr\bin\pdftotext.exe",
)
_NOISE_MARKERS = (
    "intelligence development center",
    "test raqami",
    "javoblar",
    "isbn",
    "muharrir",
    "udk",
    "kbk",
)
_QUESTION_KEYWORDS = (
    "hisoblang",
    "toping",
    "yeching",
    "tenglama",
    "tengsizlik",
    "qiymatini",
    "necha",
    "yig'indisini",
    "ayirmasi",
    "perimetri",
    "yuzini",
    "bo'lsa",
    "bo'linadi",
    "funksiya",
    "oraliq",
)
_GENERIC_TOPIC_BLACKLIST = {
    "test",
    "masalalar",
    "masi",
    "emasi",
    "istemasi",
    "qism",
    "javob",
    "yechish",
}
_OPTION_LABELS = ["A", "B", "C", "D", "E", "F"]


class BookQuestionBank:
    def __init__(self):
        os.makedirs(_CACHE_DIR, exist_ok=True)
        self._catalog: Optional[List[Dict]] = None
        self._memory_cache: Dict[str, Dict] = {}

    def get_available_topics(self, subject: str | None = None, limit: int = 10) -> List[str]:
        topic_stats: Dict[str, Dict[str, int]] = {}
        for question in self._load_questions(subject=subject):
            topic = self._clean_display_topic(question.get("topic") or "")
            if not topic or not self._is_displayable_topic(topic):
                continue
            stats = topic_stats.setdefault(topic, {"count": 0, "quality": 0, "priority": 0, "ready_test": 0})
            stats["count"] += 1
            stats["quality"] += int(question.get("quality_score", 0))
            stats["priority"] += int(question.get("source_priority", 0))
            if question.get("question_style") == "ready_test":
                stats["ready_test"] += 1
        ranked = sorted(
            topic_stats.items(),
            key=lambda item: (
                -item[1]["ready_test"],
                -(item[1]["priority"] / max(item[1]["count"], 1)),
                -(item[1]["quality"] / max(item[1]["count"], 1)),
                -item[1]["count"],
                item[0],
            ),
        )
        return [topic for topic, _ in ranked[:limit]]

    def get_test_questions(
        self,
        subject: str,
        topic: str | None,
        count: int,
        grade: int,
        difficulty: str,
        strict_topic: bool = False,
    ) -> List[Dict]:
        selected = self._select_questions_with_backfill(
            subject=subject,
            topic=topic,
            count=count,
            strict_topic=strict_topic,
        )
        result: List[Dict] = []
        for index, item in enumerate(selected, start=1):
            options_list = list(item.get("options", []))
            if len(options_list) < 4 or len(options_list) > len(_OPTION_LABELS):
                continue
            correct_index = int(item.get("correct_index", 0))
            if correct_index not in range(len(options_list)):
                continue
            labels = _OPTION_LABELS[:len(options_list)]
            options = {labels[i]: options_list[i] for i in range(len(options_list))}
            correct_label = labels[correct_index]
            result.append(
                {
                    "number": index,
                    "type": "book_question",
                    "question": item["question"],
                    "question_text": item["question"],
                    "options": options,
                    "correct": correct_label,
                    "correct_label": correct_label,
                    "correct_value": options_list[correct_index],
                    "answer": options_list[correct_index],
                    "topic": item["topic"],
                    "grade": grade,
                    "difficulty": difficulty,
                    "source": item["source_title"],
                    "source_type": "pdf_book",
                    "book_source_id": item["source_id"],
                    "quality_score": item.get("quality_score", 0),
                    "question_style": item.get("question_style", "book"),
                    "source_kind": item.get("source_kind", "reference_book"),
                    "source_priority": item.get("source_priority", 0),
                    "option_count": len(options_list),
                }
            )
        return result

    def get_quiz_payload(
        self,
        quiz_type: str,
        custom_topic: str | None = None,
        exclude_questions: Optional[set[str]] = None,
        strict_topic: bool = False,
    ) -> Optional[Dict]:
        subject = self._subject_from_quiz_type(quiz_type)
        selected = self._select_questions_with_backfill(
            subject=subject,
            topic=custom_topic,
            count=1,
            exclude_questions=exclude_questions,
            quiz_only=True,
            strict_topic=strict_topic,
        )
        if not selected:
            return None
        item = selected[0]
        options = list(item.get("options", []))[:4]
        if len(options) != 4:
            return None
        correct_index = int(item.get("correct_index", 0))
        if correct_index not in range(4):
            return None
        return {
            "question": item["question"],
            "topic": item["topic"],
            "options": options,
            "correct_index": correct_index,
            "explanation": f"Manba: {item['source_title']}. Mavzu: {item['topic']}. Javob: {options[correct_index]}",
            "geometry_hint": "null",
            "source_type": "pdf_book",
            "source": item["source_title"],
            "book_source_id": item["source_id"],
            "quality_score": item.get("quality_score", 0),
            "question_style": item.get("question_style", "book"),
        }

    def get_source_statuses(self) -> List[Dict]:
        statuses: List[Dict] = []
        for source in self._load_catalog():
            payload = self._load_source_payload(source)
            statuses.append(
                {
                    "id": source["id"],
                    "title": source["title"],
                    "status": payload.get("status", "unknown"),
                    "question_count": len(payload.get("questions", [])),
                    "source_kind": source.get("source_kind", "reference_book"),
                    "priority": int(source.get("priority", 0)),
                }
            )
        return statuses

    def _select_questions_with_backfill(
        self,
        subject: str | None,
        topic: str | None,
        count: int,
        exclude_questions: Optional[set[str]] = None,
        quiz_only: bool = False,
        strict_topic: bool = False,
    ) -> List[Dict]:
        selected = self._select_questions(
            subject=subject,
            topic=topic,
            count=count,
            exclude_questions=exclude_questions,
            quiz_only=quiz_only,
        )
        if len(selected) >= count or not count or (strict_topic and topic):
            return selected[:count]
        excluded = {self._normalize_search_text(value) for value in exclude_questions or set()}
        excluded.update(self._normalize_search_text(item.get("question", "")) for item in selected)
        backfill = self._select_questions(
            subject=subject,
            topic=None,
            count=count - len(selected),
            exclude_questions=excluded,
            quiz_only=quiz_only,
        )
        selected.extend(backfill)
        return selected[:count]

    def _load_catalog(self) -> List[Dict]:
        if self._catalog is not None:
            return self._catalog
        if not os.path.exists(_CONFIG_PATH):
            self._catalog = []
            return self._catalog
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
                raw_items = json.load(fh)
        except Exception as exc:
            logger.error("Book source config o'qilmadi: %s", exc)
            self._catalog = []
            return self._catalog
        catalog: List[Dict] = []
        for item in raw_items if isinstance(raw_items, list) else []:
            if not isinstance(item, dict):
                continue
            aliases = []
            for alias in item.get("aliases", []):
                normalized = self._normalize_subject(alias)
                if normalized:
                    aliases.append(normalized)
            catalog.append(
                {
                    "id": str(item.get("id") or "").strip(),
                    "title": str(item.get("title") or "").strip(),
                    "subject": self._normalize_subject(item.get("subject")),
                    "aliases": sorted(set(aliases)),
                    "path": str(item.get("path") or "").strip(),
                    "parse_mode": str(item.get("parse_mode") or "split_answer_key").strip() or "split_answer_key",
                    "source_kind": str(item.get("source_kind") or "reference_book").strip() or "reference_book",
                    "priority": int(item.get("priority", 0) or 0),
                    "enabled": bool(item.get("enabled", True)),
                }
            )
        self._catalog = [item for item in catalog if item["id"] and item["path"] and item["enabled"]]
        return self._catalog

    def _load_questions(self, subject: str | None = None) -> List[Dict]:
        questions: List[Dict] = []
        for source in self._load_catalog():
            if not self._source_matches_subject(source, subject):
                continue
            payload = self._load_source_payload(source)
            questions.extend(payload.get("questions", []))
        return questions

    def _load_source_payload(self, source: Dict) -> Dict:
        try:
            stat = os.stat(source["path"])
            fingerprint = f"{int(stat.st_mtime)}:{stat.st_size}:{_PARSER_VERSION}"
        except FileNotFoundError:
            fingerprint = f"missing:{_PARSER_VERSION}"
        cached = self._memory_cache.get(source["id"])
        if cached and cached.get("_fingerprint") == fingerprint:
            return cached
        cache_path = os.path.join(_CACHE_DIR, f"{source['id']}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                if payload.get("_fingerprint") == fingerprint:
                    self._memory_cache[source["id"]] = payload
                    return payload
            except Exception:
                pass
        payload = self._build_source_payload(source, fingerprint)
        try:
            with open(cache_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Book cache yozilmadi: %s", exc)
        self._memory_cache[source["id"]] = payload
        return payload

    def _build_source_payload(self, source: Dict, fingerprint: str) -> Dict:
        if not os.path.exists(source["path"]):
            return {
                "_fingerprint": fingerprint,
                "status": "missing",
                "questions": [],
                "topics": [],
            }
        pdftotext_path = self._find_pdftotext()
        if not pdftotext_path:
            return {
                "_fingerprint": fingerprint,
                "status": "pdftotext_missing",
                "questions": [],
                "topics": [],
            }
        extracted_text = self._extract_pdf_text(pdftotext_path, source["path"])
        text_signal = len(re.findall(r"[A-Za-z0-9]", extracted_text))
        if text_signal < 500:
            return {
                "_fingerprint": fingerprint,
                "status": "image_only",
                "questions": [],
                "topics": [],
            }
        parse_mode = source.get("parse_mode", "split_answer_key")
        if parse_mode == "solved_test_book":
            questions = self._parse_solved_test_book(extracted_text, source)
            status = "ready" if questions else "no_questions"
            return {
                "_fingerprint": fingerprint,
                "status": status,
                "questions": questions,
                "topics": sorted({question["topic"] for question in questions if question.get("topic")}),
            }
        if parse_mode == "solved_text_problems":
            questions = self._parse_solved_text_problems(extracted_text, source)
            status = "ready" if questions else "no_questions"
            return {
                "_fingerprint": fingerprint,
                "status": status,
                "questions": questions,
                "topics": sorted({question["topic"] for question in questions if question.get("topic")}),
            }
        question_text, answer_text = self._split_sections(extracted_text)
        if not answer_text:
            return {
                "_fingerprint": fingerprint,
                "status": "answer_key_missing",
                "questions": [],
                "topics": [],
            }
        parsed_questions = self._parse_question_section(question_text, source)
        parsed_answers = self._parse_answer_section(answer_text, source)
        questions = self._attach_answers(parsed_questions, parsed_answers, source)
        topics = sorted({question["topic"] for question in questions if question.get("topic")})
        status = "ready" if questions else "no_questions"
        return {
            "_fingerprint": fingerprint,
            "status": status,
            "questions": questions,
            "topics": topics,
        }

    def _find_pdftotext(self) -> str | None:
        for candidate in _PDFTOTEXT_CANDIDATES:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def _parse_solved_test_book(self, text: str, source: Dict) -> List[Dict]:
        questions: List[Dict] = []
        current_topic = source["title"]
        for page in text.split("\f"):
            raw_lines = [line.rstrip("\r") for line in page.splitlines()]
            if not raw_lines:
                continue
            left_lines, right_lines = self._split_page_columns(raw_lines)
            topic_candidate = self._extract_question_page_topic(raw_lines, left_lines, right_lines)
            if topic_candidate and self._should_replace_topic(current_topic, topic_candidate):
                current_topic = topic_candidate
            for column in (left_lines, right_lines):
                questions.extend(self._parse_solved_test_column(column, current_topic, source))
        return questions

    def _parse_solved_test_column(self, lines: List[str], current_topic: str, source: Dict) -> List[Dict]:
        column_text = "\n".join(lines)
        if not column_text:
            return []
        starts = [match.start() for match in re.finditer(r"(?m)(?:^|\n)\s*(?:\d+\.\s*)?\(\d{2}[-\d*]+\)", column_text)]
        if not starts:
            return []
        starts.append(len(column_text))
        parsed: List[Dict] = []
        for idx in range(len(starts) - 1):
            chunk = column_text[starts[idx]:starts[idx + 1]]
            if "A)" not in chunk or "B)" not in chunk or "C)" not in chunk or "D)" not in chunk or "E)" not in chunk:
                continue
            block = self._parse_labeled_question_block(chunk, _OPTION_LABELS[:5])
            if not block:
                continue
            correct_label = self._extract_inline_answer_label(block["tail"], _OPTION_LABELS[:5])
            if not correct_label:
                continue
            parsed_question = self._finalize_question_record(
                source=source,
                topic=current_topic,
                question_text=block["question"],
                options=block["options"],
                correct_index=_OPTION_LABELS.index(correct_label),
                question_style="ready_test",
                test_label=block.get("test_label", ""),
            )
            if parsed_question:
                parsed.append(parsed_question)
        return parsed

    def _parse_solved_text_problems(self, text: str, source: Dict) -> List[Dict]:
        page_topics = self._build_page_topic_ranges(text, source["title"])
        questions: List[Dict] = []
        pattern = re.compile(
            r"(?ms)(?:^|\n)\s*(\d+\))\s*(.+?)\n\s*Javob\s*:\s*(.+?)(?=(?:\n\s*\d+\))|(?:\n\s*[IVX]+-bob)|\Z)",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            raw_question = self._normalize_search_text(match.group(2))
            raw_answer = self._normalize_search_text(match.group(3))
            simple_answer = self._extract_simple_answer(raw_answer)
            if not simple_answer:
                continue
            options_payload = self._build_options_from_answer(raw_question, simple_answer)
            if not options_payload:
                continue
            options, correct_index = options_payload
            topic = self._topic_for_offset(page_topics, match.start())
            parsed_question = self._finalize_question_record(
                source=source,
                topic=topic,
                question_text=raw_question,
                options=options,
                correct_index=correct_index,
                question_style="text_problem",
                explanation=raw_answer,
            )
            if parsed_question:
                questions.append(parsed_question)
        return questions

    def _build_page_topic_ranges(self, text: str, fallback_topic: str) -> List[tuple[int, int, str]]:
        ranges: List[tuple[int, int, str]] = []
        current_topic = fallback_topic
        offset = 0
        for page in text.split("\f"):
            raw_lines = [line.rstrip("\r") for line in page.splitlines()]
            if raw_lines:
                left_lines, right_lines = self._split_page_columns(raw_lines)
                topic_candidate = self._extract_question_page_topic(raw_lines, left_lines, right_lines)
                if not topic_candidate:
                    topic_candidate = self._extract_general_page_topic(raw_lines)
                if topic_candidate and self._should_replace_topic(current_topic, topic_candidate):
                    current_topic = topic_candidate
            ranges.append((offset, offset + len(page), current_topic))
            offset += len(page) + 1
        return ranges

    def _extract_general_page_topic(self, raw_lines: List[str]) -> str | None:
        prioritized: List[str] = []
        fallback: List[str] = []
        for line in raw_lines[:12]:
            candidate = self._clean_topic_candidate(line)
            if candidate and self._topic_looks_reasonable(candidate):
                fallback.append(candidate)
                normalized = self._normalize_search_text(line)
                if "§" in normalized or re.match(r"^[IVX]+-BOB", normalized, flags=re.IGNORECASE) or re.match(r"^\d+(?:\.\d+)+(?:-§)?", normalized):
                    prioritized.append(candidate)
        if prioritized:
            return prioritized[-1]
        return fallback[0] if fallback else None

    def _topic_for_offset(self, ranges: List[tuple[int, int, str]], offset: int) -> str:
        for start, end, topic in ranges:
            if start <= offset <= end:
                return topic
        return ranges[-1][2] if ranges else ""

    def _parse_labeled_question_block(self, text: str, labels: List[str]) -> Optional[Dict]:
        normalized = self._normalize_search_text(text)
        pattern = rf"\b([{''.join(labels)}])\)"
        positions = [(match.group(1), match.start()) for match in re.finditer(pattern, normalized)]
        if len(positions) < len(labels):
            return None
        chosen = positions[:len(labels)]
        if [label for label, _ in chosen] != labels:
            return None
        question = self._strip_leading_marker(normalized[:chosen[0][1]])
        if len(question) < 10:
            return None
        options: List[str] = []
        tail = ""
        for idx, (_, pos) in enumerate(chosen):
            start = pos + 2
            end = chosen[idx + 1][1] if idx + 1 < len(chosen) else len(normalized)
            segment = normalized[start:end]
            if idx + 1 == len(chosen):
                marker = re.search(r"\b(?:Javob|J)\s*:", segment, flags=re.IGNORECASE)
                if marker:
                    tail = segment[marker.start():].strip()
                    segment = segment[:marker.start()]
            options.append(self._clean_option_text(segment))
        if any(not option for option in options):
            return None
        test_label_match = re.search(r"\((\d{2}[-\d*]+)\)", normalized)
        return {
            "question": question,
            "options": options,
            "tail": tail,
            "test_label": test_label_match.group(1) if test_label_match else "",
        }

    def _extract_inline_answer_label(self, text: str, labels: List[str]) -> str | None:
        label_class = "".join(labels)
        patterns = [
            rf"(?:Javob|J)\s*:\s*.*?\(([{label_class}])\)",
            rf"(?:Javob|J)\s*:\s*\(?([{label_class}])\)?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.S)
            if match:
                return match.group(1).upper()
        return None

    def _extract_simple_answer(self, answer_text: str) -> str | None:
        cleaned = self._normalize_search_text(answer_text)
        cleaned = re.sub(r"www\.ziyouz\.com.*$", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+\.\s+", "/", cleaned)
        if re.search(r"\b[A-E]\)", cleaned):
            return None
        if ";" in cleaned:
            first = cleaned.split(";", 1)[0].strip()
            simple = self._extract_simple_answer(first)
            if simple:
                return simple
        if "=" in cleaned or "≈" in cleaned:
            tail_parts = re.split(r"≈|=", cleaned)
            for candidate in reversed(tail_parts):
                candidate = candidate.strip(" .,;:")
                if self._is_simple_answer(candidate):
                    return candidate
        cleaned = cleaned.strip(" .,;:")
        if self._is_simple_answer(cleaned):
            return cleaned
        numeric_match = re.search(r"([0-9]+(?:[.,][0-9]+)?(?:/[0-9]+)?)", cleaned)
        if numeric_match:
            candidate = numeric_match.group(1).strip(" .,;:")
            if self._is_simple_answer(candidate):
                return candidate
        return None

    def _is_simple_answer(self, value: str) -> bool:
        candidate = self._normalize_search_text(value).strip(" .,;:")
        if not candidate:
            return False
        if candidate.lower() in {"ha", "yo'q", "yo‘q"}:
            return True
        if "π" in candidate and len(candidate) <= 10:
            return True
        if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", candidate):
            return True
        if re.fullmatch(r"[0-9]+/[0-9]+", candidate):
            return True
        if re.fullmatch(r"[nNxX]\s*[≥<=]+\s*[0-9]+", candidate):
            return True
        return False

    def _build_options_from_answer(self, question_text: str, answer_text: str) -> Optional[tuple[List[str], int]]:
        answer = self._normalize_search_text(answer_text).strip(" .,;:")
        if not answer:
            return None
        answer_lower = answer.lower()
        if answer_lower in {"ha", "yo'q", "yo‘q"}:
            options = ["ha", "yo'q", "aniqlab bo'lmaydi", "ikkalasi ham emas"]
            return options, options.index("ha" if answer_lower == "ha" else "yo'q")
        if "π" in answer:
            pool = ["π/6", "π/4", "π/3", "π/2"]
            if answer in pool:
                options = pool[:]
                return options, options.index(answer)
            return None
        if re.fullmatch(r"[0-9]+/[0-9]+", answer):
            numerator, denominator = answer.split("/", 1)
            try:
                num = int(numerator)
                den = int(denominator)
            except Exception:
                return None
            candidates = [f"{num}/{den}"]
            for extra_num, extra_den in ((num + 1, den), (max(1, num - 1), den), (num, den + 1), (num + 1, den + 1)):
                candidate = f"{extra_num}/{extra_den}"
                if candidate not in candidates:
                    candidates.append(candidate)
                if len(candidates) == 4:
                    break
            if len(candidates) < 4:
                return None
            rng = random.Random(f"{question_text}|{answer}")
            rng.shuffle(candidates)
            return candidates, candidates.index(answer)
        if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", answer):
            normalized_value = float(answer.replace(",", "."))
            decimals = len(answer.split(",", 1)[1]) if "," in answer else (len(answer.split(".", 1)[1]) if "." in answer else 0)
            step = 1 if decimals == 0 else max(10 ** (-decimals), round(max(normalized_value * 0.1, 10 ** (-decimals)), decimals))
            values = [normalized_value]
            for multiplier in (1, 2, -1, -2, 3):
                candidate = normalized_value + step * multiplier
                if decimals == 0:
                    candidate = int(round(candidate))
                else:
                    candidate = round(candidate, decimals)
                if candidate not in values and candidate >= 0:
                    values.append(candidate)
                if len(values) == 4:
                    break
            if len(values) < 4:
                return None
            rng = random.Random(f"{question_text}|{answer}")
            rng.shuffle(values)
            formatted = [self._format_numeric_option(value, decimals) for value in values]
            return formatted, formatted.index(answer.replace(".", ","))
        return None

    def _format_numeric_option(self, value: float | int, decimals: int) -> str:
        if decimals == 0:
            return str(int(value))
        formatted = f"{value:.{decimals}f}".replace(".", ",")
        return formatted.rstrip("0").rstrip(",") if "," in formatted else formatted

    def _finalize_question_record(
        self,
        source: Dict,
        topic: str,
        question_text: str,
        options: List[str],
        correct_index: int,
        question_style: str,
        test_label: str = "",
        explanation: str = "",
    ) -> Optional[Dict]:
        if correct_index not in range(len(options)):
            return None
        resolved_topic = self._clean_display_topic(topic) or self._normalize_search_text(topic or source["title"])
        if not self._topic_looks_reasonable(resolved_topic):
            resolved_topic = self._clean_display_topic(source["title"]) or source["title"]
        if source.get("source_kind") == "problem_book":
            resolved_topic = self._clean_display_topic(source["title"]) or source["title"]
        cleaned_question = self._clean_question_text(question_text)
        if not cleaned_question or not self._question_looks_complete(cleaned_question):
            return None
        if not self._options_look_usable(options):
            return None
        quality_score = self._question_quality_score(cleaned_question, options, resolved_topic)
        if question_style == "ready_test":
            quality_score = min(100, quality_score + 8)
        search_text = " ".join([source["title"], resolved_topic, cleaned_question, " ".join(options), explanation])
        return {
            "source_id": source["id"],
            "source_title": source["title"],
            "subject": source["subject"],
            "aliases": sorted(set([source["subject"], *source.get("aliases", [])])),
            "topic": resolved_topic,
            "test_label": test_label,
            "question_number": 0,
            "question": cleaned_question,
            "options": options,
            "correct_index": correct_index,
            "search_text": self._normalize_search_text(search_text),
            "keywords": sorted(self._keyword_tokens(search_text)),
            "quality_score": quality_score,
            "question_style": question_style,
            "source_kind": source.get("source_kind", "reference_book"),
            "source_priority": int(source.get("priority", 0)),
        }

    def _extract_pdf_text(self, pdftotext_path: str, pdf_path: str) -> str:
        try:
            proc = subprocess.run(
                [pdftotext_path, "-layout", "-enc", "UTF-8", pdf_path, "-"],
                capture_output=True,
                check=False,
            )
        except Exception as exc:
            logger.warning("pdftotext ishlamadi: %s", exc)
            return ""
        return (proc.stdout or b"").decode("utf-8", errors="ignore")

    def _split_sections(self, text: str) -> tuple[str, str]:
        marker = self._find_answer_section_start(text)
        if marker == -1:
            return text, ""
        return text[:marker], text[marker:]

    def _find_answer_section_start(self, text: str) -> int:
        candidates: List[int] = []
        for match in re.finditer(r"Javoblar", text):
            idx = match.start()
            window = text[idx:idx + 800]
            if "Test raqami" in window:
                candidates.append(idx)
        if not candidates:
            return -1
        halfway = len(text) * 0.5
        for idx in candidates:
            if idx >= halfway:
                return idx
        return candidates[0]

    def _parse_question_section(self, text: str, source: Dict) -> Dict:
        current_topic = source["title"]
        current_test = "1-test"
        groups: Dict[str, Dict] = {}
        questions: List[Dict] = []
        group_order = 0
        for page in text.split("\f"):
            raw_lines = [line.rstrip("\r") for line in page.splitlines()]
            if not self._page_has_question_content(raw_lines):
                continue
            left_lines, right_lines = self._split_page_columns(raw_lines)
            topic_candidate = self._extract_question_page_topic(raw_lines, left_lines, right_lines)
            if topic_candidate and self._should_replace_topic(current_topic, topic_candidate):
                current_topic = topic_candidate
                current_test = "1-test"
            labels = self._extract_test_labels(" ".join(raw_lines[:6]))
            if labels:
                current_test = labels[0]
            parsed_blocks: List[Dict] = []
            for column in (left_lines, right_lines):
                parsed_blocks.extend(self._parse_question_column(column))
            if not parsed_blocks:
                continue
            group_key = f"{self._canonical_topic(current_topic)}::{current_test}"
            if group_key not in groups:
                group_order += 1
                groups[group_key] = {
                    "group_key": group_key,
                    "topic": current_topic,
                    "test_label": current_test,
                    "order": group_order,
                }
            question_number = sum(1 for item in questions if item["group_key"] == group_key)
            for parsed in parsed_blocks:
                question_number += 1
                questions.append(
                    {
                        "group_key": group_key,
                        "topic": current_topic,
                        "test_label": current_test,
                        "question_number": question_number,
                        "question": parsed["question"],
                        "options": parsed["options"],
                    }
                )
        return {"questions": questions, "groups": list(groups.values())}

    def _parse_answer_section(self, text: str, source: Dict) -> Dict:
        groups: Dict[str, Dict] = {}
        ordered_groups: List[Dict] = []
        current_topic = source["title"]
        recent_headings: List[str] = []
        pending_tests: List[str] = []
        group_order = 0
        for raw_line in text.splitlines():
            line = self._normalize_search_text(raw_line)
            if not line:
                continue
            if self._is_noise_line(line):
                continue
            if line.lower() == "javoblar":
                recent_headings = []
                pending_tests = []
                continue
            if "test raqami" in line.lower():
                if recent_headings:
                    current_topic = recent_headings[-1]
                continue
            labels = self._extract_test_labels(line)
            if labels:
                pending_tests.extend(labels)
                remainder = self._remove_test_labels(line)
                chunks = self._extract_answer_chunks(remainder)
                if chunks:
                    pending_tests = self._consume_answer_chunks(
                        current_topic,
                        pending_tests,
                        chunks,
                        groups,
                        ordered_groups,
                        group_order,
                    )
                    group_order = len(ordered_groups)
                continue
            if pending_tests:
                chunks = self._extract_answer_chunks(line)
                if chunks:
                    pending_tests = self._consume_answer_chunks(
                        current_topic,
                        pending_tests,
                        chunks,
                        groups,
                        ordered_groups,
                        group_order,
                    )
                    group_order = len(ordered_groups)
                    continue
            if self._is_potential_topic(line) and not self._is_question_like(line):
                recent_headings.append(line)
                recent_headings = recent_headings[-3:]
                current_topic = recent_headings[-1]
        return {"groups": ordered_groups}

    def _consume_answer_chunks(
        self,
        current_topic: str,
        pending_tests: List[str],
        chunks: List[str],
        groups: Dict[str, Dict],
        ordered_groups: List[Dict],
        group_order: int,
    ) -> List[str]:
        remaining = list(pending_tests)
        for chunk in chunks:
            if not remaining:
                break
            test_label = remaining.pop(0)
            group_key = f"{self._canonical_topic(current_topic)}::{test_label}"
            group = groups.get(group_key)
            if not group:
                group_order += 1
                group = {
                    "group_key": group_key,
                    "topic": current_topic,
                    "test_label": test_label,
                    "order": group_order,
                    "answers": "",
                }
                groups[group_key] = group
                ordered_groups.append(group)
            group["answers"] = chunk[:20]
        return remaining

    def _attach_answers(self, parsed_questions: Dict, parsed_answers: Dict, source: Dict) -> List[Dict]:
        question_groups = parsed_questions.get("groups", [])
        answer_groups = parsed_answers.get("groups", [])
        matches = self._match_groups(question_groups, answer_groups)
        result: List[Dict] = []
        for item in parsed_questions.get("questions", []):
            answer_group = matches.get(item["group_key"])
            if not answer_group:
                continue
            answers = answer_group.get("answers", "")
            question_number = int(item.get("question_number", 0))
            if question_number < 1 or question_number > len(answers):
                continue
            options = list(item.get("options", []))[:4]
            if len(options) != 4:
                continue
            correct_label = answers[question_number - 1]
            if correct_label not in "ABCD":
                continue
            resolved_topic = item["topic"]
            answer_topic = answer_group.get("topic", "")
            if self._is_displayable_topic(answer_topic):
                resolved_topic = answer_topic
            resolved_topic = self._clean_display_topic(resolved_topic) or self._normalize_search_text(resolved_topic)
            if not self._options_look_usable(options):
                continue
            record = self._finalize_question_record(
                source=source,
                topic=resolved_topic,
                question_text=item["question"],
                options=options,
                correct_index="ABCD".index(correct_label),
                question_style="ready_test",
                test_label=item["test_label"],
            )
            if not record:
                continue
            record["question_number"] = question_number
            result.append(record)
        return result

    def _match_groups(self, question_groups: List[Dict], answer_groups: List[Dict]) -> Dict[str, Dict]:
        matches: Dict[str, Dict] = {}
        used_answer_keys: set[str] = set()
        answer_lookup = {group["group_key"]: group for group in answer_groups}
        for q_group in question_groups:
            exact = answer_lookup.get(q_group["group_key"])
            if exact and exact["group_key"] not in used_answer_keys:
                matches[q_group["group_key"]] = exact
                used_answer_keys.add(exact["group_key"])
        for q_group in question_groups:
            if q_group["group_key"] in matches:
                continue
            best_group = None
            best_score = -10**9
            for a_group in answer_groups:
                if a_group["group_key"] in used_answer_keys:
                    continue
                score = self._group_match_score(q_group, a_group)
                if score > best_score:
                    best_score = score
                    best_group = a_group
            if best_group and best_score >= 0:
                matches[q_group["group_key"]] = best_group
                used_answer_keys.add(best_group["group_key"])
        return matches

    def _group_match_score(self, question_group: Dict, answer_group: Dict) -> int:
        q_tokens = self._keyword_tokens(question_group.get("topic", ""))
        a_tokens = self._keyword_tokens(answer_group.get("topic", ""))
        overlap = len(q_tokens & a_tokens)
        distance = abs(int(question_group.get("order", 0)) - int(answer_group.get("order", 0)))
        score = overlap * 12 - distance
        if question_group.get("test_label") == answer_group.get("test_label"):
            score += 8
        else:
            score -= 20
        return score

    def _select_questions(
        self,
        subject: str | None,
        topic: str | None,
        count: int,
        exclude_questions: Optional[set[str]] = None,
        quiz_only: bool = False,
    ) -> List[Dict]:
        normalized_subject = self._normalize_subject(subject)
        normalized_topic = self._canonical_topic(topic or "")
        if normalized_topic and self._normalize_subject(normalized_topic) == normalized_subject:
            normalized_topic = ""
        topic_tokens = self._keyword_tokens(normalized_topic)
        excluded = {self._normalize_search_text(value) for value in exclude_questions or set()}
        candidates: List[tuple[int, int, float, Dict]] = []
        seen: set[str] = set()
        for question in self._load_questions(subject=subject):
            question_key = self._normalize_search_text(question.get("question", ""))
            if not question_key or question_key in excluded or question_key in seen:
                continue
            if quiz_only and len(question.get("options", [])) != 4:
                continue
            score = self._score_question(question, normalized_subject, normalized_topic, topic_tokens)
            if score is None:
                continue
            quality_score = int(question.get("quality_score", 0))
            candidates.append((score, quality_score, random.random(), question))
            seen.add(question_key)
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]["question"]))
        min_quality = 85 if normalized_topic else 75
        primary = [item for item in candidates if item[1] >= min_quality]
        secondary = [item for item in candidates if item[1] >= max(55, min_quality - 10)]
        if normalized_topic:
            pool = primary
        elif len(primary) >= count:
            pool = primary
        elif len(secondary) >= count:
            pool = secondary
        else:
            pool = candidates
        selected: List[Dict] = []
        deferred: List[Dict] = []
        used_families: set[str] = set()
        for _, _, _, question in pool:
            family_key = self._question_family_key(question.get("question", ""))
            if family_key and family_key in used_families:
                deferred.append(question)
                continue
            if family_key:
                used_families.add(family_key)
            selected.append(question)
            if len(selected) >= count:
                return selected[:count]
        for question in deferred:
            selected.append(question)
            if len(selected) >= count:
                break
        return selected[:count]

    def _score_question(
        self,
        question: Dict,
        normalized_subject: str,
        normalized_topic: str,
        topic_tokens: set[str],
    ) -> Optional[int]:
        aliases = {self._normalize_subject(alias) for alias in question.get("aliases", [])}
        search_text = self._canonical_topic(question.get("search_text", ""))
        question_topic = self._canonical_topic(question.get("topic", ""))
        score = 0
        if normalized_subject:
            if normalized_subject in aliases:
                score += 12
            elif normalized_subject == "matematika" and aliases & {"matematika", "algebra", "geometriya", "ehtimollik"}:
                score += 8
            else:
                return None
        if normalized_topic:
            overlap = len(topic_tokens & set(question.get("keywords", [])))
            exact_topic = normalized_topic in question_topic
            exact_text = normalized_topic in search_text
            min_overlap = 1 if len(topic_tokens) <= 1 else 2
            if not exact_topic and not exact_text and overlap < min_overlap:
                return None
            score += overlap * 14
            if exact_topic:
                score += 20
            if exact_text:
                score += 10
        else:
            score += 1
        score += int(question.get("source_priority", 0)) // 10
        if question.get("source_kind") == "test_book":
            score += 12
        elif question.get("source_kind") == "problem_book":
            score += 6
        if question.get("question_style") == "ready_test":
            score += 14
        elif question.get("question_style") == "text_problem":
            score += 8
        score += max(0, 6 - int(question.get("question_number", 1)) // 4)
        return score

    def _question_family_key(self, text: str) -> str:
        normalized = self._normalize_search_text(text or "").lower()
        normalized = normalized.replace("π", " pi ")
        normalized = re.sub(r"[0-9]+(?:[.,][0-9]+)?(?:/[0-9]+)?", " n ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        tokens = re.findall(r"[a-z']+", normalized)
        return " ".join(token[:12] for token in tokens[:8] if len(token) >= 3)

    def _split_page_columns(self, raw_lines: List[str]) -> tuple[List[str], List[str]]:
        if not raw_lines:
            return [], []
        max_len = max(len(line) for line in raw_lines)
        if max_len < 70:
            return [self._normalize_search_text(line) for line in raw_lines if self._normalize_search_text(line)], []
        midpoint = max(44, min(80, max_len // 2))
        left_lines: List[str] = []
        right_lines: List[str] = []
        for raw in raw_lines:
            padded = raw.ljust(max_len)
            left = self._normalize_search_text(padded[:midpoint])
            right = self._normalize_search_text(padded[midpoint:])
            if left:
                left_lines.append(left)
            if right:
                right_lines.append(right)
        return left_lines, right_lines

    def _page_has_question_content(self, raw_lines: List[str]) -> bool:
        joined = " ".join(raw_lines)
        return "A)" in joined and ("B)" in joined or "C)" in joined or "D)" in joined)

    def _extract_question_page_topic(
        self,
        raw_lines: List[str],
        left_lines: List[str],
        right_lines: List[str],
    ) -> str | None:
        candidates: List[str] = []
        for line in raw_lines[:5]:
            candidate = self._clean_topic_candidate(line)
            if candidate and self._topic_looks_reasonable(candidate):
                candidates.append(candidate)
        for line in left_lines[:4]:
            candidate = self._clean_topic_candidate(line)
            if candidate and self._topic_looks_reasonable(candidate):
                candidates.append(candidate)
        for line in right_lines[:2]:
            candidate = self._clean_topic_candidate(line)
            if candidate and self._topic_looks_reasonable(candidate):
                candidates.append(candidate)
        return candidates[-1] if candidates else None

    def _clean_topic_candidate(self, text: str) -> str | None:
        cleaned = self._normalize_search_text(text)
        cleaned = re.sub(r"\b\d+\s*-\s*test\b", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\b\d{1,3}\b$", "", cleaned).strip()
        cleaned = cleaned.strip("_ ")
        lowered = cleaned.lower()
        if lowered.startswith("javob") or lowered.startswith("yechish"):
            return None
        if re.match(rf"^[{''.join(_OPTION_LABELS)}]\)", cleaned, flags=re.IGNORECASE):
            return None
        if re.match(r"^\d+\s*[.)](?!\d)", cleaned):
            return None
        if self._count_suspicious_tokens(cleaned):
            return None
        if self._is_potential_topic(cleaned) and not self._is_question_like(cleaned) and self._is_strong_heading(cleaned):
            return cleaned
        return None

    def _parse_question_column(self, lines: List[str]) -> List[Dict]:
        parsed: List[Dict] = []
        buffer: List[str] = []
        for line in lines:
            cleaned = self._normalize_search_text(line)
            if not cleaned:
                continue
            if self._is_noise_line(cleaned):
                continue
            if cleaned.lower() == "javoblar":
                continue
            if "test raqami" in cleaned.lower():
                continue
            if self._looks_like_test_label_line(cleaned):
                continue
            if not buffer and self._is_potential_topic(cleaned) and not self._is_question_like(cleaned):
                continue
            buffer.append(cleaned)
            question = self._parse_question_block(" ".join(buffer))
            if question:
                parsed.append(question)
                buffer = []
        return parsed

    def _parse_question_block(self, text: str) -> Optional[Dict]:
        parsed = self._parse_labeled_question_block(text, _OPTION_LABELS[:4])
        if not parsed:
            return None
        return {"question": parsed["question"], "options": parsed["options"]}

    def _extract_test_labels(self, text: str) -> List[str]:
        return [f"{value}-test" for value in re.findall(r"(\d+)\s*-\s*test", text, flags=re.IGNORECASE)]

    def _remove_test_labels(self, text: str) -> str:
        return re.sub(r"\b\d+\s*-\s*test\b", " ", text, flags=re.IGNORECASE)

    def _extract_answer_chunks(self, text: str) -> List[str]:
        letters = "".join(re.findall(r"[ABCD]", text.upper()))
        return [letters[i:i + 20] for i in range(0, len(letters), 20) if len(letters[i:i + 20]) == 20]

    def _looks_like_test_label_line(self, text: str) -> bool:
        return bool(re.fullmatch(r"\d+\s*-\s*test(?:\s+\d+\s*-\s*test)*", text, flags=re.IGNORECASE))

    def _is_noise_line(self, text: str) -> bool:
        normalized = self._normalize_search_text(text).lower()
        if not normalized:
            return True
        if normalized.isdigit():
            return True
        if re.fullmatch(r"[\d\s.]+", normalized):
            return True
        return any(marker in normalized for marker in _NOISE_MARKERS)

    def _is_potential_topic(self, text: str) -> bool:
        normalized = self._normalize_search_text(text)
        if not normalized:
            return False
        if len(normalized) < 4 or len(normalized) > 120:
            return False
        if self._has_option_markers(normalized):
            return False
        alpha_count = sum(ch.isalpha() for ch in normalized)
        return alpha_count >= 4

    def _is_question_like(self, text: str) -> bool:
        normalized = self._normalize_search_text(text).lower()
        if "?" in normalized:
            return True
        if any(keyword in normalized for keyword in _QUESTION_KEYWORDS):
            return True
        if re.search(r"\d", normalized) and re.search(r"[+\-=:<>/%]", normalized):
            return True
        return False

    def _is_strong_heading(self, text: str) -> bool:
        normalized = self._normalize_search_text(text)
        if not normalized:
            return False
        if normalized.lower() in {"test", "-test"}:
            return False
        if re.match(r"^\d+\s*[.)]", normalized):
            return True
        letters = [ch for ch in normalized if ch.isalpha()]
        if not letters:
            return False
        uppercase_ratio = sum(ch.isupper() for ch in letters) / len(letters)
        if uppercase_ratio >= 0.55:
            return True
        first_alpha = next((ch for ch in normalized if ch.isalpha()), "")
        return bool(first_alpha and first_alpha.isupper() and len(normalized.split()) <= 6)

    def _is_displayable_topic(self, text: str) -> bool:
        normalized = self._clean_display_topic(text)
        if not self._is_potential_topic(normalized):
            return False
        if self._is_question_like(normalized):
            return False
        if normalized.lower().startswith("javob") or normalized.lower().startswith("yechish"):
            return False
        if normalized.lower() in {"test", "-test"}:
            return False
        tokens = [token for token in self._keyword_tokens(normalized) if token]
        if not tokens:
            return False
        if len(tokens) == 1 and tokens[0] in _GENERIC_TOPIC_BLACKLIST:
            return False
        if len(tokens) == 1 and len(tokens[0]) <= 5:
            return False
        return self._is_strong_heading(normalized)

    def _topic_looks_reasonable(self, text: str) -> bool:
        normalized = self._clean_display_topic(text)
        if not normalized:
            return False
        lowered = normalized.lower()
        if lowered.startswith("javob") or lowered.startswith("yechish"):
            return False
        if re.match(rf"^[{''.join(_OPTION_LABELS)}]\)", normalized, flags=re.IGNORECASE):
            return False
        if re.match(r"^\d+\)", normalized):
            return False
        if self._is_question_like(normalized):
            return False
        if any(keyword in normalized.lower() for keyword in _QUESTION_KEYWORDS):
            return False
        if self._count_suspicious_tokens(normalized):
            return False
        tokens = normalized.split()
        if tokens and tokens[-1].isalpha() and len(tokens[-1]) < 3:
            return False
        if len(normalized.split()) > 8:
            return False
        return True

    def _should_replace_topic(self, current_topic: str, candidate_topic: str) -> bool:
        if not candidate_topic:
            return False
        if not current_topic:
            return True
        current_tokens = self._keyword_tokens(current_topic)
        candidate_tokens = self._keyword_tokens(candidate_topic)
        if not candidate_tokens:
            return False
        if current_tokens == candidate_tokens:
            return False
        if "qism" in candidate_tokens and current_tokens & candidate_tokens:
            return False
        if len(candidate_tokens) < len(current_tokens) and current_tokens & candidate_tokens:
            return False
        return True

    def _has_option_markers(self, text: str) -> bool:
        return any(f"{label})" in text for label in _OPTION_LABELS)

    def _clean_option_text(self, text: str) -> str:
        return self._normalize_search_text(text).strip(" -_")

    def _strip_leading_marker(self, text: str) -> str:
        cleaned = self._normalize_search_text(text)
        while True:
            new_cleaned = re.sub(r"^[\[\]\|~<>]+", "", cleaned).strip()
            new_cleaned = re.sub(r"^\d+\s*[\[\]\|~<>]*", "", new_cleaned).strip()
            first, _, rest = new_cleaned.partition(" ")
            if first and len(first) <= 6 and re.search(r"[\[\]\|~0-9]", first):
                cleaned = rest.strip()
                continue
            if first and len(first) <= 6 and not any(ch in "aeiouo'’" for ch in first.lower()) and rest:
                cleaned = rest.strip()
                continue
            cleaned = new_cleaned
            break
        return cleaned.strip(" -_")

    def _clean_display_topic(self, text: str) -> str:
        cleaned = self._normalize_search_text(text)
        cleaned = re.sub(r"_+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip(" -_.,:;")
        letters = [ch for ch in cleaned if ch.isalpha()]
        if letters and sum(ch.isupper() for ch in letters) / len(letters) >= 0.8:
            prefix = ""
            body = cleaned
            match = re.match(r"^(\d+\s*[.)]?\s*)(.+)$", cleaned)
            if match:
                prefix, body = match.groups()
            body = body.lower()
            if body:
                body = body[0].upper() + body[1:]
            cleaned = f"{prefix}{body}".strip()
        return cleaned

    def _is_heading_token(self, token: str) -> bool:
        stripped = token.strip("[]{}()|_~<>.,:;")
        letters = [ch for ch in stripped if ch.isalpha()]
        if len(letters) < 3:
            return False
        return sum(ch.isupper() for ch in letters) / len(letters) >= 0.85

    def _is_leading_noise_token(self, token: str) -> bool:
        stripped = token.strip()
        if not stripped:
            return True
        lowered = stripped.lower()
        if lowered == "test" or re.fullmatch(r"\d+-?test", lowered):
            return True
        if re.fullmatch(r"[\[\]{}()|_~\\/<>^*+=-]+", stripped):
            return True
        if re.fullmatch(r"\d+[.)]?", stripped):
            return True
        core = re.sub(r"[^A-Za-z0-9']", "", stripped)
        if not core:
            return True
        if len(core) <= 1 and any(ch in stripped for ch in "[]{}()|_~<>\\"):
            return True
        if len(core) <= 5 and any(ch.islower() for ch in core) and any(ch.isupper() for ch in core):
            return True
        return False

    def _clean_question_text(self, text: str) -> str:
        cleaned = self._normalize_search_text(text)
        cleaned = re.sub(r"^\s*test\s*\d+\s*[.)]?\s*", "", cleaned, flags=re.IGNORECASE)
        tokens = cleaned.split()
        index = 0
        dropped_heading = False
        while index < len(tokens):
            token = tokens[index]
            if self._is_leading_noise_token(token):
                index += 1
                continue
            if self._is_heading_token(token):
                dropped_heading = True
                index += 1
                continue
            break
        if dropped_heading and index < len(tokens):
            while index < len(tokens) and self._is_leading_noise_token(tokens[index]):
                index += 1
        if index and len(tokens) - index >= 3:
            cleaned = " ".join(tokens[index:])
        cleaned = re.sub(r"([?.!])\s*\d{1,3}$", r"\1", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_")
        return cleaned

    def _question_looks_complete(self, text: str) -> bool:
        normalized = self._normalize_search_text(text)
        tokens = normalized.split()
        if len(tokens) < 3:
            return False
        first = tokens[0].lower().strip(",:;")
        if first in {"bo'lsa", "teng", "va", "yoki"}:
            return False
        if len(tokens) < 5 and not re.search(r"\d|[+\-=:*/<>]", normalized):
            return False
        if len(tokens) < 5 and not any(keyword in normalized.lower() for keyword in _QUESTION_KEYWORDS):
            return False
        comma_index = normalized.find(",")
        first_alpha = next((ch for ch in normalized if ch.isalpha()), "")
        if (
            first_alpha
            and first_alpha.islower()
            and 0 <= comma_index <= 35
            and not re.search(r"\d|[+\-=:*/<>]", normalized[:comma_index])
        ):
            return False
        return True

    def _option_fingerprint(self, text: str) -> str:
        normalized = self._normalize_search_text(text).lower()
        return re.sub(r"[^a-z0-9]+", "", normalized)

    def _count_suspicious_tokens(self, text: str) -> int:
        suspicious = 0
        for token in self._normalize_search_text(text).split():
            letters = re.sub(r"[^a-z]", "", token.lower())
            digits = re.sub(r"\D", "", token)
            if any(ch in token for ch in "&$@#"):
                suspicious += 1
                continue
            if len(letters) >= 4 and any(ch.islower() for ch in token) and any(ch.isupper() for ch in token):
                suspicious += 1
                continue
            if "\\" in token or "^" in token:
                suspicious += 1
                continue
            if letters and digits and len(letters) >= 2 and not any(ch in "aeiou" for ch in letters):
                suspicious += 1
                continue
            if len(letters) >= 4 and not any(ch in "aeiou" for ch in letters):
                suspicious += 1
        return suspicious

    def _options_look_usable(self, options: List[str]) -> bool:
        if len(options) < 4 or len(options) > 5:
            return False
        fingerprints = [self._option_fingerprint(option) for option in options]
        if any(not fingerprint for fingerprint in fingerprints):
            return False
        if len(set(fingerprints)) < len(options):
            return False
        if any("\\" in option for option in options):
            return False
        bad_alpha = 0
        numeric_options = 0
        for fingerprint in fingerprints:
            if fingerprint.isdigit():
                numeric_options += 1
            if len(fingerprint) == 1 and fingerprint.isalpha():
                bad_alpha += 1
        if numeric_options >= 2 and bad_alpha >= 1:
            return False
        return bad_alpha < 2

    def _question_quality_score(self, question: str, options: List[str], topic: str) -> int:
        score = 100
        weird_marks = len(re.findall(r"[\[\]{}|_~\\^]", question))
        score -= weird_marks * 6
        score -= len(re.findall(r"\d\s*['’]\s*\d", question)) * 18
        if re.search(r"\btest\b", question, flags=re.IGNORECASE):
            score -= 18
        if sum(1 for token in question.split()[:3] if self._is_heading_token(token)) >= 1:
            score -= 18
        first_parts = question.split()
        first_token = first_parts[0].lower() if first_parts else ""
        if first_token in {"bo'lsa,", "bo'lsa", "va", "ning", "ni", "ga", "da", "ham"}:
            score -= 30
        if first_parts:
            raw_first = first_parts[0]
            if len(raw_first) >= 6 and any(ch.islower() for ch in raw_first) and any(ch.isupper() for ch in raw_first):
                score -= 25
        letters = [ch for ch in question if ch.isalpha()]
        if letters:
            upper_ratio = sum(ch.isupper() for ch in letters) / len(letters)
            if upper_ratio > 0.45:
                score -= 15
        if len(question) < 16:
            score -= 20
        if len(question) > 220:
            score -= 12
        if not self._is_question_like(question):
            score -= 8
        if not self._is_displayable_topic(topic):
            score -= 10
        score -= self._count_suspicious_tokens(question) * 8
        option_fingerprints = [self._option_fingerprint(option) for option in options]
        if len(set(option_fingerprints)) < len(options):
            score -= 25
        for option, fingerprint in zip(options, option_fingerprints):
            letters = re.sub(r"[^a-z]", "", option.lower())
            digits = re.sub(r"\D", "", option)
            if len(fingerprint) == 1 and fingerprint.isalpha():
                score -= 12
            if letters and digits and len(letters) <= 2 and not any(op in option for op in "+-*/=()"):
                score -= 10
            if re.search(r"[\[\]{}|_~\\^]", option):
                score -= 6
            if re.search(r"\d\s*['’]\s*\d", option):
                score -= 12
            if self._count_suspicious_tokens(option):
                score -= 8
            if len(option) > 40:
                score -= 4
        return max(0, score)

    def _normalize_search_text(self, text: str) -> str:
        cleaned = str(text or "").replace("\u00ad", "")
        cleaned = cleaned.replace("\xa0", " ")
        cleaned = cleaned.replace("â€™", "'")
        cleaned = cleaned.replace("’", "'")
        cleaned = cleaned.replace("‘", "'")
        cleaned = cleaned.replace("ʻ", "'")
        cleaned = cleaned.replace("ʼ", "'")
        cleaned = cleaned.replace("`", "'")
        cleaned = cleaned.replace("â€”", " ")
        cleaned = cleaned.replace("â€“", " ")
        cleaned = cleaned.replace("—", " ")
        cleaned = cleaned.replace("–", " ")
        cleaned = cleaned.replace("•", " ")
        cleaned = cleaned.replace("¦", " ")
        cleaned = cleaned.replace("ﬁ", "fi")
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def _canonical_topic(self, text: str) -> str:
        normalized = self._normalize_search_text(text).lower()
        normalized = re.sub(r"^\d+\s*[.)]?\s*", "", normalized)
        normalized = re.sub(r"[^a-z0-9' ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _keyword_tokens(self, text: str) -> set[str]:
        normalized = self._canonical_topic(text)
        tokens = re.findall(r"[a-z0-9']+", normalized)
        return {token[:12] for token in tokens if len(token) >= 3}

    def _subject_from_quiz_type(self, quiz_type: str) -> str:
        normalized = self._normalize_subject(quiz_type)
        if normalized in {"algebra", "matematika", "geometriya", "ehtimollik"}:
            return normalized
        if "algebra" in normalized or "matematika" in normalized:
            return "matematika"
        return normalized

    def _source_matches_subject(self, source: Dict, subject: str | None) -> bool:
        normalized_subject = self._normalize_subject(subject)
        if not normalized_subject:
            return True
        aliases = {source["subject"], *source.get("aliases", [])}
        if normalized_subject in aliases:
            return True
        if normalized_subject == "matematika" and aliases & {"matematika", "algebra", "geometriya", "ehtimollik"}:
            return True
        return False

    def _normalize_subject(self, subject) -> str:
        raw = self._normalize_search_text(subject or "").lower()
        if "ehtimol" in raw or "statistik" in raw or "kombinator" in raw:
            return "ehtimollik"
        if "geometriya" in raw:
            return "geometriya"
        if "algebra" in raw:
            return "algebra"
        if "matematika" in raw:
            return "matematika"
        if "mantiq" in raw:
            return "mantiq"
        if "boshqotirma" in raw:
            return "boshqotirma"
        return raw


book_question_bank = BookQuestionBank()
