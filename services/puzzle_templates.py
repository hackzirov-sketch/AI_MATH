"""
services/puzzle_templates.py — ACADEMIC MATH PUZZLE DESIGNER

Bu modul maktab darsliklari uslubidagi puzzle larni generatsiya qiladi.

Template Types:
1. Vertical arithmetic (qo'shish, ayirish, ko'paytirish)
2. Flow diagram (qutilar va strelkalar)
3. Step-by-step chain operations
4. Grid-based arithmetic puzzle
5. Symbol-based unknown value puzzle
"""

import random
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class PuzzleTemplate:
    """Puzzle template - asosiy struktura"""
    template_type: str
    template_id: str
    difficulty: str
    grade_range: Tuple[int, int]
    
    def get_uniqueness_signature(self) -> str:
        """Template uniqueness signature"""
        return f"{self.template_type}|{self.template_id}|{self.difficulty}"


@dataclass
class FilledPuzzle:
    """To'ldirilgan puzzle - generatsiya natijasi"""
    template_type: str
    puzzle_structure: str
    filled_values: Dict[str, Any]
    equations: List[str]
    final_answer: Any
    uniqueness_signature: str
    
    def to_dict(self) -> Dict:
        return {
            "template_type": self.template_type,
            "puzzle_structure": self.puzzle_structure,
            "filled_values": self.filled_values,
            "equations": self.equations,
            "final_answer": self.final_answer,
            "uniqueness_signature": self.uniqueness_signature
        }


class AcademicPuzzleGenerator:
    """
    Maktab darsliklari uslubidagi puzzle generator.
    
    Har bir puzzle:
    - Aniq bir template following qiladi
    - Random sonlar ishlatadi
    - 1 ta to'g'ri javobga ega
    - Trivial yoki takroriy emas
    """
    
    SYMBOLS = ["A", "B", "C", "D", "□", "△", "○", "◇", "☆"]
    SHAPES = ["square", "circle", "triangle", "diamond"]
    
    def __init__(self):
        self.templates = self._init_templates()
    
    def _init_templates(self) -> Dict[str, List[PuzzleTemplate]]:
        """Barcha templatelarni init qilish"""
        return {
            "vertical_arithmetic": [
                PuzzleTemplate("vertical_arithmetic", "addition_2digit", "oson", (2, 3)),
                PuzzleTemplate("vertical_arithmetic", "subtraction_2digit", "oson", (2, 3)),
                PuzzleTemplate("vertical_arithmetic", "multiplication_2x1", "o'rta", (3, 4)),
                PuzzleTemplate("vertical_arithmetic", "division_remainder", "o'rta", (4, 5)),
            ],
            "flow_diagram": [
                PuzzleTemplate("flow_diagram", "single_operation", "oson", (2, 4)),
                PuzzleTemplate("flow_diagram", "double_operation", "o'rta", (3, 6)),
                PuzzleTemplate("flow_diagram", "inverse_operations", "qiyin", (4, 11)),
            ],
            "chain_operations": [
                PuzzleTemplate("chain_operations", "three_step", "oson", (2, 5)),
                PuzzleTemplate("chain_operations", "four_step", "o'rta", (3, 7)),
                PuzzleTemplate("chain_operations", "five_step", "qiyin", (4, 11)),
            ],
            "grid_arithmetic": [
                PuzzleTemplate("grid_arithmetic", "magic_square", "o'rta", (3, 11)),
                PuzzleTemplate("grid_arithmetic", "row_col_sum", "oson", (2, 8)),
                PuzzleTemplate("grid_arithmetic", "crossword_number", "o'rta", (4, 11)),
            ],
            "symbol_unknown": [
                PuzzleTemplate("symbol_unknown", "single_symbol", "oson", (2, 3)),
                PuzzleTemplate("symbol_unknown", "double_symbol", "o'rta", (4, 5)),
                PuzzleTemplate("symbol_unknown", "equation_system", "qiyin", (6, 7)),
            ],
        }
    
    def generate(self, template_type: str, difficulty: str, grade: int) -> Optional[FilledPuzzle]:
        """Puzzle generatsiya qilish"""
        templates = self.templates.get(template_type, [])
        
        suitable = [t for t in templates 
                    if t.difficulty == difficulty 
                    and t.grade_range[0] <= grade <= t.grade_range[1]]
        
        if not suitable:
            suitable = [t for t in templates 
                       if t.grade_range[0] <= grade <= t.grade_range[1]]
        
        if not suitable:
            return None
        
        template = random.choice(suitable)
        
        generator_method = f"_generate_{template.template_id}"
        if hasattr(self, generator_method):
            return getattr(self, generator_method)(grade)
        
        return None
    
    def _generate_addition_2digit(self, grade: int) -> FilledPuzzle:
        """2 xonali sonlarni qo'shish"""
        a = random.randint(10, 99)
        b = random.randint(10, 99 - (a % 100))
        result = a + b
        
        return FilledPuzzle(
            template_type="vertical_arithmetic",
            puzzle_structure=f"""
   {a:>2}
+  {b:>2}
------
   {result:>2}
            """,
            filled_values={"a": a, "b": b, "result": result},
            equations=[f"{a} + {b} = {result}"],
            final_answer=result,
            uniqueness_signature=self._make_signature("addition", a, b)
        )
    
    def _generate_subtraction_2digit(self, grade: int) -> FilledPuzzle:
        """2 xonali sonlarni ayirish"""
        a = random.randint(50, 99)
        b = random.randint(10, a - 10)
        result = a - b
        
        return FilledPuzzle(
            template_type="vertical_arithmetic",
            puzzle_structure=f"""
   {a:>2}
-  {b:>2}
------
   {result:>2}
            """,
            filled_values={"a": a, "b": b, "result": result},
            equations=[f"{a} - {b} = {result}"],
            final_answer=result,
            uniqueness_signature=self._make_signature("subtraction", a, b)
        )
    
    def _generate_multiplication_2x1(self, grade: int) -> FilledPuzzle:
        """2 xonali × 1 xonali ko'paytirish"""
        a = random.randint(11, 99)
        b = random.randint(2, 9)
        result = a * b
        
        return FilledPuzzle(
            template_type="vertical_arithmetic",
            puzzle_structure=f"""
   {a:>2}
×    {b}
------
   {result:>3}
            """,
            filled_values={"a": a, "b": b, "result": result},
            equations=[f"{a} × {b} = {result}"],
            final_answer=result,
            uniqueness_signature=self._make_signature("multiplication", a, b)
        )
    
    def _generate_division_remainder(self, grade: int) -> FilledPuzzle:
        """Bo'lish qoldiq bilan"""
        divisor = random.randint(2, 9)
        quotient = random.randint(5, 15)
        remainder = random.randint(1, divisor - 1)
        dividend = divisor * quotient + remainder
        
        return FilledPuzzle(
            template_type="vertical_arithmetic",
            puzzle_structure=f"""
   {dividend:>2} | {divisor}
- {quotient * divisor:>2} |------
   {remainder:>2}   {quotient}
            """,
            filled_values={"dividend": dividend, "divisor": divisor, "quotient": quotient, "remainder": remainder},
            equations=[f"{dividend} = {divisor} × {quotient} + {remainder}"],
            final_answer=f"{quotient} qoldiq {remainder}",
            uniqueness_signature=self._make_signature("division", dividend, divisor)
        )
    
    def _generate_single_operation(self, grade: int) -> FilledPuzzle:
        """Bitta operatsiyali flow diagram"""
        x = random.randint(5, 20)
        op = random.choice([("+", 3, 7), ("-", 1, 5), ("×", 2, 4)])
        
        op_symbol, op_min, op_max = op
        y = random.randint(op_min, op_max)
        
        if op_symbol == "+":
            result = x + y
            equation = f"{x} + {y} = {result}"
        elif op_symbol == "-":
            result = x - y
            equation = f"{x} - {y} = {result}"
        else:
            result = x * y
            equation = f"{x} × {y} = {result}"
        
        return FilledPuzzle(
            template_type="flow_diagram",
            puzzle_structure=f"""
┌─────────┐     ┌─────────┐
│    {x}    │ ──► │ {op_symbol} {y} │ ──►  {result}
└─────────┘     └─────────┘
            """,
            filled_values={"x": x, "y": y, "op": op_symbol, "result": result},
            equations=[equation],
            final_answer=result,
            uniqueness_signature=self._make_signature("flow_single", x, y)
        )
    
    def _generate_double_operation(self, grade: int) -> FilledPuzzle:
        """Ikki operatsiyali flow diagram"""
        x = random.randint(3, 15)
        op1 = random.choice([("+", 2, 8), ("×", 2, 4)])
        y = random.randint(op1[1], op1[2])
        z = random.randint(1, 10)
        
        op1_symbol, _, _ = op1
        op2 = random.choice([("+", z), ("-", z)]) if random.random() > 0.5 else ("×", z)
        
        if op1_symbol == "+":
            step1 = x + y
        elif op1_symbol == "-":
            step1 = x - y
        else:
            step1 = x * y
        
        op2_symbol = op2[0]
        op2_value = op2[1]
        
        if op2_symbol == "+":
            result = step1 + op2_value
        elif op2_symbol == "-":
            result = step1 - op2_value
        else:
            result = step1 * op2_value
        
        return FilledPuzzle(
            template_type="flow_diagram",
            puzzle_structure=f"""
┌─────────┐     ┌─────────┐     ┌─────────┐
│    {x}    │ ──► │ {op1_symbol} {y}  │ ──► │ {op2_symbol} {op2_value} │ ──►  {result}
└─────────┘     └─────────┘     └─────────┘
            """,
            filled_values={"x": x, "y": y, "op1": op1_symbol, "op2": op2_symbol, "z": op2_value, "step1": step1, "result": result},
            equations=[f"{x} {op1_symbol} {y} = {step1}", f"{step1} {op2_symbol} {op2_value} = {result}"],
            final_answer=result,
            uniqueness_signature=self._make_signature("flow_double", x, y, op2_value)
        )
    
    def _generate_three_step(self, grade: int) -> FilledPuzzle:
        """3 qadamli zanjir operatsiya"""
        a = random.randint(2, 10)
        b = random.randint(2, 8)
        c = random.randint(2, 6)
        
        step1 = a + b
        step2 = step1 * c
        step3 = step2 - random.randint(1, step2 - 1)
        
        return FilledPuzzle(
            template_type="chain_operations",
            puzzle_structure=f"""
{a} ──► +{b} ──► ×{c} ──► -{step2 - step3} ──► {step3}
            """,
            filled_values={"a": a, "b": b, "c": c, "step1": step1, "step2": step2, "step3": step3, "subtract": step2 - step3},
            equations=[f"{a} + {b} = {step1}", f"{step1} × {c} = {step2}", f"{step2} - {step2 - step3} = {step3}"],
            final_answer=step3,
            uniqueness_signature=self._make_signature("chain_3step", a, b, c)
        )
    
    def _generate_four_step(self, grade: int) -> FilledPuzzle:
        """4 qadamli zanjir operatsiya"""
        values = [random.randint(2, 8) for _ in range(4)]
        ops = [random.choice(["+", "-", "×"]) for _ in range(3)]
        
        steps = [values[0]]
        for i, op in enumerate(ops):
            if op == "+":
                steps.append(steps[-1] + values[i + 1])
            elif op == "-":
                steps.append(steps[-1] - values[i + 1])
            else:
                steps.append(steps[-1] * values[i + 1])
        
        chain = " ──► ".join([f"{values[0]}"] + [f"{op}{v}" for op, v in zip(ops, values[1:])])
        chain += f" ──► {steps[-1]}"
        
        return FilledPuzzle(
            template_type="chain_operations",
            puzzle_structure=chain,
            filled_values={"values": values, "ops": ops, "steps": steps},
            equations=[f"{values[0]} {ops[0]} {values[1]} = {steps[1]}", 
                      f"{steps[1]} {ops[1]} {values[2]} = {steps[2]}",
                      f"{steps[2]} {ops[2]} {values[3]} = {steps[3]}"],
            final_answer=steps[-1],
            uniqueness_signature=self._make_signature("chain_4step", *values)
        )
    
    def _generate_magic_square(self, grade: int) -> FilledPuzzle:
        """Magic square (9 katakli)"""
        magic_sum = random.randint(12, 24)
        
        numbers = list(range(1, 10))
        random.shuffle(numbers)
        
        grid = [
            [numbers[0], numbers[1], numbers[2]],
            [numbers[3], numbers[4], numbers[5]],
            [numbers[6], numbers[7], numbers[8]]
        ]
        
        missing_row = random.randint(0, 2)
        missing_col = random.randint(0, 2)
        missing_value = grid[missing_row][missing_col]
        grid[missing_row][missing_col] = "?"
        
        grid_str = "\n".join([" ".join([str(x) for x in row]) for row in grid])
        
        return FilledPuzzle(
            template_type="grid_arithmetic",
            puzzle_structure=f"""
Magic sum: {magic_sum}
┌───┬───┬───┐
│ {grid[0][0]} │ {grid[0][1]} │ {grid[0][2]} │
├───┼───┼───┤
│ {grid[1][0]} │ {grid[1][1]} │ {grid[1][2]} │
├───┼───┼───┤
│ {grid[2][0]} │ {grid[2][1]} │ {grid[2][2]} │
└───┴───┴───┘
            """,
            filled_values={"grid": grid, "missing_position": (missing_row, missing_col), "magic_sum": magic_sum},
            equations=[f"Har qator yig'indisi: {magic_sum}", f"To'ldirilganda: {missing_value}"],
            final_answer=missing_value,
            uniqueness_signature=self._make_signature("magic_square", magic_sum, missing_value)
        )
    
    def _generate_row_col_sum(self, grade: int) -> FilledPuzzle:
        """Satr va ustun yig'indilari"""
        size = 3
        grid = [[random.randint(1, 9) for _ in range(size)] for _ in range(size)]
        
        row_sums = [sum(row) for row in grid]
        col_sums = [sum(grid[r][c] for r in range(size)) for c in range(size)]
        
        missing_r = random.randint(0, size - 1)
        missing_c = random.randint(0, size - 1)
        missing_value = grid[missing_r][missing_c]
        grid[missing_r][missing_c] = "?"
        
        grid_str = "\n".join([" ".join([str(x) for x in row]) for row in grid])
        
        return FilledPuzzle(
            template_type="grid_arithmetic",
            puzzle_structure=f"""
Jadval (satr yig'indilari o'ng tomonda):
{grid_str}
        """,
            filled_values={"grid": grid, "row_sums": row_sums, "col_sums": col_sums, "missing": (missing_r, missing_c)},
            equations=[f"Satr {missing_r+1}: ... = {row_sums[missing_r]}", 
                      f"Ustun {missing_c+1}: ... = {col_sums[missing_c]}"],
            final_answer=missing_value,
            uniqueness_signature=self._make_signature("row_col_sum", missing_value)
        )
    
    def _generate_single_symbol(self, grade: int) -> FilledPuzzle:
        """Bitta noma'lum belgi"""
        symbol = random.choice(["□", "△", "○"])
        a = random.randint(2, 15)
        b = random.randint(1, a - 1)
        c = a + b
        
        question = f"{a} + {symbol} = {c}"
        
        return FilledPuzzle(
            template_type="symbol_unknown",
            puzzle_structure=f"""
   {a}
+  {symbol}
------
   {c}
            """,
            filled_values={"a": a, "symbol": symbol, "b": b, "c": c},
            equations=[f"{a} + {b} = {c}", f"{symbol} = {b}"],
            final_answer=b,
            uniqueness_signature=self._make_signature("single_symbol", a, b)
        )
    
    def _generate_double_symbol(self, grade: int) -> FilledPuzzle:
        """Ikki noma'lum belgi"""
        sym1, sym2 = random.sample(["□", "△", "○", "◇"], 2)
        
        a = random.randint(5, 20)
        b = random.randint(3, 15)
        
        eq1_result = a + b
        eq2_result = a - b if a > b else b - a
        
        if eq2_result < 0:
            sym1, sym2 = sym2, sym1
            eq1_result, eq2_result = eq2_result, eq1_result
            a, b = b, a
        
        return FilledPuzzle(
            template_type="symbol_unknown",
            puzzle_structure=f"""
Tenglamalar sistemasini yeching:

{a} + {sym1} = {eq1_result}
{eq2_result} = {sym2} - {b}

{sym1} = ?
{sym2} = ?
            """,
            filled_values={"a": a, "b": b, "sym1": sym1, "sym2": sym2, "eq1": eq1_result, "eq2": eq2_result},
            equations=[f"{a} + {sym1} = {eq1_result}", f"{sym2} - {b} = {eq2_result}"],
            final_answer=f"{sym1}={b}, {sym2}={eq2_result + b}",
            uniqueness_signature=self._make_signature("double_symbol", a, b)
        )
    
    def _generate_equation_system(self, grade: int) -> FilledPuzzle:
        """Tenglama sistemasi (qiyin)"""
        x = random.randint(3, 10)
        y = random.randint(2, 8)
        
        eq1 = f"{x} + {y}"
        eq2 = f"{x} - {y}"
        
        a = random.randint(1, 3)
        b = random.randint(1, 3)
        
        result1 = (x + y) * a
        result2 = (x - y) * b
        
        return FilledPuzzle(
            template_type="symbol_unknown",
            puzzle_structure=f"""
({x} + {y}) × {a} = {result1}
({x} - {y}) × {b} = {result2}

x = ?
y = ?
            """,
            filled_values={"x": x, "y": y, "a": a, "b": b, "result1": result1, "result2": result2},
            equations=[f"({x} + {y}) × {a} = {result1}", f"({x} - {y}) × {b} = {result2}"],
            final_answer=f"x={x}, y={y}",
            uniqueness_signature=self._make_signature("eq_system", x, y, a, b)
        )
    
    def _make_signature(self, *args) -> str:
        """Uniqueness signature yaratish"""
        sig_str = "_".join(str(a) for a in args)
        return hashlib.md5(sig_str.encode()).hexdigest()[:12]
    
    def get_all_template_types(self) -> List[str]:
        """Barcha template turlarini qaytarish"""
        return list(self.templates.keys())
    
    def get_templates_by_difficulty(self, difficulty: str) -> List[PuzzleTemplate]:
        """Qiyinlik bo'yicha templatelarni qaytarish"""
        all_templates = []
        for templates in self.templates.values():
            all_templates.extend([t for t in templates if t.difficulty == difficulty])
        return all_templates


class PuzzleValidator:
    """
    Puzzle validator - puzzle validligini tekshirish.
    """
    
    def __init__(self):
        self.generator = AcademicPuzzleGenerator()
    
    def is_duplicate(self, p1: FilledPuzzle, p2: FilledPuzzle) -> Tuple[bool, str]:
        """Ikki puzzle duplicate mi?"""
        if p1.template_type != p2.template_type:
            return False, "Turli template turlari"
        
        if p1.uniqueness_signature == p2.uniqueness_signature:
            return True, "Bir xil uniqueness signature"
        
        return False, "Turli puzzle lar"
    
    def validate_puzzle(self, puzzle: FilledPuzzle) -> Tuple[bool, List[str]]:
        """Puzzle validligini tekshirish"""
        issues = []
        
        if not puzzle.final_answer:
            issues.append("Javob yo'q")
        
        if not puzzle.equations:
            issues.append("Tenglamalar yo'q")
        
        if not puzzle.filled_values:
            issues.append("Qiymatlar yo'q")
        
        return len(issues) == 0, issues


academic_puzzle_generator = AcademicPuzzleGenerator()
puzzle_validator = PuzzleValidator()
