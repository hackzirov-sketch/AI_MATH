"""
services/geometry_pool.py — GEOMETRY REGISTRY AND TEMPLATES

Geometriya mavzulari registry va template tanlash.

Mavjud topiclar:
- triangle_perimeter
- triangle_area
- rectangle_area
- square_perimeter
- circle_radius
- angle_finding
- parallel_lines
- coordinate_distance

Har topic ichida kamida 3-5 template bor.
"""

import random
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from services.render_specs import (
    GeometryRenderSpec, TriangleSpec, RectangleSpec, CircleSpec, TrapezoidSpec,
    PoolType, StylePreset, Orientation, LabelSet, UnknownMarker,
    canonical_geometry_signature, canonical_render_signature,
    QuestionSpec
)
from services.quiz_uniqueness import QuizUniquenessSession


LABEL_SETS = [
    ["A", "B", "C"],
    ["P", "Q", "R"],
    ["X", "Y", "Z"],
    ["M", "N", "K"],
    ["D", "E", "F"],
    ["U", "V", "W"],
    ["K", "L", "M"],
    ["S", "T", "U"],
]

ORIENTATIONS = [
    Orientation.LEFT_TILT,
    Orientation.RIGHT_TILT,
    Orientation.UPRIGHT,
    Orientation.WIDE,
    Orientation.NARROW,
]

UNKNOWN_MARKERS = [
    UnknownMarker.X,
    UnknownMarker.QUESTION,
    UnknownMarker.BLANK,
]


@dataclass
class GeometryTemplate:
    """Geometriya template"""
    template_id: str
    topic: str
    description: str
    params_generator: Any


class GeometryPool:
    """
    Geometriya savollarini generatsiya qilish uchun pool.
    
    Registry-based yondashuv - har topic ichida template registry.
    """
    
    def __init__(self):
        self._registry: Dict[str, List[GeometryTemplate]] = {}
        self._init_registry()
    
    def _init_registry(self):
        """Registry ni to'ldirish"""
        
        self._registry["triangle_perimeter"] = [
            GeometryTemplate(
                template_id="tri_perim_all_sides",
                topic="triangle_perimeter",
                description="Barcha tomonlari ma'lum",
                params_generator=self._gen_tri_perimeter_all_sides
            ),
            GeometryTemplate(
                template_id="tri_perim_one_unknown",
                topic="triangle_perimeter",
                description="Bitta tomoni noma'lum",
                params_generator=self._gen_tri_perimeter_one_unknown
            ),
            GeometryTemplate(
                template_id="tri_perim_isosceles",
                topic="triangle_perimeter",
                description="Teng yonli uchburchak",
                params_generator=self._gen_tri_perimeter_isosceles
            ),
            GeometryTemplate(
                template_id="tri_perim_equilateral",
                topic="triangle_perimeter",
                description="Teng tomonli uchburchak",
                params_generator=self._gen_tri_perimeter_equilateral
            ),
        ]
        
        self._registry["triangle_area"] = [
            GeometryTemplate(
                template_id="tri_area_base_height",
                topic="triangle_area",
                description="Asos va balandlik bilan",
                params_generator=self._gen_tri_area_base_height
            ),
            GeometryTemplate(
                template_id="tri_area_heron",
                topic="triangle_area",
                description="Geron formulasi bilan",
                params_generator=self._gen_tri_area_heron
            ),
            GeometryTemplate(
                template_id="tri_area_right",
                topic="triangle_area",
                description="To'g'ri burchakli uchburchak",
                params_generator=self._gen_tri_area_right
            ),
        ]
        
        self._registry["rectangle_area"] = [
            GeometryTemplate(
                template_id="rect_area_wh",
                topic="rectangle_area",
                description="Bo'yi va eni bilan",
                params_generator=self._gen_rect_area_wh
            ),
            GeometryTemplate(
                template_id="rect_area_unknown_side",
                topic="rectangle_area",
                description="Noma'lum tomon bilan",
                params_generator=self._gen_rect_area_unknown
            ),
            GeometryTemplate(
                template_id="rect_area_square",
                topic="rectangle_area",
                description="Kvadrat",
                params_generator=self._gen_rect_area_square
            ),
        ]
        
        self._registry["square_perimeter"] = [
            GeometryTemplate(
                template_id="sq_perim_side",
                topic="square_perimeter",
                description="Tomoni bilan",
                params_generator=self._gen_sq_perim_side
            ),
            GeometryTemplate(
                template_id="sq_perim_area_known",
                topic="square_perimeter",
                description="Yuzasi ma'lum",
                params_generator=self._gen_sq_perim_area
            ),
        ]
        
        self._registry["circle_radius"] = [
            GeometryTemplate(
                template_id="circ_radius_diam",
                topic="circle_radius",
                description="Diametr dan radius",
                params_generator=self._gen_circ_radius_diam
            ),
            GeometryTemplate(
                template_id="circ_radius_circumf",
                topic="circle_radius",
                description="Aylana uzunligidan",
                params_generator=self._gen_circ_radius_circumf
            ),
            GeometryTemplate(
                template_id="circ_radius_area",
                topic="circle_radius",
                description="Doira yuzasidan",
                params_generator=self._gen_circ_radius_area
            ),
        ]
        
        self._registry["angle_finding"] = [
            GeometryTemplate(
                template_id="angle_tri_sum",
                topic="angle_finding",
                description="Uchburchak burchaklar yig'indisi",
                params_generator=self._gen_angle_tri_sum
            ),
            GeometryTemplate(
                template_id="angle_linear_pair",
                topic="angle_finding",
                description="Chiziqli juft burchak",
                params_generator=self._gen_angle_linear_pair
            ),
            GeometryTemplate(
                template_id="angle_complementary",
                topic="angle_finding",
                description="To'ldiruvchi burchaklar",
                params_generator=self._gen_angle_complementary
            ),
        ]
        
        self._registry["parallel_lines"] = [
            GeometryTemplate(
                template_id="par_lines_alt_int",
                topic="parallel_lines",
                description="Ichki almashgan burchaklar",
                params_generator=self._gen_parallel_alt_int
            ),
            GeometryTemplate(
                template_id="par_lines_corresponding",
                topic="parallel_lines",
                description="Mos burchaklar",
                params_generator=self._gen_parallel_corresponding
            ),
        ]
        
        self._registry["coordinate_distance"] = [
            GeometryTemplate(
                template_id="coord_dist_formula",
                topic="coordinate_distance",
                description="Masofa formulasidan",
                params_generator=self._gen_coord_distance
            ),
            GeometryTemplate(
                template_id="coord_dist_pythagorean",
                topic="coordinate_distance",
                description="Pifagor teoremasi bilan",
                params_generator=self._gen_coord_distance_pythagorean
            ),
        ]
        
        self._registry["pythagorean"] = [
            GeometryTemplate(
                template_id="pythagorean_find_hyp",
                topic="pythagorean",
                description="Gipotenuzani topish",
                params_generator=self._gen_pythagorean_hyp
            ),
            GeometryTemplate(
                template_id="pythagorean_find_leg",
                topic="pythagorean",
                description="Katekni topish",
                params_generator=self._gen_pythagorean_leg
            ),
        ]
    
    def get_topics(self) -> List[str]:
        """Barcha mavjud topiclarni qaytaradi"""
        return list(self._registry.keys())
    
    def get_templates_for_topic(self, topic: str) -> List[GeometryTemplate]:
        """Topic uchun templatelarni qaytaradi"""
        return self._registry.get(topic, [])
    
    def generate_question(
        self,
        topic: str,
        session: QuizUniquenessSession,
        grade: int = 5,
        difficulty: str = "oson"
    ) -> Optional[QuestionSpec]:
        """Savol generatsiya qilish"""
        
        templates = self.get_templates_for_topic(topic)
        if not templates:
            return None
        
        for _ in range(10):
            template = random.choice(templates)
            
            if session.check_template_used(template.template_id):
                continue
            
            try:
                result = template.params_generator(session, grade, difficulty)
                if result:
                    return result
            except Exception:
                continue
        
        return None
    
    def generate_random_topic(self, session: QuizUniquenessSession, grade: int) -> Optional[str]:
        """Random topic tanlash (uniquenessga rioya qilib)"""
        topics = self.get_topics()
        available = [t for t in topics if session.can_use_topic(t, max_per_topic=2)]
        
        if not available:
            available = topics
        
        return random.choice(available)
    
    def _select_variations(self, session: QuizUniquenessSession) -> Tuple[List[str], Orientation, UnknownMarker]:
        """Variation tanlash (label set, orientation, unknown marker)"""
        available_labels = [ls for ls in LABEL_SETS if session.can_use_label_set([str(l) for l in ls], max_per_set=2)]
        if not available_labels:
            available_labels = LABEL_SETS
        
        label_set = random.choice(available_labels)
        session.mark_label_set("".join(label_set))
        
        available_orientations = session.get_available_orientations([o.value for o in ORIENTATIONS], max_per_orientation=2)
        if not available_orientations:
            available_orientations = [o.value for o in ORIENTATIONS]
        
        orientation = Orientation(random.choice(available_orientations))
        session.mark_orientation(orientation.value)
        
        unknown_marker = random.choice(UNKNOWN_MARKERS)
        
        return label_set, orientation, unknown_marker
    
    def _make_triangle_points(self, a: float, b: float, c: float, orientation: Orientation) -> List[Tuple[float, float]]:
        """Uchburchak nuqtalarini yaratish"""
        x1, y1 = 0, 0
        x2, y2 = c, 0
        
        cos_angle = (a*a + b*b - c*c) / (2*a*b)
        if cos_angle > 1:
            cos_angle = 1
        if cos_angle < -1:
            cos_angle = -1
        
        angle = math.acos(cos_angle)
        
        x3 = b * math.cos(angle)
        y3 = b * math.sin(angle)
        
        if orientation == Orientation.LEFT_TILT:
            x3, y3 = y3, x3
        elif orientation == Orientation.RIGHT_TILT:
            x3 = -x3
        elif orientation == Orientation.NARROW:
            y3 *= 1.5
        elif orientation == Orientation.WIDE:
            y3 *= 0.6
        
        return [(x1, y1), (x2, y2), (x3, y3)]
    
    def _gen_tri_perimeter_all_sides(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Barcha tomonlari ma'lum uchburchak perimetri"""
        sides = [random.randint(3, 10) for _ in range(3)]
        perimeter = sum(sides)
        
        question_sig = canonical_geometry_signature("triangle_perimeter", {"sides": sorted(sides)})
        if session.check_question_signature(question_sig):
            return None
        
        labels, orientation, unk_marker = self._select_variations(session)
        
        question_text = f"Teng yonli bo'lmagan uchburchakning tomonlari {sides[0]} sm, {sides[1]} sm, {sides[2]} sm. Perimetri necha sm?"
        
        options = self._make_numeric_options(perimeter, difficulty)
        correct_label = self._get_correct_label(options, perimeter)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="triangle_perimeter",
            template_id="tri_perim_all_sides",
            question_signature=question_sig,
            render_signature=canonical_render_signature(
                "triangle", orientation.value, "".join(labels), "exam_clean", "default"
            ),
            shape_type="triangle",
            side_ab=sides[0],
            side_bc=sides[1],
            side_ac=sides[2],
            perimeter=perimeter,
            measurements={"a": sides[0], "b": sides[1], "c": sides[2]},
            orientation_variant=orientation,
            label_set=LabelSet(labels[0] + labels[1] + labels[2]),
            unknown_marker=unk_marker,
            labels={"A": labels[0], "B": labels[1], "C": labels[2]},
            points=self._make_triangle_points(sides[0], sides[1], sides[2], orientation)
        )
        
        session.mark_topic_used("triangle_perimeter")
        session.mark_template_used("tri_perim_all_sides")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="triangle_perimeter",
            template_id="tri_perim_all_sides",
            question_text=question_text,
            answer_data=str(perimeter),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_tri_perimeter_one_unknown(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Bitta tomoni noma'lum uchburchak"""
        known = [random.randint(3, 8) for _ in range(2)]
        perimeter = sum(known) + random.randint(5, 15)
        unknown = perimeter - sum(known)
        
        question_sig = canonical_geometry_signature("triangle_perimeter", {"known": known, "perimeter": perimeter})
        if session.check_question_signature(question_sig):
            return None
        
        labels, orientation, unk_marker = self._select_variations(session)
        
        question_text = f"Uchburchakning ikki tomoni {known[0]} sm va {known[1]} sm, perimetri {perimeter} sm. Uchinchi tomon necha sm?"
        
        options = self._make_numeric_options(unknown, difficulty)
        correct_label = self._get_correct_label(options, unknown)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="triangle_perimeter",
            template_id="tri_perim_one_unknown",
            question_signature=question_sig,
            render_signature=canonical_render_signature(
                "triangle", orientation.value, "".join(labels), "exam_clean", "unknown_side"
            ),
            shape_type="triangle",
            side_ab=known[0],
            side_bc=known[1],
            perimeter=perimeter,
            measurements={"a": known[0], "b": known[1], "c": unknown},
            orientation_variant=orientation,
            label_set=LabelSet(labels[0] + labels[1] + labels[2]),
            unknown_marker=unk_marker,
            labels={"A": labels[0], "B": labels[1], "C": labels[2]},
            points=self._make_triangle_points(known[0], known[1], unknown, orientation)
        )
        
        session.mark_topic_used("triangle_perimeter")
        session.mark_template_used("tri_perim_one_unknown")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="triangle_perimeter",
            template_id="tri_perim_one_unknown",
            question_text=question_text,
            answer_data=str(unknown),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_tri_perimeter_isosceles(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Teng yonli uchburchak"""
        base = random.randint(4, 10)
        leg = random.randint(base + 1, base + 8)
        perimeter = base + 2 * leg
        
        question_sig = canonical_geometry_signature("triangle_perimeter", {"isosceles": True, "base": base, "leg": leg})
        if session.check_question_signature(question_sig):
            return None
        
        labels, orientation, unk_marker = self._select_variations(session)
        
        question_text = f"Teng yonli uchburchakning asosi {base} sm, yon tomonlari {leg} sm. Perimetri necha sm?"
        
        options = self._make_numeric_options(perimeter, difficulty)
        correct_label = self._get_correct_label(options, perimeter)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="triangle_perimeter",
            template_id="tri_perim_isosceles",
            question_signature=question_sig,
            render_signature=canonical_render_signature(
                "triangle_isosceles", orientation.value, "".join(labels), "exam_clean", "isosceles"
            ),
            shape_type="isosceles_triangle",
            side_ab=leg,
            side_bc=leg,
            side_ac=base,
            perimeter=perimeter,
            orientation_variant=orientation,
            label_set=LabelSet(labels[0] + labels[1] + labels[2]),
            unknown_marker=unk_marker,
        )
        
        session.mark_topic_used("triangle_perimeter")
        session.mark_template_used("tri_perim_isosceles")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("isosceles_triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="triangle_perimeter",
            template_id="tri_perim_isosceles",
            question_text=question_text,
            answer_data=str(perimeter),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_tri_perimeter_equilateral(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Teng tomonli uchburchak"""
        side = random.randint(3, 12)
        perimeter = 3 * side
        
        question_sig = canonical_geometry_signature("triangle_perimeter", {"equilateral": True, "side": side})
        if session.check_question_signature(question_sig):
            return None
        
        labels, orientation, unk_marker = self._select_variations(session)
        
        question_text = f"Teng tomonli uchburchakning bir tomoni {side} sm. Perimetri necha sm?"
        
        options = self._make_numeric_options(perimeter, difficulty)
        correct_label = self._get_correct_label(options, perimeter)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="triangle_perimeter",
            template_id="tri_perim_equilateral",
            question_signature=question_sig,
            render_signature=canonical_render_signature(
                "triangle_equilateral", orientation.value, "".join(labels), "exam_clean", "equilateral"
            ),
            shape_type="equilateral_triangle",
            side_ab=side,
            perimeter=perimeter,
            orientation_variant=orientation,
            label_set=LabelSet(labels[0] + labels[1] + labels[2]),
            unknown_marker=unk_marker,
        )
        
        session.mark_topic_used("triangle_perimeter")
        session.mark_template_used("tri_perim_equilateral")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("equilateral_triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="triangle_perimeter",
            template_id="tri_perim_equilateral",
            question_text=question_text,
            answer_data=str(perimeter),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_tri_area_base_height(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Asos va balandlik bilan yuzani hisoblash"""
        base = random.randint(4, 12)
        height = random.randint(3, 10)
        area = 0.5 * base * height
        
        question_sig = canonical_geometry_signature("triangle_area", {"base": base, "height": height})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Uchburchakning asosi {base} sm, balandligi {height} sm. Yuzasi necha sm²?"
        
        options = self._make_numeric_options(area, difficulty)
        correct_label = self._get_correct_label(options, area)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="triangle_area",
            template_id="tri_area_base_height",
            question_signature=question_sig,
            render_signature=canonical_render_signature("triangle", "upright", "ABC", "exam_clean", "area"),
            shape_type="triangle",
            side_ab=base,
            side_bc=height,
            area=area,
        )
        
        session.mark_topic_used("triangle_area")
        session.mark_template_used("tri_area_base_height")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="triangle_area",
            template_id="tri_area_base_height",
            question_text=question_text,
            answer_data=str(area),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_tri_area_heron(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Geron formulasi bilan yuzani hisoblash"""
        sides = sorted([random.randint(3, 8) for _ in range(3)])
        a, b, c = sides[0], sides[1], sides[2]
        p = (a + b + c) / 2
        area = math.sqrt(p * (p - a) * (p - b) * (p - c))
        area = round(area, 1)
        
        question_sig = canonical_geometry_signature("triangle_area", {"heron": sides})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Tomonlari {a} sm, {b} sm, {c} sm bo'lgan uchburchakning yuzasini toping."
        
        options = self._make_numeric_options(area, difficulty)
        correct_label = self._get_correct_label(options, area)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="triangle_area",
            template_id="tri_area_heron",
            question_signature=question_sig,
            render_signature=canonical_render_signature("triangle", "upright", "ABC", "exam_clean", "heron"),
            shape_type="triangle",
            side_ab=a, side_bc=b, side_ac=c,
            area=area,
        )
        
        session.mark_topic_used("triangle_area")
        session.mark_template_used("tri_area_heron")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="triangle_area",
            template_id="tri_area_heron",
            question_text=question_text,
            answer_data=str(area),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_tri_area_right(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """To'g'ri burchakli uchburchak yuzasi"""
        a = random.randint(3, 8)
        b = random.randint(4, 10)
        area = 0.5 * a * b
        
        question_sig = canonical_geometry_signature("triangle_area", {"right": True, "legs": [a, b]})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"To'g'ri burchakli uchburchakning katetlari {a} sm va {b} sm. Yuzasi necha sm²?"
        
        options = self._make_numeric_options(area, difficulty)
        correct_label = self._get_correct_label(options, area)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="triangle_area",
            template_id="tri_area_right",
            question_signature=question_sig,
            render_signature=canonical_render_signature("right_triangle", "upright", "ABC", "exam_clean", "right"),
            shape_type="right_triangle",
            side_ab=a, side_bc=b,
            area=area,
        )
        
        session.mark_topic_used("triangle_area")
        session.mark_template_used("tri_area_right")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("right_triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="triangle_area",
            template_id="tri_area_right",
            question_text=question_text,
            answer_data=str(area),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_rect_area_wh(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Bo'yi va eni bilan to'g'ri to'rtburchak yuzasi"""
        w = random.randint(3, 12)
        h = random.randint(2, 10)
        area = w * h
        
        question_sig = canonical_geometry_signature("rectangle_area", {"width": w, "height": h})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"To'g'ri to'rtburchakning bo'yi {w} sm, eni {h} sm. Yuzasi necha sm²?"
        
        options = self._make_numeric_options(area, difficulty)
        correct_label = self._get_correct_label(options, area)
        
        spec = RectangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="rectangle_area",
            template_id="rect_area_wh",
            question_signature=question_sig,
            render_signature=canonical_render_signature("rectangle", "upright", "ABCD", "exam_clean", "area"),
            shape_type="rectangle",
            width=w, height=h,
            area=area,
        )
        
        session.mark_topic_used("rectangle_area")
        session.mark_template_used("rect_area_wh")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("rectangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="rectangle_area",
            template_id="rect_area_wh",
            question_text=question_text,
            answer_data=str(area),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_rect_area_unknown(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Noma'lum tomon bilan to'g'ri to'rtburchak"""
        w = random.randint(3, 10)
        area = random.randint(20, 80)
        h = area // w
        
        question_sig = canonical_geometry_signature("rectangle_area", {"width": w, "area": area})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"To'g'ri to'rtburchakning yuzasi {area} sm², bo'yi {w} sm. Eni necha sm?"
        
        options = self._make_numeric_options(h, difficulty)
        correct_label = self._get_correct_label(options, h)
        
        spec = RectangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="rectangle_area",
            template_id="rect_area_unknown_side",
            question_signature=question_sig,
            render_signature=canonical_render_signature("rectangle", "upright", "ABCD", "exam_clean", "unknown"),
            shape_type="rectangle",
            width=w, height=h,
            area=area,
        )
        
        session.mark_topic_used("rectangle_area")
        session.mark_template_used("rect_area_unknown_side")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("rectangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="rectangle_area",
            template_id="rect_area_unknown_side",
            question_text=question_text,
            answer_data=str(h),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_rect_area_square(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Kvadrat yuzasi"""
        side = random.randint(3, 10)
        area = side * side
        
        question_sig = canonical_geometry_signature("rectangle_area", {"square": True, "side": side})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Kvadratning tomoni {side} sm. Yuzasi necha sm²?"
        
        options = self._make_numeric_options(area, difficulty)
        correct_label = self._get_correct_label(options, area)
        
        spec = RectangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="rectangle_area",
            template_id="rect_area_square",
            question_signature=question_sig,
            render_signature=canonical_render_signature("square", "upright", "ABCD", "exam_clean", "square"),
            shape_type="square",
            width=side, height=side,
            area=area,
        )
        
        session.mark_topic_used("rectangle_area")
        session.mark_template_used("rect_area_square")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("square")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="rectangle_area",
            template_id="rect_area_square",
            question_text=question_text,
            answer_data=str(area),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_sq_perim_side(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Tomoni bilan kvadrat perimetri"""
        side = random.randint(2, 12)
        perimeter = 4 * side
        
        question_sig = canonical_geometry_signature("square_perimeter", {"side": side})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Kvadratning tomoni {side} sm. Perimetri necha sm?"
        
        options = self._make_numeric_options(perimeter, difficulty)
        correct_label = self._get_correct_label(options, perimeter)
        
        spec = RectangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="square_perimeter",
            template_id="sq_perim_side",
            question_signature=question_sig,
            render_signature=canonical_render_signature("square", "upright", "ABCD", "exam_clean", "perimeter"),
            shape_type="square",
            width=side, height=side,
            perimeter=perimeter,
        )
        
        session.mark_topic_used("square_perimeter")
        session.mark_template_used("sq_perim_side")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("square")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="square_perimeter",
            template_id="sq_perim_side",
            question_text=question_text,
            answer_data=str(perimeter),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_sq_perim_area(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Yuzasi bilan kvadrat perimetri"""
        side = random.randint(3, 8)
        area = side * side
        perimeter = 4 * side
        
        question_sig = canonical_geometry_signature("square_perimeter", {"area": area})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Kvadratning yuzasi {area} sm². Perimetri necha sm?"
        
        options = self._make_numeric_options(perimeter, difficulty)
        correct_label = self._get_correct_label(options, perimeter)
        
        spec = RectangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="square_perimeter",
            template_id="sq_perim_area_known",
            question_signature=question_sig,
            render_signature=canonical_render_signature("square", "upright", "ABCD", "exam_clean", "from_area"),
            shape_type="square",
            width=side, height=side,
            area=area,
            perimeter=perimeter,
        )
        
        session.mark_topic_used("square_perimeter")
        session.mark_template_used("sq_perim_area_known")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("square")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="square_perimeter",
            template_id="sq_perim_area_known",
            question_text=question_text,
            answer_data=str(perimeter),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_circ_radius_diam(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Diametrdan radius"""
        diameter = random.randint(4, 20)
        radius = diameter / 2
        
        question_sig = canonical_geometry_signature("circle_radius", {"diameter": diameter})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Aylanarning diametri {diameter} sm. Radiusi necha sm?"
        
        options = self._make_numeric_options(radius, difficulty)
        correct_label = self._get_correct_label(options, radius)
        
        spec = CircleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="circle_radius",
            template_id="circ_radius_diam",
            question_signature=question_sig,
            render_signature=canonical_render_signature("circle", "upright", "O", "exam_clean", "diam_to_rad"),
            shape_type="circle",
            radius=radius,
            diameter=diameter,
        )
        
        session.mark_topic_used("circle_radius")
        session.mark_template_used("circ_radius_diam")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("circle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="circle_radius",
            template_id="circ_radius_diam",
            question_text=question_text,
            answer_data=str(radius),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_circ_radius_circumf(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Aylana uzunligidan radius"""
        import math
        circumference = random.randint(20, 60)
        radius = circumference / (2 * math.pi)
        radius = round(radius, 1)
        
        question_sig = canonical_geometry_signature("circle_radius", {"circumference": circumference})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Aylananing uzunligi {circumference:.0f} sm. Radiusi necha sm? (π ≈ 3.14)"
        
        options = self._make_numeric_options(radius, difficulty)
        correct_label = self._get_correct_label(options, radius)
        
        spec = CircleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="circle_radius",
            template_id="circ_radius_circumf",
            question_signature=question_sig,
            render_signature=canonical_render_signature("circle", "upright", "O", "exam_clean", "circumf_to_rad"),
            shape_type="circle",
            radius=radius,
            circumference=circumference,
        )
        
        session.mark_topic_used("circle_radius")
        session.mark_template_used("circ_radius_circumf")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("circle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="circle_radius",
            template_id="circ_radius_circumf",
            question_text=question_text,
            answer_data=str(radius),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_circ_radius_area(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Doira yuzasidan radius"""
        import math
        area = random.randint(30, 100)
        radius = math.sqrt(area / math.pi)
        radius = round(radius, 1)
        
        question_sig = canonical_geometry_signature("circle_radius", {"area": area})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Doira yuzasi {area} sm². Radiusi necha sm? (π ≈ 3.14)"
        
        options = self._make_numeric_options(radius, difficulty)
        correct_label = self._get_correct_label(options, radius)
        
        spec = CircleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="circle_radius",
            template_id="circ_radius_area",
            question_signature=question_sig,
            render_signature=canonical_render_signature("circle", "upright", "O", "exam_clean", "area_to_rad"),
            shape_type="circle",
            radius=radius,
            area=area,
        )
        
        session.mark_topic_used("circle_radius")
        session.mark_template_used("circ_radius_area")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("circle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="circle_radius",
            template_id="circ_radius_area",
            question_text=question_text,
            answer_data=str(radius),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_angle_tri_sum(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Uchburchak burchaklar yig'indisi"""
        a = random.randint(30, 70)
        b = random.randint(30, 70)
        c = 180 - a - b
        
        question_sig = canonical_geometry_signature("angle_finding", {"angles": sorted([a, b])})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Uchburchakning ikki burchagi {a}° va {b}°. Uchinchi burchak necha gradus?"
        
        options = self._make_numeric_options(c, difficulty)
        correct_label = self._get_correct_label(options, c)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="angle_finding",
            template_id="angle_tri_sum",
            question_signature=question_sig,
            render_signature=canonical_render_signature("triangle", "upright", "ABC", "exam_clean", "angle_sum"),
            shape_type="triangle",
            angle_a=a, angle_b=b, angle_c=c,
        )
        
        session.mark_topic_used("angle_finding")
        session.mark_template_used("angle_tri_sum")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="angle_finding",
            template_id="angle_tri_sum",
            question_text=question_text,
            answer_data=str(c),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_angle_linear_pair(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Chiziqli juft burchak"""
        a = random.randint(30, 150)
        b = 180 - a
        
        question_sig = canonical_geometry_signature("angle_finding", {"linear_pair": a})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Chiziqli juft burchaklardan biri {a}°. Ikkinchisi necha gradus?"
        
        options = self._make_numeric_options(b, difficulty)
        correct_label = self._get_correct_label(options, b)
        
        spec = GeometryRenderSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="angle_finding",
            template_id="angle_linear_pair",
            question_signature=question_sig,
            render_signature=canonical_render_signature("angle_linear", "upright", "A", "exam_clean", "linear_pair"),
            shape_type="angle_linear",
        )
        
        session.mark_topic_used("angle_finding")
        session.mark_template_used("angle_linear_pair")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="angle_finding",
            template_id="angle_linear_pair",
            question_text=question_text,
            answer_data=str(b),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=False,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_angle_complementary(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """To'ldiruvchi burchaklar"""
        a = random.randint(20, 70)
        b = 90 - a
        
        question_sig = canonical_geometry_signature("angle_finding", {"complementary": a})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"To'ldiruvchi burchaklardan biri {a}°. Ikkinchisi necha gradus?"
        
        options = self._make_numeric_options(b, difficulty)
        correct_label = self._get_correct_label(options, b)
        
        spec = GeometryRenderSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="angle_finding",
            template_id="angle_complementary",
            question_signature=question_sig,
            render_signature=canonical_render_signature("angle_complementary", "upright", "A", "exam_clean", "complementary"),
            shape_type="angle_complementary",
        )
        
        session.mark_topic_used("angle_finding")
        session.mark_template_used("angle_complementary")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="angle_finding",
            template_id="angle_complementary",
            question_text=question_text,
            answer_data=str(b),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=False,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_parallel_alt_int(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Ichki almashgan burchaklar"""
        angle = random.randint(30, 80)
        
        question_sig = canonical_geometry_signature("parallel_lines", {"alt_int": angle})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Parallel chiziqlarni kesuvchi bilan hosil bo'lgan ichki almashgan burchaklardan biri {angle}°. Ikkinchisi necha gradus?"
        
        options = self._make_numeric_options(angle, difficulty)
        correct_label = self._get_correct_label(options, angle)
        
        spec = GeometryRenderSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="parallel_lines",
            template_id="par_lines_alt_int",
            question_signature=question_sig,
            render_signature=canonical_render_signature("parallel_lines", "upright", "A", "exam_clean", "alt_int"),
            shape_type="parallel_lines",
        )
        
        session.mark_topic_used("parallel_lines")
        session.mark_template_used("par_lines_alt_int")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="parallel_lines",
            template_id="par_lines_alt_int",
            question_text=question_text,
            answer_data=str(angle),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_parallel_corresponding(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Mos burchaklar"""
        angle = random.randint(30, 80)
        
        question_sig = canonical_geometry_signature("parallel_lines", {"corresponding": angle})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"Parallel chiziqlarni kesuvchi bilan hosil bo'lgan mos burchaklardan biri {angle}°. Ikkinchisi necha gradus?"
        
        options = self._make_numeric_options(angle, difficulty)
        correct_label = self._get_correct_label(options, angle)
        
        spec = GeometryRenderSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="parallel_lines",
            template_id="par_lines_corresponding",
            question_signature=question_sig,
            render_signature=canonical_render_signature("parallel_lines", "upright", "A", "exam_clean", "corresponding"),
            shape_type="parallel_lines",
        )
        
        session.mark_topic_used("parallel_lines")
        session.mark_template_used("par_lines_corresponding")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="parallel_lines",
            template_id="par_lines_corresponding",
            question_text=question_text,
            answer_data=str(angle),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_coord_distance(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Masofa formulasidan"""
        x1, y1 = random.randint(-5, 0), random.randint(-5, 0)
        x2, y2 = random.randint(0, 5), random.randint(0, 5)
        
        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        dist = round(dist, 1)
        
        question_sig = canonical_geometry_signature("coordinate_distance", {"points": sorted([(x1, y1), (x2, y2)])})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"A({x1}, {y1}) va B({x2}, {y2}) nuqtalar orasidagi masofani toping."
        
        options = self._make_numeric_options(dist, difficulty)
        correct_label = self._get_correct_label(options, dist)
        
        spec = GeometryRenderSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="coordinate_distance",
            template_id="coord_dist_formula",
            question_signature=question_sig,
            render_signature=canonical_render_signature("coordinate", "upright", "AB", "exam_clean", "distance"),
            shape_type="coordinate",
        )
        
        session.mark_topic_used("coordinate_distance")
        session.mark_template_used("coord_dist_formula")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="coordinate_distance",
            template_id="coord_dist_formula",
            question_text=question_text,
            answer_data=str(dist),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_coord_distance_pythagorean(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Pifagor teoremasi bilan"""
        x1, y1 = 0, 0
        x2, y2 = random.randint(3, 6), random.randint(3, 6)
        
        dist = math.sqrt(x2**2 + y2**2)
        dist = round(dist, 1)
        
        question_sig = canonical_geometry_signature("coordinate_distance", {"pythagorean": (x2, y2)})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"A(0, 0) va B({x2}, {y2}) nuqtalar orasidagi masofani toping."
        
        options = self._make_numeric_options(dist, difficulty)
        correct_label = self._get_correct_label(options, dist)
        
        spec = GeometryRenderSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="coordinate_distance",
            template_id="coord_dist_pythagorean",
            question_signature=question_sig,
            render_signature=canonical_render_signature("coordinate", "upright", "AB", "exam_clean", "pythagorean"),
            shape_type="coordinate",
        )
        
        session.mark_topic_used("coordinate_distance")
        session.mark_template_used("coord_dist_pythagorean")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="coordinate_distance",
            template_id="coord_dist_pythagorean",
            question_text=question_text,
            answer_data=str(dist),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_pythagorean_hyp(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Gipotenuzani topish"""
        a = random.randint(3, 6)
        b = random.randint(4, 8)
        c = round(math.sqrt(a**2 + b**2), 1)
        
        question_sig = canonical_geometry_signature("pythagorean", {"legs": sorted([a, b])})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"To'g'ri burchakli uchburchakning katetlari {a} sm va {b} sm. Gipotenuzasi necha sm?"
        
        options = self._make_numeric_options(c, difficulty)
        correct_label = self._get_correct_label(options, c)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="pythagorean",
            template_id="pythagorean_find_hyp",
            question_signature=question_sig,
            render_signature=canonical_render_signature("right_triangle", "upright", "ABC", "exam_clean", "find_hyp"),
            shape_type="right_triangle",
            side_ab=a, side_bc=b,
            measurements={"a": a, "b": b, "c": c},
        )
        
        session.mark_topic_used("pythagorean")
        session.mark_template_used("pythagorean_find_hyp")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("right_triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="pythagorean",
            template_id="pythagorean_find_hyp",
            question_text=question_text,
            answer_data=str(c),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _gen_pythagorean_leg(self, session, grade, difficulty) -> Optional[QuestionSpec]:
        """Katekni topish"""
        hyp = random.randint(5, 13)
        leg1 = random.randint(3, hyp - 1)
        leg2 = round(math.sqrt(hyp**2 - leg1**2), 1)
        
        question_sig = canonical_geometry_signature("pythagorean", {"hyp": hyp, "leg": leg1})
        if session.check_question_signature(question_sig):
            return None
        
        question_text = f"To'g'ri burchakli uchburchakning gipotenuzasi {hyp} sm, biri kateti {leg1} sm. Ikkinchi katet necha sm?"
        
        options = self._make_numeric_options(leg2, difficulty)
        correct_label = self._get_correct_label(options, leg2)
        
        spec = TriangleSpec(
            question_id=f"geo_{random.randint(1000, 9999)}",
            topic="pythagorean",
            template_id="pythagorean_find_leg",
            question_signature=question_sig,
            render_signature=canonical_render_signature("right_triangle", "upright", "ABC", "exam_clean", "find_leg"),
            shape_type="right_triangle",
            side_ab=leg1, side_bc=leg2,
            measurements={"a": leg1, "b": leg2, "c": hyp},
        )
        
        session.mark_topic_used("pythagorean")
        session.mark_template_used("pythagorean_find_leg")
        session.mark_question_signature(question_sig)
        session.mark_render_signature(spec.render_signature)
        session.mark_shape("right_triangle")
        
        return QuestionSpec(
            question_id=spec.question_id,
            pool_type=PoolType.GEOMETRY,
            topic="pythagorean",
            template_id="pythagorean_find_leg",
            question_text=question_text,
            answer_data=str(leg2),
            correct_answer=correct_label,
            question_signature=question_sig,
            render_signature=spec.render_signature,
            render_spec=spec,
            requires_image=True,
            grade=grade,
            difficulty=difficulty
        )
    
    def _make_numeric_options(self, correct: float, difficulty: str) -> Dict[str, float]:
        """To'g'ri javobga yaqin variantlar yaratish"""
        options = {}
        labels = ["A", "B", "C", "D"]
        
        values = [correct]
        
        if difficulty == "oson":
            variations = [
                correct * random.uniform(0.7, 0.9),
                correct * random.uniform(1.1, 1.3),
                correct + random.randint(5, 15)
            ]
        elif difficulty == "o'rta":
            variations = [
                correct * random.uniform(0.8, 0.95),
                correct * random.uniform(1.05, 1.2),
                correct + random.randint(3, 10)
            ]
        else:
            variations = [
                correct + random.uniform(-5, 5),
                correct + random.uniform(5, 10),
                correct + random.uniform(-10, -5)
            ]
        
        for v in variations:
            v = round(v, 1) if isinstance(correct, float) else int(v)
            if v not in values and v > 0:
                values.append(v)
        
        while len(values) < 4:
            values.append(values[-1] + 1)
        
        values = values[:4]
        random.shuffle(values)
        
        for i, label in enumerate(labels):
            options[label] = values[i]
        
        return options
    
    def _get_correct_label(self, options: Dict[str, float], correct_value: float) -> str:
        """To'g'ri javob labelini topish"""
        for label, value in options.items():
            if abs(value - correct_value) < 0.01 or int(value) == int(correct_value):
                return label
        return "A"


geometry_pool = GeometryPool()
