"""
services/puzzle_numpy_gen.py — CONTROLLED NUMPY PARAMETER GENERATOR

Random emas — nazoratli generatsiya.
NumPy asosida constraint-aware parameter generation.

Key Features:
- Seed-based reproducibility
- Range constraints
- Exclusion sets (no duplicates)
- Distribution control (uniform, weighted, clustered)
- Difficulty-scaled parameter ranges
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ParameterSpec:
    """Parameter spetsifikatsiyasi"""
    name: str
    min_val: int
    max_val: int
    exclude: Set[int] = field(default_factory=set)
    constraints: List[Callable[[int], bool]] = field(default_factory=list)
    weight_fn: Optional[Callable[[int], float]] = None
    
    def is_valid(self, value: int) -> bool:
        """Qiymat validligini tekshirish"""
        if value < self.min_val or value > self.max_val:
            return False
        if value in self.exclude:
            return False
        for c in self.constraints:
            if not c(value):
                return False
        return True


@dataclass
class ParameterSet:
    """Generatsiya qilingan parametrlar to'plami"""
    values: Dict[str, int]
    seed: int
    difficulty: str
    grade: int
    
    def to_dict(self) -> Dict:
        return {
            "values": self.values,
            "seed": self.seed,
            "difficulty": self.difficulty,
            "grade": self.grade,
        }


class ControlledParameterGenerator:
    """
    NumPy asosida nazoratli parameter generatsiya.
    
    Har bir son:
    - Ma'lum bir oraliqda
    - Constraint lardan o'tgan
    - Takrorlanmagan
    - Difficulty ga mos kelgan
    """
    
    DIFFICULTY_RANGES = {
        "oson": {
            "single_digit_max": 9,
            "double_digit_max": 20,
            "chain_length": 2,
            "operations": ["+", "-"],
        },
        "o'rta": {
            "single_digit_max": 9,
            "double_digit_max": 50,
            "triple_digit_max": 100,
            "chain_length": 3,
            "operations": ["+", "-", "×"],
        },
        "qiyin": {
            "single_digit_max": 12,
            "double_digit_max": 99,
            "triple_digit_max": 999,
            "chain_length": 5,
            "operations": ["+", "-", "×", "÷"],
        },
    }
    
    GRADE_RANGES = {
        1: {"max_add": 10, "max_mul": 5, "ops": ["+"]},
        2: {"max_add": 20, "max_sub": 20, "max_mul": 5, "ops": ["+", "-"]},
        3: {"max_add": 100, "max_sub": 100, "max_mul": 10, "ops": ["+", "-", "×"]},
        4: {"max_add": 999, "max_sub": 999, "max_mul": 12, "max_div": 100, "ops": ["+", "-", "×", "÷"]},
        5: {"max_add": 9999, "max_sub": 9999, "max_mul": 99, "max_div": 1000, "ops": ["+", "-", "×", "÷"]},
        6: {"max_add": 99999, "max_sub": 99999, "max_mul": 999, "max_div": 9999, "ops": ["+", "-", "×", "÷"]},
    }
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self._used_combinations: Set[str] = set()
    
    def generate_pair(self, min_val: int, max_val: int,
                      difficulty: str = "o'rta",
                      ensure_no_carry: bool = False,
                      ensure_positive_result: bool = True,
                      exclude: Set[int] = None) -> Tuple[int, int]:
        """Ikki son generatsiya qilish"""
        if exclude is None:
            exclude = set()
        
        max_attempts = 100
        for _ in range(max_attempts):
            a = self._weighted_int(min_val, max_val)
            b = self._weighted_int(min_val, max_val)
            
            if a in exclude or b in exclude:
                continue
            
            if ensure_no_carry:
                if (a % 10) + (b % 10) >= 10:
                    continue
            
            if ensure_positive_result and a - b < 0:
                a, b = max(a, b), min(a, b)
            
            combo_key = f"{a}_{b}"
            if combo_key not in self._used_combinations:
                self._used_combinations.add(combo_key)
                return (a, b)
        
        return (int(self.rng.integers(min_val, max_val + 1)), 
                int(self.rng.integers(min_val, max_val + 1)))
    
    def generate_triple(self, ranges: List[Tuple[int, int]]) -> Tuple[int, int, int]:
        """Uch son generatsiya qilish"""
        vals = []
        for min_v, max_v in ranges:
            v = self._weighted_int(min_v, max_v)
            vals.append(v)
        return tuple(vals)
    
    def generate_chain_params(self, length: int, difficulty: str,
                               grade: int) -> Tuple[List[int], List[str]]:
        """Zanjir parametrlarini generatsiya qilish"""
        diff_config = self.DIFFICULTY_RANGES.get(difficulty, self.DIFFICULTY_RANGES["o'rta"])
        grade_config = self.GRADE_RANGES.get(grade, self.GRADE_RANGES[5])
        
        available_ops = grade_config["ops"]
        
        start_val = self._weighted_int(2, diff_config.get("double_digit_max", 20))
        
        values = [start_val]
        operations = []
        
        for step in range(length):
            op = self.rng.choice(available_ops)
            operations.append(op)
            
            if op == "+":
                add_val = self._weighted_int(1, diff_config.get("double_digit_max", 20))
                values.append(add_val)
            elif op == "-":
                current = self._compute_chain(values, operations)
                max_sub = min(current - 1, diff_config.get("double_digit_max", 20))
                if max_sub < 1:
                    max_sub = 1
                sub_val = self._weighted_int(1, max_sub)
                values.append(sub_val)
            elif op == "×":
                mul_val = self._weighted_int(2, min(9, diff_config.get("single_digit_max", 9)))
                values.append(mul_val)
            elif op == "÷":
                current = self._compute_chain(values, operations)
                divisors = [d for d in range(2, 10) if current % d == 0]
                if divisors:
                    div_val = self.rng.choice(divisors)
                else:
                    div_val = 2
                values.append(div_val)
        
        return values, operations
    
    def generate_grid_params(self, rows: int, cols: int,
                              min_val: int = 1, max_val: int = 9,
                              target_sum: Optional[int] = None) -> Dict[str, Any]:
        """Jadval parametrlarini generatsiya qilish"""
        grid = []
        for _ in range(rows):
            row = [int(self.rng.integers(min_val, max_val + 1)) for _ in range(cols)]
            grid.append(row)
        
        row_sums = [sum(row) for row in grid]
        col_sums = [sum(grid[r][c] for r in range(rows)) for c in range(cols)]
        
        if target_sum is not None:
            current_total = sum(row_sums)
            adjustment = target_sum - current_total
            if adjustment != 0:
                r_idx = int(self.rng.integers(0, rows))
                c_idx = int(self.rng.integers(0, cols))
                grid[r_idx][c_idx] += adjustment
                grid[r_idx][c_idx] = max(min_val, min(max_val, grid[r_idx][c_idx]))
                row_sums = [sum(row) for row in grid]
                col_sums = [sum(grid[r][c] for r in range(rows)) for c in range(cols)]
        
        missing_r = int(self.rng.integers(0, rows))
        missing_c = int(self.rng.integers(0, cols))
        missing_value = grid[missing_r][missing_c]
        
        return {
            "grid": grid,
            "row_sums": row_sums,
            "col_sums": col_sums,
            "missing_position": (missing_r, missing_c),
            "missing_value": missing_value,
        }
    
    def generate_rebus_mapping(self, word1: str, word2: str, 
                                result_word: str) -> Optional[Dict[str, int]]:
        """Rebus mapping generatsiya qilish"""
        all_letters = list(set(word1 + word2 + result_word))
        
        if len(all_letters) > 10:
            return None
        
        max_attempts = 500
        for _ in range(max_attempts):
            digits = list(range(10))
            self.rng.shuffle(digits)
            
            mapping = {}
            for i, letter in enumerate(all_letters):
                mapping[letter] = digits[i]
            
            if mapping.get(word1[0], 0) == 0:
                continue
            if mapping.get(word2[0], 0) == 0:
                continue
            if mapping.get(result_word[0], 0) == 0:
                continue
            
            num1 = int("".join(str(mapping[ch]) for ch in word1))
            num2 = int("".join(str(mapping[ch]) for ch in word2))
            num_result = int("".join(str(mapping[ch]) for ch in result_word))
            
            if num1 + num2 == num_result:
                combo = "_".join(f"{k}={v}" for k, v in sorted(mapping.items()))
                if combo not in self._used_combinations:
                    self._used_combinations.add(combo)
                    return mapping
        
        return None
    
    def generate_equation_system(self, difficulty: str = "o'rta") -> Dict[str, Any]:
        """Tenglama sistemasini generatsiya qilish"""
        x = int(self.rng.integers(2, 15))
        y = int(self.rng.integers(1, 12))
        
        a = int(self.rng.integers(1, 4))
        b = int(self.rng.integers(1, 4))
        
        sum_val = x + y
        diff_val = abs(x - y)
        
        eq1 = f"{a}*x + {a}*y = {a * sum_val}"
        eq2 = f"{b}*x - {b}*y = {b * (x - y)}" if x >= y else f"{b}*y - {b}*x = {b * (y - x)}"
        
        return {
            "x": x, "y": y,
            "eq1": eq1, "eq2": eq2,
            "a": a, "b": b,
            "sum_val": sum_val, "diff_val": diff_val,
        }
    
    def generate_flow_params(self, steps: int, difficulty: str,
                              grade: int) -> Dict[str, Any]:
        """Flow diagram parametrlarini generatsiya qilish"""
        diff_config = self.DIFFICULTY_RANGES.get(difficulty, self.DIFFICULTY_RANGES["o'rta"])
        grade_config = self.GRADE_RANGES.get(grade, self.GRADE_RANGES[5])
        
        start = int(self.rng.integers(3, diff_config.get("double_digit_max", 20) + 1))
        
        operations = []
        values = [start]
        
        current = start
        for _ in range(steps):
            op = self.rng.choice(grade_config["ops"])
            
            if op == "+":
                val = int(self.rng.integers(2, min(current + 10, diff_config.get("double_digit_max", 20) + 1)))
                current = current + val
            elif op == "-":
                val = int(self.rng.integers(1, min(current, diff_config.get("double_digit_max", 20) + 1)))
                current = current - val
            elif op == "×":
                val = int(self.rng.integers(2, min(9, diff_config.get("single_digit_max", 9) + 1)))
                current = current * val
            elif op == "÷":
                divisors = [d for d in range(2, 10) if current % d == 0]
                val = int(self.rng.choice(divisors)) if divisors else 2
                current = current // val
            
            operations.append({"op": op, "value": val, "result": current})
            values.append(current)
        
        return {
            "start": start,
            "operations": operations,
            "values": values,
            "final": current,
        }
    
    def generate_shape_values(self, shape_type: str, 
                               difficulty: str = "o'rta") -> Dict[str, Any]:
        """Shakl qiymatlarini generatsiya qilish"""
        if shape_type == "triangle":
            a = int(self.rng.integers(3, 20))
            b = int(self.rng.integers(3, 20))
            
            c_min = abs(a - b) + 1
            c_max = a + b - 1
            if c_min > c_max:
                c_min, c_max = 3, 15
            c = int(self.rng.integers(c_min, c_max + 1))
            
            perimeter = a + b + c
            
            return {
                "sides": [a, b, c],
                "perimeter": perimeter,
                "missing_side": c,
                "question": f"Uchburchakning uchinchi tomonini toping: a={a}, b={b}, P={perimeter}",
            }
        
        elif shape_type == "square":
            side = int(self.rng.integers(3, 15))
            return {
                "side": side,
                "perimeter": 4 * side,
                "area": side * side,
            }
        
        elif shape_type == "rectangle":
            w = int(self.rng.integers(3, 20))
            h = int(self.rng.integers(3, 15))
            return {
                "width": w, "height": h,
                "perimeter": 2 * (w + h),
                "area": w * h,
                "diagonal_sq": w * w + h * h,
            }
        
        elif shape_type == "circle":
            r = int(self.rng.integers(2, 10))
            return {
                "radius": r,
                "diameter": 2 * r,
            }
        
        return {}
    
    def _weighted_int(self, min_val: int, max_val: int) -> int:
        """Og'irlikli random son"""
        if min_val >= max_val:
            return min_val
        
        mid = (min_val + max_val) / 2
        sigma = (max_val - min_val) / 4
        
        for _ in range(20):
            val = int(self.rng.normal(mid, sigma))
            if min_val <= val <= max_val:
                return val
        
        return int(self.rng.integers(min_val, max_val + 1))
    
    def _compute_chain(self, values: List[int], operations: List[str]) -> int:
        """Zanjir hisoblash"""
        result = values[0]
        for i, op in enumerate(operations):
            if i + 1 < len(values):
                if op == "+":
                    result += values[i + 1]
                elif op == "-":
                    result -= values[i + 1]
                elif op == "×":
                    result *= values[i + 1]
                elif op == "÷":
                    if values[i + 1] != 0:
                        result //= values[i + 1]
        return result
    
    def reset(self, seed: Optional[int] = None):
        """Generator ni resetlash"""
        if seed is not None:
            self.seed = seed
            self.rng = np.random.default_rng(seed)
        self._used_combinations.clear()


controlled_generator = ControlledParameterGenerator()
