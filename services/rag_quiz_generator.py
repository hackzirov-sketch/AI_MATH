from __future__ import annotations

import hashlib
import random
import re
import uuid
from typing import Any, Dict, List, Optional

from services.knowledge_retriever import RetrievalResult, knowledge_retriever
from services.math_verifier import math_verifier
from services.question_schema import QuestionItem


class RAGQuizGenerator:
    """Build quiz questions only from retrieved and cleaned knowledge."""

    def generate_questions(
        self,
        topic: str,
        subject: str,
        grade: int,
        difficulty: str,
        count: int = 5,
    ) -> Dict[str, Any]:
        retrieval = knowledge_retriever.retrieve(topic=topic, subject=subject, grade=grade, max_results=max(count, 3))
        rng = random.Random(hashlib.sha1(f"{topic}|{subject}|{grade}|{difficulty}|{count}".encode("utf-8")).hexdigest())

        question_items: List[QuestionItem] = []
        question_items.extend(self._build_formula_questions(retrieval, subject, topic, grade, difficulty, rng, count))
        question_items.extend(self._build_fact_questions(retrieval, subject, topic, grade, difficulty, rng, count))

        unique_questions: List[QuestionItem] = []
        seen = set()
        for item in question_items:
            signature = item.question_text.strip().lower()
            if not signature or signature in seen:
                continue
            seen.add(signature)
            validation = math_verifier.validate_question_item(item)
            if validation.is_valid:
                unique_questions.append(item)
            if len(unique_questions) >= count:
                break

        return {
            "questions": [self._question_to_output(item) for item in unique_questions],
            "sources": [source.to_dict() for source in retrieval.sources],
            "confidence": retrieval.confidence,
            "structured": retrieval.structured.to_dict(),
        }

    def _build_formula_questions(
        self,
        retrieval: RetrievalResult,
        subject: str,
        topic: str,
        grade: int,
        difficulty: str,
        rng: random.Random,
        count: int,
    ) -> List[QuestionItem]:
        items: List[QuestionItem] = []
        for formula in retrieval.structured.formulas:
            parsed = self._parse_formula(formula)
            if not parsed:
                continue
            lhs, rhs, variables = parsed
            if not variables:
                continue
            values = {var: rng.randint(2, 9) for var in variables}
            expression = rhs
            for key, value in values.items():
                expression = re.sub(rf"\b{re.escape(key)}\b", str(value), expression)
            options = self._numeric_options(expression, rng)
            item = QuestionItem(
                id=str(uuid.uuid4()),
                subject=subject,
                topic=topic,
                grade=grade,
                difficulty=difficulty,
                type="rag_formula",
                question_text=self._build_formula_question_text(topic, formula, lhs, values),
                options=options["options"],
                correct_answer=options["correct_value"],
                explanation=f"Retrieval formulaga ko'ra: {formula}. Javob: {options['correct_value']}",
                metadata={
                    "validation": {
                        "type": "expression_value",
                        "expression": expression,
                    },
                    "option_labels": ["A", "B", "C", "D"],
                    "correct_label": options["correct_label"],
                    "retrieved_formula": formula,
                },
                source_info=self._pick_source_info(retrieval, formula),
            )
            items.append(item)
            if len(items) >= count:
                break
        return items

    def _build_fact_questions(
        self,
        retrieval: RetrievalResult,
        subject: str,
        topic: str,
        grade: int,
        difficulty: str,
        rng: random.Random,
        count: int,
    ) -> List[QuestionItem]:
        statements = (
            retrieval.structured.definitions
            + retrieval.structured.rules
            + retrieval.structured.important_facts
        )
        cleaned = [statement for statement in statements if 30 <= len(statement) <= 200]
        items: List[QuestionItem] = []
        for index, statement in enumerate(cleaned):
            distractors = [candidate for candidate in cleaned if candidate != statement]
            if len(distractors) < 3:
                continue
            rng.shuffle(distractors)
            options = [statement, distractors[0], distractors[1], distractors[2]]
            rng.shuffle(options)
            correct_index = options.index(statement)
            item = QuestionItem(
                id=str(uuid.uuid4()),
                subject=subject,
                topic=topic,
                grade=grade,
                difficulty=difficulty,
                type="rag_fact",
                question_text=f"Retrieval ma'lumotiga ko'ra {topic} haqida qaysi fikr to'g'ri?",
                options=options,
                correct_answer=statement,
                explanation=f"To'g'ri javob retrieved contentdan olingan: {statement}",
                metadata={
                    "validation": {
                        "type": "exact_option_match",
                        "value": statement,
                    },
                    "option_labels": ["A", "B", "C", "D"],
                    "correct_label": chr(65 + correct_index),
                    "retrieved_statement": statement,
                },
                source_info=self._pick_source_info(retrieval, statement),
            )
            items.append(item)
            if len(items) >= count:
                break
        return items

    def _parse_formula(self, formula: str) -> Optional[tuple[str, str, List[str]]]:
        match = re.search(r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*([A-Za-z0-9+\-*/(). ^]+)", formula)
        if not match:
            return None
        lhs = match.group(1).strip()
        rhs = match.group(2).strip()
        variables = sorted({token for token in re.findall(r"\b[a-zA-Z]\b", rhs) if token != lhs})
        if not variables:
            return None
        return lhs, rhs, variables

    def _build_formula_question_text(self, topic: str, formula: str, lhs: str, values: Dict[str, int]) -> str:
        values_text = ", ".join(f"{key}={value}" for key, value in values.items())
        return f"{topic} mavzusidagi {formula} formula asosida {values_text} bo'lsa, {lhs} ni toping."

    def _numeric_options(self, expression: str, rng: random.Random) -> Dict[str, Any]:
        computed = math_verifier._compute_answer({"type": "expression_value", "expression": expression})
        correct_value = str(computed)
        options = [correct_value]
        deltas = [-6, -4, -2, 2, 4, 6]
        rng.shuffle(deltas)
        if isinstance(computed, (int, float)):
            for delta in deltas:
                candidate = computed + delta
                candidate_text = str(int(candidate) if float(candidate).is_integer() else round(float(candidate), 6))
                if candidate_text not in options:
                    options.append(candidate_text)
                if len(options) == 4:
                    break
        while len(options) < 4:
            fallback = str(int(computed) + len(options) + 1 if isinstance(computed, (int, float)) else len(options) + 1)
            if fallback not in options:
                options.append(fallback)
        rng.shuffle(options)
        correct_index = options.index(correct_value)
        return {
            "options": options[:4],
            "correct_value": correct_value,
            "correct_label": chr(65 + correct_index),
        }

    def _pick_source_info(self, retrieval: RetrievalResult, fragment: str) -> Optional[Dict[str, Any]]:
        fragment_lower = fragment.lower()
        for source in retrieval.sources:
            if fragment_lower[:40] in source.content.lower():
                return {
                    "name": source.title,
                    "source_type": source.source_type,
                    "url": source.url,
                    "rank_score": source.rank_score,
                }
        if retrieval.sources:
            source = retrieval.sources[0]
            return {
                "name": source.title,
                "source_type": source.source_type,
                "url": source.url,
                "rank_score": source.rank_score,
            }
        return None

    def _question_to_output(self, item: QuestionItem) -> Dict[str, Any]:
        labels = item.metadata.get("option_labels") or ["A", "B", "C", "D"]
        correct_label = item.infer_correct_label() or item.metadata.get("correct_label", "A")
        output = {
            "question": item.question_text,
            "options": [f"{labels[index]}) {option}" for index, option in enumerate(item.options or [])],
            "answer": correct_label,
            "explanation": item.explanation,
            "source": (item.source_info or {}).get("url") or (item.source_info or {}).get("name"),
        }
        return output


rag_quiz_generator = RAGQuizGenerator()
