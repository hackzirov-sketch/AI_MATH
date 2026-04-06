from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional

import sympy
from sympy import Eq, Symbol, sympify

from services.question_schema import QuestionItem


@dataclass
class MathValidationResult:
    is_valid: bool
    computed_answer: Any = None
    matched_option_indexes: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_deterministic: bool = False


class MathVerifier:
    """Deterministic validator for generated math questions."""

    def validate_question_item(self, item: QuestionItem) -> MathValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not item.question_text.strip():
            errors.append("Savol matni bo'sh")
        if item.options is not None and len(item.options) != 4:
            errors.append("Variantlar soni 4 ta emas")

        payload = self._resolve_validation_payload(item)
        if not payload:
            warnings.append("Deterministic validation payload topilmadi")
            return MathValidationResult(
                is_valid=not errors,
                errors=errors,
                warnings=warnings,
                is_deterministic=False,
            )

        try:
            computed_answer = self._compute_answer(payload)
        except Exception as exc:
            errors.append(f"Javobni hisoblashda xato: {exc}")
            return MathValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                is_deterministic=True,
            )

        matched_indexes = self._match_options(item.options, computed_answer)
        expected_answer = self._normalize_answer(item.correct_answer)
        computed_normalized = self._normalize_answer(computed_answer)

        if expected_answer is not None and computed_normalized != expected_answer:
            errors.append(f"Correct answer noto'g'ri: expected={expected_answer}, computed={computed_normalized}")

        if item.options is not None and len(matched_indexes) != 1:
            errors.append("Hisoblangan javob variantlarda aynan bitta marta topilmadi")

        return MathValidationResult(
            is_valid=not errors,
            computed_answer=computed_answer,
            matched_option_indexes=matched_indexes,
            errors=errors,
            warnings=warnings,
            is_deterministic=True,
        )

    def validate_legacy_question(
        self,
        payload: Dict[str, Any],
        subject: str,
        grade: int,
        difficulty: str,
    ) -> MathValidationResult:
        item = QuestionItem.from_legacy_dict(payload, subject=subject, grade=grade, difficulty=difficulty)
        return self.validate_question_item(item)

    def _resolve_validation_payload(self, item: QuestionItem) -> Optional[Dict[str, Any]]:
        metadata = item.metadata or {}
        payload = metadata.get("validation") or metadata.get("validation_payload")
        if isinstance(payload, dict):
            return payload

        inferred = self._infer_validation_payload(item.question_text)
        if inferred:
            return inferred
        return None

    def _compute_answer(self, payload: Dict[str, Any]) -> Any:
        kind = str(payload.get("type", "")).strip().lower()

        if kind == "expression_value":
            expr = self._normalize_arithmetic_expression(str(payload["expression"]))
            return self._parse_numeric(sympify(expr))

        if kind == "equation_solution":
            equation = str(payload["equation"])
            variable_name = str(payload.get("variable", "x"))
            variable = Symbol(variable_name)
            left_text, right_text = [self._normalize_equation_expression(part) for part in equation.split("=", 1)]
            solution = sympy.solve(Eq(sympify(left_text), sympify(right_text)), variable)
            if len(solution) != 1:
                raise ValueError("Tenglama yagona yechim bermadi")
            return self._parse_numeric(solution[0])

        if kind == "fraction_simplify":
            fraction = Fraction(int(payload["numerator"]), int(payload["denominator"]))
            return f"{fraction.numerator}/{fraction.denominator}"

        if kind == "percentage_of":
            value = Fraction(int(payload["percent"]), 100) * Fraction(str(payload["whole"]))
            return self._parse_numeric(value)

        if kind == "proportion":
            a = Fraction(str(payload["a"]))
            b = Fraction(str(payload["b"]))
            c = Fraction(str(payload["c"]))
            return self._parse_numeric((b * c) / a)

        if kind == "geometry_formula":
            expression = self._normalize_equation_expression(str(payload["formula"]))
            values = {key: sympify(str(value)) for key, value in dict(payload.get("values") or {}).items()}
            return self._parse_numeric(sympify(expression).subs(values))

        if kind == "sequence_next_term":
            sequence = [Fraction(str(value)) for value in payload.get("sequence", [])]
            strategy = str(payload.get("strategy", "infer")).lower()
            return self._compute_sequence_next_term(sequence, strategy)

        if kind == "exact_option_match":
            return payload.get("value")

        if kind == "direct_value":
            return payload.get("value")

        raise ValueError(f"Qo'llab-quvvatlanmagan validation turi: {kind}")

    def _compute_sequence_next_term(self, sequence: List[Fraction], strategy: str) -> Any:
        if len(sequence) < 3:
            raise ValueError("Ketma-ketlik uchun kamida 3 ta element kerak")

        if strategy == "infer":
            diffs = [sequence[idx + 1] - sequence[idx] for idx in range(len(sequence) - 1)]
            if len(set(diffs)) == 1:
                strategy = "arithmetic"
            else:
                ratios = []
                for idx in range(len(sequence) - 1):
                    if sequence[idx] == 0:
                        ratios = []
                        break
                    ratios.append(sequence[idx + 1] / sequence[idx])
                if ratios and len(set(ratios)) == 1:
                    strategy = "geometric"
                else:
                    raise ValueError("Ketma-ketlikni infer qilib bo'lmadi")

        if strategy == "arithmetic":
            step = sequence[1] - sequence[0]
            return self._parse_numeric(sequence[-1] + step)

        if strategy == "geometric":
            ratio = sequence[1] / sequence[0]
            return self._parse_numeric(sequence[-1] * ratio)

        raise ValueError(f"Noma'lum ketma-ketlik strategiyasi: {strategy}")

    def _match_options(self, options: Optional[List[str]], computed_answer: Any) -> List[int]:
        if not options:
            return []
        matched: List[int] = []
        target = self._normalize_answer(computed_answer)
        for index, option in enumerate(options):
            if self._normalize_answer(option) == target:
                matched.append(index)
        return matched

    def _infer_validation_payload(self, question_text: str) -> Optional[Dict[str, Any]]:
        text = question_text.strip()

        arithmetic = re.search(r"(\d+(?:\.\d+)?)\s*([+\-*/xX×÷])\s*(\d+(?:\.\d+)?)", text)
        if arithmetic:
            left, operator, right = arithmetic.groups()
            return {
                "type": "expression_value",
                "expression": f"{left} {operator} {right}",
            }

        equation = re.search(r"([a-zA-Z])\s*([+\-])\s*(\d+)\s*=\s*(\d+)", text)
        if equation:
            variable, operator, number, result = equation.groups()
            return {
                "type": "equation_solution",
                "equation": f"{variable} {operator} {number} = {result}",
                "variable": variable,
            }

        percent = re.search(r"(\d+)\s*(?:%|foiz)\w*\s*(?:i|ini)?\s*toping", text.lower())
        base = re.search(r"(\d+)\s+son", text.lower())
        if percent and base:
            return {
                "type": "percentage_of",
                "percent": int(percent.group(1)),
                "whole": int(base.group(1)),
            }

        fraction = re.search(r"(\d+)\s*/\s*(\d+)\s+kasr", text.lower())
        if fraction and "qisqart" in text.lower():
            return {
                "type": "fraction_simplify",
                "numerator": int(fraction.group(1)),
                "denominator": int(fraction.group(2)),
            }

        return None

    def _normalize_arithmetic_expression(self, expression: str) -> str:
        return (
            expression.replace("×", "*")
            .replace("÷", "/")
            .replace("^", "**")
        )

    def _normalize_equation_expression(self, expression: str) -> str:
        normalized = (
            expression.replace("×", "*")
            .replace("÷", "/")
            .replace("^", "**")
        )
        normalized = re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", "*", normalized)
        normalized = re.sub(r"(?<=\d)\s*(?=[a-zA-Z])", "*", normalized)
        normalized = re.sub(r"(?<=[a-zA-Z])\s*(?=\d)", "*", normalized)
        return normalized

    def _normalize_answer(self, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()

        if re.fullmatch(r"[A-D]", text.upper()):
            return text.upper()

        if re.fullmatch(r"-?\d+", text):
            return int(text)

        if re.fullmatch(r"-?\d+\.\d+", text):
            number = float(text)
            return int(number) if number.is_integer() else round(number, 6)

        if re.fullmatch(r"-?\d+\s*/\s*-?\d+", text):
            fraction = Fraction(text.replace(" ", ""))
            return f"{fraction.numerator}/{fraction.denominator}"

        return text.lower()

    def _parse_numeric(self, value: Any) -> Any:
        if isinstance(value, Fraction):
            return int(value) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"

        if hasattr(value, "is_real") and getattr(value, "is_real", False):
            numeric = float(value)
            return int(numeric) if numeric.is_integer() else round(numeric, 6)

        if isinstance(value, (int, float)):
            return int(value) if float(value).is_integer() else round(float(value), 6)

        return value


math_verifier = MathVerifier()
