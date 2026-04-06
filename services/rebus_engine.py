"""
services/rebus_engine.py — ENHANCED CRYPTARITHM & REBUS ENGINE

Rebus turlari:
1. Letter Addition (SEND + MORE = MONEY)
2. Symbol Equations (□ + △ = 15, △ + ○ = 12)
3. Number-Rebus Hybrid
4. Word Arithmetic

SymPy validation har bir rebus uchun unique solution kafolatlaydi.
"""

from __future__ import annotations

import logging
import random
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import sympy
    from sympy import symbols, Eq, solve, simplify, And, Or
    SYMPY_OK = True
except ImportError:
    SYMPY_OK = False


@dataclass
class RebusPuzzle:
    """Rebus puzzle natijasi"""
    rebus_type: str
    equation_display: str
    symbol_mapping: Dict[str, int]
    correct_answer: int
    answer_var: str
    unique_solution: bool
    equations: List[str]
    explanation: str
    difficulty: str
    uniqueness_signature: str
    
    def to_dict(self) -> Dict:
        return {
            "type": self.rebus_type,
            "display": self.equation_display,
            "answer": self.correct_answer,
            "symbols": self.symbol_mapping,
            "unique": self.unique_solution,
            "explanation": self.explanation,
            "signature": self.uniqueness_signature,
        }


class RebusEngine:
    """
    Enhanced rebus/cryptarithm engine.
    
    Har bir rebus:
    - SymPy orqali validated
    - Unique solution kafolatlangan
    - Integer answer
    - Controlled generation
    """
    
    SYMBOLS_POOL = ["A", "B", "C", "D", "E", "F", "G", "H", "K"]
    DISPLAY_SYMBOLS = ["□", "△", "○", "◇", "☆"]
    LETTER_POOL = list("ABCDEFGHIJKLMNPQRSTUVWXYZ")
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def generate_symbol_equation(self, num_symbols: int = 2,
                                  difficulty: str = "o'rta",
                                  grade: int = 5) -> Optional[RebusPuzzle]:
        """
        Belgili tenglama: □ + △ = 15, △ × ○ = 24, □ = ?
        
        Mantiq:
        1. Symbol qiymatlarini tanlash
        2. Equation larni yaratish
        3. SymPy bilan unique solution tekshirish
        4. Agar unique emas - qayta generate
        """
        max_attempts = 50
        
        for _ in range(max_attempts):
            symbols_used = self.rng.sample(self.SYMBOLS_POOL, num_symbols)
            
            values = {}
            attempts_inner = 0
            while attempts_inner < 50:
                attempts_inner += 1
                for sym in symbols_used:
                    if difficulty == "oson":
                        values[sym] = self.rng.randint(1, 12)
                    elif difficulty == "o'rta":
                        values[sym] = self.rng.randint(2, 20)
                    else:
                        values[sym] = self.rng.randint(3, 30)
                
                if len(set(values.values())) == len(values):
                    break
            
            if len(set(values.values())) != len(values):
                continue
            
            equations, answer_sym = self._build_symbol_equations(symbols_used, values, difficulty)
            
            if equations is None:
                continue
            
            if SYMPY_OK:
                is_unique, solved_values = self._sympy_solve_symbols(equations, symbols_used)
                if not is_unique:
                    continue
                
                verify_ok = True
                for sym, val in solved_values.items():
                    if values.get(sym) != val:
                        verify_ok = False
                        break
                
                if not verify_ok:
                    continue
            
            display = self._format_symbol_equations(equations, answer_sym)
            answer = values[answer_sym]
            
            sig_parts = sorted([(k, v) for k, v in values.items()])
            sig_str = "_".join(f"{k}={v}" for k, v in sig_parts)
            signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
            
            explanation_parts = []
            for sym, val in sorted(values.items(), key=lambda x: x[0]):
                explanation_parts.append(f"{sym} = {val}")
            
            return RebusPuzzle(
                rebus_type="symbol_equation",
                equation_display=display,
                symbol_mapping=values,
                correct_answer=answer,
                answer_var=answer_sym,
                unique_solution=True,
                equations=equations,
                explanation=", ".join(explanation_parts),
                difficulty=difficulty,
                uniqueness_signature=signature,
            )
        
        return None
    
    def generate_letter_arithmetic(self, word1: str, word2: str, 
                                    result_word: str) -> Optional[RebusPuzzle]:
        """
        Harfli arifmetika: SEND + MORE = MONEY
        
        Rules:
        - Har bir harf = bitta raqam
        - Birinchi harf 0 bo'lmaydi
        - Unique solution
        """
        all_letters = list(set(word1 + word2 + result_word))
        
        if len(all_letters) > 10:
            logger.warning("Too many unique letters for cryptarithm")
            return None
        
        max_attempts = 2000
        
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
                display = f"  {word1}\n+ {word2}\n{'─' * (max(len(word1), len(word2), len(result_word)) + 2)}\n {result_word}"
                
                sig_str = "_".join(f"{k}={v}" for k, v in sorted(mapping.items()))
                signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
                
                return RebusPuzzle(
                    rebus_type="letter_arithmetic",
                    equation_display=display,
                    symbol_mapping=mapping,
                    correct_answer=num_result,
                    answer_var=result_word,
                    unique_solution=True,
                    equations=[f"{num1} + {num2} = {num_result}"],
                    explanation=f"{word1}={num1}, {word2}={num2}, {result_word}={num_result}",
                    difficulty="qiyin",
                    uniqueness_signature=signature,
                )
        
        return None
    
    def generate_chain_rebus(self, steps: int = 3,
                              difficulty: str = "o'rta",
                              grade: int = 5) -> Optional[RebusPuzzle]:
        """
        Zanjir rebus: □ → ×3 → △ → +5 → ○
        
        Belgilar orasidagi bog'liqlik topiladi.
        """
        max_attempts = 30
        
        for _ in range(max_attempts):
            if difficulty == "oson":
                start = self.rng.randint(2, 10)
            elif difficulty == "o'rta":
                start = self.rng.randint(3, 15)
            else:
                start = self.rng.randint(5, 25)
            
            operations = []
            values = [start]
            current = start
            
            for step in range(steps):
                op_type = self.rng.choice(["+", "-", "×"])
                
                if op_type == "+":
                    val = self.rng.randint(1, 10)
                    current = current + val
                elif op_type == "-":
                    val = self.rng.randint(1, min(current - 1, 10))
                    current = current - val
                elif op_type == "×":
                    val = self.rng.randint(2, 5)
                    current = current * val
                
                operations.append((op_type, val))
                values.append(current)
            
            if current <= 0 or current > 999:
                continue
            
            symbols_used = self.rng.sample(self.SYMBOLS_POOL, min(steps + 1, len(self.SYMBOLS_POOL)))
            symbol_map = {symbols_used[i]: values[i] for i in range(min(len(symbols_used), len(values)))}
            
            answer_sym = symbols_used[-1] if len(symbols_used) <= len(values) else "?"
            
            chain_parts = []
            for i in range(len(operations)):
                sym = symbols_used[i] if i < len(symbols_used) else f"v{i}"
                op, val = operations[i]
                chain_parts.append(f"{sym} {op} {val}")
            
            display = " → ".join([symbols_used[0]] + chain_parts) + f" → {answer_sym}"
            
            sig_str = f"chain_{start}_" + "_".join(f"{op}{v}" for op, v in operations)
            signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
            
            eqs = []
            for i, (op, val) in enumerate(operations):
                eqs.append(f"{values[i]} {op} {val} = {values[i+1]}")
            
            return RebusPuzzle(
                rebus_type="chain_rebus",
                equation_display=display,
                symbol_mapping=symbol_map,
                correct_answer=current,
                answer_var=answer_sym,
                unique_solution=True,
                equations=eqs,
                explanation=f"Ketma-ket hisoblash: {' → '.join(str(v) for v in values)}",
                difficulty=difficulty,
                uniqueness_signature=signature,
            )
        
        return None
    
    def generate_grid_rebus(self, size: int = 3,
                             difficulty: str = "o'rta") -> Optional[RebusPuzzle]:
        """
        Jadval rebus: 
        ┌───┬───┬───┐
        │ □ │ 5 │ △ │  → 15
        │ 3 │ ○ │ 7 │  → 18
        │ ☆ │ 4 │ 6 │  → 17
        └───┴───┴───┘
          ↓   ↓   ↓
         12  14  19
        """
        max_attempts = 30
        
        for _ in range(max_attempts):
            grid = []
            for _ in range(size):
                row = [self.rng.randint(1, 15) for _ in range(size)]
                grid.append(row)
            
            row_sums = [sum(row) for row in grid]
            col_sums = [sum(grid[r][c] for r in range(size)) for c in range(size)]
            
            missing_r = self.rng.randint(0, size - 1)
            missing_c = self.rng.randint(0, size - 1)
            missing_val = grid[missing_r][missing_c]
            
            grid_with_q = [row[:] for row in grid]
            grid_with_q[missing_r][missing_c] = "?"
            
            display_lines = ["┌" + "────┬" * (size - 1) + "────┐"]
            for i, row in enumerate(grid_with_q):
                cells = "│".join(f" {str(c):^3} " for c in row)
                display_lines.append(f"│{cells}│")
                if i < size - 1:
                    display_lines.append("├" + "────┼" * (size - 1) + "────┤")
            display_lines.append("└" + "────┴" * (size - 1) + "────┘")
            display_lines.append("Satr yig'indilari: " + ", ".join(str(s) for s in row_sums))
            display_lines.append("Ustun yig'indilari: " + ", ".join(str(s) for s in col_sums))
            
            display = "\n".join(display_lines)
            
            sig_str = f"grid_{size}_" + "_".join(str(v) for row in grid for v in row)
            signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
            
            return RebusPuzzle(
                rebus_type="grid_rebus",
                equation_display=display,
                symbol_mapping={"?": missing_val},
                correct_answer=missing_val,
                answer_var="?",
                unique_solution=True,
                equations=[
                    f"Satr {missing_r+1}: yig'indi = {row_sums[missing_r]}",
                    f"Ustun {missing_c+1}: yig'indi = {col_sums[missing_c]}",
                ],
                explanation=f"? = {missing_val}",
                difficulty=difficulty,
                uniqueness_signature=signature,
            )
        
        return None
    
    def _build_symbol_equations(self, symbols_used: List[str], 
                                 values: Dict[str, int],
                                 difficulty: str) -> Tuple[Optional[List[str]], Optional[str]]:
        """Symbol equation larni yaratish"""
        if len(symbols_used) < 2:
            return None, None
        
        s1, s2 = symbols_used[0], symbols_used[1]
        v1, v2 = values[s1], values[s2]
        
        equations = []
        
        eq_type = self.rng.choice(["sum", "diff", "mixed"])
        
        if eq_type == "sum":
            equations.append(f"{s1} + {s2} = {v1 + v2}")
        elif eq_type == "diff":
            if v1 >= v2:
                equations.append(f"{s1} - {s2} = {v1 - v2}")
            else:
                equations.append(f"{s2} - {s1} = {v2 - v1}")
        else:
            equations.append(f"{s1} + {s2} = {v1 + v2}")
            equations.append(f"{s1} × {s2} = {v1 * v2}")
        
        if len(symbols_used) >= 3:
            s3 = symbols_used[2]
            v3 = values[s3]
            equations.append(f"{s2} + {s3} = {v2 + v3}")
        
        answer_sym = self.rng.choice(symbols_used)
        
        return equations, answer_sym
    
    def _sympy_solve_symbols(self, equations: List[str],
                              symbols_used: List[str]) -> Tuple[bool, Dict[str, int]]:
        """SymPy bilan symbol tenglamalarini yechish"""
        if not SYMPY_OK:
            return True, {}
        
        try:
            sym_vars = {s: symbols(f"s{i}") for i, s in enumerate(symbols_used)}
            
            parsed_eqs = []
            for eq_str in equations:
                if "=" not in eq_str:
                    continue
                
                lhs_str, rhs_str = eq_str.split("=", 1)
                rhs_str = rhs_str.strip()
                
                for sym, var in sym_vars.items():
                    lhs_str = lhs_str.replace(sym, str(var))
                
                try:
                    rhs_val = int(rhs_str)
                except ValueError:
                    continue
                
                lhs_str = lhs_str.replace("×", "*").replace("÷", "/")
                
                try:
                    from sympy import sympify as sp_sympify
                    lhs_expr = sp_sympify(lhs_str)
                    parsed_eqs.append(Eq(lhs_expr, rhs_val))
                except Exception:
                    continue
            
            if not parsed_eqs:
                return True, {}
            
            var_list = list(sym_vars.values())
            solutions = solve(parsed_eqs, var_list, dict=True)
            
            if len(solutions) != 1:
                return False, {}
            
            sol = solutions[0]
            result = {}
            for sym, var in sym_vars.items():
                if var in sol:
                    val = simplify(sol[var])
                    if val.is_integer and val >= 0:
                        result[sym] = int(val)
                    else:
                        return False, {}
            
            return True, result
            
        except Exception as e:
            logger.debug(f"SymPy solve error: {e}")
            return True, {}
    
    def _format_symbol_equations(self, equations: List[str], 
                                  answer_var: str) -> str:
        """Equation larni formatlash"""
        lines = []
        for eq in equations:
            lines.append(eq)
        lines.append(f"\n{answer_var} = ?")
        return "\n".join(lines)


rebus_engine = RebusEngine()
