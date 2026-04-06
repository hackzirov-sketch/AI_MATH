"""
services/render_specs.py — UNIFIED SPEC SYSTEM (SOURCE OF TRUTH)

Har bir savol/chizma avval DiagramSpec yoki RenderSpec ko'rinishida ifodalansin.
Backendlar (Matplotlib, TikZ, SymPy) bir xil source-of-truth dan ishlaydi.

Spec ichida:
- canvas size, coordinate system
- elements list (points, segments, shapes, labels)
- style profile, layout hints
- answer-highlight data
- export options
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class PoolType(Enum):
    GEOMETRY = "geometry"
    PUZZLE = "puzzle"
    TEXT = "text"
    HYBRID = "hybrid"


class StylePreset(Enum):
    EXAM_CLEAN = "exam_clean"
    KIDS_VISUAL = "kids_visual"
    WORKSHEET_PLAIN = "worksheet_plain"
    ANSWER_MARKED = "answer_marked"
    PRINT_BLACK_WHITE = "print_black_white"


class Orientation(Enum):
    LEFT_TILT = "left_tilt"
    RIGHT_TILT = "right_tilt"
    UPRIGHT = "upright"
    WIDE = "wide"
    NARROW = "narrow"
    SLIGHTLY_ROTATED = "slightly_rotated"


class LabelSet(Enum):
    ABC = "ABC"
    PQR = "PQR"
    XYZ = "XYZ"
    MNK = "MNK"
    DEF = "DEF"
    UVW = "UVW"


class UnknownMarker(Enum):
    X = "x"
    QUESTION = "?"
    BLANK = "_blank_"
    DELTA = "Δ"


class DiagramType(Enum):
    GEOMETRY = "geometry"
    PUZZLE = "puzzle"
    FLOW_DIAGRAM = "flow_diagram"
    GRID = "grid"
    CHAIN = "chain"
    TABLE = "table"
    MIXED = "mixed"


class StyleProfile(Enum):
    ACADEMIC = "academic"
    MINIMAL = "minimal"
    PRINT_FRIENDLY = "print_friendly"
    HIGH_CONTRAST = "high_contrast"


# =============================================================================
# STYLE CONFIGURATION
# =============================================================================

@dataclass
class StyleConfig:
    """Stil sozlamalari - print-friendly, academic"""
    background_color: str = "#FFFFFF"
    line_color: str = "#000000"
    text_color: str = "#000000"
    fill_color: Optional[str] = None
    highlight_color: Optional[str] = None
    line_width: float = 1.0
    font_size: float = 10.0
    font_family: str = "DejaVu Sans"
    style_profile: StyleProfile = StyleProfile.ACADEMIC
    
    def to_dict(self) -> Dict:
        return {
            "background_color": self.background_color,
            "line_color": self.line_color,
            "text_color": self.text_color,
            "fill_color": self.fill_color,
            "highlight_color": self.highlight_color,
            "line_width": self.line_width,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "style_profile": self.style_profile.value,
        }


# =============================================================================
# CANVAS SPECIFICATION
# =============================================================================

@dataclass
class CanvasSpec:
    """Canvas o'lchamlari va koordinata tizimi"""
    width: float = 10.0
    height: float = 8.0
    margin_left: float = 0.5
    margin_right: float = 0.5
    margin_top: float = 0.5
    margin_bottom: float = 0.5
    dpi: int = 150
    equal_aspect: bool = False
    
    @property
    def plot_width(self) -> float:
        return self.width - self.margin_left - self.margin_right
    
    @property
    def plot_height(self) -> float:
        return self.height - self.margin_top - self.margin_bottom
    
    def to_dict(self) -> Dict:
        return {
            "width": self.width,
            "height": self.height,
            "margins": (self.margin_left, self.margin_right, self.margin_top, self.margin_bottom),
            "dpi": self.dpi,
            "equal_aspect": self.equal_aspect,
        }


# =============================================================================
# ELEMENT SPECS - GEOMETRIC
# =============================================================================

@dataclass
class PointElement:
    """Nuqta elementi"""
    x: float
    y: float
    label: str = ""
    label_offset: Tuple[float, float] = (0.15, 0.15)
    style: str = "filled"
    radius: float = 0.05
    
    def to_dict(self) -> Dict:
        return {"type": "point", "x": self.x, "y": self.y, "label": self.label}


@dataclass
class SegmentElement:
    """Kesma elementi"""
    x1: float
    y1: float
    x2: float
    y2: float
    label: str = ""
    label_position: str = "midpoint"
    style: str = "solid"
    tick_mark: bool = False
    tick_count: int = 1
    
    def to_dict(self) -> Dict:
        return {"type": "segment", "p1": (self.x1, self.y1), "p2": (self.x2, self.y2), "label": self.label}


@dataclass
class RayElement:
    """Nur elementi"""
    x1: float
    y1: float
    x2: float
    y2: float
    arrow: bool = True
    
    def to_dict(self) -> Dict:
        return {"type": "ray", "start": (self.x1, self.y1), "direction": (self.x2, self.y2)}


@dataclass
class LineElement:
    """To'g'ri chiziq elementi"""
    slope: Optional[float] = None
    intercept: Optional[float] = None
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    style: str = "dashed"
    
    def to_dict(self) -> Dict:
        return {"type": "line", "style": self.style}


@dataclass
class PolygonElement:
    """Ko'pburchak elementi"""
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    fill_color: Optional[str] = None
    edge_color: str = "#000000"
    edge_width: float = 1.0
    labels: List[str] = field(default_factory=list)
    label_offsets: List[Tuple[float, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {"type": "polygon", "vertices": self.vertices, "labels": self.labels}


@dataclass
class TriangleElement:
    """Uchburchak elementi"""
    v1: Tuple[float, float] = (0, 0)
    v2: Tuple[float, float] = (4, 0)
    v3: Tuple[float, float] = (2, 3)
    labels: Tuple[str, str, str] = ("A", "B", "C")
    show_angles: Tuple[bool, bool, bool] = (False, False, False)
    angle_marks: Tuple[str, str, str] = ("", "", "")
    angle_values: Tuple[Optional[float], Optional[float], Optional[float]] = (None, None, None)
    equal_sides: List[Tuple[int, int]] = field(default_factory=list)
    side_labels: Tuple[str, str, str] = ("", "", "")
    fill_color: Optional[str] = None
    
    def get_vertices(self) -> List[Tuple[float, float]]:
        return [self.v1, self.v2, self.v3]
    
    def to_dict(self) -> Dict:
        return {
            "type": "triangle",
            "vertices": [self.v1, self.v2, self.v3],
            "labels": list(self.labels),
            "equal_sides": self.equal_sides,
        }


@dataclass
class RectangleElement:
    """To'g'ri to'rtburchak elementi"""
    x: float = 0.0
    y: float = 0.0
    width: float = 4.0
    height: float = 3.0
    fill_color: Optional[str] = None
    edge_color: str = "#000000"
    edge_width: float = 1.0
    labels: List[str] = field(default_factory=list)
    show_diagonals: bool = False
    
    def get_corners(self) -> List[Tuple[float, float]]:
        return [(self.x, self.y), (self.x + self.width, self.y),
                (self.x + self.width, self.y + self.height), (self.x, self.y + self.height)]
    
    def to_dict(self) -> Dict:
        return {"type": "rectangle", "x": self.x, "y": self.y, "w": self.width, "h": self.height}


@dataclass
class SquareElement:
    """Kvadrat elementi"""
    x: float = 0.0
    y: float = 0.0
    side: float = 3.0
    fill_color: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    
    def to_rectangle(self) -> RectangleElement:
        return RectangleElement(self.x, self.y, self.side, self.side, self.fill_color)
    
    def to_dict(self) -> Dict:
        return {"type": "square", "x": self.x, "y": self.y, "side": self.side}


@dataclass
class CircleElement:
    """Aylana elementi"""
    cx: float = 0.0
    cy: float = 0.0
    radius: float = 2.0
    center_label: str = ""
    show_radius: bool = False
    radius_label: str = "r"
    radius_endpoint_label: str = ""
    fill_color: Optional[str] = None
    edge_color: str = "#000000"
    show_diameter: bool = False
    diameter_label: str = "d"
    
    def to_dict(self) -> Dict:
        return {"type": "circle", "center": (self.cx, self.cy), "radius": self.radius}


@dataclass
class ArcElement:
    """Yoy elementi"""
    cx: float = 0.0
    cy: float = 0.0
    radius: float = 1.0
    start_angle: float = 0.0
    end_angle: float = 90.0
    arrow: bool = False
    label: str = ""
    label_offset: float = 0.2
    
    def to_dict(self) -> Dict:
        return {"type": "arc", "center": (self.cx, self.cy), "radius": self.radius,
                "angles": (self.start_angle, self.end_angle)}


@dataclass
class AngleMarkerElement:
    """Burchak belgisi"""
    vertex: Tuple[float, float] = (0, 0)
    ray1: Tuple[float, float] = (1, 0)
    ray2: Tuple[float, float] = (0, 1)
    radius: float = 0.4
    label: str = ""
    label_offset: float = 0.15
    style: str = "arc"
    arc_color: str = "#000000"
    
    def to_dict(self) -> Dict:
        return {"type": "angle_marker", "vertex": self.vertex, "rays": [self.ray1, self.ray2]}


@dataclass
class PerpendicularElement:
    """Perpendikulyar belgisi"""
    vertex: Tuple[float, float] = (0, 0)
    dir1: Tuple[float, float] = (1, 0)
    dir2: Tuple[float, float] = (0, 1)
    size: float = 0.3
    
    def to_dict(self) -> Dict:
        return {"type": "perpendicular", "vertex": self.vertex}


@dataclass
class MidpointElement:
    """O'rta nuqta belgisi"""
    p1: Tuple[float, float] = (0, 0)
    p2: Tuple[float, float] = (1, 0)
    label: str = ""
    style: str = "double_tick"
    
    def get_midpoint(self) -> Tuple[float, float]:
        return ((self.p1[0] + self.p2[0]) / 2, (self.p1[1] + self.p2[1]) / 2)
    
    def to_dict(self) -> Dict:
        return {"type": "midpoint", "segment": (self.p1, self.p2), "label": self.label}


@dataclass
class TickMarkElement:
    """Teng yonlar uchun belgi"""
    p1: Tuple[float, float] = (0, 0)
    p2: Tuple[float, float] = (1, 0)
    count: int = 1
    length: float = 0.15
    
    def to_dict(self) -> Dict:
        return {"type": "tick_mark", "segment": (self.p1, self.p2), "count": self.count}


@dataclass
class LabelElement:
    """Matn belgisi"""
    text: str
    x: float = 0.0
    y: float = 0.0
    font_size: Optional[float] = None
    color: str = "#000000"
    ha: str = "center"
    va: str = "center"
    rotation: float = 0.0
    
    def to_dict(self) -> Dict:
        return {"type": "label", "text": self.text, "pos": (self.x, self.y)}


@dataclass
class ParallelElement:
    """Parallel belgisi"""
    segment1: Tuple[Tuple[float, float], Tuple[float, float]] = ((0, 0), (1, 0))
    segment2: Tuple[Tuple[float, float], Tuple[float, float]] = ((0, 1), (1, 1))
    count: int = 1
    length: float = 0.15
    
    def to_dict(self) -> Dict:
        return {"type": "parallel", "segs": [self.segment1, self.segment2], "count": self.count}


# =============================================================================
# ELEMENT SPECS - PUZZLE
# =============================================================================

@dataclass
class BoxElement:
    """Oddiy quti"""
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 0.6
    content: str = ""
    fill_color: Optional[str] = None
    border_color: str = "#000000"
    font_size: float = 11.0
    
    def to_dict(self) -> Dict:
        return {"type": "box", "pos": (self.x, self.y), "content": self.content}


@dataclass
class RoundedBoxElement:
    """Yumaloq burchakli quti"""
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 0.6
    content: str = ""
    radius: float = 0.1
    fill_color: Optional[str] = None
    border_color: str = "#000000"
    font_size: float = 11.0
    
    def to_dict(self) -> Dict:
        return {"type": "rounded_box", "pos": (self.x, self.y), "content": self.content}


@dataclass
class ArrowElement:
    """Strelka elementi"""
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 1.0
    y2: float = 0.0
    label: str = ""
    style: str = "solid"
    arrow_style: str = "->"
    line_width: float = 1.0
    
    def to_dict(self) -> Dict:
        return {"type": "arrow", "from": (self.x1, self.y1), "to": (self.x2, self.y2)}


@dataclass
class FlowNodeElement:
    """Oqim diagramma tuguni"""
    x: float = 0.0
    y: float = 0.0
    width: float = 1.5
    height: float = 0.8
    content: str = ""
    fill_color: Optional[str] = "#E3F2FD"
    border_color: str = "#2196F3"
    next_node: Optional[str] = None
    node_id: str = ""
    
    def to_dict(self) -> Dict:
        return {"type": "flow_node", "id": self.node_id, "content": self.content}


@dataclass
class ChainNodeElement:
    """Zanjir operatsiya tuguni"""
    x: float = 0.0
    y: float = 0.0
    content: str = ""
    index: int = 0
    is_start: bool = False
    is_end: bool = False
    fill_color: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {"type": "chain_node", "index": self.index, "content": self.content}


@dataclass
class GridCellElement:
    """Jadval katakchasi"""
    row: int = 0
    col: int = 0
    content: str = ""
    fill_color: Optional[str] = None
    border_color: str = "#000000"
    is_unknown: bool = False
    font_size: float = 12.0
    
    def to_dict(self) -> Dict:
        return {"type": "grid_cell", "pos": (self.row, self.col), "content": self.content}


@dataclass
class UnknownSymbolElement:
    """Noma'lum belgi (□, △, ○)"""
    x: float = 0.0
    y: float = 0.0
    symbol: str = "?"
    symbol_style: str = "circle"
    size: float = 0.3
    content: str = "?"
    fill_color: Optional[str] = "#FFECB3"
    border_color: str = "#FF6F00"
    
    def to_dict(self) -> Dict:
        return {"type": "unknown_symbol", "pos": (self.x, self.y), "symbol": self.symbol}


# =============================================================================
# DIAGRAM SPEC (TO'LIQ SPEKTI)
# =============================================================================

@dataclass
class DiagramSpec:
    """
    Diagram/Puzzle uchun to'liq spetsifikatsiya.
    SOURCE OF TRUTH - Matplotlib, TikZ, SymPy bittadan o'qiydi.
    """
    diagram_type: DiagramType
    canvas: CanvasSpec
    style: StyleConfig
    title: str = ""
    
    points: List[PointElement] = field(default_factory=list)
    segments: List[SegmentElement] = field(default_factory=list)
    rays: List[RayElement] = field(default_factory=list)
    lines: List[LineElement] = field(default_factory=list)
    polygons: List[PolygonElement] = field(default_factory=list)
    triangles: List[TriangleElement] = field(default_factory=list)
    rectangles: List[RectangleElement] = field(default_factory=list)
    squares: List[SquareElement] = field(default_factory=list)
    circles: List[CircleElement] = field(default_factory=list)
    arcs: List[ArcElement] = field(default_factory=list)
    angle_markers: List[AngleMarkerElement] = field(default_factory=list)
    perpendiculars: List[PerpendicularElement] = field(default_factory=list)
    midpoints: List[MidpointElement] = field(default_factory=list)
    tick_marks: List[TickMarkElement] = field(default_factory=list)
    labels: List[LabelElement] = field(default_factory=list)
    parallels: List[ParallelElement] = field(default_factory=list)
    
    boxes: List[BoxElement] = field(default_factory=list)
    rounded_boxes: List[RoundedBoxElement] = field(default_factory=list)
    arrows: List[ArrowElement] = field(default_factory=list)
    flow_nodes: List[FlowNodeElement] = field(default_factory=list)
    chain_nodes: List[ChainNodeElement] = field(default_factory=list)
    grid_cells: List[GridCellElement] = field(default_factory=list)
    unknown_symbols: List[UnknownSymbolElement] = field(default_factory=list)
    
    highlight_elements: List[str] = field(default_factory=list)
    solution_geometry: Optional[Dict] = None
    
    export_options: Dict[str, Any] = field(default_factory=dict)
    
    def get_signature(self) -> str:
        parts = [
            self.diagram_type.value,
            str(self.canvas.width), str(self.canvas.height),
            str(len(self.triangles)), str(len(self.circles)),
        ]
        for t in self.triangles:
            parts.append(str(t.v1) + str(t.v2) + str(t.v3))
        for c in self.circles:
            parts.append(f"{c.cx},{c.cy},{c.radius}")
        return hashlib.md5("|".join(parts).encode()).hexdigest()[:16]
    
    def get_all_elements(self) -> List[Any]:
        return (
            self.points + self.segments + self.rays + self.lines +
            self.polygons + self.triangles + self.rectangles + self.squares +
            self.circles + self.arcs + self.angle_markers + self.perpendiculars +
            self.midpoints + self.tick_marks + self.labels + self.parallels +
            self.boxes + self.rounded_boxes + self.arrows + self.flow_nodes +
            self.chain_nodes + self.grid_cells + self.unknown_symbols
        )
    
    def to_dict(self) -> Dict:
        return {
            "diagram_type": self.diagram_type.value,
            "canvas": self.canvas.to_dict(),
            "style": self.style.to_dict(),
            "title": self.title,
            "elements_count": len(self.get_all_elements()),
            "signature": self.get_signature(),
        }


# =============================================================================
# RENDER RESULT
# =============================================================================

@dataclass
class RenderMetadata:
    """Render metadata"""
    render_time_ms: float = 0.0
    cache_hit: bool = False
    width: float = 0
    height: float = 0
    dpi: int = 150
    signature: str = ""
    cache_key: str = ""
    fallback_used: bool = False
    fallback_reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "render_time_ms": self.render_time_ms,
            "cache_hit": self.cache_hit,
            "width": self.width,
            "height": self.height,
            "dpi": self.dpi,
            "signature": self.signature,
            "cache_key": self.cache_key,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
        }


@dataclass
class RenderResult:
    """Render natijasi"""
    spec: Optional[Any] = None
    image_bytes: Optional[bytes] = None
    metadata: RenderMetadata = field(default_factory=RenderMetadata)
    success: bool = True
    error_message: str = ""
    image_path: Optional[str] = None
    tikz_source: Optional[str] = None
    width: float = 0
    height: float = 0
    dpi: int = 150
    spec_signature: str = ""
    cache_key: str = ""
    render_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.metadata:
            if not self.width:
                self.width = self.metadata.width
            if not self.height:
                self.height = self.metadata.height
            if not self.dpi:
                self.dpi = self.metadata.dpi
            if not self.spec_signature:
                self.spec_signature = self.metadata.signature
            if not self.cache_key:
                self.cache_key = self.metadata.cache_key
            if not self.render_time_ms:
                self.render_time_ms = self.metadata.render_time_ms
        if self.spec is not None and not self.spec_signature:
            self.spec_signature = getattr(self.spec, "render_signature", "")
        if self.error_message and self.error_message not in self.errors:
            self.errors.append(self.error_message)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "has_image": self.image_bytes is not None,
            "width": self.width,
            "height": self.height,
            "spec_signature": self.spec_signature,
            "cache_key": self.cache_key,
            "metadata": self.metadata.to_dict(),
        }


# =============================================================================
# LEGACY RENDER SPEC (backward compatibility)
# =============================================================================

@dataclass
class RenderSpec:
    """Legacy RenderSpec - backward compatibility uchun"""
    question_id: str = ""
    pool_type: PoolType = PoolType.PUZZLE
    topic: str = ""
    template_id: str = ""
    question_signature: str = ""
    render_signature: str = ""
    style_preset: StylePreset = StylePreset.EXAM_CLEAN
    width: int = 8
    height: int = 6
    dpi: int = 150
    layout_type: str = "vertical"
    element_positions: Dict[str, Any] = field(default_factory=dict)
    figure_size: Tuple[float, float] = (10, 6)
    
    def to_dict(self) -> Dict:
        return {
            "question_id": self.question_id,
            "pool_type": self.pool_type.value,
            "topic": self.topic,
            "template_id": self.template_id,
            "question_signature": self.question_signature,
            "render_signature": self.render_signature,
            "style_preset": self.style_preset.value,
            "width": self.width,
            "height": self.height,
            "dpi": self.dpi,
            "layout_type": self.layout_type,
        }
    
    def get_cache_key(self) -> str:
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# BUILDER HELPER
# =============================================================================

class DiagramSpecBuilder:
    """DiagramSpec yaratish uchun builder pattern"""
    
    def __init__(self, diagram_type: DiagramType = DiagramType.GEOMETRY):
        self._spec = DiagramSpec(
            diagram_type=diagram_type,
            canvas=CanvasSpec(),
            style=StyleConfig(),
        )
    
    def with_canvas(self, width: float = 10, height: float = 8, dpi: int = 150,
                    equal_aspect: bool = False) -> "DiagramSpecBuilder":
        self._spec.canvas = CanvasSpec(width=width, height=height, dpi=dpi, equal_aspect=equal_aspect)
        return self
    
    def with_style(self, line_width: float = 1.0, font_size: float = 10.0,
                   profile: StyleProfile = StyleProfile.ACADEMIC) -> "DiagramSpecBuilder":
        self._spec.style = StyleConfig(line_width=line_width, font_size=font_size, style_profile=profile)
        return self
    
    def with_title(self, title: str) -> "DiagramSpecBuilder":
        self._spec.title = title
        return self
    
    def add_triangle(self, v1, v2, v3, labels=("A", "B", "C"), **kwargs) -> "DiagramSpecBuilder":
        self._spec.triangles.append(TriangleElement(v1=v1, v2=v2, v3=v3, labels=labels, **kwargs))
        return self
    
    def add_point(self, x, y, label="", **kwargs) -> "DiagramSpecBuilder":
        self._spec.points.append(PointElement(x=x, y=y, label=label, **kwargs))
        return self
    
    def add_segment(self, x1, y1, x2, y2, label="", **kwargs) -> "DiagramSpecBuilder":
        self._spec.segments.append(SegmentElement(x1=x1, y1=y1, x2=x2, y2=y2, label=label, **kwargs))
        return self
    
    def add_circle(self, cx, cy, radius, **kwargs) -> "DiagramSpecBuilder":
        self._spec.circles.append(CircleElement(cx=cx, cy=cy, radius=radius, **kwargs))
        return self
    
    def add_angle_marker(self, vertex, ray1, ray2, **kwargs) -> "DiagramSpecBuilder":
        self._spec.angle_markers.append(AngleMarkerElement(vertex=vertex, ray1=ray1, ray2=ray2, **kwargs))
        return self
    
    def add_rectangle(self, x, y, width, height, **kwargs) -> "DiagramSpecBuilder":
        self._spec.rectangles.append(RectangleElement(x=x, y=y, width=width, height=height, **kwargs))
        return self
    
    def add_label(self, text, x, y, **kwargs) -> "DiagramSpecBuilder":
        self._spec.labels.append(LabelElement(text=text, x=x, y=y, **kwargs))
        return self
    
    def add_box(self, x, y, width, height, content="", **kwargs) -> "DiagramSpecBuilder":
        self._spec.boxes.append(BoxElement(x=x, y=y, width=width, height=height, content=content, **kwargs))
        return self
    
    def add_arrow(self, x1, y1, x2, y2, **kwargs) -> "DiagramSpecBuilder":
        self._spec.arrows.append(ArrowElement(x1=x1, y1=y1, x2=x2, y2=y2, **kwargs))
        return self
    
    def add_grid_cell(self, row, col, content="", **kwargs) -> "DiagramSpecBuilder":
        self._spec.grid_cells.append(GridCellElement(row=row, col=col, content=content, **kwargs))
        return self
    
    def add_unknown_symbol(self, x, y, symbol="?", **kwargs) -> "DiagramSpecBuilder":
        self._spec.unknown_symbols.append(UnknownSymbolElement(x=x, y=y, symbol=symbol, **kwargs))
        return self
    
    def add_tick_mark(self, p1, p2, count=1, **kwargs) -> "DiagramSpecBuilder":
        self._spec.tick_marks.append(TickMarkElement(p1=p1, p2=p2, count=count, **kwargs))
        return self
    
    def add_perpendicular(self, vertex, dir1, dir2, **kwargs) -> "DiagramSpecBuilder":
        self._spec.perpendiculars.append(PerpendicularElement(vertex=vertex, dir1=dir1, dir2=dir2, **kwargs))
        return self
    
    def add_midpoint(self, p1, p2, **kwargs) -> "DiagramSpecBuilder":
        self._spec.midpoints.append(MidpointElement(p1=p1, p2=p2, **kwargs))
        return self
    
    def add_arc(self, cx, cy, radius, start_angle, end_angle, **kwargs) -> "DiagramSpecBuilder":
        self._spec.arcs.append(ArcElement(cx=cx, cy=cy, radius=radius,
                                           start_angle=start_angle, end_angle=end_angle, **kwargs))
        return self
    
    def add_parallel(self, seg1, seg2, count=1, **kwargs) -> "DiagramSpecBuilder":
        self._spec.parallels.append(ParallelElement(segment1=seg1, segment2=seg2, count=count, **kwargs))
        return self
    
    def build(self) -> DiagramSpec:
        return self._spec


# =============================================================================
# CONVENIENCE FACTORY
# =============================================================================

class DiagramFactory:
    """Eng ko'p ishlatiladigan diagrammalar uchun factory"""
    
    @staticmethod
    def right_triangle(a: float = 3, b: float = 4,
                       labels: Tuple[str, str, str] = ("A", "B", "C")) -> DiagramSpec:
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(8, 6, equal_aspect=True)
        builder.add_triangle((0, 0), (a, 0), (0, b), labels=labels)
        builder.add_perpendicular((0, 0), (a, 0), (0, b))
        return builder.build()
    
    @staticmethod
    def circle_with_radius(cx: float = 0, cy: float = 0, r: float = 3,
                           center_label: str = "O") -> DiagramSpec:
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(8, 8, equal_aspect=True)
        builder.add_circle(cx, cy, r, center_label=center_label, show_radius=True)
        builder.add_point(cx, cy, label=center_label)
        builder.add_segment(cx, cy, cx + r, cy, label="r")
        return builder.build()
    
    @staticmethod
    def triangle_diagram(vertices: List[Tuple[float, float]],
                         labels: List[str] = None) -> DiagramSpec:
        if labels is None:
            labels = ["A", "B", "C"]
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        v = vertices
        if len(v) == 3:
            builder.with_canvas(10, 8, equal_aspect=True)
            builder.add_triangle(v[0], v[1], v[2], labels=tuple(labels[:3]))
        return builder.build()
    
    @staticmethod
    def rectangle_diagram(w: float = 5, h: float = 3) -> DiagramSpec:
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(w + 2, h + 2, equal_aspect=True)
        builder.add_rectangle(1, 1, w, h)
        return builder.build()
    
    @staticmethod
    def angle_diagram(vertex: Tuple[float, float], ray1: Tuple[float, float],
                      ray2: Tuple[float, float], label: str = "α") -> DiagramSpec:
        builder = DiagramSpecBuilder(DiagramType.GEOMETRY)
        builder.with_canvas(8, 6, equal_aspect=True)
        builder.add_point(vertex[0], vertex[1], label="")
        builder.add_angle_marker(vertex, ray1, ray2, label=label)
        builder.add_segment(vertex[0], vertex[1], ray1[0], ray1[1])
        builder.add_segment(vertex[0], vertex[1], ray2[0], ray2[1])
        return builder.build()
    
    @staticmethod
    def vertical_arithmetic(a: int, b: int, op: str = "+") -> DiagramSpec:
        """Vertikal arifmetika uchun puzzle diagram"""
        builder = DiagramSpecBuilder(DiagramType.PUZZLE)
        builder.with_canvas(6, 6)
        result = a + b if op == "+" else a - b if op == "-" else a * b
        builder.add_label(str(a), 3, 4, font_size=16)
        builder.add_label(f"{op} {b}", 3, 3.2, font_size=14)
        builder.add_segment(2.2, 2.8, 4.2, 2.8)
        builder.add_label(str(result), 3, 2, font_size=16)
        return builder.build()
    
    @staticmethod
    def flow_diagram(values: List[Tuple[str, str]]) -> DiagramSpec:
        """Oqim diagramma"""
        builder = DiagramSpecBuilder(DiagramType.FLOW_DIAGRAM)
        n = len(values)
        builder.with_canvas(max(3 * n, 8), 4)
        for i, (input_val, operation) in enumerate(values):
            x = 1.5 + i * 2.5
            builder.add_box(x, 1.5, 1.5, 0.8, content=input_val)
            if i < n - 1:
                builder.add_arrow(x + 1.6, 1.9, x + 2.5, 1.9, label=operation if i == 0 else "")
        return builder.build()


# =============================================================================
# SIGNATURE FUNCTIONS (backward compatibility)
# =============================================================================

def canonical_geometry_signature(topic: str, params: Dict) -> str:
    sorted_params = sorted(params.items())
    param_str = "|".join(f"{k}={v}" for k, v in sorted_params)
    return f"geo|{topic}|{param_str}"


def canonical_puzzle_signature(topic: str, params: Dict) -> str:
    sorted_params = sorted(params.items())
    param_str = "|".join(f"{k}={v}" for k, v in sorted_params)
    return f"puz|{topic}|{param_str}"


def canonical_render_signature(
    shape_type: str, orientation: str, label_set: str,
    style: str, layout: str, extra: Optional[Dict] = None
) -> str:
    parts = [shape_type, orientation, label_set, style, layout]
    if extra:
        sorted_extra = sorted(extra.items())
        extra_str = "|".join(f"{k}={v}" for k, v in sorted_extra)
        parts.append(extra_str)
    return "|".join(parts)


# =============================================================================
# DEFAULT INSTANCES
# =============================================================================

default_style = StyleConfig()
default_canvas = CanvasSpec()


# =============================================================================
# PROBLEM SPEC (SYMPY VALIDATION UCHUN)
# =============================================================================

@dataclass
class ProblemSpec:
    """
    SymPy validatsiya uchun savol spetsifikatsiyasi.
    Generator yaratadi, validator tekshiradi.
    """
    problem_id: str = ""
    expressions: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    expected_answer: Optional[Any] = None
    answer_type: str = "integer"
    tolerance: float = 0.001
    context: str = ""

    def to_dict(self) -> Dict:
        return {
            "problem_id": self.problem_id,
            "expressions": self.expressions,
            "variables": {k: str(v) for k, v in self.variables.items()},
            "constraints": self.constraints,
            "expected_answer": str(self.expected_answer) if self.expected_answer is not None else None,
            "answer_type": self.answer_type,
        }


@dataclass
class ValidationReport:
    """SymPy validatsiya hisoboti"""
    is_valid: bool = True
    correct_answer: Optional[Any] = None
    normalized_answer: Optional[Any] = None
    derived_values: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    difficulty_score: float = 0.0
    template_family: str = ""

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "correct_answer": str(self.correct_answer) if self.correct_answer is not None else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# EXPORT METADATA (TIKZ UCHUN)
# =============================================================================

@dataclass
class TikzExportResult:
    """TikZ export natijasi"""
    success: bool = True
    tikz_code: str = ""
    full_document: str = ""
    unsupported_elements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    export_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "has_tikz_code": bool(self.tikz_code),
            "unsupported_count": len(self.unsupported_elements),
        }


# =============================================================================
# LEGACY GEOMETRY SPECS (backward compatibility for geometry_pool)
# =============================================================================

@dataclass
class GeometryRenderSpec:
    """Legacy GeometryRenderSpec - backward compatibility"""
    question_id: str = ""
    topic: str = ""
    template_id: str = ""
    question_signature: str = ""
    render_signature: str = ""
    shape_type: str = ""
    diagram_type: DiagramType = DiagramType.GEOMETRY
    style_preset: StylePreset = StylePreset.EXAM_CLEAN
    figure_size: Tuple[float, float] = (8.0, 6.0)
    dpi: int = 150
    elements: List[Any] = field(default_factory=list)
    canvas: CanvasSpec = field(default_factory=CanvasSpec)
    style: StyleConfig = field(default_factory=StyleConfig)
    measurements: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, Any] = field(default_factory=dict)
    points: List[Any] = field(default_factory=list)
    orientation_variant: Orientation = Orientation.UPRIGHT
    label_set: LabelSet = LabelSet.ABC
    unknown_marker: UnknownMarker = UnknownMarker.X
    
    def to_dict(self) -> Dict:
        return {
            "question_id": self.question_id,
            "topic": self.topic,
            "template_id": self.template_id,
            "question_signature": self.question_signature,
            "render_signature": self.render_signature,
            "shape_type": self.shape_type,
            "diagram_type": self.diagram_type.value,
            "style_preset": self.style_preset.value,
            "figure_size": self.figure_size,
            "dpi": self.dpi,
            "measurements": self.measurements,
            "labels": self.labels,
            "points_count": len(self.points),
        }


@dataclass
class TriangleSpec(GeometryRenderSpec):
    """Legacy TriangleSpec for backward compatibility"""
    side_ab: float = 0
    side_bc: float = 0
    side_ac: float = 0
    perimeter: float = 0
    area: float = 0
    angle_a: float = 0
    angle_b: float = 0
    angle_c: float = 0
    label_a: str = "A"
    label_b: str = "B"
    label_c: str = "C"
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update(
            {
                "side_ab": self.side_ab,
                "side_bc": self.side_bc,
                "side_ac": self.side_ac,
                "perimeter": self.perimeter,
                "area": self.area,
                "angle_a": self.angle_a,
                "angle_b": self.angle_b,
                "angle_c": self.angle_c,
            }
        )
        return data


@dataclass
class RectangleSpec(GeometryRenderSpec):
    """Legacy RectangleSpec for backward compatibility"""
    width: float = 0
    height: float = 0
    label_width: str = ""
    label_height: str = ""
    area: float = 0
    perimeter: float = 0
    diagonal: float = 0
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update(
            {
                "width": self.width,
                "height": self.height,
                "label_width": self.label_width,
                "label_height": self.label_height,
                "area": self.area,
                "perimeter": self.perimeter,
                "diagonal": self.diagonal,
            }
        )
        return data


@dataclass
class CircleSpec(GeometryRenderSpec):
    """Legacy CircleSpec for backward compatibility"""
    radius: float = 0
    diameter: float = 0
    circumference: float = 0
    area: float = 0
    center_label: str = "O"
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update(
            {
                "radius": self.radius,
                "diameter": self.diameter,
                "circumference": self.circumference,
                "area": self.area,
                "center_label": self.center_label,
            }
        )
        return data


@dataclass
class TrapezoidSpec(GeometryRenderSpec):
    """Legacy TrapezoidSpec for backward compatibility"""
    base1: float = 0
    base2: float = 0
    height: float = 0
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({"base1": self.base1, "base2": self.base2, "height": self.height})
        return data


@dataclass
class QuestionSpec:
    """Legacy QuestionSpec for backward compatibility"""
    question_id: str = ""
    pool_type: PoolType = PoolType.GEOMETRY
    template_type: str = ""
    template_id: str = ""
    question_text: str = ""
    answer_data: Any = None
    correct_answer: Any = None
    question_signature: str = ""
    render_signature: str = ""
    render_spec: Optional[Union[GeometryRenderSpec, RenderSpec]] = None
    geometry: Optional[GeometryRenderSpec] = None
    puzzle_data: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    answer: Any = None
    topic: str = ""
    requires_image: bool = False
    grade: int = 5
    difficulty: str = "o'rta"
    
    def to_dict(self) -> Dict:
        return {
            "question_id": self.question_id,
            "pool_type": self.pool_type.value,
            "template_type": self.template_type or self.template_id,
            "template_id": self.template_id,
            "question": self.question_text,
            "question_text": self.question_text,
            "answer_data": self.answer_data,
            "correct": self.correct_answer,
            "correct_answer": self.correct_answer,
            "question_signature": self.question_signature,
            "render_signature": self.render_signature,
            "render_spec": self.render_spec,
            "geometry": self.geometry,
            "puzzle_data": self.puzzle_data,
            "options": self.options,
            "topic": self.topic,
            "requires_image": self.requires_image,
            "grade": self.grade,
            "difficulty": self.difficulty,
        }


PuzzleRenderSpec = RenderSpec


@dataclass
class GridPuzzleSpec:
    """Legacy GridPuzzleSpec for backward compatibility"""
    grid_size: Tuple[int, int] = (3, 3)
    grid_data: List[List[Any]] = field(default_factory=list)
    labels_row: List[str] = field(default_factory=list)
    labels_col: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {"grid_size": self.grid_size}


@dataclass
class LogicGridSpec:
    """Legacy LogicGridSpec for backward compatibility"""
    items: List[Dict[str, Any]] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {"categories": self.categories}


@dataclass
class VerticalArithmeticSpec:
    """Legacy VerticalArithmeticSpec for backward compatibility"""
    operation: str = "+"
    operand1: int = 0
    operand2: int = 0
    result: int = 0
    
    def to_dict(self) -> Dict:
        return {"operation": self.operation, "operand1": self.operand1, "operand2": self.operand2}


@dataclass
class FlowDiagramSpec:
    """Legacy FlowDiagramSpec for backward compatibility"""
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {"operations": self.operations}


@dataclass
class ChainOperationsSpec:
    """Legacy ChainOperationsSpec for backward compatibility"""
    chain: List[Dict[str, Any]] = field(default_factory=list)
    steps: int = 3
    
    def to_dict(self) -> Dict:
        return {"steps": self.steps}


@dataclass
class RebusPuzzleSpec:
    """Legacy RebusPuzzleSpec for backward compatibility"""
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    expression: str = ""
    
    def to_dict(self) -> Dict:
        return {"expression": self.expression}
