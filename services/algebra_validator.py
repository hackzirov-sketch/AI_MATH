"""
services/algebra_validator.py — ALGEBRA VALIDATION ENGINE

Savol generatsiyasi va answer tekshirish bir xil matematik asosga tayansin.

Mas'uliyatlar:
- Generated answers correctness checking
- Puzzle equations consistency
- Rebus/symbol equation validation
- Distractor plausibility
- Unique solution verification
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from fractions import Fraction

from services.symbolic_engine import symbolic_engine, SymbolicEngine
from services.render_specs import ValidationReport, ProblemSpec

logger = logging.getLogger(__name__)


@dataclass
class AlgebraValidation:
    """Algebra validatsiya natijasi"""
    is_valid: bool = True
    correct_answer: Optional[Any] = None
    equivalent_forms: List[str] = field(default_factory=list)
    step_by_step: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class AlgebraValidator:
    """
    Algebra validatsiya engine.

    Puzzle generatsiya natijalarini tekshiradi:
    1. Arifmetik ifoda to'g'riligi
    2. Tenglama konsistentligi
    3. Rebus qiymatlarining yagonaligi
    4. Distractor plausibility
    """

    def __init__(self):
        self.engine = symbolic_engine

    def validate_arithmetic(self, expression: str, expected_answer: Any) -> AlgebraValidation:
        """Arifmetik ifoda validatsiyasi"""
        result = AlgebraValidation()

        is_correct = self.engine.verify_answer(expression, expected_answer)
        result.is_valid = is_correct

        if not is_correct:
            result.errors.append(f"Expression '{expression}' != {expected_answer}")
            actual = self.engine.simplify_expression(expression)
            result.correct_answer = actual.get_answer()
            result.warnings.append(f"Actual answer: {result.correct_answer}")

        if is_correct:
            result.correct_answer = expected_answer
            canonical = self.engine.canonical_answer(expression)
            if canonical:
                result.equivalent_forms.append(canonical)

        return result

    def validate_chain_operations(self, values: List[int], operations: List[str],
                                   final_answer: Any) -> AlgebraValidation:
        """Zanjir operatsiyalarni tekshirish"""
        result = AlgebraValidation()

        if not values or not operations:
            result.is_valid = False
            result.errors.append("Empty values or operations")
            return result

        if len(operations) != len(values) - 1:
            result.is_valid = False
            result.errors.append("Operations count != values count - 1")
            return result

        computed = values[0]
        steps = [f"{values[0]}"]

        for i, op in enumerate(operations):
            val = values[i + 1]
            if op == "+":
                computed += val
                steps.append(f"+ {val} = {computed}")
            elif op == "-":
                computed -= val
                steps.append(f"- {val} = {computed}")
            elif op == "×" or op == "*":
                computed *= val
                steps.append(f"× {val} = {computed}")
            elif op == "÷" or op == "/":
                if val == 0:
                    result.is_valid = False
                    result.errors.append("Division by zero")
                    return result
                computed = Fraction(computed, val)
                if computed.denominator == 1:
                    computed = computed.numerator
                steps.append(f"÷ {val} = {computed}")

        result.step_by_step = steps

        expected = final_answer
        if isinstance(expected, str):
            try:
                expected = int(expected)
            except ValueError:
                try:
                    expected = float(expected)
                except ValueError:
                    pass

        if isinstance(computed, (int, float)) and isinstance(expected, (int, float)):
            result.is_valid = abs(float(computed) - float(expected)) < 0.001
        else:
            result.is_valid = str(computed) == str(expected)

        result.correct_answer = computed

        if not result.is_valid:
            result.errors.append(f"Computed {computed} != expected {expected}")

        return result

    def validate_flow_diagram(self, input_val: int, operations: List[Tuple[str, int]],
                               expected_output: Any) -> AlgebraValidation:
        """Oqim diagrammasi validatsiyasi"""
        values = [input_val]
        ops = []

        for op, val in operations:
            values.append(val)
            ops.append(op)

        return self.validate_chain_operations(values, ops, expected_output)

    def validate_grid_sums(self, grid: List[List[Any]], missing_pos: Tuple[int, int],
                            expected_answer: Any, rule_type: str = "row_sum",
                            rule_value: Any = None) -> AlgebraValidation:
        """Jadval yig'indi validatsiyasi"""
        result = AlgebraValidation()

        rows = len(grid)
        cols = len(grid[0]) if grid else 0

        if rows == 0 or cols == 0:
            result.is_valid = False
            result.errors.append("Empty grid")
            return result

        mr, mc = missing_pos

        if rule_type == "row_sum":
            if mr >= rows:
                result.is_valid = False
                result.errors.append("Missing row out of range")
                return result

            row = grid[mr]
            known_sum = sum(v for v in row if isinstance(v, (int, float)))
            if rule_value is not None:
                computed = rule_value - known_sum
            else:
                computed = None

        elif rule_type == "col_sum":
            if mc >= cols:
                result.is_valid = False
                result.errors.append("Missing col out of range")
                return result

            col_vals = [grid[r][mc] for r in range(rows)]
            known_sum = sum(v for v in col_vals if isinstance(v, (int, float)))
            if rule_value is not None:
                computed = rule_value - known_sum
            else:
                computed = None

        else:
            computed = expected_answer

        if computed is not None:
            if isinstance(computed, (int, float)) and isinstance(expected_answer, (int, float)):
                result.is_valid = abs(float(computed) - float(expected_answer)) < 0.001
            else:
                result.is_valid = str(computed) == str(expected_answer)

            result.correct_answer = computed

            if not result.is_valid:
                result.errors.append(f"Grid answer {computed} != expected {expected_answer}")

        return result

    def validate_rebus_symbols(self, equations: List[str],
                                symbol_mapping: Dict[str, int]) -> AlgebraValidation:
        """Rebus belgi tenglamalari validatsiyasi"""
        result = AlgebraValidation()

        if not symbol_mapping:
            result.is_valid = False
            result.errors.append("No symbol mapping provided")
            return result

        unique_values = set(symbol_mapping.values())
        if len(unique_values) != len(symbol_mapping):
            result.is_valid = False
            result.errors.append("Symbols must have unique values")
            return result

        for eq_str in equations:
            substituted = eq_str
            for sym, val in symbol_mapping.items():
                substituted = substituted.replace(sym, str(val))

            if "=" in substituted:
                parts = substituted.split("=", 1)
                lhs = parts[0].strip()
                rhs = parts[1].strip()

                try:
                    lhs_val = eval(lhs.replace("×", "*").replace("÷", "/"))
                    rhs_val = eval(rhs.replace("×", "*").replace("÷", "/"))

                    if abs(lhs_val - rhs_val) > 0.001:
                        result.is_valid = False
                        result.errors.append(f"Equation not satisfied: {lhs}={lhs_val} != {rhs}={rhs_val}")
                except Exception as e:
                    result.warnings.append(f"Cannot verify equation: {e}")

        result.correct_answer = symbol_mapping
        return result

    def validate_unique_solution(self, problem: ProblemSpec) -> bool:
        """Yagona yechim borligini tekshirish"""
        if not problem.expressions:
            return True

        for expr_str in problem.expressions:
            if "=" in expr_str:
                solution = self.engine.solve_equation(expr_str)
                if not solution.is_unique:
                    return False
                if solution.errors:
                    return False

        return True

    def generate_distractors(self, correct_answer: int, count: int = 3,
                              difficulty: str = "o'rta") -> List[int]:
        """
        Plausible distractor variantlari yaratish.
        
        Strategiya:
        1. 1 qadam xato hisob natijasi
        2. Amal almashtirish (ko'paytirish o'rniga qo'shish)
        3. Qo'shni son
        4. O'xshash ko'rinish
        """
        distractors: set = set()
        attempts = 0

        while len(distractors) < count and attempts < 50:
            attempts += 1
            d = self._generate_single_distractor(correct_answer, difficulty)
            if d != correct_answer and d > 0:
                distractors.add(d)

        result = list(distractors)[:count]
        while len(result) < count:
            result.append(correct_answer + random.randint(1, 10))

        random.shuffle(result)
        return result

    def _generate_single_distractor(self, correct: int, difficulty: str) -> int:
        """Bitta distractor yaratish"""
        strategies = []

        if difficulty == "oson":
            strategies = [
                lambda: correct + random.randint(1, 5),
                lambda: correct - random.randint(1, min(5, correct - 1)),
                lambda: correct + 10,
                lambda: correct - 10 if correct > 10 else correct + 3,
            ]
        elif difficulty == "o'rta":
            strategies = [
                lambda: correct + random.randint(1, 10),
                lambda: correct - random.randint(1, min(10, correct - 1)),
                lambda: correct * 2,
                lambda: correct // 2 if correct > 2 else correct + 5,
                lambda: int(correct * 1.1),
                lambda: int(correct * 0.9),
            ]
        else:
            strategies = [
                lambda: correct + random.randint(1, 20),
                lambda: correct - random.randint(1, min(20, correct - 1)),
                lambda: correct * random.choice([2, 3]),
                lambda: correct + random.choice([1, -1, 5, -5, 10, -10]),
                lambda: int(correct * random.uniform(0.8, 1.2)),
                lambda: int(correct * random.uniform(1.5, 2.5)),
            ]

        strategy = random.choice(strategies)
        try:
            d = strategy()
            return max(1, int(d))
        except Exception:
            return correct + random.randint(1, 5)

    def validate_answer_options(self, correct_answer: int,
                                 options: Dict[str, int]) -> bool:
        """Answer options validligini tekshirish"""
        if len(options) != 4:
            return False

        if correct_answer not in options.values():
            return False

        if len(set(options.values())) != 4:
            return False

        return True


algebra_validator = AlgebraValidator()
