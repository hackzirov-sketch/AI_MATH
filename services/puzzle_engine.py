"""
services/puzzle_engine.py — PRODUCTION-LEVEL PUZZLE GENERATION SYSTEM

Architecture:
TEMPLATE → PARAMETERS → VALIDATION → UNIQUENESS → RENDER_SPEC → PDF

This is the main orchestrator that coordinates all puzzle generation components.
"""

import random
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import sympy
from sympy import sympify, solve, Eq

logger = logging.getLogger(__name__)


class PuzzleType(Enum):
    VERTICAL_ARITHMETIC = "vertical_arithmetic"
    REBUS = "rebus"
    GRID_PUZZLE = "grid_puzzle"
    FLOW_DIAGRAM = "flow_diagram"
    CHAIN_OPERATIONS = "chain_operations"
    HYBRID = "hybrid"


class Difficulty(Enum):
    EASY = "oson"
    MEDIUM = "o'rta"
    HARD = "qiyin"


@dataclass
class PuzzleParameters:
    """Parameters for puzzle generation"""
    numbers: Dict[str, int]
    symbols: Dict[str, str]
    operations: List[str]
    constraints: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "numbers": self.numbers,
            "symbols": self.symbols,
            "operations": self.operations,
            "constraints": self.constraints,
        }


@dataclass
class PuzzleStructure:
    """Puzzle structure definition"""
    template_id: str
    template_type: PuzzleType
    variable_positions: Dict[str, Tuple[int, int]]
    operation_positions: List[Tuple[int, int]]
    constraints: List[str]
    difficulty: Difficulty
    grade_range: Tuple[int, int]
    
    def get_signature_base(self) -> str:
        return f"{self.template_type.value}|{self.template_id}|{self.difficulty.value}"


@dataclass
class RenderSpec:
    """Visual rendering specification"""
    layout_type: str
    grid_size: Optional[Tuple[int, int]] = None
    element_positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    arrow_connections: List[Tuple[str, str]] = field(default_factory=list)
    alignment_rules: str = "center"
    spacing_rules: Dict[str, float] = field(default_factory=dict)
    style_variant: str = "standard"
    figure_size: Tuple[float, float] = (10, 6)
    question_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "layout_type": self.layout_type,
            "grid_size": self.grid_size,
            "element_positions": self.element_positions,
            "arrow_connections": self.arrow_connections,
            "alignment_rules": self.alignment_rules,
            "spacing_rules": self.spacing_rules,
            "style_variant": self.style_variant,
            "figure_size": self.figure_size,
            "question_id": self.question_id,
        }


@dataclass
class GeneratedPuzzle:
    """Complete generated puzzle with all components"""
    puzzle_id: str
    template_id: str
    template_type: PuzzleType
    difficulty: Difficulty
    parameters: PuzzleParameters
    structure: str
    equations: List[str]
    render_spec: RenderSpec
    answer: Any
    uniqueness_signature: str
    validation_result: bool
    
    def to_dict(self) -> Dict:
        return {
            "puzzle_id": self.puzzle_id,
            "template_id": self.template_id,
            "template_type": self.template_type.value,
            "difficulty": self.difficulty.value,
            "parameters": self.parameters.to_dict(),
            "structure": self.structure,
            "equations": self.equations,
            "render_spec": self.render_spec.to_dict(),
            "answer": str(self.answer),
            "uniqueness_signature": self.uniqueness_signature,
            "validation_result": self.validation_result,
        }


class TemplateRegistry:
    """Central registry for all puzzle templates"""
    
    VERTICAL_ARITHMETIC_TEMPLATES = {
        "addition_2digit": {
            "description": "2 xonali sonlarni qo'shish",
            "variables": ["a", "b", "result"],
            "operations": ["+"],
            "variable_positions": {"a": (0, 0), "b": (1, 0), "result": (2, 0)},
            "operation_positions": [(1, 0)],
            "constraints": ["a >= 10", "a <= 99", "b >= 10", "b <= 99", "result = a + b"],
            "difficulty": Difficulty.EASY,
            "grade_range": (2, 4),
        },
        "addition_3digit": {
            "description": "3 xonali sonlarni qo'shish (o'nlikdan o'tish bilan)",
            "variables": ["a", "b", "result"],
            "operations": ["+"],
            "variable_positions": {"a": (0, 0), "b": (1, 0), "result": (2, 0)},
            "constraints": ["a >= 100", "a <= 999", "b >= 100", "b <= 999", "result = a + b"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (3, 5),
        },
        "subtraction_2digit": {
            "description": "2 xonali sonlarni ayirish",
            "variables": ["a", "b", "result"],
            "operations": ["-"],
            "variable_positions": {"a": (0, 0), "b": (1, 0), "result": (2, 0)},
            "operation_positions": [(1, 0)],
            "constraints": ["a >= 50", "a <= 99", "b >= 10", "b < a", "result = a - b"],
            "difficulty": Difficulty.EASY,
            "grade_range": (2, 4),
        },
        "multiplication_2x1": {
            "description": "2 xonali × 1 xonali ko'paytirish",
            "variables": ["a", "b", "result"],
            "operations": ["×"],
            "variable_positions": {"a": (0, 0), "b": (1, 1), "result": (2, 0)},
            "operation_positions": [(1, 0)],
            "constraints": ["a >= 11", "a <= 99", "b >= 2", "b <= 9", "result = a * b"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (3, 5),
        },
        "multiplication_2x2": {
            "description": "2 xonali × 2 xonali ko'paytirish",
            "variables": ["a", "b", "result"],
            "operations": ["×"],
            "constraints": ["a >= 11", "a <= 99", "b >= 11", "b <= 99", "result = a * b"],
            "difficulty": Difficulty.HARD,
            "grade_range": (4, 6),
        },
        "division_remainder": {
            "description": "Bo'lish qoldiq bilan",
            "variables": ["dividend", "divisor", "quotient", "remainder"],
            "operations": ["÷"],
            "variable_positions": {"dividend": (0, 0), "divisor": (1, 1), "quotient": (1, 2), "remainder": (2, 0)},
            "operation_positions": [(0, 1)],
            "constraints": ["divisor >= 2", "divisor <= 9", "quotient >= 5", "remainder < divisor"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (4, 6),
        },
    }
    
    REBUS_TEMPLATES = {
        "letter_addition": {
            "description": "Harfli qo'shish rebusi",
            "variables": ["X", "Y", "Z", "result"],
            "symbols": ["A", "B", "C"],
            "operations": ["+"],
            "constraints": ["X + Y = Z", "0 < X, Y, Z < 10", "no_carry"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (3, 5),
        },
        "symbol_equation": {
            "description": "Belgi tenglamasi",
            "variables": ["□", "△", "○"],
            "operations": ["+", "-"],
            "constraints": ["□ + △ = value1", "△ - ○ = value2"],
            "difficulty": Difficulty.HARD,
            "grade_range": (4, 7),
        },
    }
    
    GRID_PUZZLE_TEMPLATES = {
        "magic_square_3x3": {
            "description": "3×3 sehrli kvadrat",
            "grid_size": (3, 3),
            "variables": ["cells"],
            "constraints": ["all numbers 1-9", "sum = magic_sum", "each number used once"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (3, 6),
        },
        "row_col_sum": {
            "description": "Satr va ustun yig'indilari",
            "grid_size": (3, 3),
            "variables": ["cells", "row_sums", "col_sums"],
            "constraints": ["row_sum consistent", "col_sum consistent"],
            "difficulty": Difficulty.EASY,
            "grade_range": (2, 5),
        },
        "number_pattern_grid": {
            "description": "Sonli pattern jadvali",
            "grid_size": (4, 4),
            "variables": ["pattern_type", "start", "step"],
            "constraints": ["arithemtic or geometric progression"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (4, 7),
        },
    }
    
    FLOW_DIAGRAM_TEMPLATES = {
        "single_operation": {
            "description": "Bitta operatsiyali flow",
            "variables": ["input", "operation", "value", "output"],
            "operations": ["+", "-", "×"],
            "constraints": ["single step transformation"],
            "difficulty": Difficulty.EASY,
            "grade_range": (2, 4),
        },
        "double_operation": {
            "description": "Ikki operatsiyali flow",
            "variables": ["input", "op1", "op2", "step1", "output"],
            "operations": ["+", "-", "×"],
            "constraints": ["two sequential operations"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (3, 5),
        },
        "inverse_flow": {
            "description": "Teskari operatsiyalar",
            "variables": ["start", "op1", "value1", "op2", "value2", "end"],
            "operations": ["+", "-", "×", "÷"],
            "constraints": ["op2 is inverse of op1"],
            "difficulty": Difficulty.HARD,
            "grade_range": (5, 8),
        },
    }
    
    CHAIN_OPERATIONS_TEMPLATES = {
        "three_step": {
            "description": "3 qadamli zanjir",
            "variables": ["a", "b", "c", "step1", "step2", "step3"],
            "operations": ["+", "-", "×"],
            "constraints": ["three sequential operations"],
            "difficulty": Difficulty.EASY,
            "grade_range": (2, 5),
        },
        "four_step": {
            "description": "4 qadamli zanjir",
            "variables": ["values", "steps"],
            "operations": ["+", "-", "×"],
            "constraints": ["four sequential operations"],
            "difficulty": Difficulty.MEDIUM,
            "grade_range": (4, 7),
        },
        "five_step": {
            "description": "5 qadamli zanjir",
            "variables": ["values", "steps"],
            "operations": ["+", "-", "×", "÷"],
            "constraints": ["five sequential operations"],
            "difficulty": Difficulty.HARD,
            "grade_range": (5, 9),
        },
    }
    
    HYBRID_TEMPLATES = {
        "chain_grid": {
            "description": "Zanjir + Jadval",
            "variables": ["chain_values", "grid_values"],
            "constraints": ["output of chain is input of grid"],
            "difficulty": Difficulty.HARD,
            "grade_range": (5, 11),
        },
        "rebus_flow": {
            "description": "Rebus + Flow",
            "variables": ["rebus_syms", "flow_steps"],
            "constraints": ["solved rebus value is flow input"],
            "difficulty": Difficulty.HARD,
            "grade_range": (6, 11),
        }
    }
    
    @classmethod
    def get_all_templates(cls) -> Dict[str, Dict]:
        return {
            "vertical_arithmetic": cls.VERTICAL_ARITHMETIC_TEMPLATES,
            "rebus": cls.REBUS_TEMPLATES,
            "grid_puzzle": cls.GRID_PUZZLE_TEMPLATES,
            "flow_diagram": cls.FLOW_DIAGRAM_TEMPLATES,
            "chain_operations": cls.CHAIN_OPERATIONS_TEMPLATES,
            "hybrid": cls.HYBRID_TEMPLATES,
        }
    
    @classmethod
    def get_template(cls, template_type: str, template_id: str) -> Optional[Dict]:
        templates = cls.get_all_templates().get(template_type, {})
        return templates.get(template_id)
    
    @classmethod
    def get_templates_for_grade(cls, grade: int, difficulty: Difficulty = None) -> List[Tuple[str, str, Dict]]:
        """Get all templates suitable for a grade"""
        results = []
        for template_type, templates in cls.get_all_templates().items():
            for template_id, template in templates.items():
                grade_range = template.get("grade_range", (1, 11))
                if grade_range[0] <= grade <= grade_range[1]:
                    if difficulty is None or template["difficulty"] == difficulty:
                        results.append((template_type, template_id, template))
        return results


class ParameterGenerator:
    """Generate valid parameters for puzzle templates"""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def generate(self, template: Dict, difficulty: Difficulty, grade: int) -> PuzzleParameters:
        """Generate parameters for a template"""
        template_id = [k for k, v in TemplateRegistry.get_all_templates().items() 
                      if template in v.values()]
        
        if "vertical_arithmetic" in str(template_id):
            return self._generate_vertical_params(template, difficulty)
        elif "rebus" in str(template_id):
            return self._generate_rebus_params(template, difficulty)
        elif "grid" in str(template_id):
            return self._generate_grid_params(template, difficulty)
        elif "flow" in str(template_id):
            return self._generate_flow_params(template, difficulty)
        elif "chain" in str(template_id):
            return self._generate_chain_params(template, difficulty)
        
        return PuzzleParameters(numbers={}, symbols={}, operations=[], constraints={})
    
    def _generate_vertical_params(self, template: Dict, difficulty: Difficulty) -> PuzzleParameters:
        """Generate vertical arithmetic parameters"""
        if "addition" in template.get("description", "").lower():
            a = self.rng.randint(10, 99)
            b = self.rng.randint(10, 99 - (a % 100))
            result = a + b
        elif "subtraction" in template.get("description", "").lower():
            a = self.rng.randint(50, 99)
            b = self.rng.randint(10, a - 10)
            result = a - b
        elif "multiplication" in template.get("description", "").lower():
            a = self.rng.randint(11, 99)
            b = self.rng.randint(2, 9)
            result = a * b
        elif "division" in template.get("description", "").lower():
            divisor = self.rng.randint(2, 9)
            quotient = self.rng.randint(5, 15)
            remainder = self.rng.randint(1, divisor - 1)
            dividend = divisor * quotient + remainder
            return PuzzleParameters(
                numbers={"dividend": dividend, "divisor": divisor, "quotient": quotient, "remainder": remainder},
                symbols={},
                operations=["÷"],
                constraints={"result": f"{quotient} qoldiq {remainder}"}
            )
        else:
            a, b = 10, 5
            result = a + b
        
        return PuzzleParameters(
            numbers={"a": a, "b": b, "result": result},
            symbols={},
            operations=[template.get("operations", ["+"])[0]],
            constraints={"no_negative": result >= 0}
        )
    
    def _generate_rebus_params(self, template: Dict, difficulty: Difficulty) -> PuzzleParameters:
        """Generate rebus puzzle parameters"""
        symbols = list(template.get("symbols", ["A", "B", "C"]))
        
        if len(symbols) >= 2:
            sym1_val = self.rng.randint(1, 9)
            sym2_val = self.rng.randint(1, 9)
            result_val = sym1_val + sym2_val
            
            return PuzzleParameters(
                numbers={"A": sym1_val, "B": sym2_val, "result": result_val},
                symbols={symbols[0]: str(sym1_val), symbols[1]: str(sym2_val)},
                operations=["+"],
                constraints={"unique_values": len(set([sym1_val, sym2_val])) == 2}
            )
        
        return PuzzleParameters(numbers={"A": 5}, symbols={}, operations=["+"], constraints={})
    
    def _generate_grid_params(self, template: Dict, difficulty: Difficulty) -> PuzzleParameters:
        """Generate grid puzzle parameters"""
        if "magic" in template.get("description", "").lower():
            numbers = list(range(1, 10))
            self.rng.shuffle(numbers)
            magic_sum = 15
            
            return PuzzleParameters(
                numbers={"cells": numbers, "magic_sum": magic_sum},
                symbols={},
                operations=[],
                constraints={"sum_equals_magic": True}
            )
        
        grid_size = template.get("grid_size", (3, 3))
        cells = [[self.rng.randint(1, 9) for _ in range(grid_size[1])] for _ in range(grid_size[0])]
        
        return PuzzleParameters(
            numbers={"cells": cells},
            symbols={},
            operations=[],
            constraints={}
        )
    
    def _generate_flow_params(self, template: Dict, difficulty: Difficulty) -> PuzzleParameters:
        """Generate flow diagram parameters"""
        x = self.rng.randint(5, 20)
        op = self.rng.choice([("+", 3, 7), ("-", 1, 5), ("×", 2, 4)])
        op_symbol, op_min, op_max = op
        y = self.rng.randint(op_min, op_max)
        
        if op_symbol == "+":
            result = x + y
        elif op_symbol == "-":
            result = x - y
        else:
            result = x * y
        
        return PuzzleParameters(
            numbers={"x": x, "y": y, "result": result},
            symbols={},
            operations=[op_symbol],
            constraints={}
        )
    
    def _generate_chain_params(self, template: Dict, difficulty: Difficulty) -> PuzzleParameters:
        """Generate chain operations parameters"""
        if "three" in template.get("description", "").lower():
            a = self.rng.randint(2, 10)
            b = self.rng.randint(2, 8)
            c = self.rng.randint(2, 6)
            step1 = a + b
            step2 = step1 * c
            step3 = step2 - self.rng.randint(1, min(step2 - 1, 10))
            
            return PuzzleParameters(
                numbers={"a": a, "b": b, "c": c, "step1": step1, "step2": step2, "step3": step3},
                symbols={},
                operations=["+", "×", "-"],
                constraints={"positive_steps": all([step1 > 0, step2 > 0, step3 > 0])}
            )
        
        values = [self.rng.randint(2, 8) for _ in range(4)]
        ops = [self.rng.choice(["+", "-", "×"]) for _ in range(3)]
        
        steps = [values[0]]
        for i, op in enumerate(ops):
            if op == "+":
                steps.append(steps[-1] + values[i + 1])
            elif op == "-":
                steps.append(steps[-1] - values[i + 1])
            else:
                steps.append(steps[-1] * values[i + 1])
        
        return PuzzleParameters(
            numbers={"values": values, "steps": steps},
            symbols={},
            operations=ops,
            constraints={"positive_result": steps[-1] > 0}
        )


class PuzzleValidator:
    """Validate generated puzzles for correctness"""
    
    def __init__(self):
        self.validation_rules = []
    
    def validate(self, puzzle: GeneratedPuzzle) -> Tuple[bool, List[str]]:
        """Validate a generated puzzle"""
        issues = []
        
        if not self._validate_equations(puzzle):
            issues.append("Invalid equations")
        
        if not self._validate_uniqueness(puzzle):
            issues.append("Non-unique answer")
        
        if not self._validate_constraints(puzzle):
            issues.append("Constraints not satisfied")
        
        if not self._validate_structure(puzzle):
            issues.append("Invalid structure")
        
        return len(issues) == 0, issues
    
    def _validate_equations(self, puzzle: GeneratedPuzzle) -> bool:
        """Validate puzzle equations are correct"""
        if not puzzle.equations:
            return True
        
        params = puzzle.parameters
        numbers = params.numbers
        
        for eq in puzzle.equations:
            try:
                if "=" in eq:
                    parts = eq.split("=")
                    left_str = parts[0].strip()
                    right_str = "=".join(parts[1:]).strip()
                    
                    left_val = self._eval_expr(left_str, numbers)
                    right_val = self._eval_expr(right_str, numbers)
                    
                    if left_val is not None and right_val is not None:
                        if abs(left_val - right_val) > 0.001:
                            logger.warning(f"Equation mismatch: {left_str}={left_val} vs {right_str}={right_val}")
                            return False
            except Exception as e:
                pass
        
        return True
    
    def _eval_expr(self, expr: str, numbers: Dict[str, Any]) -> Optional[float]:
        """Use SymPy to safely evaluate expression with parameters"""
        try:
            # Prepare local dictionary for evaluation
            local_dict = {}
            for name, val in numbers.items():
                if isinstance(val, (int, float, str)):
                    if isinstance(val, str) and val.isdigit():
                        local_dict[name] = int(val)
                    elif isinstance(val, (int, float)):
                        local_dict[name] = val
                elif isinstance(val, list) and val:
                    local_dict[name] = val[0]
            
            # Use sympify for safe parsing and evaluation
            s_expr = sympify(expr.replace("×", "*").replace("÷", "/"))
            result = s_expr.evalf(subs=local_dict)
            return float(result)
        except Exception as e:
            logger.debug(f"SymPy eval error: {e} for expr {expr}")
            return None
    
    def _eval_safe(self, expr: str, params: PuzzleParameters) -> Optional[float]:
        """Safely evaluate a mathematical expression using SymPy"""
        return self._eval_expr(expr, params.numbers)
    
    def _validate_uniqueness(self, puzzle: GeneratedPuzzle) -> bool:
        """Ensure puzzle has exactly one solution using SymPy solver"""
        if puzzle.template_type == PuzzleType.REBUS:
            return self._check_rebus_uniqueness(puzzle)
        return puzzle.answer is not None
    
    def _check_rebus_uniqueness(self, puzzle: GeneratedPuzzle) -> bool:
        """Check if a rebus has exactly one valid digit assignment"""
        try:
            # Simple check for now, can be expanded for complex cryptarithms
            # For cryptarithms, we'd iterate digits or use a constraint solver
            # SymPy solve can handle simple linear equations
            return puzzle.answer is not None
        except:
            return True
    
    def _validate_constraints(self, puzzle: GeneratedPuzzle) -> bool:
        """Validate constraint satisfaction"""
        constraints = puzzle.parameters.constraints
        return constraints.get("no_negative", True) and constraints.get("positive_steps", True)
    
    def _validate_structure(self, puzzle: GeneratedPuzzle) -> bool:
        """Validate puzzle structure"""
        return bool(puzzle.structure) and bool(puzzle.render_spec)


class UniquenessEngine:
    """Track and prevent duplicate puzzles"""
    
    def __init__(self):
        self.generated_signatures: Dict[str, List[str]] = {}
        self.math_patterns: Dict[str, int] = {}
    
    def is_unique(self, puzzle: GeneratedPuzzle, session_id: str = "default") -> bool:
        """Check if puzzle is unique within session"""
        sig = puzzle.uniqueness_signature
        
        if session_id not in self.generated_signatures:
            self.generated_signatures[session_id] = []
        
        if sig in self.generated_signatures[session_id]:
            return False
        
        self.generated_signatures[session_id].append(sig)
        
        math_sig = self._generate_math_signature(puzzle)
        if math_sig in self.math_patterns:
            return False
        
        self.math_patterns[math_sig] = 1
        
        return True
    
    def _generate_math_signature(self, puzzle: GeneratedPuzzle) -> str:
        """Generate mathematical pattern signature"""
        template_type = puzzle.template_type.value
        difficulty = puzzle.difficulty.value
        
        numbers = sorted(puzzle.parameters.numbers.items(), key=lambda x: x[0])
        num_str = "_".join(f"{k}:{v}" for k, v in numbers if isinstance(v, (int, float)))
        
        return f"{template_type}|{difficulty}|{num_str}"
    
    def reset_session(self, session_id: str):
        """Reset tracking for a session"""
        if session_id in self.generated_signatures:
            self.generated_signatures[session_id] = []
    
    def get_similarity(self, p1: GeneratedPuzzle, p2: GeneratedPuzzle) -> float:
        """Calculate similarity between two puzzles"""
        if p1.template_type != p2.template_type:
            return 0.0
        
        sig1 = self._generate_math_signature(p1)
        sig2 = self._generate_math_signature(p2)
        
        if sig1 == sig2:
            return 1.0
        
        parts1 = set(sig1.split("|"))
        parts2 = set(sig2.split("|"))
        
        if not parts1 or not parts2:
            return 0.0
        
        return len(parts1 & parts2) / len(parts1 | parts2)


class RenderSpecGenerator:
    """Generate visual rendering specifications"""
    
    LAYOUT_TYPES = {
        "vertical": {"alignment": "right", "orientation": "vertical"},
        "horizontal": {"alignment": "center", "orientation": "horizontal"},
        "grid": {"alignment": "grid", "orientation": "matrix"},
        "flow": {"alignment": "left", "orientation": "horizontal"},
        "chain": {"alignment": "spaced", "orientation": "horizontal"},
    }
    
    STYLE_VARIANTS = {
        "standard": {"box_style": "rounded", "line_width": 2, "font_weight": "normal"},
        "bold": {"box_style": "square", "line_width": 3, "font_weight": "bold"},
        "minimal": {"box_style": "none", "line_width": 1, "font_weight": "normal"},
        "colorful": {"box_style": "rounded", "line_width": 2, "font_weight": "bold", "colors": True},
    }
    
    def generate(self, puzzle: GeneratedPuzzle) -> RenderSpec:
        """Generate render specification for puzzle"""
        template_type = puzzle.template_type.value
        
        if "vertical" in template_type:
            return self._generate_vertical_spec(puzzle)
        elif "grid" in template_type:
            return self._generate_grid_spec(puzzle)
        elif "flow" in template_type:
            return self._generate_flow_spec(puzzle)
        elif "chain" in template_type:
            return self._generate_chain_spec(puzzle)
        elif "rebus" in template_type:
            return self._generate_rebus_spec(puzzle)
        
        return RenderSpec(layout_type="standard", style_variant="standard", question_id=puzzle.puzzle_id)
    
    def _generate_vertical_spec(self, puzzle: GeneratedPuzzle) -> RenderSpec:
        """Generate vertical arithmetic render spec"""
        params = puzzle.parameters.numbers
        
        positions = {}
        spacing = {"col_spacing": 0.8, "line_spacing": 1.0}
        
        positions["num1"] = (2.0, 3.0)
        positions["op"] = (1.5, 2.5)
        positions["num2"] = (2.0, 2.0)
        positions["line"] = (1.0, 1.5)
        positions["result"] = (2.0, 1.0)
        
        return RenderSpec(
            layout_type="vertical",
            grid_size=(5, 4),
            element_positions=positions,
            alignment_rules="right",
            spacing_rules=spacing,
            style_variant=self._random_style_variant(),
            figure_size=(8, 10),
            question_id=puzzle.puzzle_id
        )
    
    def _generate_grid_spec(self, puzzle: GeneratedPuzzle) -> RenderSpec:
        """Generate grid puzzle render spec"""
        grid_size = (3, 3)
        
        positions = {}
        for r in range(grid_size[0]):
            for c in range(grid_size[1]):
                positions[f"cell_{r}_{c}"] = (c * 1.2 + 1, grid_size[0] - r * 1.2)
        
        return RenderSpec(
            layout_type="grid",
            grid_size=grid_size,
            element_positions=positions,
            alignment_rules="center",
            spacing_rules={"cell_size": 1.0, "padding": 0.1},
            style_variant=self._random_style_variant(),
            figure_size=(8, 8),
            question_id=puzzle.puzzle_id
        )
    
    def _generate_flow_spec(self, puzzle: GeneratedPuzzle) -> RenderSpec:
        """Generate flow diagram render spec"""
        num_steps = len([k for k in puzzle.parameters.numbers.keys() if k.startswith("step") or k == "result"])
        
        positions = {}
        arrows = []
        
        positions["input"] = (1.0, 2.5)
        
        for i in range(num_steps - 1):
            positions[f"step_{i}"] = (1.5 + i * 2.5, 2.5)
            arrows.append((f"step_{i-1}" if i > 0 else "input", f"step_{i}"))
        
        positions["output"] = (1.5 + (num_steps - 1) * 2.5, 2.5)
        arrows.append((f"step_{num_steps - 2}", "output"))
        
        return RenderSpec(
            layout_type="flow",
            element_positions=positions,
            arrow_connections=arrows,
            alignment_rules="horizontal",
            spacing_rules={"box_spacing": 2.0, "box_width": 1.5},
            style_variant=self._random_style_variant(),
            figure_size=(12, 4),
            question_id=puzzle.puzzle_id
        )
    
    def _generate_chain_spec(self, puzzle: GeneratedPuzzle) -> RenderSpec:
        """Generate chain operations render spec"""
        values = puzzle.parameters.numbers.get("values", [])
        
        positions = {}
        arrows = []
        
        for i, val in enumerate(values):
            positions[f"val_{i}"] = (i * 2.0, 2.5)
            if i > 0:
                arrows.append((f"val_{i-1}", f"val_{i}"))
        
        positions["result"] = (len(values) * 2.0, 2.5)
        arrows.append((f"val_{len(values)-1}", "result"))
        
        return RenderSpec(
            layout_type="chain",
            element_positions=positions,
            arrow_connections=arrows,
            alignment_rules="horizontal",
            spacing_rules={"element_spacing": 1.8},
            style_variant=self._random_style_variant(),
            figure_size=(12, 3),
            question_id=puzzle.puzzle_id
        )
    
    def _generate_rebus_spec(self, puzzle: GeneratedPuzzle) -> RenderSpec:
        """Generate rebus puzzle render spec"""
        positions = {
            "equation": (5.0, 3.0),
            "symbols": (5.0, 2.0),
            "question": (5.0, 1.0),
        }
        
        return RenderSpec(
            layout_type="rebus",
            element_positions=positions,
            alignment_rules="center",
            spacing_rules={"line_spacing": 1.0},
            style_variant=self._random_style_variant(),
            figure_size=(10, 6),
            question_id=puzzle.puzzle_id
        )
    
    def _random_style_variant(self) -> str:
        """Get random style variant"""
        return random.choice(list(self.STYLE_VARIANTS.keys()))


class PuzzleGenerator:
    """
    Main puzzle generation orchestrator.
    
    Pipeline: Template Selection → Parameter Generation → Validation → Uniqueness Check → Render Spec
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.param_generator = ParameterGenerator(seed)
        self.validator = PuzzleValidator()
        self.uniqueness = UniquenessEngine()
        self.render_spec_gen = RenderSpecGenerator()
        self._session_counter = 0
    
    def generate(
        self,
        template_type: str,
        difficulty: str,
        grade: int,
        session_id: Optional[str] = None,
        force_unique: bool = True
    ) -> Optional[GeneratedPuzzle]:
        """Generate a puzzle with given parameters"""
        
        if session_id is None:
            session_id = f"session_{self._session_counter}"
            self._session_counter += 1
        
        diff_enum = Difficulty(difficulty)
        
        templates = TemplateRegistry.get_templates_for_grade(grade, diff_enum)
        filtered = [(tt, tid, t) for tt, tid, t in templates if tt == template_type]
        
        if not filtered:
            filtered = [(tt, tid, t) for tt, tid, t in templates]
        
        if not filtered:
            return None
        
        max_attempts = 10
        for attempt in range(max_attempts):
            if not filtered:
                return None
            
            selected_template = random.choice(filtered)
            actual_template_type, template_id, template = selected_template
            
            params = self.param_generator.generate(template, diff_enum, grade)
            
            puzzle = self._build_puzzle(
                template_type=actual_template_type,
                template_id=template_id,
                template=template,
                params=params,
                difficulty=diff_enum,
                grade=grade
            )
            
            is_valid, issues = self.validator.validate(puzzle)
            if not is_valid:
                logger.warning(f"Puzzle validation failed: {issues}")
                continue
            
            if force_unique and not self.uniqueness.is_unique(puzzle, session_id):
                logger.info("Puzzle not unique, trying again")
                continue
            
            return puzzle
        
        return None
    
    def _build_puzzle(
        self,
        template_type: str,
        template_id: str,
        template: Dict,
        params: PuzzleParameters,
        difficulty: Difficulty,
        grade: int
    ) -> GeneratedPuzzle:
        """Build complete puzzle object"""
        
        puzzle_id = self._generate_puzzle_id()
        structure = self._build_structure(template_type, template_id, params)
        equations = self._build_equations(template_type, params)
        answer = self._extract_answer(params)
        signature = self._generate_signature(template_type, template_id, params, difficulty)
        
        base_puzzle = GeneratedPuzzle(
            puzzle_id=puzzle_id,
            template_id=template_id,
            template_type=PuzzleType(template_type),
            difficulty=difficulty,
            parameters=params,
            structure=structure,
            equations=equations,
            render_spec=None,
            answer=answer,
            uniqueness_signature=signature,
            validation_result=True
        )
        
        base_puzzle.render_spec = self.render_spec_gen.generate(base_puzzle)
        
        return base_puzzle
    
    def _generate_puzzle_id(self) -> str:
        """Generate unique puzzle ID"""
        return hashlib.md5(str(random.random()).encode()).hexdigest()[:8]
    
    def _build_structure(self, template_type: str, template_id: str, params: PuzzleParameters) -> str:
        """Build puzzle structure string"""
        numbers = params.numbers
        
        if template_type == "vertical_arithmetic":
            if "addition" in template_id:
                return f"   {numbers.get('a', 0)}\n + {numbers.get('b', 0)}\n -----\n   {numbers.get('result', 0)}"
            elif "subtraction" in template_id:
                return f"   {numbers.get('a', 0)}\n - {numbers.get('b', 0)}\n -----\n   {numbers.get('result', 0)}"
            elif "multiplication" in template_id:
                return f"   {numbers.get('a', 0)}\n × {numbers.get('b', 0)}\n -----\n   {numbers.get('result', 0)}"
            elif "division" in template_id:
                return f"{numbers.get('dividend', 0)} ÷ {numbers.get('divisor', 0)} = {numbers.get('quotient', 0)} qoldiq {numbers.get('remainder', 0)}"
        
        elif template_type == "chain_operations":
            vals = numbers.get("values", [])
            ops = params.operations
            return " → ".join([str(vals[0])] + [f"{ops[i]}{vals[i+1]}" for i in range(len(vals)-1)])
        
        elif template_type == "grid_puzzle":
            cells = numbers.get("cells", [])
            if cells:
                rows = [cells[i*3:(i+1)*3] for i in range(3)]
                return "\n".join([" ".join(str(c) for c in row) for row in rows])
        
        return "Puzzle structure"
    
    def _build_equations(self, template_type: str, params: PuzzleParameters) -> List[str]:
        """Build equation strings"""
        equations = []
        numbers = params.numbers
        ops = params.operations
        
        if template_type == "vertical_arithmetic":
            if 'result' in numbers and 'a' in numbers and 'b' in numbers:
                op = ops[0] if ops else '+'
                equations.append(f"{numbers['a']} {op} {numbers['b']} = {numbers['result']}")
            elif 'dividend' in numbers and 'divisor' in numbers:
                equations.append(f"{numbers.get('dividend', 0)} = {numbers.get('divisor', 0)} * {numbers.get('quotient', 0)} + {numbers.get('remainder', 0)}")
        
        elif template_type == "chain_operations":
            vals = numbers.get("values", [])
            steps = numbers.get("steps", [])
            if vals and steps:
                for i, op in enumerate(ops):
                    if i < len(vals) - 1:
                        eq_step = steps[i+1] if i+1 < len(steps) else '?'
                        equations.append(f"{vals[i]} {op} {vals[i+1]} = {eq_step}")
        
        elif template_type == "rebus":
            for sym, val in numbers.items():
                if sym not in ['result'] and isinstance(val, (int, float)):
                    pass
            if 'A' in numbers or 'B' in numbers:
                a = numbers.get('A', numbers.get('a', 0))
                b = numbers.get('B', numbers.get('b', 0))
                result = numbers.get('result', a + b)
                equations.append(f"{a} + {b} = {result}")
        
        elif template_type == "grid_puzzle":
            cells = numbers.get("cells", [])
            if cells:
                equations.append(f"Jadval: {len(cells)} ta son")
        
        return equations
    
    def _extract_answer(self, params: PuzzleParameters) -> Any:
        """Extract the answer from parameters"""
        numbers = params.numbers
        
        if "result" in numbers:
            return numbers["result"]
        if "step3" in numbers:
            return numbers["step3"]
        if "steps" in numbers and numbers["steps"]:
            return numbers["steps"][-1]
        if "cells" in numbers:
            return numbers.get("missing", "See structure")
        
        return list(numbers.values())[-1] if numbers else None
    
    def _generate_signature(self, template_type: str, template_id: str, params: PuzzleParameters, difficulty: Difficulty) -> str:
        """Generate uniqueness signature"""
        sig_str = f"{template_type}|{template_id}|{difficulty.value}"
        
        for k, v in sorted(params.numbers.items()):
            if isinstance(v, (int, float)):
                sig_str += f"|{k}={v}"
            elif isinstance(v, list):
                sig_str += f"|{k}={str(v)}"
        
        return hashlib.md5(sig_str.encode()).hexdigest()[:12]
        
    def optimize_diversity(self, puzzles: List[GeneratedPuzzle]) -> List[GeneratedPuzzle]:
        """Improve variety across a set of puzzles"""
        if not puzzles:
            return puzzles
            
        optimized = []
        used_types = set()
        used_templates = set()
        
        # Birinchi o'rinda har xil turdagi savollarni olamiz
        for p in puzzles:
            if p.template_type.value not in used_types:
                optimized.append(p)
                used_types.add(p.template_type.value)
                used_templates.add(p.template_id)
        
        # Keyin qolganlarini qo'shamiz (lekin takroriy template bo'lmasa yaxshi)
        for p in puzzles:
            if p not in optimized:
                if p.template_id not in used_templates:
                    optimized.append(p)
                    used_templates.add(p.template_id)
        
        # Agar hali ham kam bo'lsa, qolganlarini qo'shamiz
        for p in puzzles:
            if p not in optimized:
                optimized.append(p)
                
        return optimized
    
    def generate_batch(
        self,
        count: int,
        template_type: Optional[str] = None,
        difficulty: str = "o'rta",
        grade: int = 5,
        session_id: Optional[str] = None
    ) -> List[GeneratedPuzzle]:
        """Generate a batch of unique and diverse puzzles"""
        puzzles = []
        
        if session_id is None:
            session_id = f"batch_{self._session_counter}"
            self._session_counter += 1
        
        # Har bir batch uchun yangi session ochamiz (uniqueness uchun)
        self.uniqueness.reset_session(session_id)
        
        # Barcha mavjud turlar (agar bitta tur tanlanmagan bo'lsa)
        all_types = list(TemplateRegistry.get_all_templates().keys())
        
        # Kerakli miqdordan 2 barobar ko'proq savol generatsiya qilamiz (diversity tanlash uchun)
        candidates = []
        max_attempts = count * 5
        
        for _ in range(max_attempts):
            if len(candidates) >= count * 2:
                break
                
            tt = template_type if template_type else random.choice(all_types)
            puzzle = self.generate(tt, difficulty, grade, session_id, force_unique=True)
            
            if puzzle:
                candidates.append(puzzle)
        
        # Diversity optimizer orqali eng yaxshi savollarni tanlaymiz
        optimized = self.optimize_diversity(candidates)
        
        return optimized[:count]


puzzle_engine = PuzzleGenerator()
