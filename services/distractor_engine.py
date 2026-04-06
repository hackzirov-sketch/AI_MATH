"""
services/distractor_engine.py — SMART DISTRACTOR GENERATION ENGINE

Variantlar shunchaki random bo'lmasin.
Noto'g'ri variantlar quyidagicha quriladi:
- 1 qadam xato hisob natijasi
- Amal ketma-ketligini noto'g'ri qo'llash
- Ko'paytirish o'rniga qo'shish yoki aksincha
- Qo'shni son
- O'xshash ko'rinish

Talablar:
- 4 ta variant
- 1 ta to'g'ri javob
- Variantlar takrorlanmasin
- To'g'ri javob joyi random
"""

from __future__ import annotations

import random
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DistractorResult:
    """Distractor generatsiya natijasi"""
    correct_answer: Any
    options: Dict[str, Any]
    correct_label: str
    generation_method: str = ""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)


class DistractorEngine:
    """
    Smart distractor generation engine.

    Strategiyalar:
    1. Off-by-one / off-by-step
    2. Operation swap (× o'rniga +)
    3. Partial computation (ketma-ketlikni oxirigacha bajarmagan)
    4. Adjacent number
    5. Sign error
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def generate_for_integer(self, correct: int, count: int = 3,
                              difficulty: str = "o'rta",
                              operations: List[str] = None) -> DistractorResult:
        """Integer javob uchun distractorlar"""
        distractor_set: set = {correct}
        methods_used = []

        strategies = self._get_strategies(correct, difficulty, operations)

        attempts = 0
        while len(distractor_set) < count + 1 and attempts < 50:
            attempts += 1
            strategy = self.rng.choice(strategies)
            try:
                d = strategy()
                if d is not None and d > 0 and d not in distractor_set:
                    distractor_set.add(d)
                    methods_used.append(strategy.__name__ if hasattr(strategy, '__name__') else 'unknown')
            except Exception:
                continue

        distractors = [d for d in distractor_set if d != correct]
        self.rng.shuffle(distractors)

        labels = ["A", "B", "C", "D"]
        values = [correct] + distractors[:count]

        while len(values) < 4:
            values.append(correct + self.rng.randint(1, 10))

        values = values[:4]
        self.rng.shuffle(values)

        options = {}
        correct_label = "A"
        for i, val in enumerate(values):
            options[labels[i]] = val
            if val == correct:
                correct_label = labels[i]

        return DistractorResult(
            correct_answer=correct,
            options=options,
            correct_label=correct_label,
            generation_method=", ".join(methods_used[:3]),
        )

    def generate_for_chain(self, values: List[int], operations: List[str],
                            correct: int) -> DistractorResult:
        """Zanjir operatsiya uchun distractorlar"""
        distractors = set()

        # Strategy 1: Partial chain (oxirgi amalni bajarmagan)
        if len(values) >= 2 and operations:
            partial = values[0]
            for i, op in enumerate(operations[:-1]):
                if op == "+":
                    partial += values[i + 1]
                elif op == "-":
                    partial -= values[i + 1]
                elif op == "×":
                    partial *= values[i + 1]
            distractors.add(partial)

        # Strategy 2: Operation swap (oxirgi amalni almashtirgan)
        if operations:
            last_op = operations[-1]
            last_val = values[-1]
            if last_op == "+":
                distractors.add(correct - 2 * last_val)
            elif last_op == "-":
                distractors.add(correct + 2 * last_val)
            elif last_op == "×":
                if last_val != 0:
                    distractors.add(correct + last_val)

        # Strategy 3: Off by first value
        distractors.add(correct + values[0])
        distractors.add(correct - values[0])

        # Strategy 4: Wrong operation (× o'rniga +)
        if operations and len(values) >= 2:
            for i, op in enumerate(operations):
                if op == "×" and i < len(values) - 1:
                    wrong = correct - values[i+1] * values[i] + values[i+1] + values[i]
                    distractors.add(wrong)
                    break

        distractors.discard(correct)
        distractors = {d for d in distractors if d > 0}

        return self._build_result(correct, list(distractors))

    def generate_for_equation(self, correct: int, equation_vars: Dict[str, int]) -> DistractorResult:
        """Tenglama uchun distractorlar"""
        distractors = set()

        # Off by variable
        for var, val in equation_vars.items():
            if isinstance(val, (int, float)):
                distractors.add(correct + int(val))
                distractors.add(correct - int(val))
                if val != 0:
                    distractors.add(correct * 2)

        # Common mistakes
        distractors.add(correct + 1)
        distractors.add(correct - 1)
        distractors.add(correct + 5)

        distractors.discard(correct)
        distractors = {d for d in distractors if d > 0}

        return self._build_result(correct, list(distractors))

    def generate_for_grid(self, correct: int, row_sum: int = None,
                           col_sum: int = None) -> DistractorResult:
        """Jadval uchun distractorlar"""
        distractors = set()

        if row_sum is not None:
            distractors.add(row_sum)
            distractors.add(row_sum + 1)
            distractors.add(row_sum - 1)

        if col_sum is not None:
            distractors.add(col_sum)
            distractors.add(col_sum + 1)
            distractors.add(col_sum - 1)

        distractors.add(correct + 3)
        distractors.add(correct - 3)
        distractors.add(correct + 10)

        distractors.discard(correct)
        distractors = {d for d in distractors if d > 0}

        return self._build_result(correct, list(distractors))

    def _get_strategies(self, correct: int, difficulty: str,
                        operations: List[str] = None) -> List:
        """Distractor strategiyalarini olish"""
        strategies = []

        if difficulty == "oson":
            strategies = [
                lambda: correct + self.rng.randint(1, 3),
                lambda: correct - self.rng.randint(1, min(3, correct - 1)),
                lambda: correct + self.rng.choice([2, 5, 10]),
                lambda: correct - self.rng.choice([2, 5]) if correct > 5 else correct + 3,
            ]
        elif difficulty == "o'rta":
            strategies = [
                lambda: correct + self.rng.randint(1, 8),
                lambda: correct - self.rng.randint(1, min(8, correct - 1)),
                lambda: correct * 2,
                lambda: correct // 2 if correct > 4 else correct + 5,
                lambda: int(correct * 1.1),
                lambda: int(correct * 0.9),
                lambda: correct + 10,
                lambda: correct - 10 if correct > 10 else correct + 7,
            ]
        else:
            strategies = [
                lambda: correct + self.rng.randint(1, 15),
                lambda: correct - self.rng.randint(1, min(15, correct - 1)),
                lambda: correct * self.rng.choice([2, 3]),
                lambda: correct + self.rng.choice([1, -1, 5, -5, 10, -10, 25, -25]),
                lambda: int(correct * self.rng.uniform(0.7, 1.3)),
                lambda: int(correct * self.rng.uniform(1.5, 2.5)),
                lambda: correct ** 2 if correct < 20 else correct * 2,
            ]

        return strategies

    def _build_result(self, correct: int, distractors: List[int]) -> DistractorResult:
        """Final result yaratish"""
        labels = ["A", "B", "C", "D"]
        distractors = [d for d in distractors if d > 0 and d != correct]
        self.rng.shuffle(distractors)

        values = [correct] + distractors[:3]
        while len(values) < 4:
            values.append(correct + self.rng.randint(1, 10))

        values = values[:4]
        self.rng.shuffle(values)

        options = {}
        correct_label = "A"
        for i, val in enumerate(values):
            options[labels[i]] = val
            if val == correct:
                correct_label = labels[i]

        return DistractorResult(
            correct_answer=correct,
            options=options,
            correct_label=correct_label,
        )


distractor_engine = DistractorEngine()
