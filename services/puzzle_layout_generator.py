"""
services/puzzle_layout_generator.py — ACADEMIC PUZZLE LAYOUT DESIGNER

Bu modul puzzle larni vizual tarzda chizish uchun layout specs yaratadi.
Matplotlib uchun qatorlar, ustunlar, box lar va arrow larni boshqaradi.
"""

import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class LayoutType(Enum):
    VERTICAL_ARITHMETIC = "vertical_arithmetic"
    FLOW_DIAGRAM = "flow_diagram"
    CHAIN_HORIZONTAL = "chain_horizontal"
    GRID_3X3 = "grid_3x3"
    GRID_4X4 = "grid_4x4"
    TABLE_ROWS = "table_rows"
    SCALE_BALANCE = "scale_balance"
    NUMBER_LINE = "number_line"


class BoxStyle(Enum):
    ROUNDED = "rounded"
    SQUARE = "square"
    CIRCLE = "circle"
    DIAMOND = "diamond"


@dataclass
class LayoutBox:
    """Bitta box (quti) layout da"""
    content: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    style: BoxStyle = BoxStyle.ROUNDED
    width: float = 1.0
    height: float = 0.6
    color: str = "#E8F4FD"
    border_color: str = "#2196F3"
    text_color: str = "#1565C0"
    font_size: int = 12
    is_answer: bool = False
    is_question: bool = False


@dataclass
class LayoutArrow:
    """Ikki box orasidagi arrow"""
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    label: str = ""
    style: str = "->"
    color: str = "#666666"


@dataclass
class LayoutRow:
    """Layout qator"""
    boxes: List[LayoutBox]
    height: float = 0.8


@dataclass
class PuzzleLayout:
    """To'liq puzzle layout"""
    layout_type: LayoutType
    title: str
    rows: List[List[LayoutBox]]
    arrows: List[LayoutArrow] = field(default_factory=list)
    extra_lines: List[Tuple[Tuple[float, float], Tuple[float, float]]] = field(default_factory=list)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    figure_size: Tuple[float, float] = (10, 6)
    font_family: str = "DejaVu Sans"
    
    def get_all_boxes(self) -> List[LayoutBox]:
        """Barcha box larni olish"""
        boxes = []
        for row in self.rows:
            boxes.extend(row)
        return boxes
    
    def get_box_at(self, row: int, col: int) -> Optional[LayoutBox]:
        """Berilgan pozitsiyadagi box"""
        if 0 <= row < len(self.rows):
            if 0 <= col < len(self.rows[row]):
                return self.rows[row][col]
        return None


class PuzzleLayoutGenerator:
    """
    Puzzle layout generator.
    
    AcademicPuzzleGenerator dan FilledPuzzle oladi va 
    uni vizual tarzda chizish uchun LayoutSpec yaratadi.
    """
    
    def __init__(self):
        self.theme_colors = {
            "easy": {"fill": "#E8F5E9", "border": "#4CAF50", "text": "#2E7D32"},
            "medium": {"fill": "#FFF3E0", "border": "#FF9800", "text": "#E65100"},
            "hard": {"fill": "#FFEBEE", "border": "#F44336", "text": "#C62828"},
        }
        self.default_colors = {"fill": "#E3F2FD", "border": "#2196F3", "text": "#1565C0"}
    
    def generate_layout(self, puzzle, difficulty: str = "medium") -> PuzzleLayout:
        """Puzzle ga mos layout yaratish"""
        colors = self.theme_colors.get(difficulty, self.default_colors)
        
        template_type = puzzle.template_type
        puzzle_structure = puzzle.puzzle_structure
        
        if template_type == "vertical_arithmetic":
            return self._generate_vertical_layout(puzzle, colors)
        elif template_type == "flow_diagram":
            return self._generate_flow_layout(puzzle, colors)
        elif template_type == "chain_operations":
            return self._generate_chain_layout(puzzle, colors)
        elif template_type == "grid_arithmetic":
            return self._generate_grid_layout(puzzle, colors)
        elif template_type == "symbol_unknown":
            return self._generate_symbol_layout(puzzle, colors)
        else:
            return self._generate_simple_layout(puzzle, colors)
    
    def _generate_vertical_layout(self, puzzle, colors: Dict) -> PuzzleLayout:
        """Vertical arithmetic layout"""
        values = puzzle.filled_values
        a = values.get("a", 0)
        b = values.get("b", 0)
        result = values.get("result", a + b)
        
        template_id = puzzle.puzzle_structure.split("\n")[1].strip() if puzzle.puzzle_structure else "+"
        op_symbol = "+" if "+" in template_id else "-" if "-" in template_id else "×" if "×" in template_id else "÷"
        
        rows = [
            [LayoutBox(f"{a}", 0, 0, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])],
            [LayoutBox(f"{op_symbol} {b}", 1, 0, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])],
            [LayoutBox("─────", 2, 0, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])],
            [LayoutBox(f"{result}", 3, 0, is_answer=True, color="#FFF9C4", border_color="#FBC02D", text_color="#F57F17")],
        ]
        
        return PuzzleLayout(
            layout_type=LayoutType.VERTICAL_ARITHMETIC,
            title="Vertikal arifmetika",
            rows=rows,
            figure_size=(6, 8),
        )
    
    def _generate_flow_layout(self, puzzle, colors: Dict) -> PuzzleLayout:
        """Flow diagram layout"""
        values = puzzle.filled_values
        x = values.get("x", 0)
        op1 = values.get("op1", values.get("op", "+"))
        y = values.get("y", 0)
        op2 = values.get("op2", "")
        z = values.get("z", "")
        step1 = values.get("step1", 0)
        result = values.get("result", 0)
        
        rows = [
            [LayoutBox(f"{x}", 0, 0, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])],
            [LayoutBox(f"{op1} {y}", 1, 0, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])],
            [LayoutBox(f"{step1}", 2, 0, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])],
        ]
        
        if op2:
            rows.append([LayoutBox(f"{op2} {z}", 3, 0, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])])
            rows.append([LayoutBox(f"{result}", 4, 0, is_answer=True, color="#FFF9C4", border_color="#FBC02D", text_color="#F57F17")])
        else:
            rows.append([LayoutBox(f"{result}", 3, 0, is_answer=True, color="#FFF9C4", border_color="#FBC02D", text_color="#F57F17")])
        
        arrows = [LayoutArrow(i, 0, i + 1, 0, "→") for i in range(len(rows) - 1)]
        
        return PuzzleLayout(
            layout_type=LayoutType.FLOW_DIAGRAM,
            title="Oqim diagrammasi",
            rows=rows,
            arrows=arrows,
            figure_size=(8, 10),
        )
    
    def _generate_chain_layout(self, puzzle, colors: Dict) -> PuzzleLayout:
        """Chain operations layout - horizontal"""
        values = puzzle.filled_values
        vals = values.get("values", [])
        ops = values.get("ops", [])
        
        if not vals:
            a = values.get("a", 0)
            b = values.get("b", 0)
            c = values.get("c", 0)
            step1 = values.get("step1", a + b)
            step2 = values.get("step2", step1 * c)
            step3 = values.get("step3", 0)
            subtract = values.get("subtract", 0)
            
            vals = [a, b, c, subtract]
            ops = ["+", "×", "-"]
            steps = [a, step1, step2, step3]
        else:
            steps = values.get("steps", vals)
        
        boxes = []
        for i, val in enumerate(vals):
            box = LayoutBox(
                f"{ops[i] if i > 0 else ''}{val}",
                0, i,
                color=colors["fill"],
                border_color=colors["border"],
                text_color=colors["text"]
            )
            boxes.append(box)
        
        answer_box = LayoutBox(
            f"{steps[-1]}",
            0, len(vals),
            is_answer=True,
            color="#FFF9C4",
            border_color="#FBC02D",
            text_color="#F57F17"
        )
        boxes.append(answer_box)
        
        arrows = [LayoutArrow(0, i, 0, i + 1, "→") for i in range(len(boxes) - 1)]
        
        return PuzzleLayout(
            layout_type=LayoutType.CHAIN_HORIZONTAL,
            title="Zanjir operatsiyalar",
            rows=[boxes],
            arrows=arrows,
            figure_size=(12, 3),
        )
    
    def _generate_grid_layout(self, puzzle, colors: Dict) -> PuzzleLayout:
        """Grid arithmetic layout"""
        values = puzzle.filled_values
        grid = values.get("grid", [])
        
        if not grid or not isinstance(grid[0], list):
            return self._generate_simple_layout(puzzle, colors)
        
        rows = []
        for r, row in enumerate(grid):
            row_boxes = []
            for c, cell in enumerate(row):
                content = str(cell) if cell != "?" else "?"
                is_question = cell == "?"
                row_boxes.append(LayoutBox(
                    content, r, c,
                    is_question=is_question,
                    color="#FFECB3" if is_question else colors["fill"],
                    border_color="#FF6F00" if is_question else colors["border"],
                    text_color="#E65100" if is_question else colors["text"],
                    font_size=16 if is_question else 14
                ))
            rows.append(row_boxes)
        
        magic_sum = values.get("magic_sum")
        if magic_sum:
            rows.append([LayoutBox(f"Yig'indi: {magic_sum}", len(grid), 0, col_span=3, color="#E1F5FE", border_color="#0288D1", text_color="#01579B")])
        
        return PuzzleLayout(
            layout_type=LayoutType.GRID_3X3,
            title="Jadval arifmetikasi",
            rows=rows,
            figure_size=(8, 8),
        )
    
    def _generate_symbol_layout(self, puzzle, colors: Dict) -> PuzzleLayout:
        """Symbol unknown layout"""
        values = puzzle.filled_values
        sym = values.get("symbol", values.get("sym1", "?"))
        
        rows = [
            [LayoutBox(f"{puzzle.equations[0] if puzzle.equations else '? = ?'}", 0, 0, col_span=2, color=colors["fill"], border_color=colors["border"], text_color=colors["text"])],
            [LayoutBox(f"{sym} = ?", 1, 0, is_question=True, color="#FFECB3", border_color="#FF6F00", text_color="#E65100", font_size=16)],
        ]
        
        return PuzzleLayout(
            layout_type=LayoutType.TABLE_ROWS,
            title="Belgi topish",
            rows=rows,
            figure_size=(8, 4),
        )
    
    def _generate_simple_layout(self, puzzle, colors: Dict) -> PuzzleLayout:
        """Simple text-based layout"""
        content = puzzle.puzzle_structure.strip() if puzzle.puzzle_structure else "?"
        
        rows = [[LayoutBox(
            content, 0, 0,
            color=colors["fill"],
            border_color=colors["border"],
            text_color=colors["text"],
            width=2.0,
            height=1.0,
            font_size=14
        )]]
        
        return PuzzleLayout(
            layout_type=LayoutType.TABLE_ROWS,
            title="Puzzle",
            rows=rows,
            figure_size=(10, 6),
        )


class PuzzleLayoutRenderer:
    """
    PuzzleLayout ni Matplotlib bilan chizish.
    """
    
    def __init__(self):
        self.layout_generator = PuzzleLayoutGenerator()
    
    def render(self, puzzle, difficulty: str = "medium") -> Tuple[Any, Dict]:
        """
        Puzzle ni matplotlib figurega chizish.
        
        Returns:
            (figure, layout) - matplotlib figure va layout dict
        """
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
        import numpy as np
        
        layout = self.layout_generator.generate_layout(puzzle, difficulty)
        
        fig_width, fig_height = layout.figure_size
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.set_xlim(-0.5, fig_width + 0.5)
        ax.set_ylim(-0.5, fig_height + 0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        
        for box in layout.get_all_boxes():
            self._draw_box(ax, box, fig_width, fig_height)
        
        for arrow in layout.arrows:
            self._draw_arrow(ax, arrow, fig_width, fig_height)
        
        for line in layout.extra_lines:
            x1, y1 = line[0]
            x2, y2 = line[1]
            ax.plot([x1, x2], [y1, y2], color='#666666', linewidth=2)
        
        for annotation in layout.annotations:
            ax.annotate(
                annotation.get("text", ""),
                xy=annotation.get("xy", (0, 0)),
                fontsize=annotation.get("fontsize", 10),
                color=annotation.get("color", "#333333")
            )
        
        ax.set_title(layout.title, fontsize=16, fontweight='bold', pad=20)
        
        return fig, layout
    
    def _draw_box(self, ax, box: LayoutBox, fig_width: float, fig_height: float):
        """Bitta box chizish"""
        from matplotlib.patches import FancyBboxPatch
        
        col_width = fig_width / max(len(row) for row in [box] if hasattr(box, 'col'))
        x = box.col * 1.5 + 1
        y = fig_height - box.row * 1.2 - 1.5
        
        if box.style == BoxStyle.ROUNDED:
            rect = FancyBboxPatch(
                (x, y), box.width, box.height,
                boxstyle="round,pad=0.05,rounding_size=0.2",
                facecolor=box.color,
                edgecolor=box.border_color,
                linewidth=2
            )
        elif box.style == BoxStyle.CIRCLE:
            circle = patches.Circle((x + box.width/2, y + box.height/2), box.width/2,
                                    facecolor=box.color, edgecolor=box.border_color, linewidth=2)
            ax.add_patch(circle)
            rect = None
        elif box.style == BoxStyle.DIAMOND:
            diamond = patches.RegularPolygon(
                (x + box.width/2, y + box.height/2), 4, box.width/2,
                facecolor=box.color, edgecolor=box.border_color, linewidth=2,
                orientation=np.pi/4
            )
            ax.add_patch(diamond)
            rect = None
        else:
            rect = patches.Rectangle(
                (x, y), box.width, box.height,
                facecolor=box.color,
                edgecolor=box.border_color,
                linewidth=2
            )
        
        if rect:
            ax.add_patch(rect)
        
        weight = 'bold' if box.is_question or box.is_answer else 'normal'
        ax.text(x + box.width/2, y + box.height/2, box.content,
                ha='center', va='center', fontsize=box.font_size,
                fontweight=weight, color=box.text_color)
    
    def _draw_arrow(self, ax, arrow: LayoutArrow, fig_width: float, fig_height: float):
        """Arrow chizish"""
        from matplotlib.patches import FancyArrowPatch
        
        x1 = arrow.from_col * 1.5 + 2
        y1 = fig_height - arrow.from_row * 1.2 - 1.8
        x2 = arrow.to_col * 1.5 + 2
        y2 = fig_height - arrow.to_row * 1.2 - 1.8
        
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle="->", color=arrow.color, lw=2))
        
        if arrow.label:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            ax.text(mid_x, mid_y, arrow.label, fontsize=10, ha='center', va='center', color=arrow.color)


puzzle_layout_generator = PuzzleLayoutGenerator()
puzzle_layout_renderer = PuzzleLayoutRenderer()
