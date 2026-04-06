"""
services/puzzle_diagram_renderer.py — MATPLOTLIB PUZZLE DIAGRAM RENDERER

Oq fon, qora chiziq, kataklar, arrowlar.
Academic style, print-friendly.

Render types:
- Chain puzzle diagram
- Flow diagram
- Grid puzzle
- Rebus equation
- Shape puzzle
- Symbol equation
"""

from __future__ import annotations

import io
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (
    FancyBboxPatch, Circle, Rectangle, Polygon, FancyArrowPatch, Arc, Wedge
)

logger = logging.getLogger(__name__)

DEFAULT_LINE_COLOR = "#000000"
DEFAULT_TEXT_COLOR = "#000000"
DEFAULT_BG_COLOR = "#FFFFFF"
FILL_COLORS = {
    "white": "#FFFFFF",
    "light_blue": "#E3F2FD",
    "light_green": "#E8F5E9",
    "light_yellow": "#FFF9C4",
    "light_orange": "#FFE0B2",
    "light_gray": "#F5F5F5",
    "highlight": "#FFECB3",
}


@dataclass
class RenderedDiagram:
    """Render natijasi"""
    image_bytes: bytes
    width: int
    height: int
    dpi: int
    
    def save(self, filepath: str):
        """Faylga saqlash"""
        with open(filepath, 'wb') as f:
            f.write(self.image_bytes)


class PuzzleDiagramRenderer:
    """
    Matplotlib asosida puzzle diagram chizish.
    
    Academic print style:
    - White background
    - Black lines and text
    - Clean, clear boxes
    - Professional arrows
    """
    
    def __init__(self, dpi: int = 150):
        self.dpi = dpi
    
    def render_chain(self, values: List[int], operations: List[str],
                      hide_index: Optional[int] = None,
                      title: str = "") -> RenderedDiagram:
        """Zanjir puzzle chizish"""
        n = len(values)
        cell_width = 1.5
        spacing = 0.8
        total_width = n * cell_width + (n - 1) * spacing + 1
        fig_height = 3.0
        
        fig, ax = plt.subplots(1, 1, figsize=(total_width, fig_height), dpi=self.dpi)
        fig.patch.set_facecolor(DEFAULT_BG_COLOR)
        ax.set_xlim(0, total_width)
        ax.set_ylim(0, fig_height)
        ax.set_aspect('equal')
        ax.axis('off')
        
        for i, val in enumerate(values):
            x = 0.5 + i * (cell_width + spacing)
            y = fig_height / 2 - cell_width / 4
            
            is_hidden = (hide_index == i)
            fill = FILL_COLORS["highlight"] if is_hidden else FILL_COLORS["light_blue"]
            edge = "#FF6F00" if is_hidden else DEFAULT_LINE_COLOR
            
            box = FancyBboxPatch(
                (x, y), cell_width, cell_width / 1.5,
                boxstyle="round,pad=0.05",
                facecolor=fill, edgecolor=edge,
                linewidth=2, zorder=2
            )
            ax.add_patch(box)
            
            display_text = "?" if is_hidden else str(val)
            ax.text(
                x + cell_width / 2, y + cell_width / 3,
                display_text,
                ha='center', va='center',
                fontsize=16, fontweight='bold',
                color=DEFAULT_TEXT_COLOR,
                zorder=3
            )
            
            if i < len(operations):
                arrow_x = x + cell_width + 0.1
                arrow_end = x + cell_width + spacing - 0.1
                arrow_y = y + cell_width / 3
                
                ax.annotate(
                    "",
                    xy=(arrow_end, arrow_y),
                    xytext=(arrow_x, arrow_y),
                    arrowprops=dict(
                        arrowstyle="->",
                        color=DEFAULT_LINE_COLOR,
                        lw=2,
                    ),
                    zorder=1
                )
                
                op = operations[i] if i < len(operations) else ""
                ax.text(
                    (arrow_x + arrow_end) / 2,
                    arrow_y + 0.2,
                    op,
                    ha='center', va='bottom',
                    fontsize=12, color='#1565C0',
                    fontweight='bold',
                    zorder=3
                )
        
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        
        return self._fig_to_rendered(fig)
    
    def render_flow(self, steps: List[Dict[str, Any]],
                     hide_step: Optional[int] = None,
                     title: str = "") -> RenderedDiagram:
        """Flow diagram chizish"""
        n = len(steps)
        box_w = 2.0
        box_h = 1.0
        spacing = 0.8
        total_w = n * box_w + (n - 1) * spacing + 1
        fig_h = 3.0
        
        fig, ax = plt.subplots(1, 1, figsize=(total_w, fig_h), dpi=self.dpi)
        fig.patch.set_facecolor(DEFAULT_BG_COLOR)
        ax.set_xlim(0, total_w)
        ax.set_ylim(0, fig_h)
        ax.set_aspect('equal')
        ax.axis('off')
        
        for i, step in enumerate(steps):
            x = 0.5 + i * (box_w + spacing)
            y = fig_h / 2 - box_h / 2
            
            is_hidden = (hide_step == i)
            fill = FILL_COLORS["highlight"] if is_hidden else FILL_COLORS["light_blue"]
            edge = "#FF6F00" if is_hidden else DEFAULT_LINE_COLOR
            
            box = FancyBboxPatch(
                (x, y), box_w, box_h,
                boxstyle="round,pad=0.1",
                facecolor=fill, edgecolor=edge,
                linewidth=2, zorder=2
            )
            ax.add_patch(box)
            
            if is_hidden:
                text = "?"
            else:
                label = step.get("label", "")
                val = step.get("value", "")
                text = f"{label}\n{val}" if label else str(val)
            
            ax.text(
                x + box_w / 2, y + box_h / 2,
                text,
                ha='center', va='center',
                fontsize=11, fontweight='bold',
                color=DEFAULT_TEXT_COLOR,
                zorder=3
            )
            
            if i < n - 1:
                ax.annotate(
                    "",
                    xy=(x + box_w + spacing * 0.1, y + box_h / 2),
                    xytext=(x + box_w + spacing * 0.5, y + box_h / 2),
                    arrowprops=dict(
                        arrowstyle="->",
                        color=DEFAULT_LINE_COLOR,
                        lw=2,
                    ),
                    zorder=1
                )
        
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        
        return self._fig_to_rendered(fig)
    
    def render_grid(self, grid: List[List[Any]], 
                     missing_pos: Optional[Tuple[int, int]] = None,
                     row_sums: Optional[List[int]] = None,
                     col_sums: Optional[List[int]] = None,
                     title: str = "") -> RenderedDiagram:
        """Jadval puzzle chizish"""
        rows = len(grid)
        cols = len(grid[0]) if grid else 0
        
        cell_size = 1.2
        margin = 1.0
        sum_width = 1.5 if row_sums else 0
        sum_height = 0.8 if col_sums else 0
        
        fig_w = cols * cell_size + margin * 2 + sum_width
        fig_h = rows * cell_size + margin * 2 + sum_height
        
        fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h), dpi=self.dpi)
        fig.patch.set_facecolor(DEFAULT_BG_COLOR)
        ax.set_xlim(0, fig_w)
        ax.set_ylim(0, fig_h)
        ax.set_aspect('equal')
        ax.axis('off')
        
        start_x = margin
        start_y = margin
        
        for r in range(rows):
            for c in range(cols):
                x = start_x + c * cell_size
                y = start_y + (rows - 1 - r) * cell_size
                
                is_missing = missing_pos == (r, c)
                fill = FILL_COLORS["highlight"] if is_missing else FILL_COLORS["white"]
                edge = "#FF6F00" if is_missing else DEFAULT_LINE_COLOR
                
                rect = Rectangle(
                    (x, y), cell_size, cell_size,
                    facecolor=fill, edgecolor=edge,
                    linewidth=2, zorder=2
                )
                ax.add_patch(rect)
                
                val = grid[r][c]
                text = "?" if is_missing else str(val)
                
                ax.text(
                    x + cell_size / 2, y + cell_size / 2,
                    text,
                    ha='center', va='center',
                    fontsize=14, fontweight='bold',
                    color='#D32F2F' if is_missing else DEFAULT_TEXT_COLOR,
                    zorder=3
                )
        
        if row_sums:
            for r in range(rows):
                x = start_x + cols * cell_size + 0.2
                y = start_y + (rows - 1 - r) * cell_size + cell_size / 2
                ax.text(
                    x, y,
                    f"= {row_sums[r]}",
                    ha='left', va='center',
                    fontsize=12, fontweight='bold',
                    color='#1565C0',
                    zorder=3
                )
        
        if col_sums:
            for c in range(cols):
                x = start_x + c * cell_size + cell_size / 2
                y = start_y - 0.5
                ax.text(
                    x, y,
                    f"↓{col_sums[c]}",
                    ha='center', va='top',
                    fontsize=11, fontweight='bold',
                    color='#1565C0',
                    zorder=3
                )
        
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        
        return self._fig_to_rendered(fig)
    
    def render_rebus(self, equation_lines: List[str],
                      symbol_hint: str = "?",
                      title: str = "") -> RenderedDiagram:
        """Rebus equation chizish"""
        fig, ax = plt.subplots(1, 1, figsize=(8, 5), dpi=self.dpi)
        fig.patch.set_facecolor(DEFAULT_BG_COLOR)
        ax.set_xlim(0, 8)
        ax.set_ylim(0, 5)
        ax.axis('off')
        
        y_start = 4.0
        line_spacing = 0.5
        
        for i, line in enumerate(equation_lines):
            y = y_start - i * line_spacing
            ax.text(
                4, y, line,
                ha='center', va='center',
                fontsize=18, fontweight='bold',
                fontfamily='serif',
                color=DEFAULT_TEXT_COLOR,
                zorder=3
            )
        
        if symbol_hint:
            ax.text(
                4, 0.8,
                f"{symbol_hint} = ?",
                ha='center', va='center',
                fontsize=20, fontweight='bold',
                color='#D32F2F',
                bbox=dict(
                    boxstyle='round,pad=0.3',
                    facecolor=FILL_COLORS["highlight"],
                    edgecolor='#FF6F00',
                    linewidth=2
                ),
                zorder=4
            )
        
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        
        return self._fig_to_rendered(fig)
    
    def render_shape(self, shape_type: str, 
                      shape_data: Dict[str, Any],
                      highlight: Optional[str] = None,
                      title: str = "") -> RenderedDiagram:
        """Shakl puzzle chizish"""
        fig, ax = plt.subplots(1, 1, figsize=(6, 6), dpi=self.dpi)
        fig.patch.set_facecolor(DEFAULT_BG_COLOR)
        ax.set_xlim(-1, 7)
        ax.set_ylim(-1, 7)
        ax.set_aspect('equal')
        ax.axis('off')
        
        if shape_type == "triangle":
            self._draw_triangle_shape(ax, shape_data, highlight)
        elif shape_type == "square":
            self._draw_square_shape(ax, shape_data, highlight)
        elif shape_type == "rectangle":
            self._draw_rectangle_shape(ax, shape_data, highlight)
        elif shape_type == "circle":
            self._draw_circle_shape(ax, shape_data, highlight)
        
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        
        return self._fig_to_rendered(fig)
    
    def render_symbol_equation(self, equations: List[str],
                                answer_var: str = "?") -> RenderedDiagram:
        """Symbol equation chizish"""
        fig, ax = plt.subplots(1, 1, figsize=(8, 4), dpi=self.dpi)
        fig.patch.set_facecolor(DEFAULT_BG_COLOR)
        ax.set_xlim(0, 8)
        ax.set_ylim(0, 4)
        ax.axis('off')
        
        y = 3.0
        for eq in equations:
            ax.text(
                4, y, eq,
                ha='center', va='center',
                fontsize=16, fontweight='bold',
                color=DEFAULT_TEXT_COLOR,
                zorder=3
            )
            y -= 0.6
        
        ax.text(
            4, 0.8,
            f"{answer_var} = ?",
            ha='center', va='center',
            fontsize=22, fontweight='bold',
            color='#D32F2F',
            bbox=dict(
                boxstyle='round,pad=0.3',
                facecolor=FILL_COLORS["highlight"],
                edgecolor='#FF6F00',
                linewidth=2
            ),
            zorder=4
        )
        
        return self._fig_to_rendered(fig)
    
    def _draw_triangle_shape(self, ax, data: Dict, highlight: Optional[str]):
        """Uchburchak chizish"""
        sides = data.get("sides", [3, 4, 5])
        scale = 0.8
        
        a, b, c = sides[0] * scale, sides[1] * scale, sides[2] * scale
        
        v1 = (1, 1)
        v2 = (1 + a, 1)
        
        cos_c = (a * a + b * b - c * c) / (2 * a * b) if a * b > 0 else 0
        cos_c = max(-1, min(1, cos_c))
        sin_c = (1 - cos_c * cos_c) ** 0.5
        
        v3 = (1 + b * cos_c, 1 + b * sin_c)
        
        tri = Polygon(
            [v1, v2, v3],
            closed=True,
            facecolor=FILL_COLORS["light_blue"],
            edgecolor=DEFAULT_LINE_COLOR,
            linewidth=2,
            zorder=2
        )
        ax.add_patch(tri)
        
        labels = ["A", "B", "C"]
        for i, (v, lbl) in enumerate(zip([v1, v2, v3], labels)):
            offset_y = -0.3 if v[1] < 2 else 0.3
            ax.text(v[0], v[1] + offset_y, lbl,
                    ha='center', va='center', fontsize=14, fontweight='bold')
        
        mid_ab = ((v1[0] + v2[0]) / 2, (v1[1] + v2[1]) / 2 - 0.25)
        mid_bc = ((v2[0] + v3[0]) / 2 + 0.2, (v2[1] + v3[1]) / 2)
        mid_ca = ((v3[0] + v1[0]) / 2 - 0.2, (v3[1] + v1[1]) / 2)
        
        side_labels = [
            str(sides[0]) if highlight != "c" or i != 0 else "?",
            str(sides[1]) if highlight != "b" or i != 1 else "?",
            str(sides[2]) if highlight != "a" or i != 2 else "?",
        ]
        
        for mid, slbl, side_val in zip(
            [mid_ab, mid_bc, mid_ca],
            side_labels,
            sides
        ):
            is_highlight = (highlight == "side" and slbl == "?")
            color = '#D32F2F' if is_highlight else DEFAULT_TEXT_COLOR
            ax.text(mid[0], mid[1], str(side_val),
                    ha='center', va='center', fontsize=12,
                    fontweight='bold', color=color)
    
    def _draw_square_shape(self, ax, data: Dict, highlight: Optional[str]):
        """Kvadrat chizish"""
        side = data.get("side", 4)
        scale = 0.6
        
        x, y = 1.5, 1.5
        s = side * scale
        
        rect = Rectangle(
            (x, y), s, s,
            facecolor=FILL_COLORS["light_green"],
            edgecolor=DEFAULT_LINE_COLOR,
            linewidth=2,
            zorder=2
        )
        ax.add_patch(rect)
        
        label = f"{side}" if highlight != "side" else "?"
        color = '#D32F2F' if highlight == "side" else DEFAULT_TEXT_COLOR
        
        ax.text(x + s / 2, y - 0.3, label,
                ha='center', va='center', fontsize=14,
                fontweight='bold', color=color)
    
    def _draw_rectangle_shape(self, ax, data: Dict, highlight: Optional[str]):
        """To'g'ri to'rtburchak chizish"""
        w = data.get("width", 5)
        h = data.get("height", 3)
        scale = 0.5
        
        x, y = 1, 1.5
        rw, rh = w * scale, h * scale
        
        rect = Rectangle(
            (x, y), rw, rh,
            facecolor=FILL_COLORS["light_yellow"],
            edgecolor=DEFAULT_LINE_COLOR,
            linewidth=2,
            zorder=2
        )
        ax.add_patch(rect)
        
        w_label = f"{w}" if highlight != "width" else "?"
        h_label = f"{h}" if highlight != "height" else "?"
        w_color = '#D32F2F' if highlight == "width" else DEFAULT_TEXT_COLOR
        h_color = '#D32F2F' if highlight == "height" else DEFAULT_TEXT_COLOR
        
        ax.text(x + rw / 2, y - 0.3, w_label,
                ha='center', va='center', fontsize=14,
                fontweight='bold', color=w_color)
        ax.text(x - 0.3, y + rh / 2, h_label,
                ha='center', va='center', fontsize=14,
                fontweight='bold', color=h_color, rotation=90)
    
    def _draw_circle_shape(self, ax, data: Dict, highlight: Optional[str]):
        """Aylana chizish"""
        r = data.get("radius", 3)
        scale = 0.5
        
        cx, cy = 3, 3
        radius = r * scale
        
        circle = Circle(
            (cx, cy), radius,
            facecolor=FILL_COLORS["light_orange"],
            edgecolor=DEFAULT_LINE_COLOR,
            linewidth=2,
            zorder=2
        )
        ax.add_patch(circle)
        
        ax.plot(cx, cy, 'o', color=DEFAULT_LINE_COLOR, markersize=5, zorder=3)
        
        r_label = f"r={r}" if highlight != "radius" else "r=?"
        r_color = '#D32F2F' if highlight == "radius" else DEFAULT_TEXT_COLOR
        
        ax.plot([cx, cx + radius], [cy, cy], color=DEFAULT_LINE_COLOR, linewidth=1.5, zorder=3)
        ax.text(cx + radius / 2, cy + 0.2, r_label,
                ha='center', va='bottom', fontsize=12,
                fontweight='bold', color=r_color)
    
    def _fig_to_rendered(self, fig: plt.Figure) -> RenderedDiagram:
        """Figure ni RenderedDiagram ga aylantirish"""
        buf = io.BytesIO()
        fig.savefig(
            buf, format='png', dpi=self.dpi,
            bbox_inches='tight', facecolor=fig.get_facecolor(),
            edgecolor='none'
        )
        buf.seek(0)
        image_bytes = buf.read()
        buf.close()
        
        width = int(fig.get_size_inches()[0] * self.dpi)
        height = int(fig.get_size_inches()[1] * self.dpi)
        
        plt.close(fig)
        
        return RenderedDiagram(
            image_bytes=image_bytes,
            width=width,
            height=height,
            dpi=self.dpi,
        )


puzzle_diagram_renderer = PuzzleDiagramRenderer()
