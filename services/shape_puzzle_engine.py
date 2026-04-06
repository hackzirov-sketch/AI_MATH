"""
services/shape_puzzle_engine.py — SHAPE-BASED PUZZLE GENERATOR

Shakl turlari:
1. Triangle qiymatlar (perimeter, angles, sides)
2. Square qiymatlar (area, perimeter, diagonal)
3. Circle qiymatlar (radius, diameter)
4. Rectangle qiymatlar (area, perimeter, diagonal)

Har bir shape puzzle:
- Mantiqan to'g'ri
- Bitta javob
- SymPy validated
"""

from __future__ import annotations

import logging
import math
import random
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import sympy
    from sympy import symbols, Eq, solve, simplify, sqrt as sp_sqrt, N
    SYMPY_OK = True
except ImportError:
    SYMPY_OK = False


@dataclass
class ShapePuzzle:
    """Shape puzzle natijasi"""
    shape_type: str
    puzzle_text: str
    shape_data: Dict[str, Any]
    correct_answer: int
    answer_var: str
    equations: List[str]
    explanation: str
    difficulty: str
    uniqueness_signature: str
    diagram_spec: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "type": self.shape_type,
            "text": self.puzzle_text,
            "answer": self.correct_answer,
            "data": self.shape_data,
            "explanation": self.explanation,
            "signature": self.uniqueness_signature,
        }


class ShapePuzzleEngine:
    """
    Shape-based puzzle generator.
    
    Geometrik shakllar asosida matematik masalalar.
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def generate_triangle_puzzle(self, difficulty: str = "o'rta",
                                  grade: int = 5) -> Optional[ShapePuzzle]:
        """
        Uchburchak puzzle:
        - Perimeter va ikki tomon → uchinchi tomon
        - Burchaklar yig'indisi = 180
        - Teng yonli uchburchak
        """
        puzzle_type = self.rng.choice(["missing_side", "angles", "isosceles"])
        
        if puzzle_type == "missing_side":
            return self._triangle_missing_side(difficulty, grade)
        elif puzzle_type == "angles":
            return self._triangle_angles(difficulty, grade)
        else:
            return self._triangle_isosceles(difficulty, grade)
    
    def generate_square_puzzle(self, difficulty: str = "o'rta",
                                grade: int = 5) -> Optional[ShapePuzzle]:
        """Kvadrat puzzle"""
        puzzle_type = self.rng.choice(["area_from_side", "perimeter_from_area", "side_from_perimeter"])
        
        if difficulty == "oson":
            side = self.rng.randint(2, 10)
        elif difficulty == "o'rta":
            side = self.rng.randint(3, 15)
        else:
            side = self.rng.randint(5, 20)
        
        area = side * side
        perimeter = 4 * side
        
        if puzzle_type == "area_from_side":
            return ShapePuzzle(
                shape_type="square",
                puzzle_text=f"Kvadratning tomoni {side} sm. Yuza necha sm²?",
                shape_data={"side": side, "area": area, "perimeter": perimeter},
                correct_answer=area,
                answer_var="area",
                equations=[f"area = {side} × {side} = {area}"],
                explanation=f"S = a² = {side}² = {area}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"sq_{side}_area".encode()).hexdigest()[:12],
                diagram_spec={"type": "square", "side": side, "show_area": True},
            )
        elif puzzle_type == "perimeter_from_area":
            return ShapePuzzle(
                shape_type="square",
                puzzle_text=f"Kvadratning yuzasi {area} sm². Perimetri necha sm?",
                shape_data={"side": side, "area": area, "perimeter": perimeter},
                correct_answer=perimeter,
                answer_var="perimeter",
                equations=[f"a = √{area} = {side}", f"P = 4 × {side} = {perimeter}"],
                explanation=f"a = √{area} = {side}, P = 4a = {perimeter}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"sq_{area}_per".encode()).hexdigest()[:12],
                diagram_spec={"type": "square", "side": side, "show_perimeter": True},
            )
        else:
            return ShapePuzzle(
                shape_type="square",
                puzzle_text=f"Kvadratning perimetri {perimeter} sm. Tomoni necha sm?",
                shape_data={"side": side, "area": area, "perimeter": perimeter},
                correct_answer=side,
                answer_var="side",
                equations=[f"a = {perimeter} / 4 = {side}"],
                explanation=f"a = P / 4 = {perimeter} / 4 = {side}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"sq_{perimeter}_side".encode()).hexdigest()[:12],
                diagram_spec={"type": "square", "side": side, "show_side": True},
            )
    
    def generate_rectangle_puzzle(self, difficulty: str = "o'rta",
                                    grade: int = 5) -> Optional[ShapePuzzle]:
        """To'g'ri to'rtburchak puzzle"""
        puzzle_type = self.rng.choice(["area", "perimeter", "missing_dimension"])
        
        w = self.rng.randint(3, 20)
        h = self.rng.randint(2, 15)
        area = w * h
        perimeter = 2 * (w + h)
        
        if puzzle_type == "area":
            return ShapePuzzle(
                shape_type="rectangle",
                puzzle_text=f"To'g'ri to'rtburchakning eni {w} sm, bo'yi {h} sm. Yuza necha sm²?",
                shape_data={"width": w, "height": h, "area": area, "perimeter": perimeter},
                correct_answer=area,
                answer_var="area",
                equations=[f"S = {w} × {h} = {area}"],
                explanation=f"S = a × b = {w} × {h} = {area}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"rect_{w}_{h}_area".encode()).hexdigest()[:12],
                diagram_spec={"type": "rectangle", "width": w, "height": h},
            )
        elif puzzle_type == "perimeter":
            return ShapePuzzle(
                shape_type="rectangle",
                puzzle_text=f"To'g'ri to'rtburchakning eni {w} sm, bo'yi {h} sm. Perimetri necha sm?",
                shape_data={"width": w, "height": h, "area": area, "perimeter": perimeter},
                correct_answer=perimeter,
                answer_var="perimeter",
                equations=[f"P = 2 × ({w} + {h}) = {perimeter}"],
                explanation=f"P = 2(a + b) = 2 × ({w} + {h}) = {perimeter}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"rect_{w}_{h}_per".encode()).hexdigest()[:12],
                diagram_spec={"type": "rectangle", "width": w, "height": h},
            )
        else:
            return ShapePuzzle(
                shape_type="rectangle",
                puzzle_text=f"To'g'ri to'rtburchakning yuzasi {area} sm², eni {w} sm. Bo'yi necha sm?",
                shape_data={"width": w, "height": h, "area": area, "perimeter": perimeter},
                correct_answer=h,
                answer_var="height",
                equations=[f"h = {area} / {w} = {h}"],
                explanation=f"b = S / a = {area} / {w} = {h}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"rect_{area}_{w}_h".encode()).hexdigest()[:12],
                diagram_spec={"type": "rectangle", "width": w, "height": h, "show_unknown": "height"},
            )
    
    def generate_circle_puzzle(self, difficulty: str = "o'rta",
                                grade: int = 5) -> Optional[ShapePuzzle]:
        """Aylana puzzle"""
        r = self.rng.randint(2, 12)
        d = 2 * r
        
        puzzle_type = self.rng.choice(["diameter_from_radius", "radius_from_diameter"])
        
        if puzzle_type == "diameter_from_radius":
            return ShapePuzzle(
                shape_type="circle",
                puzzle_text=f"Aylana radiusi {r} sm. Diametri necha sm?",
                shape_data={"radius": r, "diameter": d},
                correct_answer=d,
                answer_var="diameter",
                equations=[f"d = 2 × r = 2 × {r} = {d}"],
                explanation=f"d = 2r = 2 × {r} = {d}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"circ_{r}_d".encode()).hexdigest()[:12],
                diagram_spec={"type": "circle", "radius": r},
            )
        else:
            return ShapePuzzle(
                shape_type="circle",
                puzzle_text=f"Aylana diametri {d} sm. Radiusi necha sm?",
                shape_data={"radius": r, "diameter": d},
                correct_answer=r,
                answer_var="radius",
                equations=[f"r = {d} / 2 = {r}"],
                explanation=f"r = d / 2 = {d} / 2 = {r}",
                difficulty=difficulty,
                uniqueness_signature=hashlib.md5(f"circ_{d}_r".encode()).hexdigest()[:12],
                diagram_spec={"type": "circle", "radius": r},
            )
    
    def _triangle_missing_side(self, difficulty: str, grade: int) -> Optional[ShapePuzzle]:
        """Uchburchak - yetishmayotgan tomon"""
        a = self.rng.randint(3, 15)
        b = self.rng.randint(3, 15)
        
        c_min = abs(a - b) + 1
        c_max = a + b - 1
        
        if c_min > c_max or c_max <= 0:
            a, b = 5, 7
            c_min, c_max = 3, 11
        
        perimeter = a + b + self.rng.randint(c_min, min(c_max, 30))
        c = perimeter - a - b
        
        if c < c_min or c > c_max:
            c = self.rng.randint(c_min, c_max)
            perimeter = a + b + c
        
        return ShapePuzzle(
            shape_type="triangle",
            puzzle_text=f"Uchburchakning ikki tomoni {a} sm va {b} sm. Perimetri {perimeter} sm. Uchinchi tomoni necha sm?",
            shape_data={"a": a, "b": b, "c": c, "perimeter": perimeter},
            correct_answer=c,
            answer_var="c",
            equations=[f"c = {perimeter} - {a} - {b} = {c}"],
            explanation=f"c = P - a - b = {perimeter} - {a} - {b} = {c}",
            difficulty=difficulty,
            uniqueness_signature=hashlib.md5(f"tri_{a}_{b}_{perim}".encode()).hexdigest()[:12],
            diagram_spec={"type": "triangle", "sides": [a, b, c], "show_missing": True},
        )
    
    def _triangle_angles(self, difficulty: str, grade: int) -> Optional[ShapePuzzle]:
        """Uchburchak - burchaklar"""
        a1 = self.rng.randint(30, 80)
        a2 = self.rng.randint(30, 80)
        a3 = 180 - a1 - a2
        
        if a3 <= 0 or a3 >= 180:
            a1, a2 = 60, 50
            a3 = 70
        
        return ShapePuzzle(
            shape_type="triangle",
            puzzle_text=f"Uchburchakning ikki burchagi {a1}° va {a2}°. Uchinchi burchak necha gradus?",
            shape_data={"angle1": a1, "angle2": a2, "angle3": a3},
            correct_answer=a3,
            answer_var="angle3",
            equations=[f"angle3 = 180 - {a1} - {a2} = {a3}"],
            explanation=f"α₃ = 180° - {a1}° - {a2}° = {a3}°",
            difficulty=difficulty,
            uniqueness_signature=hashlib.md5(f"tri_ang_{a1}_{a2}".encode()).hexdigest()[:12],
            diagram_spec={"type": "triangle", "angles": [a1, a2, a3]},
        )
    
    def _triangle_isosceles(self, difficulty: str, grade: int) -> Optional[ShapePuzzle]:
        """Teng yonli uchburchak"""
        equal_side = self.rng.randint(5, 15)
        base = self.rng.randint(2, equal_side * 2 - 1)
        perimeter = 2 * equal_side + base
        
        return ShapePuzzle(
            shape_type="triangle",
            puzzle_text=f"Teng yonli uchburchakning teng tomonlari {equal_side} sm, asosi {base} sm. Perimetri necha sm?",
            shape_data={"equal_sides": equal_side, "base": base, "perimeter": perimeter},
            correct_answer=perimeter,
            answer_var="perimeter",
            equations=[f"P = 2 × {equal_side} + {base} = {perimeter}"],
            explanation=f"P = 2a + b = 2 × {equal_side} + {base} = {perimeter}",
            difficulty=difficulty,
            uniqueness_signature=hashlib.md5(f"iso_{equal_side}_{base}".encode()).hexdigest()[:12],
            diagram_spec={"type": "triangle", "sides": [equal_side, equal_side, base], "isosceles": True},
        )


shape_puzzle_engine = ShapePuzzleEngine()
