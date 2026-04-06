"""
services/geometry_problem_engine.py — GEOMETRY PROBLEM GENERATOR + DIAGRAM ENGINE

Pipeline: Template → NumPy coords → SymPy validate → Question text → DiagramSpec → Render

Supported:
- Triangle (isosceles, equilateral, right, acute, obtuse)
- Angles (find x, sum of angles, complementary, supplementary)
- Parallel lines (alternate interior, corresponding, co-interior)
- Circle (radius, chord, arc, tangent)
- Coordinate geometry (distance, midpoint, slope, line equation)
- Pythagorean theorem (find hypotenuse, find leg)
- Midpoint and distance formulas
- Multi-step problems (angle + length)

Style: white background, black lines, clean academic, print-friendly.
"""

from __future__ import annotations

import math
import random
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import numpy as np

from services.render_specs import (
    DiagramSpec, DiagramSpecBuilder, DiagramType, CanvasSpec, StyleConfig,
    StyleProfile, PoolType, TriangleElement, CircleElement, RectangleElement,
    SegmentElement, PointElement, LabelElement, AngleMarkerElement,
    PerpendicularElement, TickMarkElement, ArcElement, UnknownMarker
)
from services.geometry_math import geometry_math, GeometryResult
from services.symbolic_engine import symbolic_engine
from services.distractor_engine import distractor_engine

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class GeometryProblem:
    """To'liq geometrik masala"""
    problem_id: str
    topic: str
    template_id: str
    difficulty: str
    grade_range: Tuple[int, int]
    question_text: str
    correct_answer: Any
    answer_type: str
    options: Dict[str, Any]
    correct_label: str
    diagram_spec: Optional[DiagramSpec]
    solution_steps: List[str]
    derived_values: Dict[str, Any]
    validation: Dict[str, Any]
    diagram_hints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "problem_id": self.problem_id,
            "topic": self.topic,
            "template_id": self.template_id,
            "difficulty": self.difficulty,
            "question_text": self.question_text,
            "correct_answer": str(self.correct_answer),
            "answer_type": self.answer_type,
            "options": {k: str(v) for k, v in self.options.items()},
            "correct_label": self.correct_label,
            "solution_steps": self.solution_steps,
            "derived_values": {k: str(v) for k, v in self.derived_values.items()},
            "validation": self.validation,
        }


@dataclass
class GeometryValidationResult:
    """Geometrik masala validatsiya natijasi"""
    is_valid: bool = True
    is_degenerate: bool = False
    has_unique_answer: bool = True
    is_computationally_correct: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# COORDINATE GENERATORS
# =============================================================================

class GeometryCoordinates:
    """NumPy asosida deterministik geometrik koordinatalar"""

    @staticmethod
    def triangle_vertices(sides: Tuple[float, float, float],
                          rotation_deg: float = 0,
                          translate: Tuple[float, float] = (0, 0)) -> List[Tuple[float, float]]:
        """
        Uchburchak nuqtalarini yaratish.
        sides: (a, b, c) where a=BC, b=AC, c=AB (standard notation)
        """
        a, b, c = sides
        x1, y1 = 0.0, 0.0
        x2, y2 = c, 0.0

        cos_B = (a * a + c * c - b * b) / (2 * a * c)
        cos_B = np.clip(cos_B, -1.0, 1.0)
        sin_B = math.sqrt(1.0 - cos_B * cos_B)

        x3 = a * cos_B
        y3 = a * sin_B

        pts = np.array([[x1, y1], [x2, y2], [x3, y3]])

        if abs(rotation_deg) > 0.01:
            theta = math.radians(rotation_deg)
            R = np.array([[math.cos(theta), -math.sin(theta)],
                          [math.sin(theta), math.cos(theta)]])
            centroid = pts.mean(axis=0)
            pts = (pts - centroid) @ R.T + centroid

        pts[:, 0] += translate[0]
        pts[:, 1] += translate[1]

        return [(float(pts[i, 0]), float(pts[i, 1])) for i in range(3)]

    @staticmethod
    def right_triangle_vertices(leg_a: float, leg_b: float,
                                 rotation_deg: float = 0) -> List[Tuple[float, float]]:
        """To'g'ri burchakli uchburchak"""
        pts = np.array([[0.0, 0.0], [leg_a, 0.0], [0.0, leg_b]])

        if abs(rotation_deg) > 0.01:
            theta = math.radians(rotation_deg)
            R = np.array([[math.cos(theta), -math.sin(theta)],
                          [math.sin(theta), math.cos(theta)]])
            centroid = pts.mean(axis=0)
            pts = (pts - centroid) @ R.T + centroid

        return [(float(pts[i, 0]), float(pts[i, 1])) for i in range(3)]

    @staticmethod
    def rectangle_vertices(width: float, height: float,
                           origin: Tuple[float, float] = (0, 0)) -> List[Tuple[float, float]]:
        """To'g'ri to'rtburchak"""
        ox, oy = origin
        return [(ox, oy), (ox + width, oy), (ox + width, oy + height), (ox, oy + height)]

    @staticmethod
    def circle_points(cx: float = 0, cy: float = 0, radius: float = 3,
                      n_points: int = 36) -> List[Tuple[float, float]]:
        """Aylana nuqtalari"""
        angles = np.linspace(0, 2 * math.pi, n_points, endpoint=False)
        return [(cx + radius * math.cos(a), cy + radius * math.sin(a)) for a in angles]

    @staticmethod
    def parallel_lines_with_transversal(
        line_y1: float = 2, line_y2: float = 5,
        transversal_angle: float = 60,
        x_range: Tuple[float, float] = (-1, 8)
    ) -> Dict[str, Any]:
        """Parallel chiziqlar va kesuvchi"""
        angle_rad = math.radians(transversal_angle)
        slope = math.tan(angle_rad)

        x0 = (x_range[0] + x_range[1]) / 2
        t_y1 = line_y1 + slope * (x_range[0] - x0)
        t_y2 = line_y2 + slope * (x_range[1] - x0)

        return {
            "line1": ((x_range[0], line_y1), (x_range[1], line_y1)),
            "line2": ((x_range[0], line_y2), (x_range[1], line_y2)),
            "transversal": ((x_range[0], t_y1), (x_range[1], t_y2)),
            "slope": slope,
            "angle": transversal_angle,
        }

    @staticmethod
    def coordinate_integer_points(count: int = 2,
                                   x_range: Tuple[int, int] = (-5, 5),
                                   y_range: Tuple[int, int] = (-5, 5),
                                   seed: Optional[int] = None) -> List[Tuple[int, int]]:
        """Butun sonli koordinata nuqtalari"""
        rng = np.random.RandomState(seed)
        points = set()
        while len(points) < count:
            x = rng.randint(x_range[0], x_range[1] + 1)
            y = rng.randint(y_range[0], y_range[1] + 1)
            points.add((int(x), int(y)))
        return list(points)


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================

GEOMETRY_TEMPLATES = {
    # ── TRIANGLES ──
    "tri_perimeter_all_sides": {
        "topic": "triangle_perimeter",
        "description": "Barcha tomonlari berilgan, perimetrni toping",
        "difficulty": "oson",
        "grade_range": (3, 6),
        "requires_diagram": True,
    },
    "tri_perimeter_one_unknown": {
        "topic": "triangle_perimeter",
        "description": "Bitta tomon noma'lum",
        "difficulty": "oson",
        "grade_range": (3, 6),
        "requires_diagram": True,
    },
    "tri_area_base_height": {
        "topic": "triangle_area",
        "description": "Asos va balandlik bilan yuza",
        "difficulty": "oson",
        "grade_range": (4, 7),
        "requires_diagram": True,
    },
    "tri_area_heron": {
        "topic": "triangle_area",
        "description": "Geron formulasi",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },
    "tri_area_right": {
        "topic": "triangle_area",
        "description": "To'g'ri burchakli uchburchak yuzasi",
        "difficulty": "oson",
        "grade_range": (4, 7),
        "requires_diagram": True,
    },
    "tri_isosceles_base": {
        "topic": "triangle_properties",
        "description": "Teng yonli uchburchak asosi",
        "difficulty": "o'rta",
        "grade_range": (5, 8),
        "requires_diagram": True,
    },
    "tri_equilateral_area": {
        "topic": "triangle_area",
        "description": "Teng tomonli uchburchak yuzasi",
        "difficulty": "o'rta",
        "grade_range": (5, 8),
        "requires_diagram": True,
    },

    # ── ANGLES ──
    "angle_triangle_sum": {
        "topic": "angle_finding",
        "description": "Uchburchak burchaklari yig'indisi",
        "difficulty": "oson",
        "grade_range": (4, 7),
        "requires_diagram": True,
    },
    "angle_linear_pair": {
        "topic": "angle_finding",
        "description": "Chiziqli juft burchak",
        "difficulty": "oson",
        "grade_range": (4, 6),
        "requires_diagram": False,
    },
    "angle_complementary": {
        "topic": "angle_finding",
        "description": "To'ldiruvchi burchaklar",
        "difficulty": "oson",
        "grade_range": (4, 6),
        "requires_diagram": False,
    },
    "angle_exterior_triangle": {
        "topic": "angle_finding",
        "description": "Tashqi burchak teoremasi",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },

    # ── PARALLEL LINES ──
    "parallel_alt_interior": {
        "topic": "parallel_lines",
        "description": "Ichki almashgan burchaklar",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },
    "parallel_corresponding": {
        "topic": "parallel_lines",
        "description": "Mos burchaklar",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },
    "parallel_co_interior": {
        "topic": "parallel_lines",
        "description": "Ichki bir tomonlama burchaklar",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },

    # ── CIRCLE ──
    "circle_radius_from_diameter": {
        "topic": "circle_radius",
        "description": "Diametrdan radius",
        "difficulty": "oson",
        "grade_range": (3, 5),
        "requires_diagram": True,
    },
    "circle_circumference": {
        "topic": "circle_circumference",
        "description": "Aylana uzunligi",
        "difficulty": "o'rta",
        "grade_range": (5, 8),
        "requires_diagram": True,
    },
    "circle_area": {
        "topic": "circle_area",
        "description": "Doira yuzasi",
        "difficulty": "o'rta",
        "grade_range": (5, 8),
        "requires_diagram": True,
    },

    # ── PYTHAGOREAN ──
    "pythagorean_hypotenuse": {
        "topic": "pythagorean",
        "description": "Gipotenuzani topish",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },
    "pythagorean_leg": {
        "topic": "pythagorean",
        "description": "Katekni topish",
        "difficulty": "qiyin",
        "grade_range": (7, 10),
        "requires_diagram": True,
    },

    # ── COORDINATE GEOMETRY ──
    "coord_distance": {
        "topic": "coordinate_distance",
        "description": "Ikki nuqta orasidagi masofa",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },
    "coord_midpoint": {
        "topic": "coordinate_midpoint",
        "description": "O'rta nuqta",
        "difficulty": "o'rta",
        "grade_range": (6, 9),
        "requires_diagram": True,
    },
    "coord_slope": {
        "topic": "coordinate_slope",
        "description": "To'g'ri chiziq egilishi",
        "difficulty": "o'rta",
        "grade_range": (7, 10),
        "requires_diagram": True,
    },

    # ── RECTANGLE / SQUARE ──
    "rect_area_wh": {
        "topic": "rectangle_area",
        "description": "Bo'yi va eni bilan yuza",
        "difficulty": "oson",
        "grade_range": (3, 5),
        "requires_diagram": True,
    },
    "rect_perimeter": {
        "topic": "rectangle_perimeter",
        "description": "To'g'ri to'rtburchak perimetri",
        "difficulty": "oson",
        "grade_range": (3, 5),
        "requires_diagram": True,
    },
    "square_area_from_perimeter": {
        "topic": "square_area",
        "description": "Perimetrdan kvadrat yuzasi",
        "difficulty": "o'rta",
        "grade_range": (4, 7),
        "requires_diagram": True,
    },
}


# =============================================================================
# PROBLEM GENERATORS
# =============================================================================

class GeometryProblemGenerator:
    """
    Geometrik masalalar generatori.

    Pipeline:
    1. Template tanlash
    2. NumPy orqali parametrlar
    3. SymPy validation
    4. Question text
    5. DiagramSpec
    6. Options + distractors
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)
        self.coords = GeometryCoordinates()

    def generate(self, template_id: str, difficulty: str = None,
                 grade: int = 5) -> Optional[GeometryProblem]:
        """Bitta geometrik masala generatsiya qilish"""
        template = GEOMETRY_TEMPLATES.get(template_id)
        if not template:
            logger.warning(f"Unknown template: {template_id}")
            return None

        if difficulty is None:
            difficulty = template["difficulty"]

        if not (template["grade_range"][0] <= grade <= template["grade_range"][1]):
            return None

        generator_name = f"_gen_{template_id}"
        if hasattr(self, generator_name):
            return getattr(self, generator_name)(difficulty, grade)

        return None

    def generate_random(self, difficulty: str = None, grade: int = 5,
                        topic_filter: Optional[str] = None) -> Optional[GeometryProblem]:
        """Random geometrik masala"""
        suitable = []
        for tid, tmpl in GEOMETRY_TEMPLATES.items():
            if tmpl["grade_range"][0] <= grade <= tmpl["grade_range"][1]:
                if difficulty is None or tmpl["difficulty"] == difficulty:
                    if topic_filter is None or tmpl["topic"] == topic_filter:
                        if hasattr(self, f"_gen_{tid}"):
                            suitable.append(tid)

        if not suitable:
            for tid, tmpl in GEOMETRY_TEMPLATES.items():
                if tmpl["grade_range"][0] <= grade <= tmpl["grade_range"][1]:
                    if hasattr(self, f"_gen_{tid}"):
                        suitable.append(tid)

        self.rng.shuffle(suitable)
        for tid in suitable[:10]:
            result = self.generate(tid, difficulty, grade)
            if result:
                return result
        return None

    def generate_batch(self, count: int, difficulty: str = None,
                       grade: int = 5) -> List[GeometryProblem]:
        """Bir nechta geometrik masala"""
        problems = []
        used_ids = set()

        for _ in range(count * 3):
            if len(problems) >= count:
                break
            p = self.generate_random(difficulty, grade)
            if p and p.problem_id not in used_ids:
                problems.append(p)
                used_ids.add(p.problem_id)

        return problems[:count]

    # ── TRIANGLE GENERATORS ──

    def _gen_tri_perimeter_all_sides(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        sides = sorted([self.rng.randint(3, 12) for _ in range(3)])

        if not geometry_math.validate_triangle_sides(*sides):
            return None

        perimeter = sum(sides)
        rotation = self.rng.uniform(-15, 15)

        labels = ["A", "B", "C"]
        vertices = self.coords.triangle_vertices(tuple(sides), rotation_deg=rotation)

        question_text = (
            f"Uchburchakning tomonlari {sides[0]} sm, {sides[1]} sm, {sides[2]} sm. "
            f"Perimetri necha sm?"
        )

        dist_result = geometry_math.distance(vertices[0], vertices[1])
        solution_steps = [
            f"P = a + b + c",
            f"P = {sides[0]} + {sides[1]} + {sides[2]}",
            f"P = {perimeter} sm",
        ]

        options_result = distractor_engine.generate_for_integer(perimeter, difficulty=difficulty)

        return self._build_problem(
            template_id="tri_perimeter_all_sides",
            topic="triangle_perimeter",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=perimeter,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"a": sides[0], "b": sides[1], "c": sides[2], "P": perimeter},
            diagram_spec=self._build_triangle_diagram(vertices, labels, sides),
        )

    def _gen_tri_perimeter_one_unknown(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        known = sorted([self.rng.randint(4, 10) for _ in range(2)])
        perimeter = sum(known) + self.rng.randint(5, 15)
        unknown = perimeter - sum(known)

        if not geometry_math.validate_triangle_sides(known[0], known[1], unknown):
            return None

        rotation = self.rng.uniform(-15, 15)
        labels = ["A", "B", "C"]
        all_sides = sorted([known[0], known[1], unknown])
        vertices = self.coords.triangle_vertices(tuple(all_sides), rotation_deg=rotation)

        question_text = (
            f"Uchburchakning ikki tomoni {known[0]} sm va {known[1]} sm, "
            f"perimetri {perimeter} sm. Uchinchi tomon necha sm?"
        )

        solution_steps = [
            f"c = P - a - b",
            f"c = {perimeter} - {known[0]} - {known[1]}",
            f"c = {unknown} sm",
        ]

        options_result = distractor_engine.generate_for_integer(unknown, difficulty=difficulty)

        return self._build_problem(
            template_id="tri_perimeter_one_unknown",
            topic="triangle_perimeter",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=unknown,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"a": known[0], "b": known[1], "P": perimeter, "c": unknown},
            diagram_spec=self._build_triangle_diagram(
                vertices, labels,
                side_labels=[str(known[0]), "?", str(known[1])]
            ),
        )

    def _gen_tri_area_base_height(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        base = self.rng.randint(4, 14)
        height = self.rng.randint(3, 12)
        area = 0.5 * base * height

        vertices = self.coords.right_triangle_vertices(base, height,
                                                        rotation_deg=self.rng.uniform(-10, 10))
        labels = ["A", "B", "C"]

        question_text = (
            f"Uchburchakning asosi {base} sm, balandligi {height} sm. "
            f"Yuzasi necha sm²?"
        )

        solution_steps = [
            f"S = (a × h) / 2",
            f"S = ({base} × {height}) / 2",
            f"S = {area} sm²",
        ]

        options_result = distractor_engine.generate_for_integer(int(area), difficulty=difficulty)

        return self._build_problem(
            template_id="tri_area_base_height",
            topic="triangle_area",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=int(area),
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"base": base, "height": height, "area": area},
            diagram_spec=self._build_triangle_with_height(vertices, labels, base, height),
        )

    def _gen_tri_area_heron(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        sides = sorted([self.rng.randint(5, 10) for _ in range(3)])
        a, b, c = sides

        if not geometry_math.validate_triangle_sides(a, b, c):
            return None

        heron_result = geometry_math.heron_formula(a, b, c)
        if not heron_result.is_valid:
            return None

        area = heron_result.numeric_values.get("area", 0)
        area_rounded = round(area, 1)

        rotation = self.rng.uniform(-15, 15)
        labels = ["A", "B", "C"]
        vertices = self.coords.triangle_vertices((a, b, c), rotation_deg=rotation)

        question_text = (
            f"Tomonlari {a} sm, {b} sm, {c} sm bo'lgan uchburchakning "
            f"yuzasini toping. (Geron formulasi)"
        )

        s = (a + b + c) / 2
        solution_steps = [
            f"s = (a + b + c) / 2 = ({a} + {b} + {c}) / 2 = {s}",
            f"S = √(s(s-a)(s-b)(s-c))",
            f"S = √({s} × {s-a} × {s-b} × {s-c})",
            f"S ≈ {area_rounded} sm²",
        ]

        options_result = distractor_engine.generate_for_integer(int(area_rounded), difficulty=difficulty)

        return self._build_problem(
            template_id="tri_area_heron",
            topic="triangle_area",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=int(area_rounded),
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"a": a, "b": b, "c": c, "s": s, "area": area_rounded},
            diagram_spec=self._build_triangle_diagram(vertices, labels,
                                                       side_labels=[str(a), str(b), str(c)]),
        )

    # ── ANGLE GENERATORS ──

    def _gen_angle_triangle_sum(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        angle_a = self.rng.randint(25, 80)
        angle_b = self.rng.randint(25, 80)

        if angle_a + angle_b >= 155:
            angle_b = 155 - angle_a

        angle_c = 180 - angle_a - angle_b

        if angle_c < 20 or angle_c > 130:
            return None

        rotation = self.rng.uniform(-15, 15)
        labels = ["A", "B", "C"]
        sides = (5, 5, 5)
        vertices = self.coords.triangle_vertices(sides, rotation_deg=rotation)

        question_text = (
            f"Uchburchakning ikki burchagi {angle_a}° va {angle_b}°. "
            f"Uchinchi burchak necha gradus?"
        )

        solution_steps = [
            f"∠A + ∠B + ∠C = 180°",
            f"{angle_a}° + {angle_b}° + ∠C = 180°",
            f"∠C = 180° - {angle_a}° - {angle_b}° = {angle_c}°",
        ]

        options_result = distractor_engine.generate_for_integer(angle_c, difficulty=difficulty)

        return self._build_problem(
            template_id="angle_triangle_sum",
            topic="angle_finding",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=angle_c,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"A": angle_a, "B": angle_b, "C": angle_c},
            diagram_spec=self._build_triangle_diagram(
                vertices, labels,
                angle_labels=[f"{angle_a}°", f"{angle_b}°", "?"]
            ),
        )

    def _gen_angle_exterior_triangle(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        int_angle1 = self.rng.randint(30, 70)
        int_angle2 = self.rng.randint(30, 70)
        exterior = int_angle1 + int_angle2

        question_text = (
            f"Uchburchakning ichki burchaklaridan ikkitasi {int_angle1}° va {int_angle2}°. "
            f"Ularga qarama-qarshi tashqi burchak necha gradus?"
        )

        solution_steps = [
            f"Tashqi burchak = qarama-qarshi ichki burchaklar yig'indisi",
            f"= {int_angle1}° + {int_angle2}°",
            f"= {exterior}°",
        ]

        options_result = distractor_engine.generate_for_integer(exterior, difficulty=difficulty)

        return self._build_problem(
            template_id="angle_exterior_triangle",
            topic="angle_finding",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=exterior,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"int1": int_angle1, "int2": int_angle2, "exterior": exterior},
            diagram_spec=None,
        )

    # ── PARALLEL LINES ──

    def _gen_parallel_alt_interior(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        angle = self.rng.randint(30, 80)

        question_text = (
            f"Parallel chiziqlarni kesuvchi bilan hosil bo'lgan "
            f"ichki almashgan burchaklardan biri {angle}°. Ikkinchisi necha gradus?"
        )

        solution_steps = [
            f"Ichki almashgan burchaklar teng bo'ladi",
            f"Javob: {angle}°",
        ]

        options_result = distractor_engine.generate_for_integer(angle, difficulty=difficulty)

        parallel_data = self.coords.parallel_lines_with_transversal(
            line_y1=2, line_y2=5, transversal_angle=50
        )

        return self._build_problem(
            template_id="parallel_alt_interior",
            topic="parallel_lines",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=angle,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"angle": angle},
            diagram_spec=self._build_parallel_lines_diagram(parallel_data, angle),
        )

    # ── PYTHAGOREAN ──

    def _gen_pythagorean_hypotenuse(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        pythagorean_triples = [
            (3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25),
            (6, 8, 10), (9, 12, 15), (10, 24, 26), (12, 16, 20),
        ]

        triple = self.rng.choice(pythagorean_triples)
        a, b, c = triple

        vertices = self.coords.right_triangle_vertices(a, b,
                                                        rotation_deg=self.rng.uniform(-10, 10))
        labels = ["A", "B", "C"]

        question_text = (
            f"To'g'ri burchakli uchburchakning katetlari {a} sm va {b} sm. "
            f"Gipotenuzasi necha sm?"
        )

        result = geometry_math.verify_pythagorean(a, b, c)

        solution_steps = [
            f"c² = a² + b²",
            f"c² = {a}² + {b}² = {a*a} + {b*b} = {a*a + b*b}",
            f"c = √{a*a + b*b} = {c} sm",
        ]

        options_result = distractor_engine.generate_for_integer(c, difficulty=difficulty)

        return self._build_problem(
            template_id="pythagorean_hypotenuse",
            topic="pythagorean",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=c,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"a": a, "b": b, "c": c},
            diagram_spec=self._build_triangle_diagram(
                vertices, labels,
                side_labels=[str(a), str(c), str(b)],
                show_right_angle=1
            ),
        )

    # ── COORDINATE GEOMETRY ──

    def _gen_coord_distance(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        points = self.coords.coordinate_integer_points(
            count=2, x_range=(-3, 6), y_range=(-3, 6)
        )
        p1, p2 = points[0], points[1]

        dist_result = geometry_math.distance(p1, p2)
        dist = dist_result.numeric_values.get("distance", 0)

        if dist < 2 or dist > 15:
            return self._gen_coord_distance(difficulty, grade)

        dist_int = int(round(dist))
        is_perfect = abs(dist - dist_int) < 0.001

        if is_perfect:
            answer = dist_int
            answer_type = "integer"
        else:
            answer = round(dist, 1)
            answer_type = "float"

        question_text = (
            f"({p1[0]}, {p1[1]}) va ({p2[0]}, {p2[1]}) nuqtalar orasidagi "
            f"masofani toping."
        )

        solution_steps = [
            f"d = √((x₂-x₁)² + (y₂-y₁)²)",
            f"d = √(({p2[0]}-{p1[0]})² + ({p2[1]}-{p1[1]})²)",
            f"d = √({(p2[0]-p1[0])**2} + {(p2[1]-p1[1])**2})",
            f"d = √{(p2[0]-p1[0])**2 + (p2[1]-p1[1])**2} = {answer}",
        ]

        options_result = distractor_engine.generate_for_integer(
            int(answer) if is_perfect else int(answer), difficulty=difficulty
        )

        return self._build_problem(
            template_id="coord_distance",
            topic="coordinate_distance",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=answer,
            answer_type=answer_type,
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"p1": p1, "p2": p2, "distance": answer},
            diagram_spec=self._build_coordinate_diagram([p1, p2]),
        )

    # ── CIRCLE ──

    def _gen_circle_circumference(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        radius = self.rng.randint(3, 10)
        circumference = round(2 * 3.14 * radius, 1)
        circumference_int = round(circumference)

        question_text = (
            f"Aylananing radiusi {radius} sm. Aylana uzunligi necha sm? (π ≈ 3.14)"
        )

        solution_steps = [
            f"L = 2πr",
            f"L = 2 × 3.14 × {radius}",
            f"L ≈ {circumference} sm",
        ]

        options_result = distractor_engine.generate_for_integer(circumference_int, difficulty=difficulty)

        return self._build_problem(
            template_id="circle_circumference",
            topic="circle_circumference",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=circumference_int,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"radius": radius, "circumference": circumference},
            diagram_spec=self._build_circle_diagram(radius, show_radius=True),
        )

    def _gen_circle_area(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        radius = self.rng.randint(3, 8)
        area = round(3.14 * radius * radius, 1)
        area_int = round(area)

        question_text = (
            f"Doira radiusi {radius} sm. Yuzasi necha sm²? (π ≈ 3.14)"
        )

        solution_steps = [
            f"S = πr²",
            f"S = 3.14 × {radius}²",
            f"S ≈ {area} sm²",
        ]

        options_result = distractor_engine.generate_for_integer(area_int, difficulty=difficulty)

        return self._build_problem(
            template_id="circle_area",
            topic="circle_area",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=area_int,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"radius": radius, "area": area},
            diagram_spec=self._build_circle_diagram(radius, show_radius=True),
        )

    # ── RECTANGLE ──

    def _gen_rect_area_wh(self, difficulty: str, grade: int) -> Optional[GeometryProblem]:
        w = self.rng.randint(3, 12)
        h = self.rng.randint(2, 10)
        area = w * h

        question_text = (
            f"To'g'ri to'rtburchakning bo'yi {w} sm, eni {h} sm. Yuzasi necha sm²?"
        )

        solution_steps = [
            f"S = a × b",
            f"S = {w} × {h}",
            f"S = {area} sm²",
        ]

        options_result = distractor_engine.generate_for_integer(area, difficulty=difficulty)

        rect_spec = DiagramSpecBuilder(DiagramType.GEOMETRY)
        rect_spec.with_canvas(w + 3, h + 3, equal_aspect=True)
        rect_spec.add_rectangle(1, 1, w, h, labels=["A", "B", "C", "D"])
        rect_spec.add_label(str(w), (1 + w/2), 0.5)
        rect_spec.add_label(str(h), 0.5, (1 + h/2))

        return self._build_problem(
            template_id="rect_area_wh",
            topic="rectangle_area",
            difficulty=difficulty,
            grade=grade,
            question_text=question_text,
            correct_answer=area,
            answer_type="integer",
            options=options_result.options,
            correct_label=options_result.correct_label,
            solution_steps=solution_steps,
            derived_values={"width": w, "height": h, "area": area},
            diagram_spec=rect_spec.build(),
        )

    # ── BUILD HELPERS ──

    def _build_problem(self, **kwargs) -> GeometryProblem:
        """GeometryProblem yaratish"""
        problem_id = f"geo_{hashlib.md5(str(random.random()).encode()).hexdigest()[:8]}"

        validation = self._validate_problem(kwargs)

        return GeometryProblem(
            problem_id=problem_id,
            topic=kwargs.get("topic", ""),
            template_id=kwargs.get("template_id", ""),
            difficulty=kwargs.get("difficulty", "oson"),
            grade_range=GEOMETRY_TEMPLATES.get(kwargs.get("template_id", ""), {}).get("grade_range", (3, 10)),
            question_text=kwargs.get("question_text", ""),
            correct_answer=kwargs.get("correct_answer", 0),
            answer_type=kwargs.get("answer_type", "integer"),
            options=kwargs.get("options", {}),
            correct_label=kwargs.get("correct_label", "A"),
            diagram_spec=kwargs.get("diagram_spec"),
            solution_steps=kwargs.get("solution_steps", []),
            derived_values=kwargs.get("derived_values", {}),
            validation=validation,
        )

    def _validate_problem(self, params: Dict) -> Dict[str, Any]:
        """Masala validatsiyasi"""
        result = {
            "is_valid": True,
            "has_unique_answer": True,
            "is_computationally_correct": True,
            "errors": [],
            "warnings": [],
        }

        correct = params.get("correct_answer")
        if correct is None or correct <= 0:
            result["is_valid"] = False
            result["errors"].append("Invalid answer")

        options = params.get("options", {})
        if len(options) != 4:
            result["warnings"].append(f"Options count: {len(options)}")

        if correct and correct not in options.values():
            if isinstance(correct, float):
                if not any(abs(v - correct) < 0.5 for v in options.values()):
                    result["is_valid"] = False
                    result["errors"].append("Correct answer not in options")
            else:
                result["is_valid"] = False
                result["errors"].append("Correct answer not in options")

        return result

    # ── DIAGRAM BUILDERS ──

    def _build_triangle_diagram(self, vertices, labels,
                                 side_labels=None, angle_labels=None,
                                 show_right_angle=-1) -> DiagramSpec:
        """Uchburchak DiagramSpec"""
        v = vertices
        xs = [p[0] for p in v]
        ys = [p[1] for p in v]
        pad = 1.5

        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(
            max(xs) - min(xs) + 2 * pad,
            max(ys) - min(ys) + 2 * pad,
            equal_aspect=True
        )

        builder.add_triangle(v[0], v[1], v[2], labels=tuple(labels[:3]))

        if side_labels:
            pairs = [(v[0], v[1]), (v[1], v[2]), (v[0], v[2])]
            for i, lbl in enumerate(side_labels):
                if lbl and i < 3:
                    builder.add_segment(pairs[i][0][0], pairs[i][0][1],
                                        pairs[i][1][0], pairs[i][1][1], label=lbl)

        if angle_labels:
            for i, lbl in enumerate(angle_labels):
                if lbl and lbl != "?" and i < 3:
                    vx = v[i]
                    p1 = v[(i + 1) % 3]
                    p2 = v[(i + 2) % 3]
                    builder.add_angle_marker(vx, p1, p2, label=lbl)

        if show_right_angle >= 0:
            vx = v[show_right_angle]
            p1 = v[(show_right_angle + 1) % 3]
            p2 = v[(show_right_angle + 2) % 3]
            builder.add_perpendicular(vx, p1, p2)

        return builder.build()

    def _build_triangle_with_height(self, vertices, labels, base, height) -> DiagramSpec:
        """Balandlik bilan uchburchak"""
        v = vertices
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(base + 3, height + 3, equal_aspect=True)
        builder.add_triangle(v[0], v[1], v[2], labels=tuple(labels[:3]))

        base_mid = ((v[0][0] + v[1][0]) / 2, (v[0][1] + v[1][1]) / 2)
        builder.add_segment(base_mid[0], base_mid[1], v[2][0], v[2][1],
                           style="dashed", label=f"h={height}")
        builder.add_label(f"a={base}", (v[0][0] + v[1][0]) / 2, v[0][1] - 0.4)

        return builder.build()

    def _build_circle_diagram(self, radius, show_radius=True) -> DiagramSpec:
        """Aylana DiagramSpec"""
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(radius * 3, radius * 3, equal_aspect=True)
        builder.add_circle(0, 0, radius, center_label="O", show_radius=show_radius,
                          radius_label="r")
        builder.add_point(0, 0, label="O")

        return builder.build()

    def _build_parallel_lines_diagram(self, parallel_data, angle) -> DiagramSpec:
        """Parallel chiziqlar DiagramSpec"""
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(10, 8, equal_aspect=True)

        l1 = parallel_data["line1"]
        l2 = parallel_data["line2"]
        t = parallel_data["transversal"]

        builder.add_segment(l1[0][0], l1[0][1], l1[1][0], l1[1][1])
        builder.add_segment(l2[0][0], l2[0][1], l2[1][0], l2[1][1])
        builder.add_segment(t[0][0], t[0][1], t[1][0], t[1][1])

        return builder.build()

    def _build_coordinate_diagram(self, points) -> DiagramSpec:
        """Koordinata diagram"""
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(12, 12, equal_aspect=True)

        for p in points:
            builder.add_point(p[0], p[1], label=f"({p[0]},{p[1]})")

        if len(points) >= 2:
            builder.add_segment(points[0][0], points[0][1],
                               points[1][0], points[1][1])

        return builder.build()


geometry_problem_engine = GeometryProblemGenerator()
