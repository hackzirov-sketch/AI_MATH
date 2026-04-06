"""
services/geometry_math.py — GEOMETRY MATH WITH SYMPY

Geometrik hisob-kitoblar va validatsiya SymPy orqali.
Mas'uliyatlar:
- Distance, midpoint, slope
- Triangle side relations (Pythagorean)
- Area/perimeter calculations
- Angle computations
- Line equations
- Circle equations
- Geometric constraint validation
"""

from __future__ import annotations

import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import sympy
    from sympy import (
        symbols, sqrt, Abs, simplify, N, Rational, pi,
        sin, cos, tan, asin, acos, atan, atan2, S, oo, latex, Point, Triangle as SympyTriangle,
        Line, Circle as SympyCircle, Segment, Polygon as SympyPolygon
    )
    from sympy.geometry import Point2D
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    logger.warning("SymPy not available for geometry_math")


@dataclass
class GeometryResult:
    """Geometrik hisob-kitob natijasi"""
    operation: str = ""
    exact_values: Dict[str, Any] = field(default_factory=dict)
    numeric_values: Dict[str, float] = field(default_factory=dict)
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    latex_repr: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "operation": self.operation,
            "exact": {k: str(v) for k, v in self.exact_values.items()},
            "numeric": self.numeric_values,
            "is_valid": self.is_valid,
            "errors": self.errors,
        }


class GeometryMath:
    """
    Geometrik hisob-kitoblar engine.

    Ishlatish:
        gmath = GeometryMath()
        result = gmath.distance((0, 0), (3, 4))
        result = gmath.triangle_area((0, 0), (3, 0), (0, 4))
        result = gmath.verify_pythagorean(3, 4, 5)
    """

    def __init__(self):
        self._sympy_ok = SYMPY_AVAILABLE

    def distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> GeometryResult:
        """Ikki nuqta orasidagi masofa"""
        result = GeometryResult(operation="distance")

        if self._sympy_ok:
            try:
                x1, y1 = Rational(p1[0]), Rational(p1[1])
                x2, y2 = Rational(p2[0]), Rational(p2[1])
                dist = sqrt((x2 - x1)**2 + (y2 - y1)**2)
                dist_simplified = simplify(dist)

                result.exact_values["distance"] = dist_simplified
                result.numeric_values["distance"] = float(N(dist_simplified))
                result.latex_repr["distance"] = latex(dist_simplified)

                if dist_simplified.is_integer:
                    result.exact_values["distance_int"] = int(dist_simplified)

            except Exception as e:
                result.errors.append(str(e))
        else:
            result.numeric_values["distance"] = math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        return result

    def midpoint(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> GeometryResult:
        """O'rta nuqta"""
        result = GeometryResult(operation="midpoint")

        try:
            mx = Rational(p1[0] + p2[0], 2)
            my = Rational(p1[1] + p2[1], 2)

            result.exact_values["midpoint"] = (mx, my)
            result.numeric_values["midpoint_x"] = float(mx)
            result.numeric_values["midpoint_y"] = float(my)

            if self._sympy_ok:
                result.latex_repr["midpoint"] = f"({latex(mx)}, {latex(my)})"

        except Exception as e:
            result.errors.append(str(e))

        return result

    def slope(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> GeometryResult:
        """Egilish (slope)"""
        result = GeometryResult(operation="slope")

        try:
            dx = Rational(p2[0]) - Rational(p1[0])
            dy = Rational(p2[1]) - Rational(p1[1])

            if dx == 0:
                result.exact_values["slope"] = "undefined"
                result.warnings.append("Vertical line - slope undefined")
            else:
                m = dy / dx
                result.exact_values["slope"] = m
                result.numeric_values["slope"] = float(m)

                if self._sympy_ok:
                    result.latex_repr["slope"] = latex(m)

        except Exception as e:
            result.errors.append(str(e))

        return result

    def triangle_area(self, v1: Tuple[float, float], v2: Tuple[float, float],
                      v3: Tuple[float, float]) -> GeometryResult:
        """Uchburchak yuzasi (Shoelace formula)"""
        result = GeometryResult(operation="triangle_area")

        if self._sympy_ok:
            try:
                p1 = Point2D(Rational(v1[0]), Rational(v1[1]))
                p2 = Point2D(Rational(v2[0]), Rational(v2[1]))
                p3 = Point2D(Rational(v3[0]), Rational(v3[1]))

                tri = SympyTriangle(p1, p2, p3)
                area = simplify(tri.area)

                result.exact_values["area"] = area
                result.numeric_values["area"] = float(N(area))
                result.latex_repr["area"] = latex(area)

                perimeter = simplify(p1.distance(p2) + p2.distance(p3) + p3.distance(p1))
                result.exact_values["perimeter"] = perimeter
                result.numeric_values["perimeter"] = float(N(perimeter))

            except Exception as e:
                result.errors.append(str(e))
                result = self._fallback_area(v1, v2, v3, result)
        else:
            result = self._fallback_area(v1, v2, v3, result)

        return result

    def _fallback_area(self, v1, v2, v3, result: GeometryResult) -> GeometryResult:
        """Fallback area calculation without SymPy"""
        x1, y1 = v1
        x2, y2 = v2
        x3, y3 = v3
        area = abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2
        result.numeric_values["area"] = area
        return result

    def verify_pythagorean(self, a: float, b: float, c: float) -> GeometryResult:
        """Pifagor teoremasini tekshirish"""
        result = GeometryResult(operation="pythagorean")

        if self._sympy_ok:
            try:
                a_r, b_r, c_r = Rational(a), Rational(b), Rational(c)
                lhs = simplify(a_r**2 + b_r**2)
                rhs = simplify(c_r**2)

                result.exact_values["a_squared"] = a_r**2
                result.exact_values["b_squared"] = b_r**2
                result.exact_values["c_squared"] = c_r**2
                result.exact_values["a2_plus_b2"] = lhs
                result.exact_values["c2"] = rhs

                is_pythagorean = (lhs == rhs)
                result.is_valid = is_pythagorean
                result.exact_values["is_pythagorean"] = is_pythagorean

                if not is_pythagorean:
                    computed_c = simplify(sqrt(a_r**2 + b_r**2))
                    result.exact_values["computed_c"] = computed_c
                    result.numeric_values["computed_c"] = float(N(computed_c))
                    result.warnings.append(f"Pythagorean not satisfied: {a}²+{b}² ≠ {c}²")

            except Exception as e:
                result.errors.append(str(e))
        else:
            is_pyth = abs(a*a + b*b - c*c) < 0.001
            result.is_valid = is_pyth
            result.exact_values["is_pythagorean"] = is_pyth

        return result

    def circle_properties(self, cx: float = 0, cy: float = 0,
                          radius: float = 1) -> GeometryResult:
        """Aylana xususiyatlari"""
        result = GeometryResult(operation="circle")

        if self._sympy_ok:
            try:
                r = Rational(radius)
                area = simplify(pi * r**2)
                circumference = simplify(2 * pi * r)
                diameter = 2 * r

                result.exact_values["radius"] = r
                result.exact_values["diameter"] = diameter
                result.exact_values["area"] = area
                result.exact_values["circumference"] = circumference

                result.numeric_values["radius"] = float(r)
                result.numeric_values["diameter"] = float(diameter)
                result.numeric_values["area"] = float(N(area))
                result.numeric_values["circumference"] = float(N(circumference))

                result.latex_repr["area"] = latex(area)
                result.latex_repr["circumference"] = latex(circumference)

            except Exception as e:
                result.errors.append(str(e))
        else:
            r = radius
            result.numeric_values["area"] = math.pi * r * r
            result.numeric_values["circumference"] = 2 * math.pi * r
            result.numeric_values["diameter"] = 2 * r

        return result

    def rectangle_properties(self, width: float, height: float) -> GeometryResult:
        """To'g'ri to'rtburchak xususiyatlari"""
        result = GeometryResult(operation="rectangle")

        if self._sympy_ok:
            try:
                w, h = Rational(width), Rational(height)
                area = simplify(w * h)
                perimeter = simplify(2 * (w + h))
                diagonal = simplify(sqrt(w**2 + h**2))

                result.exact_values["width"] = w
                result.exact_values["height"] = h
                result.exact_values["area"] = area
                result.exact_values["perimeter"] = perimeter
                result.exact_values["diagonal"] = diagonal

                result.numeric_values["area"] = float(N(area))
                result.numeric_values["perimeter"] = float(N(perimeter))
                result.numeric_values["diagonal"] = float(N(diagonal))

                if diagonal.is_integer:
                    result.exact_values["diagonal_int"] = int(diagonal)

            except Exception as e:
                result.errors.append(str(e))
        else:
            result.numeric_values["area"] = width * height
            result.numeric_values["perimeter"] = 2 * (width + height)
            result.numeric_values["diagonal"] = math.hypot(width, height)

        return result

    def trapezoid_area(self, base1: float, base2: float, height: float) -> GeometryResult:
        """Trapetsiya yuzasi"""
        result = GeometryResult(operation="trapezoid")

        if self._sympy_ok:
            try:
                b1, b2, h = Rational(base1), Rational(base2), Rational(height)
                area = simplify((b1 + b2) * h / 2)

                result.exact_values["base1"] = b1
                result.exact_values["base2"] = b2
                result.exact_values["height"] = h
                result.exact_values["area"] = area

                result.numeric_values["area"] = float(N(area))
                result.latex_repr["area"] = latex(area)

            except Exception as e:
                result.errors.append(str(e))
        else:
            result.numeric_values["area"] = (base1 + base2) * height / 2

        return result

    def line_equation(self, p1: Tuple[float, float],
                      p2: Tuple[float, float]) -> GeometryResult:
        """To'g'ri chiziq tenglamasi y = mx + b"""
        result = GeometryResult(operation="line_equation")

        if self._sympy_ok:
            try:
                x1, y1 = Rational(p1[0]), Rational(p1[1])
                x2, y2 = Rational(p2[0]), Rational(p2[1])

                dx = x2 - x1
                if dx == 0:
                    result.exact_values["type"] = "vertical"
                    result.exact_values["x"] = x1
                    result.latex_repr["equation"] = f"x = {latex(x1)}"
                else:
                    m = simplify((y2 - y1) / dx)
                    b = simplify(y1 - m * x1)

                    result.exact_values["slope"] = m
                    result.exact_values["intercept"] = b
                    result.numeric_values["slope"] = float(N(m))
                    result.numeric_values["intercept"] = float(N(b))

                    if b >= 0:
                        result.latex_repr["equation"] = f"y = {latex(m)}x + {latex(b)}"
                    else:
                        result.latex_repr["equation"] = f"y = {latex(m)}x - {latex(Abs(b))}"

            except Exception as e:
                result.errors.append(str(e))

        return result

    def triangle_angles_from_sides(self, a: float, b: float, c: float) -> GeometryResult:
        """Uchburchak burchaklarini tomonlardan hisoblash"""
        result = GeometryResult(operation="triangle_angles")

        try:
            cos_A = (b**2 + c**2 - a**2) / (2 * b * c)
            cos_B = (a**2 + c**2 - b**2) / (2 * a * c)
            cos_C = (a**2 + b**2 - c**2) / (2 * a * b)

            if abs(cos_A) <= 1 and abs(cos_B) <= 1 and abs(cos_C) <= 1:
                angle_A = math.degrees(math.acos(cos_A))
                angle_B = math.degrees(math.acos(cos_B))
                angle_C = math.degrees(math.acos(cos_C))

                result.numeric_values["angle_A"] = round(angle_A, 1)
                result.numeric_values["angle_B"] = round(angle_B, 1)
                result.numeric_values["angle_C"] = round(angle_C, 1)
                result.numeric_values["sum"] = round(angle_A + angle_B + angle_C, 1)

                if self._sympy_ok:
                    try:
                        result.exact_values["cos_A"] = Rational(cos_A).limit_denominator(1000)
                        result.exact_values["cos_B"] = Rational(cos_B).limit_denominator(1000)
                        result.exact_values["cos_C"] = Rational(cos_C).limit_denominator(1000)
                    except Exception:
                        pass
            else:
                result.is_valid = False
                result.errors.append("Triangle inequality not satisfied")

        except Exception as e:
            result.is_valid = False
            result.errors.append(str(e))

        return result

    def validate_triangle_sides(self, a: float, b: float, c: float) -> bool:
        """Uchburchak tomonlar shartini tekshirish"""
        return (a + b > c) and (a + c > b) and (b + c > a)

    def heron_formula(self, a: float, b: float, c: float) -> GeometryResult:
        """Geron formulasi bilan uchburchak yuzasi"""
        result = GeometryResult(operation="heron")

        if not self.validate_triangle_sides(a, b, c):
            result.is_valid = False
            result.errors.append("Invalid triangle sides")
            return result

        if self._sympy_ok:
            try:
                a_r, b_r, c_r = Rational(a), Rational(b), Rational(c)
                s = simplify((a_r + b_r + c_r) / 2)
                area_squared = simplify(s * (s - a_r) * (s - b_r) * (s - c_r))

                if area_squared >= 0:
                    area = simplify(sqrt(area_squared))
                    result.exact_values["semi_perimeter"] = s
                    result.exact_values["area"] = area
                    result.numeric_values["semi_perimeter"] = float(N(s))
                    result.numeric_values["area"] = float(N(area))
                    result.latex_repr["formula"] = f"\\sqrt{{{latex(s)} \\cdot {latex(s-a_r)} \\cdot {latex(s-b_r)} \\cdot {latex(s-c_r)}}}"
                else:
                    result.is_valid = False
                    result.errors.append("Negative area squared")

            except Exception as e:
                result.errors.append(str(e))
        else:
            s = (a + b + c) / 2
            area = math.sqrt(s * (s - a) * (s - b) * (s - c))
            result.numeric_values["area"] = area

        return result


geometry_math = GeometryMath()
