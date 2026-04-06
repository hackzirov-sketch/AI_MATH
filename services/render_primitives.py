"""
services/render_primitives.py — PRODUCTION-LEVEL LOW-LEVEL DRAWING FUNCTIONS

Print-friendly, academic, black/white style.
Geomatik chizmalar: oq fon, qora chiziqlar, aniq, kitob-uslubida.

Primitives:
- draw_point, draw_segment, draw_ray, draw_line
- draw_polygon, draw_triangle, draw_rectangle, draw_square
- draw_circle, draw_arc
- draw_angle_marker, draw_perpendicular, draw_parallel, draw_midpoint
- draw_tick_marks, draw_equal_mark
- draw_label, draw_vertex_label, draw_side_label, draw_measurement
- draw_box, draw_rounded_box, draw_arrow, draw_flow_node
- draw_grid_cell, draw_number_cell
- setup_figure, export_to_bytes, export_to_file
"""

from __future__ import annotations

import math
import io
import logging
from typing import List, Tuple, Optional, Dict, Any, Union

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon, Rectangle, Arc, Wedge, Ellipse
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D

logger = logging.getLogger(__name__)


# =============================================================================
# PRINT-FRIENDLY STYLE CONSTANTS
# =============================================================================

DEFAULT_LINE_COLOR = "#000000"
DEFAULT_TEXT_COLOR = "#000000"
DEFAULT_BG_COLOR = "#FFFFFF"
DEFAULT_LINE_WIDTH = 1.2
DEFAULT_FONT_SIZE = 10.0
DEFAULT_FONT_FAMILY = "DejaVu Sans"

# Fill colors - grayscale-safe, print-friendly
FILL_COLORS = {
    "white": "#FFFFFF",
    "light_gray": "#F5F5F5",
    "gray": "#E8E8E8",
    "highlight_yellow": "#FFF9C4",
    "highlight_blue": "#E3F2FD",
    "highlight_green": "#E8F5E9",
    "highlight_red": "#FFEBEE",
}


# =============================================================================
# FIGURE SETUP & EXPORT
# =============================================================================

def setup_figure(width: float = 10, height: float = 8,
                 dpi: int = 150, equal_aspect: bool = True,
                 hide_axes: bool = True) -> Tuple[plt.Figure, plt.Axes]:
    """Figure va Axes yaratish - academic print style"""
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    fig.patch.set_facecolor(DEFAULT_BG_COLOR)
    fig.patch.set_edgecolor("none")
    
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    
    if equal_aspect:
        ax.set_aspect("equal", adjustable="datalim")
    
    if hide_axes:
        ax.axis("off")
    
    ax.set_facecolor(DEFAULT_BG_COLOR)
    
    return fig, ax


def export_to_bytes(fig: plt.Figure, dpi: int = 150, format: str = "png") -> bytes:
    """Figure ni bytes ga export qilish"""
    buf = io.BytesIO()
    fig.savefig(buf, format=format, dpi=dpi, bbox_inches="tight",
                pad_inches=0.05, facecolor=fig.get_facecolor(),
                edgecolor="none", transparent=False)
    buf.seek(0)
    data = buf.read()
    buf.close()
    plt.close(fig)
    return data


def export_to_file(fig: plt.Figure, filepath: str,
                   dpi: int = 150, format: str = "png") -> str:
    """Figure ni faylga saqlash"""
    fig.savefig(filepath, format=format, dpi=dpi, bbox_inches="tight",
                pad_inches=0.05, facecolor=fig.get_facecolor(),
                edgecolor="none", transparent=False)
    plt.close(fig)
    return filepath


def cleanup_figure(fig: plt.Figure) -> None:
    """Figure tozalash"""
    plt.close(fig)


# =============================================================================
# BASIC GEOMETRY PRIMITIVES
# =============================================================================

def draw_point(ax: plt.Axes, x: float, y: float,
               color: str = DEFAULT_LINE_COLOR,
               size: float = 5.0,
               style: str = "filled") -> None:
    """Nuqta chizish"""
    if style == "filled":
        ax.plot(x, y, 'o', color=color, markersize=size, zorder=5)
    elif style == "hollow":
        ax.plot(x, y, 'o', color=color, markersize=size,
                markerfacecolor="white", markeredgewidth=1.5, zorder=5)
    elif style == "cross":
        ax.plot(x, y, '+', color=color, markersize=size, markeredgewidth=2, zorder=5)


def draw_segment(ax: plt.Axes,
                 p1: Tuple[float, float],
                 p2: Tuple[float, float],
                 color: str = DEFAULT_LINE_COLOR,
                 linewidth: float = DEFAULT_LINE_WIDTH,
                 style: str = "solid") -> None:
    """Kesma chizish"""
    linestyle = "-"
    if style == "dashed":
        linestyle = "--"
    elif style == "dotted":
        linestyle = ":"
    
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
            color=color, linewidth=linewidth, linestyle=linestyle, zorder=2)


def draw_ray(ax: plt.Axes,
             origin: Tuple[float, float],
             direction: Tuple[float, float],
             length: float = 8.0,
             color: str = DEFAULT_LINE_COLOR,
             linewidth: float = DEFAULT_LINE_WIDTH,
             arrow: bool = True) -> None:
    """Nur chizish"""
    dx = direction[0] - origin[0]
    dy = direction[1] - origin[1]
    dist = math.sqrt(dx * dx + dy * dy)
    
    if dist == 0:
        return
    
    dx /= dist
    dy /= dist
    
    end = (origin[0] + dx * length, origin[1] + dy * length)
    
    ax.plot([origin[0], end[0]], [origin[1], end[1]],
            color=color, linewidth=linewidth, zorder=2)
    
    if arrow:
        ax.annotate("", xy=end, xytext=origin,
                    arrowprops=dict(arrowstyle="->", color=color, lw=linewidth))


def draw_line(ax: plt.Axes,
              p1: Tuple[float, float],
              p2: Tuple[float, float],
              color: str = DEFAULT_LINE_COLOR,
              linewidth: float = DEFAULT_LINE_WIDTH,
              style: str = "dashed") -> None:
    """To'g'ri chiziq (uzunlik)"""
    linestyle = "--" if style == "dashed" else ":" if style == "dotted" else "-"
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
            color=color, linewidth=linewidth, linestyle=linestyle, zorder=1)


# =============================================================================
# POLYGON PRIMITIVES
# =============================================================================

def draw_polygon(ax: plt.Axes,
                 vertices: List[Tuple[float, float]],
                 fill_color: Optional[str] = None,
                 edge_color: str = DEFAULT_LINE_COLOR,
                 edge_width: float = DEFAULT_LINE_WIDTH,
                 labels: Optional[List[str]] = None,
                 label_offsets: Optional[List[Tuple[float, float]]] = None) -> None:
    """Ko'pburchak chizish"""
    if len(vertices) < 3:
        return
    
    face = fill_color if fill_color else "none"
    poly = Polygon(vertices, closed=True, facecolor=face,
                   edgecolor=edge_color, linewidth=edge_width, zorder=2)
    ax.add_patch(poly)
    
    if labels:
        for i, label in enumerate(labels):
            if i < len(vertices):
                offset = (0, -0.2)
                if label_offsets and i < len(label_offsets):
                    offset = label_offsets[i]
                draw_label(ax, vertices[i][0] + offset[0],
                          vertices[i][1] + offset[1], label)


def draw_triangle(ax: plt.Axes,
                  v1: Tuple[float, float],
                  v2: Tuple[float, float],
                  v3: Tuple[float, float],
                  labels: Tuple[str, str, str] = ("", "", ""),
                  fill_color: Optional[str] = None,
                  edge_color: str = DEFAULT_LINE_COLOR,
                  edge_width: float = DEFAULT_LINE_WIDTH,
                  label_offsets: Optional[Tuple[Tuple[float, float], ...]] = None) -> None:
    """Uchburchak chizish"""
    vertices = [v1, v2, v3]
    draw_polygon(ax, vertices, fill_color, edge_color, edge_width)
    
    # Auto label offsets based on vertex position
    if labels:
        auto_offsets = []
        for i, v in enumerate(vertices):
            cx = (v1[0] + v2[0] + v3[0]) / 3
            cy = (v1[1] + v2[1] + v3[1]) / 3
            dx = v[0] - cx
            dy = v[1] - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                auto_offsets.append((dx / dist * 0.3, dy / dist * 0.3))
            else:
                auto_offsets.append((0, 0.3))
        
        if label_offsets:
            auto_offsets = list(label_offsets)
        
        for i, label in enumerate(labels):
            if label:
                draw_label(ax, vertices[i][0] + auto_offsets[i][0],
                          vertices[i][1] + auto_offsets[i][1], label,
                          fontweight="bold")


def draw_rectangle(ax: plt.Axes,
                   x: float, y: float,
                   width: float, height: float,
                   fill_color: Optional[str] = None,
                   edge_color: str = DEFAULT_LINE_COLOR,
                   edge_width: float = DEFAULT_LINE_WIDTH,
                   labels: Optional[List[str]] = None) -> None:
    """To'g'ri to'rtburchak chizish"""
    face = fill_color if fill_color else "none"
    rect = Rectangle((x, y), width, height, facecolor=face,
                     edgecolor=edge_color, linewidth=edge_width, zorder=2)
    ax.add_patch(rect)
    
    if labels and len(labels) >= 4:
        corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
        offsets = [(-0.15, -0.15), (0.15, -0.15), (0.15, 0.15), (-0.15, 0.15)]
        for i, label in enumerate(labels):
            if label:
                draw_label(ax, corners[i][0] + offsets[i][0],
                          corners[i][1] + offsets[i][1], label, fontweight="bold")


def draw_square(ax: plt.Axes,
                x: float, y: float,
                side: float,
                fill_color: Optional[str] = None,
                edge_color: str = DEFAULT_LINE_COLOR,
                edge_width: float = DEFAULT_LINE_WIDTH) -> None:
    """Kvadrat chizish"""
    draw_rectangle(ax, x, y, side, side, fill_color, edge_color, edge_width)


# =============================================================================
# CIRCLE & ARC PRIMITIVES
# =============================================================================

def draw_circle(ax: plt.Axes,
                center: Tuple[float, float],
                radius: float,
                fill_color: Optional[str] = None,
                edge_color: str = DEFAULT_LINE_COLOR,
                edge_width: float = DEFAULT_LINE_WIDTH,
                center_label: str = "",
                show_radius: bool = False,
                radius_label: str = "r") -> None:
    """Aylana chizish"""
    face = fill_color if fill_color else "none"
    circle = Circle(center, radius, facecolor=face,
                    edgecolor=edge_color, linewidth=edge_width, zorder=2)
    ax.add_patch(circle)
    
    if center_label:
        draw_label(ax, center[0], center[1], center_label,
                  ha="center", va="top", offset=(0, 0.1), fontweight="bold")
    
    if show_radius:
        draw_segment(ax, center, (center[0] + radius, center[1]),
                    color=edge_color, linewidth=edge_width)
        mid = (center[0] + radius / 2, center[1])
        draw_label(ax, mid[0], mid[1] - 0.15, radius_label)


def draw_arc(ax: plt.Axes,
             center: Tuple[float, float],
             radius: float,
             start_angle: float,
             end_angle: float,
             color: str = DEFAULT_LINE_COLOR,
             linewidth: float = DEFAULT_LINE_WIDTH,
             arrow: bool = False,
             label: str = "") -> None:
    """Yoy chizish"""
    arc = Arc(center, radius * 2, radius * 2, angle=0,
              theta1=start_angle, theta2=end_angle,
              color=color, linewidth=linewidth, zorder=3)
    ax.add_patch(arc)
    
    if label:
        mid_angle = math.radians((start_angle + end_angle) / 2)
        lx = center[0] + (radius + 0.2) * math.cos(mid_angle)
        ly = center[1] + (radius + 0.2) * math.sin(mid_angle)
        draw_label(ax, lx, ly, label)


# =============================================================================
# ANGLE MARKERS
# =============================================================================

def draw_angle_arc(ax: plt.Axes,
                   vertex: Tuple[float, float],
                   p1: Tuple[float, float],
                   p2: Tuple[float, float],
                   radius: float = 0.4,
                   color: str = DEFAULT_LINE_COLOR,
                   linewidth: float = 1.2,
                   label: str = "",
                   label_offset: float = 0.15) -> None:
    """Burchak yoyi chizish"""
    angle1 = math.degrees(math.atan2(p1[1] - vertex[1], p1[0] - vertex[0])) % 360
    angle2 = math.degrees(math.atan2(p2[1] - vertex[1], p2[0] - vertex[0])) % 360
    
    t1, t2 = min(angle1, angle2), max(angle1, angle2)
    if t2 - t1 > 180:
        t1, t2 = t2, t1 + 360
    
    arc = Arc(vertex, radius * 2, radius * 2, angle=0,
              theta1=t1, theta2=t2, color=color, linewidth=linewidth, zorder=3)
    ax.add_patch(arc)
    
    if label:
        mid_angle = math.radians((t1 + t2) / 2)
        lx = vertex[0] + (radius + label_offset) * math.cos(mid_angle)
        ly = vertex[1] + (radius + label_offset) * math.sin(mid_angle)
        draw_label(ax, lx, ly, label, color=color)


def draw_right_angle(ax: plt.Axes,
                     vertex: Tuple[float, float],
                     p1: Tuple[float, float],
                     p2: Tuple[float, float],
                     size: float = 0.25,
                     color: str = DEFAULT_LINE_COLOR,
                     linewidth: float = 1.0) -> None:
    """To'g'ri burchak belgisi"""
    dx1 = p1[0] - vertex[0]
    dy1 = p1[1] - vertex[1]
    dx2 = p2[0] - vertex[0]
    dy2 = p2[1] - vertex[1]
    
    len1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
    len2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
    
    if len1 == 0 or len2 == 0:
        return
    
    dx1, dy1 = dx1 / len1, dy1 / len1
    dx2, dy2 = dx2 / len2, dy2 / len2
    
    p_a = (vertex[0] + dx1 * size, vertex[1] + dy1 * size)
    p_b = (vertex[0] + dx1 * size + dx2 * size, vertex[1] + dy1 * size + dy2 * size)
    p_c = (vertex[0] + dx2 * size, vertex[1] + dy2 * size)
    
    draw_segment(ax, p_a, p_b, color=color, linewidth=linewidth)
    draw_segment(ax, p_b, p_c, color=color, linewidth=linewidth)


def draw_angle_tics(ax: plt.Axes,
                    vertex: Tuple[float, float],
                    p1: Tuple[float, float],
                    p2: Tuple[float, float],
                    radius: float = 0.4,
                    count: int = 1,
                    color: str = DEFAULT_LINE_COLOR,
                    linewidth: float = 1.0) -> None:
    """Burchak ichidagi tics (teng burchaklar belgisi)"""
    angle1 = math.atan2(p1[1] - vertex[1], p1[0] - vertex[0])
    angle2 = math.atan2(p2[1] - vertex[1], p2[0] - vertex[0])
    
    mid_angle = (angle1 + angle2) / 2
    
    tick_len = 0.12
    
    for i in range(count):
        offset = (i - (count - 1) / 2) * 0.08
        if count == 1:
            offset = 0
        
        cx = vertex[0] + radius * math.cos(mid_angle + offset)
        cy = vertex[1] + radius * math.sin(mid_angle + offset)
        
        inner = (vertex[0] + (radius - tick_len) * math.cos(mid_angle + offset),
                 vertex[1] + (radius - tick_len) * math.sin(mid_angle + offset))
        outer = (vertex[0] + (radius + tick_len) * math.cos(mid_angle + offset),
                 vertex[1] + (radius + tick_len) * math.sin(mid_angle + offset))
        
        draw_segment(ax, inner, outer, color=color, linewidth=linewidth)


def draw_perpendicular_mark(ax: plt.Axes,
                            vertex: Tuple[float, float],
                            dir1: Tuple[float, float],
                            dir2: Tuple[float, float],
                            size: float = 0.3,
                            color: str = DEFAULT_LINE_COLOR,
                            linewidth: float = 1.0) -> None:
    """Perpendikulyar belgisi"""
    draw_right_angle(ax, vertex, dir1, dir2, size, color, linewidth)


# =============================================================================
# TICK MARKS & EQUAL SIDE MARKS
# =============================================================================

def draw_tick_mark_on_segment(ax: plt.Axes,
                              p1: Tuple[float, float],
                              p2: Tuple[float, float],
                              count: int = 1,
                              length: float = 0.15,
                              color: str = DEFAULT_LINE_COLOR,
                              linewidth: float = 1.0) -> None:
    """Kesma o'rtasida tick belgilar"""
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.sqrt(dx * dx + dy * dy)
    
    if dist == 0:
        return
    
    # Perpendicular direction
    nx = -dy / dist
    ny = dx / dist
    
    spacing = 0.1
    start_offset = -(count - 1) / 2 * spacing
    
    for i in range(count):
        offset = start_offset + i * spacing
        cx = mx - dy / dist * offset
        cy = my + dx / dist * offset
        
        x1 = cx + nx * length / 2
        y1 = cy + ny * length / 2
        x2 = cx - nx * length / 2
        y2 = cy - ny * length / 2
        
        draw_segment(ax, (x1, y1), (x2, y2), color=color, linewidth=linewidth)


def draw_equal_side_markers(ax: plt.Axes,
                            sides: List[Tuple[Tuple[float, float], Tuple[float, float]]],
                            count: int = 1,
                            color: str = DEFAULT_LINE_COLOR,
                            linewidth: float = 1.0) -> None:
    """Teng yonlarni belgilash"""
    for side in sides:
        draw_tick_mark_on_segment(ax, side[0], side[1], count=count,
                                  color=color, linewidth=linewidth)


def draw_midpoint(ax: plt.Axes,
                  p1: Tuple[float, float],
                  p2: Tuple[float, float],
                  label: str = "",
                  style: str = "filled",
                  color: str = DEFAULT_LINE_COLOR,
                  size: float = 4) -> None:
    """O'rta nuqta belgisi"""
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    
    if style == "filled":
        draw_point(ax, mx, my, color=color, size=size, style="filled")
    elif style == "hollow":
        draw_point(ax, mx, my, color=color, size=size, style="hollow")
    
    if label:
        draw_label(ax, mx, my - 0.2, label, fontweight="bold")


# =============================================================================
# LABELING SYSTEM
# =============================================================================

def draw_label(ax: plt.Axes,
               x: float, y: float,
               text: str,
               fontsize: float = DEFAULT_FONT_SIZE,
               color: str = DEFAULT_TEXT_COLOR,
               fontweight: str = "normal",
               ha: str = "center",
               va: str = "center",
               offset: Tuple[float, float] = (0, 0),
               rotation: float = 0.0) -> None:
    """Matn label chizish"""
    ax.text(x + offset[0], y + offset[1], text,
            fontsize=fontsize, color=color, fontweight=fontweight,
            ha=ha, va=va, rotation=rotation, zorder=5,
            fontfamily=DEFAULT_FONT_FAMILY)


def draw_vertex_label(ax: plt.Axes,
                      point: Tuple[float, float],
                      label: str,
                      offset: Tuple[float, float] = (0, 0.25),
                      fontsize: float = DEFAULT_FONT_SIZE + 2,
                      color: str = DEFAULT_TEXT_COLOR) -> None:
    """Vertex label chizish"""
    draw_label(ax, point[0], point[1], label, fontsize=fontsize,
               color=color, fontweight="bold",
               ha="center", va="bottom", offset=offset)


def draw_side_label(ax: plt.Axes,
                    p1: Tuple[float, float],
                    p2: Tuple[float, float],
                    label: str,
                    offset_percent: float = 0.2,
                    fontsize: float = DEFAULT_FONT_SIZE,
                    color: str = DEFAULT_TEXT_COLOR) -> None:
    """Tomon label"""
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx * dx + dy * dy)
    
    if length == 0:
        return
    
    nx = -dy / length
    ny = dx / length
    
    offset_x = nx * length * offset_percent
    offset_y = ny * length * offset_percent
    
    draw_label(ax, mx + offset_x, my + offset_y, label,
               fontsize=fontsize, color=color, fontweight="bold")


def draw_measurement(ax: plt.Axes,
                     p1: Tuple[float, float],
                     p2: Tuple[float, float],
                     label: str,
                     offset: float = 0.4,
                     color: str = DEFAULT_TEXT_COLOR,
                     fontsize: float = DEFAULT_FONT_SIZE - 1) -> None:
    """O'lcham chizig'i va matni"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx * dx + dy * dy)
    
    if length == 0:
        return
    
    nx = -dy / length
    ny = dx / length
    
    off_x = nx * offset
    off_y = ny * offset
    
    # Dimension line
    draw_segment(ax, (p1[0] + off_x, p1[1] + off_y),
                 (p2[0] + off_x, p2[1] + off_y),
                 color=color, linewidth=0.8, style="solid")
    
    # Arrows
    mid = ((p1[0] + p2[0]) / 2 + off_x, (p1[1] + p2[1]) / 2 + off_y)
    
    # Label
    draw_label(ax, mid[0], mid[1] + 0.15, label, fontsize=fontsize, color=color)


def draw_angle_label(ax: plt.Axes,
                     vertex: Tuple[float, float],
                     p1: Tuple[float, float],
                     p2: Tuple[float, float],
                     label: str,
                     radius: float = 0.5,
                     fontsize: float = DEFAULT_FONT_SIZE + 1,
                     color: str = DEFAULT_TEXT_COLOR) -> None:
    """Burchak qiymatini yozish"""
    angle1 = math.atan2(p1[1] - vertex[1], p1[0] - vertex[0])
    angle2 = math.atan2(p2[1] - vertex[1], p2[0] - vertex[0])
    
    mid_angle = (angle1 + angle2) / 2
    
    lx = vertex[0] + radius * math.cos(mid_angle)
    ly = vertex[1] + radius * math.sin(mid_angle)
    
    draw_label(ax, lx, ly, label, fontsize=fontsize, color=color, fontweight="bold")


# =============================================================================
# PUZZLE PRIMITIVES
# =============================================================================

def draw_box(ax: plt.Axes,
             x: float, y: float,
             width: float, height: float,
             content: str = "",
             fill_color: Optional[str] = None,
             border_color: str = DEFAULT_LINE_COLOR,
             border_width: float = 1.2,
             font_size: float = 12.0) -> None:
    """Oddiy quti chizish"""
    face = fill_color if fill_color else "none"
    rect = Rectangle((x, y), width, height, facecolor=face,
                     edgecolor=border_color, linewidth=border_width, zorder=2)
    ax.add_patch(rect)
    
    if content:
        draw_label(ax, x + width / 2, y + height / 2, content,
                   fontsize=font_size, fontweight="bold")


def draw_rounded_box(ax: plt.Axes,
                     x: float, y: float,
                     width: float, height: float,
                     content: str = "",
                     radius: float = 0.1,
                     fill_color: Optional[str] = None,
                     border_color: str = DEFAULT_LINE_COLOR,
                     border_width: float = 1.2,
                     font_size: float = 12.0) -> None:
    """Yumaloq burchakli quti"""
    face = fill_color if fill_color else "none"
    
    box = FancyBboxPatch((x, y), width, height,
                         boxstyle=f"round,pad={radius}",
                         facecolor=face, edgecolor=border_color,
                         linewidth=border_width, zorder=2)
    ax.add_patch(box)
    
    if content:
        draw_label(ax, x + width / 2, y + height / 2, content,
                   fontsize=font_size, fontweight="bold")


def draw_arrow(ax: plt.Axes,
               x1: float, y1: float,
               x2: float, y2: float,
               color: str = DEFAULT_LINE_COLOR,
               linewidth: float = 1.2,
               label: str = "",
               style: str = "->") -> None:
    """Strelka chizish"""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=linewidth))
    
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        draw_label(ax, mx, my + 0.15, label)


def draw_flow_node(ax: plt.Axes,
                   x: float, y: float,
                   width: float, height: float,
                   content: str = "",
                   fill_color: Optional[str] = None,
                   border_color: str = DEFAULT_LINE_COLOR) -> None:
    """Oqim diagramma tuguni"""
    draw_rounded_box(ax, x, y, width, height, content,
                     fill_color=fill_color, border_color=border_color)


def draw_chain_node(ax: plt.Axes,
                    x: float, y: float,
                    radius: float = 0.4,
                    content: str = "",
                    fill_color: Optional[str] = None,
                    border_color: str = DEFAULT_LINE_COLOR) -> None:
    """Zanjir operatsiya tuguni"""
    face = fill_color if fill_color else "none"
    circle = Circle((x, y), radius, facecolor=face,
                    edgecolor=border_color, linewidth=1.2, zorder=2)
    ax.add_patch(circle)
    
    if content:
        draw_label(ax, x, y, content, fontweight="bold")


def draw_grid_cell(ax: plt.Axes,
                   x: float, y: float,
                   width: float, height: float,
                   content: str = "",
                   fill_color: Optional[str] = None,
                   border_color: str = DEFAULT_LINE_COLOR,
                   is_unknown: bool = False,
                   font_size: float = 12.0) -> None:
    """Jadval katakchasi"""
    if is_unknown:
        fill_color = FILL_COLORS["highlight_yellow"]
        border_color = "#FF6F00"
    
    draw_box(ax, x, y, width, height, content,
             fill_color=fill_color, border_color=border_color, font_size=font_size)


def draw_number_cell(ax: plt.Axes,
                     x: float, y: float,
                     size: float = 1.0,
                     number: Union[int, str] = "",
                     fill_color: Optional[str] = None,
                     border_color: str = DEFAULT_LINE_COLOR) -> None:
    """Son katakchasi"""
    content = str(number) if number != "" else ""
    is_unknown = content == "?" or content == ""
    draw_grid_cell(ax, x, y, size, size, content,
                   fill_color=fill_color, border_color=border_color,
                   is_unknown=is_unknown)


def draw_unknown_symbol(ax: plt.Axes,
                        x: float, y: float,
                        symbol: str = "?",
                        style: str = "circle",
                        size: float = 0.3,
                        fill_color: Optional[str] = "#FFF9C4",
                        border_color: str = DEFAULT_LINE_COLOR) -> None:
    """Noma'lum belgi (□, △, ○)"""
    face = fill_color if fill_color else "none"
    
    if style == "circle":
        shape = Circle((x, y), size, facecolor=face,
                       edgecolor=border_color, linewidth=1.5, zorder=3)
    elif style == "square":
        shape = Rectangle((x - size, y - size), size * 2, size * 2,
                          facecolor=face, edgecolor=border_color,
                          linewidth=1.5, zorder=3)
    elif style == "diamond":
        pts = [(x, y + size), (x + size, y), (x, y - size), (x - size, y)]
        shape = Polygon(pts, facecolor=face, edgecolor=border_color,
                        linewidth=1.5, zorder=3)
    else:
        return
    
    ax.add_patch(shape)
    draw_label(ax, x, y, symbol, fontweight="bold", fontsize=14)


def draw_table_layout(ax: plt.Axes,
                      x: float, y: float,
                      rows: int, cols: int,
                      cell_width: float = 1.2,
                      cell_height: float = 0.8,
                      data: Optional[List[List[str]]] = None,
                      border_color: str = DEFAULT_LINE_COLOR) -> None:
    """Jadval layout chizish"""
    for r in range(rows):
        for c in range(cols):
            cx = x + c * cell_width
            cy = y + r * cell_height
            content = ""
            if data and r < len(data) and c < len(data[r]):
                content = data[r][c]
            draw_grid_cell(ax, cx, cy, cell_width, cell_height, content,
                          border_color=border_color)


# =============================================================================
# GEOMETRY HELPERS
# =============================================================================

def draw_triangle_with_angles(ax: plt.Axes,
                              v1: Tuple[float, float],
                              v2: Tuple[float, float],
                              v3: Tuple[float, float],
                              angles: Tuple[Optional[float], Optional[float], Optional[float]] = (None, None, None),
                              labels: Tuple[str, str, str] = ("A", "B", "C"),
                              fill_color: Optional[str] = None) -> None:
    """Uchburchak va burchak belgilari"""
    draw_triangle(ax, v1, v2, v3, labels=labels, fill_color=fill_color)
    
    vertices = [v1, v2, v3]
    for i in range(3):
        if angles[i] is not None:
            v = vertices[i]
            p1 = vertices[(i + 1) % 3]
            p2 = vertices[(i + 2) % 3]
            draw_angle_arc(ax, v, p1, p2)
            label = f"{angles[i]}°"
            draw_angle_label(ax, v, p1, p2, label)


def draw_triangle_with_sides(ax: plt.Axes,
                             v1: Tuple[float, float],
                             v2: Tuple[float, float],
                             v3: Tuple[float, float],
                             side_labels: Tuple[str, str, str] = ("", "", ""),
                             equal_sides: Optional[List[Tuple[int, int]]] = None,
                             labels: Tuple[str, str, str] = ("A", "B", "C")) -> None:
    """Uchburchak va tomon belgilari"""
    draw_triangle(ax, v1, v2, v3, labels=labels)
    
    vertices = [v1, v2, v3]
    sides = [(v1, v2), (v2, v3), (v3, v1)]
    
    for i, label in enumerate(side_labels):
        if label:
            draw_side_label(ax, sides[i][0], sides[i][1], label)
    
    if equal_sides:
        for pair in equal_sides:
            if 0 <= pair[0] < 3 and 0 <= pair[1] < 3:
                draw_tick_mark_on_segment(ax, sides[pair[0]][0], sides[pair[0]][1], count=1)
                draw_tick_mark_on_segment(ax, sides[pair[1]][0], sides[pair[1]][1], count=1)


def draw_circle_with_info(ax: plt.Axes,
                          cx: float, cy: float, r: float,
                          center_label: str = "O",
                          show_radius: bool = True,
                          radius_label: str = "r",
                          show_diameter: bool = False,
                          diameter_label: str = "d") -> None:
    """Aylana va ma'lumotlar"""
    draw_circle(ax, (cx, cy), r, center_label=center_label,
                show_radius=show_radius, radius_label=radius_label)
    
    if show_diameter:
        draw_segment(ax, (cx - r, cy), (cx + r, cy), style="dashed", linewidth=0.8)
        draw_label(ax, cx, cy + 0.2, diameter_label, fontsize=9)


# =============================================================================
# DIMENSION & MEASUREMENT HELPERS
# =============================================================================

def draw_dimension_line(ax: plt.Axes,
                        p1: Tuple[float, float],
                        p2: Tuple[float, float],
                        label: str,
                        offset: float = 0.4,
                        color: str = DEFAULT_TEXT_COLOR,
                        fontsize: float = DEFAULT_FONT_SIZE - 1) -> None:
    """O'lcham chizig'i (<->)"""
    draw_measurement(ax, p1, p2, label, offset, color, fontsize)


def draw_height_marker(ax: plt.Axes,
                       base: Tuple[float, float],
                       apex: Tuple[float, float],
                       label: str = "h",
                       color: str = DEFAULT_LINE_COLOR,
                       style: str = "dashed") -> None:
    """Balandlik belgisi"""
    draw_segment(ax, base, apex, color=color, linewidth=0.8, style=style)
    draw_label(ax, (base[0] + apex[0]) / 2 + 0.15,
               (base[1] + apex[1]) / 2, label,
               fontsize=9, color=color)


# =============================================================================
# PARALLEL MARKERS
# =============================================================================

def draw_parallel_marker(ax: plt.Axes,
                         seg1: Tuple[Tuple[float, float], Tuple[float, float]],
                         seg2: Tuple[Tuple[float, float], Tuple[Tuple[float, float]]],
                         count: int = 1,
                         color: str = DEFAULT_LINE_COLOR,
                         linewidth: float = 1.0,
                         length: float = 0.12) -> None:
    """Parallel belgisi"""
    mid1 = ((seg1[0][0] + seg1[1][0]) / 2, (seg1[0][1] + seg1[1][1]) / 2)
    mid2 = ((seg2[0][0] + seg2[1][0]) / 2, (seg2[0][1] + seg2[1][1]) / 2)
    
    draw_tick_mark_on_segment(ax, seg1[0], seg1[1], count=count,
                              length=length, color=color, linewidth=linewidth)
    draw_tick_mark_on_segment(ax, seg2[0], seg2[1], count=count,
                              length=length, color=color, linewidth=linewidth)


# =============================================================================
# ALTERNATE SYMBOL SYSTEM
# =============================================================================

def draw_symbol_box(ax: plt.Axes,
                    x: float, y: float,
                    symbol: str = "A",
                    size: float = 0.5,
                    fill: Optional[str] = None,
                    border: str = DEFAULT_LINE_COLOR) -> None:
    """Symbol qutisi"""
    draw_box(ax, x - size / 2, y - size / 2, size, size,
             content=symbol, fill_color=fill, border_color=border, font_size=11)


def draw_eq_label(ax: plt.Axes,
                  x: float, y: float,
                  equation: str,
                  fontsize: float = DEFAULT_FONT_SIZE + 2,
                  color: str = DEFAULT_TEXT_COLOR) -> None:
    """Tenglama matni"""
    draw_label(ax, x, y, equation, fontsize=fontsize, color=color, fontweight="normal")
