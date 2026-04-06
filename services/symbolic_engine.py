"""
services/symbolic_engine.py — SYMPY CORE ENGINE

SymPy asosidagi hisob-kitob, validatsiya va symbolic reasoning.
Pipeline: Expression → Simplify → Validate → Canonical Answer

Mas'uliyatlar:
- Algebraic simplification (simplify, factor, expand)
- Equation solving (solve, Eq based checks)
- Rational simplification
- Float error reduction (exact arithmetic)
- Canonical answer generation
- Equivalent answer recognition
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, field
from fractions import Fraction

logger = logging.getLogger(__name__)

try:
    import sympy
    from sympy import (
        symbols, sympify, simplify, factor, expand, solve, Eq,
        Rational, Integer, sqrt, Abs, S, oo, N, nsimplify,
        latex, pi, sin, cos, tan, atan2, Rational as Rat
    )
    from sympy.parsing.sympy_parser import parse_expr
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    logger.warning("SymPy not installed. Symbolic engine will use fallback.")


@dataclass
class SymbolicResult:
    """Symbolic hisob-kitob natijasi"""
    original_expr: str = ""
    simplified: Optional[Any] = None
    numeric_value: Optional[float] = None
    exact_value: Optional[str] = None
    latex_repr: str = ""
    is_integer: bool = False
    is_rational: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def get_answer(self) -> Any:
        if self.is_integer and self.numeric_value is not None:
            return int(round(self.numeric_value))
        if self.simplified is not None:
            return self.simplified
        return self.numeric_value

    def to_dict(self) -> Dict:
        return {
            "original": self.original_expr,
            "simplified": str(self.simplified) if self.simplified is not None else None,
            "numeric": self.numeric_value,
            "exact": self.exact_value,
            "is_integer": self.is_integer,
            "errors": self.errors,
        }


@dataclass
class EquationSolution:
    """Tenglama yechimi"""
    equation_str: str = ""
    variable: str = ""
    solutions: List[Any] = field(default_factory=list)
    unique_solution: Optional[Any] = None
    is_unique: bool = False
    is_integer: bool = False
    is_positive: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "equation": self.equation_str,
            "variable": self.variable,
            "solutions": [str(s) for s in self.solutions],
            "unique": self.unique_solution,
            "is_unique": self.is_unique,
            "is_integer": self.is_integer,
        }


class SymbolicEngine:
    """
    SymPy asosidagi core engine.

    Ishlatish:
        engine = SymbolicEngine()
        result = engine.simplify_expression("2*x + 3*x")
        solution = engine.solve_equation("x + 5 = 12", "x")
        is_valid = engine.verify_answer("3 + 4", "7")
    """

    def __init__(self):
        self._cache: Dict[str, SymbolicResult] = {}
        self._sympy_ok = SYMPY_AVAILABLE

    def simplify_expression(self, expr_str: str) -> SymbolicResult:
        """Ifodani soddalashtirish"""
        if not self._sympy_ok:
            return self._fallback_eval(expr_str)

        result = SymbolicResult(original_expr=expr_str)

        try:
            expr = self._parse_expr(expr_str)
            if expr is None:
                result.errors.append(f"Parse error: {expr_str}")
                return result

            result.simplified = simplify(expr)

            try:
                result.numeric_value = float(N(result.simplified))
                result.is_integer = result.simplified.is_integer if hasattr(result.simplified, 'is_integer') else False
                result.is_rational = result.simplified.is_rational if hasattr(result.simplified, 'is_rational') else False
            except (TypeError, ValueError):
                pass

            try:
                result.exact_value = str(result.simplified)
                result.latex_repr = latex(result.simplified)
            except Exception:
                pass

        except Exception as e:
            result.errors.append(str(e))
            logger.warning(f"simplify_expression error: {e}")

        return result

    def solve_equation(self, equation_str: str, variable: str = "x") -> EquationSolution:
        """Tenglama yechish"""
        solution = EquationSolution(equation_str=equation_str, variable=variable)

        if not self._sympy_ok:
            solution.errors.append("SymPy not available")
            return solution

        try:
            var = symbols(variable)

            if "=" in equation_str:
                parts = equation_str.split("=", 1)
                lhs = self._parse_expr(parts[0].strip())
                rhs = self._parse_expr(parts[1].strip())
                eq = Eq(lhs, rhs)
            else:
                eq = Eq(self._parse_expr(equation_str), 0)

            if eq is None:
                solution.errors.append("Cannot parse equation")
                return solution

            sols = solve(eq, var)
            solution.solutions = [simplify(s) for s in sols]

            if len(solution.solutions) == 1:
                solution.is_unique = True
                solution.unique_solution = solution.solutions[0]

                try:
                    val = solution.unique_solution
                    solution.is_integer = val.is_integer if hasattr(val, 'is_integer') else False
                    solution.is_positive = (val > 0) if hasattr(val, '__gt__') else False
                except Exception:
                    pass

        except Exception as e:
            solution.errors.append(str(e))
            logger.warning(f"solve_equation error: {e}")

        return solution

    def verify_answer(self, expression: str, expected: Any, tolerance: float = 0.001) -> bool:
        """Javobni tekshirish"""
        if not self._sympy_ok:
            return self._fallback_verify(expression, expected, tolerance)

        try:
            expr = self._parse_expr(expression)
            if expr is None:
                return False

            simplified = simplify(expr)

            if isinstance(expected, str):
                expected_parsed = self._parse_expr(expected)
                if expected_parsed is None:
                    return False
                diff = simplify(simplified - expected_parsed)
                return diff == 0
            else:
                try:
                    numeric = float(N(simplified))
                    return abs(numeric - float(expected)) < tolerance
                except (TypeError, ValueError):
                    return str(simplify(simplified)) == str(expected)

        except Exception as e:
            logger.warning(f"verify_answer error: {e}")
            return False

    def check_equation_consistency(self, equations: List[str]) -> Dict[str, Any]:
        """Tenglamalar sistemining konsistentligini tekshirish"""
        result = {
            "is_consistent": True,
            "has_unique_solution": False,
            "solutions": {},
            "errors": [],
        }

        if not self._sympy_ok:
            result["errors"].append("SymPy not available")
            return result

        try:
            all_vars: Set[str] = set()
            parsed_eqs = []

            for eq_str in equations:
                if "=" in eq_str:
                    parts = eq_str.split("=", 1)
                    lhs = self._parse_expr(parts[0].strip())
                    rhs = self._parse_expr(parts[1].strip())
                    if lhs is not None and rhs is not None:
                        parsed_eqs.append(Eq(lhs, rhs))
                        all_vars.update(str(s) for s in lhs.free_symbols)
                        all_vars.update(str(s) for s in rhs.free_symbols)

            if parsed_eqs and all_vars:
                var_symbols = [symbols(v) for v in all_vars]
                sol = solve(parsed_eqs, var_symbols, dict=True)

                if sol:
                    result["has_unique_solution"] = len(sol) == 1
                    for s in sol:
                        for var_sym, val in s.items():
                            result["solutions"][str(var_sym)] = str(simplify(val))
                else:
                    result["is_consistent"] = False

        except Exception as e:
            result["errors"].append(str(e))
            result["is_consistent"] = False

        return result

    def canonical_answer(self, expr_str: str) -> Optional[str]:
        """Canonical javob shakli"""
        if not self._sympy_ok:
            return expr_str

        try:
            expr = self._parse_expr(expr_str)
            if expr is None:
                return expr_str

            simplified = simplify(expr)

            if simplified.is_integer:
                return str(int(simplified))
            elif simplified.is_rational:
                frac = Rational(simplified)
                if frac.denominator == 1:
                    return str(frac.numerator)
                return str(frac)
            else:
                return str(simplified)

        except Exception:
            return expr_str

    def are_equivalent(self, expr1: str, expr2: str) -> bool:
        """Ikki ifoda ekvivalent ekanligini tekshirish"""
        if not self._sympy_ok:
            return self._fallback_verify(expr1, expr2)

        try:
            e1 = self._parse_expr(expr1)
            e2 = self._parse_expr(expr2)
            if e1 is None or e2 is None:
                return False
            return simplify(e1 - e2) == 0
        except Exception:
            return False

    def factor_expression(self, expr_str: str) -> SymbolicResult:
        """Ifodani ko'paytuvchilarga ajratish"""
        result = SymbolicResult(original_expr=expr_str)

        if not self._sympy_ok:
            return result

        try:
            expr = self._parse_expr(expr_str)
            if expr is None:
                return result

            result.simplified = factor(expr)
            result.exact_value = str(result.simplified)

        except Exception as e:
            result.errors.append(str(e))

        return result

    def expand_expression(self, expr_str: str) -> SymbolicResult:
        """Ifodani yoyish"""
        result = SymbolicResult(original_expr=expr_str)

        if not self._sympy_ok:
            return result

        try:
            expr = self._parse_expr(expr_str)
            if expr is None:
                return result

            result.simplified = expand(expr)
            result.exact_value = str(result.simplified)

        except Exception as e:
            result.errors.append(str(e))

        return result

    def compute_geometry(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Geometrik hisob-kitoblar"""
        result = {"operation": operation, "values": {}, "errors": []}

        if not self._sympy_ok:
            result["errors"].append("SymPy not available")
            return result

        try:
            if operation == "distance":
                x1, y1 = kwargs.get("p1", (0, 0))
                x2, y2 = kwargs.get("p2", (0, 0))
                dist = sqrt((x2 - x1)**2 + (y2 - y1)**2)
                result["values"]["distance_exact"] = str(simplify(dist))
                result["values"]["distance_numeric"] = float(N(dist))

            elif operation == "midpoint":
                x1, y1 = kwargs.get("p1", (0, 0))
                x2, y2 = kwargs.get("p2", (0, 0))
                mx = simplify((x1 + x2) / 2)
                my = simplify((y1 + y2) / 2)
                result["values"]["midpoint"] = (str(mx), str(my))

            elif operation == "slope":
                x1, y1 = kwargs.get("p1", (0, 0))
                x2, y2 = kwargs.get("p2", (0, 0))
                if x2 - x1 == 0:
                    result["values"]["slope"] = "undefined"
                else:
                    slope = simplify((y2 - y1) / (x2 - x1))
                    result["values"]["slope"] = str(slope)
                    result["values"]["slope_numeric"] = float(N(slope))

            elif operation == "triangle_area":
                vertices = kwargs.get("vertices", [(0, 0), (1, 0), (0, 1)])
                if len(vertices) == 3:
                    (x1, y1), (x2, y2), (x3, y3) = vertices
                    area = Abs((x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2)
                    result["values"]["area_exact"] = str(simplify(area))
                    result["values"]["area_numeric"] = float(N(area))

            elif operation == "pythagorean":
                a = kwargs.get("a", 3)
                b = kwargs.get("b", 4)
                c = sqrt(a**2 + b**2)
                result["values"]["c_exact"] = str(simplify(c))
                result["values"]["c_numeric"] = float(N(c))
                result["values"]["is_pythagorean"] = c.is_integer

        except Exception as e:
            result["errors"].append(str(e))

        return result

    def _parse_expr(self, expr_str: str):
        """Xavfsiz ifoda parsing"""
        if not self._sympy_ok or not expr_str:
            return None

        try:
            expr_str = expr_str.strip()
            expr_str = expr_str.replace("^", "**")
            expr_str = expr_str.replace("×", "*")
            expr_str = expr_str.replace("÷", "/")
            expr_str = expr_str.replace("−", "-")

            try:
                return parse_expr(expr_str, transformations="all")
            except Exception:
                return sympify(expr_str)

        except Exception as e:
            logger.debug(f"Parse error for '{expr_str}': {e}")
            return None

    def _fallback_eval(self, expr_str: str) -> SymbolicResult:
        """SymPy yo'q bo'lganda fallback"""
        result = SymbolicResult(original_expr=expr_str)
        try:
            safe_expr = expr_str.replace("^", "**")
            for ch in ["sin", "cos", "tan", "sqrt", "log", "exp"]:
                safe_expr = safe_expr.replace(ch, f"math.{ch}")
            val = eval(safe_expr, {"__builtins__": {}}, {"math": __import__("math")})
            result.numeric_value = float(val)
            result.is_integer = float(val).is_integer()
        except Exception as e:
            result.errors.append(f"Fallback eval error: {e}")
        return result

    def _fallback_verify(self, expr: str, expected: Any, tolerance: float = 0.001) -> bool:
        """SymPy yo'q bo'lganda verify fallback"""
        try:
            safe_expr = expr.replace("^", "**")
            val = eval(safe_expr, {"__builtins__": {}}, {"math": __import__("math")})
            if isinstance(expected, str):
                exp_val = eval(expected.replace("^", "**"), {"__builtins__": {}}, {"math": __import__("math")})
            else:
                exp_val = float(expected)
            return abs(float(val) - float(exp_val)) < tolerance
        except Exception:
            return False


symbolic_engine = SymbolicEngine()
