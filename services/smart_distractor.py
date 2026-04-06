"""
services/smart_distractor.py — CONTEXT-AWARE DISTRACTOR GENERATOR

Variantlar shunchaki random bo'lmasin.
Noto'g'ri variantlar quyidagicha quriladi:
- Hisob xatosi (common mistake patterns)
- Amal noto'g'ri qo'llanishi (operation swap)
- Yaqin son (adjacent number)
- Chalg'ituvchi natija (partial computation)
- Shu puzzle ga mos keladigan distractorlar

4 variant:
- 1 ta to'g'ri
- 3 ta noto'g'ri (har biri mantiqiy)
- Variantlar takrorlanmasin
- To'g'ri javob joyi random
"""

from __future__ import annotations

import random
import logging
import math
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DistractorOptions:
    """Variantlar natijasi"""
    correct_answer: Any
    options: Dict[str, Any]
    correct_label: str
    strategies_used: List[str]
    is_valid: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "correct": self.correct_answer,
            "options": self.options,
            "label": self.correct_label,
            "strategies": self.strategies_used,
        }


class SmartDistractor:
    """
    Context-aware distractor generator.
    
    Puzzle tipiga qarab turli strategiyalar:
    1. Arithmetic: off-by-one, operation swap, carry error
    2. Chain: partial computation, skipped step
    3. Grid: row/col sum confusion
    4. Rebus: symbol swap, digit confusion
    5. Shape: formula confusion (area vs perimeter)
    6. Flowchart: wrong path, incomplete step
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
    
    def generate_for_arithmetic(self, a: int, b: int, op: str,
                                 correct: int) -> DistractorOptions:
        """Arithmetic uchun distractorlar"""
        distractors: Set[int] = set()
        strategies = []
        
        d1 = correct + self.rng.choice([1, -1, 2, -2])
        if d1 > 0 and d1 != correct:
            distractors.add(d1)
            strategies.append("off_by_one")
        
        if op == "+":
            swap = a * b
            if swap != correct and swap > 0:
                distractors.add(swap)
                strategies.append("operation_swap_+_to_x")
            
            sign_err = correct - 2 * b
            if sign_err > 0 and sign_err != correct:
                distractors.add(sign_err)
                strategies.append("sign_error")
        
        elif op == "-":
            swap = a + b
            if swap != correct and swap > 0:
                distractors.add(swap)
                strategies.append("operation_swap_-_to_+")
            
            reverse = b - a
            if reverse > 0 and reverse != correct:
                distractors.add(reverse)
                strategies.append("reversed_order")
        
        elif op in ("×", "x", "*"):
            swap = a + b
            if swap != correct and swap > 0:
                distractors.add(swap)
                strategies.append("operation_swap_x_to_+")
            
            off_mul = correct + a
            if off_mul > 0 and off_mul != correct:
                distractors.add(off_mul)
                strategies.append("multiplication_extra")
        
        elif op in ("÷", "/"):
            swap = a * b
            if swap != correct and swap > 0:
                distractors.add(swap)
                strategies.append("operation_swap_/_to_x")
        
        carry_err = correct + self.rng.choice([10, -10])
        if carry_err > 0 and carry_err != correct:
            distractors.add(carry_err)
            strategies.append("carry_error")
        
        return self._build_options(correct, distractors, strategies)
    
    def generate_for_chain(self, values: List[int], operations: List[str],
                            correct: int) -> DistractorOptions:
        """Zanjir uchun distractorlar"""
        distractors: Set[int] = set()
        strategies = []
        
        if len(values) >= 2:
            partial = values[0]
            for i, op in enumerate(operations[:-1]):
                if i + 1 < len(values):
                    partial = self._apply_op(partial, values[i + 1], op)
            if partial > 0 and partial != correct:
                distractors.add(partial)
                strategies.append("partial_computation")
        
        if operations:
            last_op = operations[-1]
            last_val = values[-1] if len(values) > 1 else 1
            if last_op == "+":
                wrong = correct - 2 * last_val
            elif last_op == "-":
                wrong = correct + 2 * last_val
            elif last_op in ("×", "x"):
                wrong = correct + last_val
            else:
                wrong = correct * 2
            
            if wrong > 0 and wrong != correct:
                distractors.add(wrong)
                strategies.append("last_operation_error")
        
        if len(values) >= 2:
            skip = correct - values[1] if correct > values[1] else correct + values[1]
            if skip > 0 and skip != correct:
                distractors.add(skip)
                strategies.append("skipped_step")
        
        adj = correct + self.rng.choice([values[0] if values else 1, 
                                          -(values[0] if values else 1)])
        if adj > 0 and adj != correct:
            distractors.add(adj)
            strategies.append("adjacent_by_start")
        
        return self._build_options(correct, distractors, strategies)
    
    def generate_for_grid(self, correct: int, row_sum: Optional[int] = None,
                           col_sum: Optional[int] = None) -> DistractorOptions:
        """Jadval uchun distractorlar"""
        distractors: Set[int] = set()
        strategies = []
        
        if row_sum is not None:
            if row_sum != correct:
                distractors.add(row_sum)
                strategies.append("row_sum_confusion")
            if row_sum + 1 != correct:
                distractors.add(row_sum + 1)
                strategies.append("row_sum_plus_one")
        
        if col_sum is not None:
            if col_sum != correct:
                distractors.add(col_sum)
                strategies.append("col_sum_confusion")
            if col_sum - 1 > 0 and col_sum - 1 != correct:
                distractors.add(col_sum - 1)
                strategies.append("col_sum_minus_one")
        
        off = correct + self.rng.choice([2, -2, 3, -3, 5, -5])
        if off > 0 and off != correct:
            distractors.add(off)
            strategies.append("small_offset")
        
        return self._build_options(correct, distractors, strategies)
    
    def generate_for_shape(self, correct: int, shape_type: str,
                            shape_data: Dict[str, Any]) -> DistractorOptions:
        """Shakl uchun distractorlar"""
        distractors: Set[int] = set()
        strategies = []
        
        if shape_type == "square":
            side = shape_data.get("side", 3)
            if side != correct:
                distractors.add(side)
                strategies.append("confused_with_side")
            
            wrong_formula = 2 * side
            if wrong_formula != correct and wrong_formula > 0:
                distractors.add(wrong_formula)
                strategies.append("wrong_formula_P_instead_of_S")
        
        elif shape_type == "rectangle":
            w = shape_data.get("width", 4)
            h = shape_data.get("height", 3)
            
            wrong_sum = w + h
            if wrong_sum != correct and wrong_sum > 0:
                distractors.add(wrong_sum)
                strategies.append("sum_instead_of_product")
            
            wrong_2sum = 2 * (w + h)
            if wrong_2sum != correct and wrong_2sum > 0:
                distractors.add(wrong_2sum)
                strategies.append("perimeter_instead_of_area")
        
        elif shape_type == "triangle":
            sides = shape_data.get("sides", [3, 4, 5])
            if len(sides) >= 2:
                wrong = sides[0] + sides[1]
                if wrong != correct and wrong > 0:
                    distractors.add(wrong)
                    strategies.append("two_sides_sum")
        
        elif shape_type == "circle":
            r = shape_data.get("radius", 3)
            if r != correct:
                distractors.add(r)
                strategies.append("radius_instead_of_diameter")
            
            wrong = 2 + r
            if wrong != correct and wrong > 0:
                distractors.add(wrong)
                strategies.append("off_by_two")
        
        if len(distractors) < 3:
            extra = correct + self.rng.choice([1, -1, 5, -5])
            if extra > 0 and extra != correct:
                distractors.add(extra)
                strategies.append("nearby_value")
        
        return self._build_options(correct, distractors, strategies)
    
    def generate_for_flowchart(self, correct: int, operations: List[Dict],
                                flow_type: str) -> DistractorOptions:
        """Flowchart uchun distractorlar"""
        distractors: Set[int] = set()
        strategies = []
        
        if operations:
            partial = operations[0].get("input", correct)
            for op_info in operations[:-1]:
                partial = self._apply_op(
                    partial,
                    op_info.get("value", 0),
                    op_info.get("op", "+")
                )
            if partial > 0 and partial != correct:
                distractors.add(partial)
                strategies.append("incomplete_flow")
        
        if operations:
            last = operations[-1]
            op = last.get("op", "+")
            val = last.get("value", 1)
            if op == "+":
                wrong = correct - 2 * val
            elif op == "-":
                wrong = correct + 2 * val
            elif op in ("×", "x"):
                wrong = correct + val
            else:
                wrong = correct + val * 2
            if wrong > 0 and wrong != correct:
                distractors.add(wrong)
                strategies.append("last_step_error")
        
        if flow_type == "branching_flow":
            wrong_path = correct + self.rng.choice([5, -5, 10, -10])
            if wrong_path > 0 and wrong_path != correct:
                distractors.add(wrong_path)
                strategies.append("wrong_path")
        
        if flow_type == "multi_path":
            wrong_merge = correct + self.rng.choice([3, -3, 7, -7])
            if wrong_merge > 0 and wrong_merge != correct:
                distractors.add(wrong_merge)
                strategies.append("merge_error")
        
        return self._build_options(correct, distractors, strategies)
    
    def generate_for_rebus(self, correct: int,
                            symbol_mapping: Dict[str, int]) -> DistractorOptions:
        """Rebus uchun distractorlar"""
        distractors: Set[int] = set()
        strategies = []
        
        for sym, val in symbol_mapping.items():
            if val != correct:
                distractors.add(val)
                strategies.append(f"symbol_swap_{sym}")
        
        digits = list(str(correct))
        if len(digits) >= 2:
            reversed_num = int("".join(reversed(digits)))
            if reversed_num > 0 and reversed_num != correct:
                distractors.add(reversed_num)
                strategies.append("digit_reversal")
        
        off = correct + self.rng.choice([1, -1, 2, -2])
        if off > 0 and off != correct:
            distractors.add(off)
            strategies.append("close_value")
        
        return self._build_options(correct, distractors, strategies)
    
    def _build_options(self, correct: int, distractors: Set[int],
                        strategies: List[str]) -> DistractorOptions:
        """Final 4 ta variant yaratish"""
        correct = int(correct)
        distractors = {int(d) for d in distractors}
        distractors.discard(correct)
        distractors = {d for d in distractors if d > 0}
        
        distractor_list = list(distractors)
        self.rng.shuffle(distractor_list)
        
        values = [correct] + distractor_list[:3]
        
        attempts = 0
        while len(values) < 4 and attempts < 20:
            filler = correct + self.rng.choice([-5, -3, -2, -1, 1, 2, 3, 5, 7, 10])
            if filler > 0 and filler not in values:
                values.append(filler)
            attempts += 1
        
        while len(values) < 4:
            values.append(correct + len(values))
        
        values = values[:4]
        
        seen = set()
        unique_values = []
        for v in values:
            if v not in seen:
                seen.add(v)
                unique_values.append(v)
        
        while len(unique_values) < 4:
            fill = max(unique_values) + self.rng.randint(1, 10)
            if fill not in seen:
                seen.add(fill)
                unique_values.append(fill)
        
        values = unique_values[:4]
        self.rng.shuffle(values)
        
        labels = ["A", "B", "C", "D"]
        options = {}
        correct_label = "A"
        
        for i, val in enumerate(values):
            options[labels[i]] = val
            if val == correct:
                correct_label = labels[i]
        
        return DistractorOptions(
            correct_answer=correct,
            options=options,
            correct_label=correct_label,
            strategies_used=strategies[:5],
            is_valid=len(options) == 4,
        )
    
    def _apply_op(self, a: int, b: int, op: str) -> int:
        """Amalni qo'llash"""
        if op == "+":
            return a + b
        elif op == "-":
            return a - b
        elif op in ("×", "x", "*"):
            return a * b
        elif op in ("÷", "/"):
            return a // b if b != 0 else a
        return a


smart_distractor = SmartDistractor()
