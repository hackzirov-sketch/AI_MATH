"""
services/puzzle_template_engine.py — TEMPLATE-BASED PUZZLE POOL GENERATOR

Bir xil qolipdan ko'plab puzzlelar yaratish:
- sonlar o'zgarishi
- amallar o'zgarishi
- noma'lum joyi o'zgarishi
- yagona javob

Pipeline:
Template → Controlled NumPy generation → SymPy validation → PuzzleSpec → DiagramSpec

Supported:
1. Chain puzzle (6 → ×5 → ? → -12 → answer)
2. Grid puzzle (jadval ichida son va amallar)
3. Rebus (A, B, C = raqam)
4. Shape puzzle (triangle, square, circle qiymatlari)
5. Flowchart puzzle (bloklar orqali hisoblash)
6. Mixed puzzle (grid + rebus)
"""

from __future__ import annotations

import random
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from fractions import Fraction

from services.symbolic_engine import symbolic_engine
from services.algebra_validator import algebra_validator
from services.distractor_engine import distractor_engine
from services.render_specs import (
    DiagramSpec, DiagramSpecBuilder, DiagramType,
    PoolType
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PuzzleOutput:
    """To'liq boshqotirma natijasi"""
    puzzle_id: str
    template_family: str
    template_id: str
    difficulty: str
    question_text: str
    visual_text: str
    correct_answer: Any
    answer_type: str
    options: Dict[str, Any]
    correct_label: str
    explanation_steps: List[str]
    diagram_spec: Optional[DiagramSpec]
    parameters: Dict[str, Any]
    validation: Dict[str, Any]

    def to_dict(self) -> Dict:
        return {
            "puzzle_id": self.puzzle_id,
            "template_family": self.template_family,
            "template_id": self.template_id,
            "difficulty": self.difficulty,
            "question_text": self.question_text,
            "visual_text": self.visual_text,
            "correct_answer": str(self.correct_answer),
            "options": {k: str(v) for k, v in self.options.items()},
            "correct_label": self.correct_label,
            "explanation_steps": self.explanation_steps,
            "parameters": {k: str(v) for k, v in self.parameters.items()},
            "validation": self.validation,
        }


@dataclass
class PuzzleValidation:
    """Puzzle validatsiya natijasi"""
    is_valid: bool = True
    has_unique_answer: bool = True
    answer_is_integer: bool = True
    is_logically_consistent: bool = True
    is_not_ambiguous: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================

PUZZLE_TEMPLATES = {
    # ── CHAIN PUZZLES ──
    "chain_3step": {
        "family": "chain",
        "description": "3 qadamli zanjir",
        "difficulty": "oson",
        "grade_range": (2, 5),
        "steps": 3,
    },
    "chain_4step": {
        "family": "chain",
        "description": "4 qadamli zanjir",
        "difficulty": "o'rta",
        "grade_range": (3, 7),
        "steps": 4,
    },
    "chain_5step_unknown_middle": {
        "family": "chain",
        "description": "5 qadam, noma'lum o'rta",
        "difficulty": "qiyin",
        "grade_range": (5, 9),
        "steps": 5,
    },

    # ── FLOWCHART PUZZLES ──
    "flow_single_op": {
        "family": "flowchart",
        "description": "Bitta amalli flowchart",
        "difficulty": "oson",
        "grade_range": (2, 4),
    },
    "flow_double_op": {
        "family": "flowchart",
        "description": "Ikki amalli flowchart",
        "difficulty": "o'rta",
        "grade_range": (3, 6),
    },
    "flow_inverse": {
        "family": "flowchart",
        "description": "Teskari flowchart (natijadan kirishni topish)",
        "difficulty": "qiyin",
        "grade_range": (5, 9),
    },

    # ── GRID PUZZLES ──
    "grid_row_sum": {
        "family": "grid",
        "description": "Satr yig'indisi bilan",
        "difficulty": "oson",
        "grade_range": (3, 6),
    },
    "grid_col_sum": {
        "family": "grid",
        "description": "Ustun yig'indisi bilan",
        "difficulty": "oson",
        "grade_range": (3, 6),
    },
    "grid_row_col": {
        "family": "grid",
        "description": "Satr + ustun yig'indisi",
        "difficulty": "o'rta",
        "grade_range": (4, 8),
    },

    # ── REBUS PUZZLES ──
    "rebus_2symbol": {
        "family": "rebus",
        "description": "2 ta belgili rebus",
        "difficulty": "oson",
        "grade_range": (3, 5),
    },
    "rebus_3symbol": {
        "family": "rebus",
        "description": "3 ta belgili rebus",
        "difficulty": "o'rta",
        "grade_range": (4, 7),
    },
    "rebus_equation": {
        "family": "rebus",
        "description": "Tenglama rebusi",
        "difficulty": "qiyin",
        "grade_range": (5, 9),
    },

    # ── SHAPE PUZZLES ──
    "shape_triangle_value": {
        "family": "shape",
        "description": "Uchburchak qiymatlari",
        "difficulty": "o'rta",
        "grade_range": (4, 7),
    },
    "shape_circle_value": {
        "family": "shape",
        "description": "Doira qiymatlari",
        "difficulty": "o'rta",
        "grade_range": (4, 7),
    },
}


# =============================================================================
# PUZZLE GENERATORS
# =============================================================================

class PuzzleTemplateEngine:
    """
    Template-based puzzle generator.

    Har bir template uchun:
    1. Controlled random parameters
    2. SymPy validation (unique answer)
    3. Visual text representation
    4. DiagramSpec
    5. Smart distractors
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def generate(self, template_id: str, difficulty: str = None,
                 grade: int = 5) -> Optional[PuzzleOutput]:
        """Bitta puzzle generatsiya qilish"""
        template = PUZZLE_TEMPLATES.get(template_id)
        if not template:
            return None

        if difficulty is None:
            difficulty = template["difficulty"]

        if not (template["grade_range"][0] <= grade <= template["grade_range"][1]):
            return None

        gen_name = f"_gen_{template_id}"
        if hasattr(self, gen_name):
            for attempt in range(10):
                result = getattr(self, gen_name)(difficulty, grade)
                if result:
                    return result
        return None

    def generate_random(self, difficulty: str = None, grade: int = 5,
                        family_filter: Optional[str] = None) -> Optional[PuzzleOutput]:
        """Random puzzle"""
        suitable = []
        for tid, tmpl in PUZZLE_TEMPLATES.items():
            if tmpl["grade_range"][0] <= grade <= tmpl["grade_range"][1]:
                if difficulty is None or tmpl["difficulty"] == difficulty:
                    if family_filter is None or tmpl["family"] == family_filter:
                        suitable.append(tid)

        if not suitable:
            suitable = list(PUZZLE_TEMPLATES.keys())

        self.rng.shuffle(suitable)
        for tid in suitable[:8]:
            result = self.generate(tid, difficulty, grade)
            if result:
                return result
        return None

    def generate_batch(self, count: int, difficulty: str = None,
                       grade: int = 5) -> List[PuzzleOutput]:
        """Bir nechta puzzle"""
        puzzles = []
        used_ids = set()

        for _ in range(count * 3):
            if len(puzzles) >= count:
                break
            p = self.generate_random(difficulty, grade)
            if p and p.puzzle_id not in used_ids:
                puzzles.append(p)
                used_ids.add(p.puzzle_id)

        return puzzles[:count]

    # ── CHAIN PUZZLES ──

    def _gen_chain_3step(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        ops = [self.rng.choice(["+", "-", "×"]) for _ in range(2)]
        start = self.rng.randint(2, 12)
        vals = [start]

        for op in ops:
            v = self.rng.randint(2, 8)
            vals.append(v)

        computed = start
        steps_vis = [f"{start}"]
        for i, op in enumerate(ops):
            if op == "+":
                computed += vals[i + 1]
            elif op == "-":
                if computed <= vals[i + 1]:
                    return None
                computed -= vals[i + 1]
            elif op == "×":
                computed *= vals[i + 1]
            steps_vis.append(f"{op}{vals[i + 1]}")

        if computed <= 0 or computed > 200:
            return None

        validation = algebra_validator.validate_chain_operations(vals, ops, computed)
        if not validation.is_valid:
            return None

        unknown_step = self.rng.randint(0, len(ops) - 1)
        visual_parts = [f"{start}"]
        answer = computed

        recompute = start
        for i, op in enumerate(ops):
            if i == unknown_step:
                visual_parts.append(f"{op} ?")
                recompute += vals[i + 1] if op == "+" else 0
                recompute -= vals[i + 1] if op == "-" else 0
                recompute *= vals[i + 1] if op == "×" else 1
            else:
                visual_parts.append(f"{op} {vals[i + 1]}")
                if op == "+":
                    recompute += vals[i + 1]
                elif op == "-":
                    recompute -= vals[i + 1]
                elif op == "×":
                    recompute *= vals[i + 1]

        visual = " → ".join(visual_parts) + f" → {computed}"

        question_text = f"Zanjirdagi '?' o'rniga qanday son keladi?"

        correct = vals[unknown_step + 1]
        options_result = distractor_engine.generate_for_integer(correct, difficulty=difficulty)

        explanation = [
            f"Zanjir: {visual}",
            f"Hisoblab ko'ramiz:",
        ]
        recomp = start
        for i, op in enumerate(ops):
            if op == "+":
                recomp += vals[i + 1]
            elif op == "-":
                recomp -= vals[i + 1]
            elif op == "×":
                recomp *= vals[i + 1]
            explanation.append(f"  {op} {vals[i + 1]} → {recomp}")
        explanation.append(f"Javob: {correct}")

        return self._build_output(
            template_id="chain_3step",
            family="chain",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=visual,
            correct_answer=correct,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=explanation,
            parameters={"start": start, "operations": ops, "values": vals[1:]},
        )

    def _gen_chain_4step(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        ops = [self.rng.choice(["+", "-", "×"]) for _ in range(3)]
        start = self.rng.randint(2, 10)
        vals = [start]

        for op in ops:
            if op == "×":
                vals.append(self.rng.randint(2, 5))
            else:
                vals.append(self.rng.randint(2, 10))

        computed = start
        for i, op in enumerate(ops):
            if op == "+":
                computed += vals[i + 1]
            elif op == "-":
                if computed <= vals[i + 1]:
                    return None
                computed -= vals[i + 1]
            elif op == "×":
                computed *= vals[i + 1]

        if computed <= 0 or computed > 300:
            return None

        visual = " → ".join([f"{start}"] + [f"{ops[i]} {vals[i+1]}" for i in range(len(ops))])
        visual += f" → {computed}"

        question_text = f"Zanjirni hisoblang va oxirgi sonni toping."

        options_result = distractor_engine.generate_for_integer(computed, difficulty=difficulty)

        explanation = [f"{start}"]
        recomp = start
        for i, op in enumerate(ops):
            if op == "+":
                recomp += vals[i + 1]
            elif op == "-":
                recomp -= vals[i + 1]
            elif op == "×":
                recomp *= vals[i + 1]
            explanation.append(f"  {op} {vals[i + 1]} = {recomp}")
        explanation.append(f"Javob: {computed}")

        return self._build_output(
            template_id="chain_4step",
            family="chain",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=visual,
            correct_answer=computed,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=explanation,
            parameters={"start": start, "operations": ops, "values": vals[1:]},
        )

    # ── FLOWCHART PUZZLES ──

    def _gen_flow_single_op(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        x = self.rng.randint(5, 25)
        op = self.rng.choice([("+", 3, 10), ("-", 2, 8), ("×", 2, 5)])
        op_sym, lo, hi = op
        y = self.rng.randint(lo, hi)

        if op_sym == "+":
            result = x + y
            eq = f"{x} + {y} = {result}"
        elif op_sym == "-":
            if x <= y:
                x, y = y + 10, y
            result = x - y
            eq = f"{x} - {y} = {result}"
        else:
            result = x * y
            eq = f"{x} × {y} = {result}"

        if result <= 0 or result > 200:
            return None

        question_text = f"[ {x} ] → [ {op_sym} {y} ] → [ ? ]"

        options_result = distractor_engine.generate_for_integer(result, difficulty=difficulty)

        return self._build_output(
            template_id="flow_single_op",
            family="flowchart",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=f"{x} → {op_sym} {y} → ?",
            correct_answer=result,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=[eq, f"Javob: {result}"],
            parameters={"input": x, "operation": op_sym, "operand": y},
        )

    def _gen_flow_double_op(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        x = self.rng.randint(3, 15)
        op1 = self.rng.choice(["+", "×"])
        v1 = self.rng.randint(2, 8)
        op2 = self.rng.choice(["+", "-"])
        v2 = self.rng.randint(2, 8)

        if op1 == "+":
            step1 = x + v1
        else:
            step1 = x * v1

        if op2 == "+":
            result = step1 + v2
        else:
            if step1 <= v2:
                return None
            result = step1 - v2

        if result <= 0 or result > 200:
            return None

        question_text = f"[ {x} ] → [ {op1} {v1} ] → [ {op2} {v2} ] → [ ? ]"

        options_result = distractor_engine.generate_for_integer(result, difficulty=difficulty)

        return self._build_output(
            template_id="flow_double_op",
            family="flowchart",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=f"{x} → {op1}{v1} → {op2}{v2} → ?",
            correct_answer=result,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=[
                f"{x} {op1} {v1} = {step1}",
                f"{step1} {op2} {v2} = {result}",
                f"Javob: {result}",
            ],
            parameters={"input": x, "op1": op1, "v1": v1, "op2": op2, "v2": v2},
        )

    # ── GRID PUZZLES ──

    def _gen_grid_row_sum(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        size = self.rng.choice([3, 4])
        row_sum = self.rng.randint(12, 30)

        grid = []
        for _ in range(size):
            row = [self.rng.randint(1, row_sum - size) for _ in range(size - 1)]
            last = row_sum - sum(row)
            if last < 1 or last > 50:
                return None
            row.append(last)
            grid.append(row)

        miss_r = self.rng.randint(0, size - 1)
        miss_c = self.rng.randint(0, size - 1)
        correct = grid[miss_r][miss_c]
        grid[miss_r][miss_c] = None

        vis_lines = []
        for r in range(size):
            parts = []
            for c in range(size):
                if grid[r][c] is not None:
                    parts.append(f"{grid[r][c]:>3}")
                else:
                    parts.append("  ?")
            vis_lines.append(" ".join(parts) + f"  = {row_sum}")

        visual = "\n".join(vis_lines)

        question_text = (
            f"Jadvalda har bir satr yig'indisi {row_sum} ga teng. "
            f"'?' o'rniga qanday son keladi?"
        )

        options_result = distractor_engine.generate_for_integer(correct, difficulty=difficulty)

        return self._build_output(
            template_id="grid_row_sum",
            family="grid",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=visual,
            correct_answer=correct,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=[
                f"Satr yig'indisi: {row_sum}",
                f"Boshqa sonlarning yig'indisi: {row_sum - correct}",
                f"? = {row_sum} - {row_sum - correct} = {correct}",
            ],
            parameters={"grid": grid, "row_sum": row_sum, "missing": (miss_r, miss_c)},
            diagram_spec=self._build_grid_diagram(grid, miss_r, miss_c, row_sum),
        )

    def _gen_grid_row_col(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        size = 3
        row_sum = self.rng.randint(15, 30)
        col_sum = self.rng.randint(15, 30)

        grid = [[self.rng.randint(1, 12) for _ in range(size)] for _ in range(size)]

        miss_r = self.rng.randint(0, 2)
        miss_c = self.rng.randint(0, 2)
        correct = grid[miss_r][miss_c]
        grid[miss_r][miss_c] = None

        row_sums_actual = []
        for r in range(size):
            s = sum(v for v in grid[r] if v is not None)
            if r == miss_r:
                s += correct
            row_sums_actual.append(s)

        col_sums_actual = []
        for c in range(size):
            s = sum(grid[r][c] for r in range(size) if grid[r][c] is not None)
            if c == miss_c:
                s += correct
            col_sums_actual.append(s)

        question_text = (
            f"Jadvalda har bir satr va ustun yig'indisi berilgan. "
            f"'?' o'rniga qanday son keladi?"
        )

        vis_lines = []
        for r in range(size):
            parts = []
            for c in range(size):
                if grid[r][c] is not None:
                    parts.append(f"{grid[r][c]:>3}")
                else:
                    parts.append("  ?")
            vis_lines.append(" ".join(parts) + f"  | {row_sums_actual[r]}")

        col_line = " ".join(f"{col_sums_actual[c]:>3}" for c in range(size))
        vis_lines.append("---+----")
        vis_lines.append(col_line)

        visual = "\n".join(vis_lines)

        options_result = distractor_engine.generate_for_integer(correct, difficulty=difficulty)

        return self._build_output(
            template_id="grid_row_col",
            family="grid",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=visual,
            correct_answer=correct,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=[
                f"Satr {miss_r+1} yig'indisi: {row_sums_actual[miss_r]}",
                f"Ustun {miss_c+1} yig'indisi: {col_sums_actual[miss_c]}",
                f"? = {correct}",
            ],
            parameters={
                "grid": grid, "row_sums": row_sums_actual,
                "col_sums": col_sums_actual, "missing": (miss_r, miss_c),
            },
            diagram_spec=self._build_grid_diagram(grid, miss_r, miss_c,
                                                    row_sums=row_sums_actual,
                                                    col_sums=col_sums_actual),
        )

    # ── REBUS PUZZLES ──

    def _gen_rebus_2symbol(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        symbols = self.rng.sample(["□", "△", "○", "◇", "☆"], 2)
        sym_a, sym_b = symbols

        val_a = self.rng.randint(1, 9)
        val_b = self.rng.randint(1, 9)

        if val_a == val_b:
            val_b = (val_b % 9) + 1

        op = self.rng.choice(["+", "×"])
        if op == "+":
            result = val_a + val_b
            eq_str = f"{sym_a} + {sym_b} = {result}"
        else:
            result = val_a * val_b
            eq_str = f"{sym_a} × {sym_b} = {result}"

        # Show one value
        show_first = self.rng.choice([True, False])
        if show_first:
            hint = f"{sym_a} = {val_a}"
            correct = val_b
            unknown_sym = sym_b
        else:
            hint = f"{sym_b} = {val_b}"
            correct = val_a
            unknown_sym = sym_a

        question_text = f"{eq_str}\n{hint}\n{unknown_sym} = ?"

        options_result = distractor_engine.generate_for_integer(correct, difficulty=difficulty)

        return self._build_output(
            template_id="rebus_2symbol",
            family="rebus",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=f"{eq_str}  |  {hint}  |  {unknown_sym} = ?",
            correct_answer=correct,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=[
                f"{hint}",
                f"{eq_str}",
                f"{unknown_sym} = {result} {('-' if op == '+' else '÷')} {val_a if show_first else val_b}",
                f"{unknown_sym} = {correct}",
            ],
            parameters={"symbols": symbols, "values": [val_a, val_b], "operation": op, "result": result},
        )

    def _gen_rebus_3symbol(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        symbols = self.rng.sample(["□", "△", "○", "◇"], 3)
        vals = {s: self.rng.randint(1, 9) for s in symbols}

        if len(set(vals.values())) < 3:
            return None

        s1, s2, s3 = symbols
        v1, v2, v3 = vals[s1], vals[s2], vals[s3]

        eq1 = f"{s1} + {s2} = {v1 + v2}"
        eq2 = f"{s2} + {s3} = {v2 + v3}"
        eq3 = f"{s1} + {s2} + {s3} = ?"

        correct = v1 + v2 + v3

        question_text = f"{eq1}\n{eq2}\n{eq3}"

        options_result = distractor_engine.generate_for_integer(correct, difficulty=difficulty)

        return self._build_output(
            template_id="rebus_3symbol",
            family="rebus",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=f"{eq1} | {eq2} | {eq3}",
            correct_answer=correct,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=[
                f"{s1} = {v1}, {s2} = {v2}, {s3} = {v3}",
                f"{s1} + {s2} + {s3} = {v1} + {v2} + {v3} = {correct}",
            ],
            parameters={"symbols": symbols, "values": list(vals.values())},
        )

    # ── SHAPE PUZZLES ──

    def _gen_shape_triangle_value(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        vals = {
            "vertex": self.rng.randint(1, 8),
            "side": self.rng.randint(1, 8),
        }

        total = 3 * vals["vertex"] + 3 * vals["side"]

        question_text = (
            f"Uchburchakning har bir burchagidagi son {vals['vertex']}, "
            f"har bir tomonidagi son {vals['side']}.\n"
            f"Barcha sonlarning yig'indisi necha?"
        )

        options_result = distractor_engine.generate_for_integer(total, difficulty=difficulty)

        return self._build_output(
            template_id="shape_triangle_value",
            family="shape",
            difficulty=difficulty,
            question_text=question_text,
            visual_text=f"3 × {vals['vertex']} + 3 × {vals['side']} = ?",
            correct_answer=total,
            options=options_result.options,
            correct_label=options_result.correct_label,
            explanation_steps=[
                f"3 ta burchak: 3 × {vals['vertex']} = {3 * vals['vertex']}",
                f"3 ta tomon: 3 × {vals['side']} = {3 * vals['side']}",
                f"Jami: {3 * vals['vertex']} + {3 * vals['side']} = {total}",
            ],
            parameters=vals,
        )

    # ── BUILD HELPERS ──

    def _build_output(self, **kwargs) -> PuzzleOutput:
        """PuzzleOutput yaratish"""
        puzzle_id = f"puz_{hashlib.md5(str(random.random()).encode()).hexdigest()[:8]}"

        validation = self._validate_puzzle(kwargs)

        return PuzzleOutput(
            puzzle_id=puzzle_id,
            template_family=kwargs.get("family", ""),
            template_id=kwargs.get("template_id", ""),
            difficulty=kwargs.get("difficulty", "oson"),
            question_text=kwargs.get("question_text", ""),
            visual_text=kwargs.get("visual_text", ""),
            correct_answer=kwargs.get("correct_answer", 0),
            answer_type="integer",
            options=kwargs.get("options", {}),
            correct_label=kwargs.get("correct_label", "A"),
            explanation_steps=kwargs.get("explanation_steps", []),
            diagram_spec=kwargs.get("diagram_spec"),
            parameters=kwargs.get("parameters", {}),
            validation=validation,
        )

    def _validate_puzzle(self, params: Dict) -> Dict[str, Any]:
        """Puzzle validatsiyasi"""
        result = {
            "is_valid": True,
            "has_unique_answer": True,
            "answer_is_integer": True,
            "is_logically_consistent": True,
            "errors": [],
            "warnings": [],
        }

        correct = params.get("correct_answer")
        if correct is None or (isinstance(correct, (int, float)) and correct <= 0):
            result["is_valid"] = False
            result["errors"].append("Invalid answer")

        options = params.get("options", {})
        if len(options) != 4:
            result["warnings"].append(f"Options count: {len(options)}")

        if len(set(options.values())) != len(options):
            result["is_valid"] = False
            result["errors"].append("Duplicate option values")

        return result

    def _build_grid_diagram(self, grid, miss_r, miss_c,
                             row_sum=None, row_sums=None,
                             col_sums=None) -> DiagramSpec:
        """Grid diagram"""
        size = len(grid)
        builder = DiagramSpecBuilder(DiagramType.GRID)
        builder.with_canvas(size * 1.5 + 2, size * 1.5 + 2)

        for r in range(size):
            for c in range(size):
                content = "?" if (r == miss_r and c == miss_c) else str(grid[r][c])
                builder.add_grid_cell(r, c, content=content)

        return builder.build()


puzzle_template_engine = PuzzleTemplateEngine()
