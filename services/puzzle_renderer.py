"""
services/puzzle_renderer.py — PUZZLE RENDERING ENGINE

Puzzle spec olib rasm generatsiya qilish.
Grid, box, sequence, symbols, pattern blocklar chizish.
"""

import io
import random
import numpy as np
from typing import List, Dict, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Polygon, FancyArrowPatch
from matplotlib.patches import Arc
import matplotlib.patches as patches

from services.render_specs import (
    PuzzleRenderSpec, GridPuzzleSpec, LogicGridSpec, RenderMetadata,
    VerticalArithmeticSpec, FlowDiagramSpec, ChainOperationsSpec, RebusPuzzleSpec
)
from services.render_primitives import (
    setup_figure, export_to_bytes, cleanup_figure,
    draw_box, draw_rounded_box, draw_arrow, draw_chain_node,
    draw_grid_cell, draw_number_cell, draw_label, draw_table_layout,
    DEFAULT_LINE_COLOR, DEFAULT_TEXT_COLOR, DEFAULT_BG_COLOR, FILL_COLORS
)


class PuzzleRenderer:
    """
    Puzzle render engine.
    
    Puzzle spec olib image bytes qaytaradi.
    """
    
    def __init__(self):
        self.default_size = (8, 6)
        self.default_dpi = 150
    
    def render(self, spec: PuzzleRenderSpec) -> Tuple[bytes, RenderMetadata]:
        """Puzzle render qilish"""
        import time
        start_time = time.time()
        
        try:
            if isinstance(spec, GridPuzzleSpec):
                return self._render_grid_puzzle(spec, start_time)
            elif isinstance(spec, LogicGridSpec):
                return self._render_logic_grid(spec, start_time)
            elif isinstance(spec, VerticalArithmeticSpec):
                return self._render_vertical_arithmetic(spec, start_time)
            elif isinstance(spec, FlowDiagramSpec):
                return self._render_flow_diagram(spec, start_time)
            elif isinstance(spec, ChainOperationsSpec):
                return self._render_chain_operations(spec, start_time)
            elif isinstance(spec, RebusPuzzleSpec):
                return self._render_rebus_puzzle(spec, start_time)
            else:
                return self._render_generic_puzzle(spec, start_time)
        
        except Exception as e:
            metadata = RenderMetadata(
                render_time_ms=(time.time() - start_time) * 1000,
                fallback_used=True,
                fallback_reason=str(e)
            )
            return self._render_fallback(spec, metadata)
    
    def _render_grid_puzzle(self, spec: GridPuzzleSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Grid puzzle render"""
        fig, ax = setup_figure(spec.width, spec.height, spec.dpi)
        
        rows, cols = spec.grid_size
        cell_size = min(5.0 / rows, 5.0 / cols, 1.5)
        start_x = (spec.width - cols * cell_size) / 2
        start_y = (spec.height - rows * cell_size) / 2
        
        self._draw_grid(ax, rows, cols, cell_size, start_x, start_y)
        
        self._fill_grid_cells(ax, spec, cell_size, start_x, start_y)
        
        ax.set_title("Mantiqiy qatorni to'ldiring", fontsize=14, fontweight='bold', pad=10)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=spec.dpi, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        image_bytes = buf.getvalue()
        plt.close()
        
        metadata = RenderMetadata(
            render_time_ms=(time.time() - start_time) * 1000,
            width=spec.width,
            height=spec.height,
            signature=spec.render_signature
        )
        
        return image_bytes, metadata
    
    def _render_logic_grid(self, spec: LogicGridSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Logic grid puzzle render"""
        fig, ax = setup_figure(spec.width, spec.height, spec.dpi)
        
        rows, cols = spec.grid_size
        cell_size = min(5.0 / rows, 5.0 / cols, 1.5)
        start_x = (spec.width - cols * cell_size) / 2
        start_y = (spec.height - rows * cell_size) / 2
        
        pattern = spec.pattern if spec.pattern else [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        
        for i in range(rows):
            for j in range(cols):
                x = start_x + j * cell_size
                y = start_y + (rows - i - 1) * cell_size
                
                if pattern[i][j] == 1:
                    rect = FancyBboxPatch(
                        (x + 0.02, y + 0.02), cell_size - 0.04, cell_size - 0.04,
                        boxstyle="round,pad=0.02,rounding_size=0.1",
                        facecolor='#E8F5E9', edgecolor='#4CAF50',
                        linewidth=2
                    )
                else:
                    rect = FancyBboxPatch(
                        (x + 0.02, y + 0.02), cell_size - 0.04, cell_size - 0.04,
                        boxstyle="round,pad=0.02,rounding_size=0.1",
                        facecolor='#FFEBEE', edgecolor='#F44336',
                        linewidth=2
                    )
                
                ax.add_patch(rect)
                
                if pattern[i][j] == 1:
                    circle = Circle((x + cell_size/2, y + cell_size/2), cell_size * 0.25,
                                    color='#4CAF50', zorder=2)
                    ax.add_patch(circle)
                else:
                    ax.plot([x + 0.15, x + cell_size - 0.15], 
                           [y + cell_size - 0.15, y + 0.15],
                           color='#F44336', linewidth=2, zorder=2)
                    ax.plot([x + 0.15, x + cell_size - 0.15],
                           [y + 0.15, y + cell_size - 0.15],
                           color='#F44336', linewidth=2, zorder=2)
        
        ax.set_title("Mantiqiy qatorni to'ldiring", fontsize=14, fontweight='bold', pad=10)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=spec.dpi, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        image_bytes = buf.getvalue()
        plt.close()
        
        metadata = RenderMetadata(
            render_time_ms=(time.time() - start_time) * 1000,
            width=spec.width,
            height=spec.height,
            signature=spec.render_signature
        )
        
        return image_bytes, metadata
    
    def _render_generic_puzzle(self, spec: PuzzleRenderSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Generic puzzle render"""
        fig, ax = setup_figure(spec.width, spec.height, spec.dpi)
        
        ax.text(0.5, 0.5, f"Puzzle: {spec.topic}",
               transform=ax.transAxes, fontsize=16, ha='center', va='center')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=spec.dpi, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        image_bytes = buf.getvalue()
        plt.close()
        
        metadata = RenderMetadata(
            render_time_ms=(time.time() - start_time) * 1000,
            width=spec.width,
            height=spec.height,
            signature=spec.render_signature
        )
        
        return image_bytes, metadata
    
    def _draw_grid(self, ax, rows: int, cols: int, cell_size: float, start_x: float, start_y: float):
        """Grid chizish"""
        for i in range(rows + 1):
            y = start_y + i * cell_size
            ax.plot([start_x, start_x + cols * cell_size], [y, y],
                   color='#333', linewidth=1.5)
        
        for j in range(cols + 1):
            x = start_x + j * cell_size
            ax.plot([x, x], [start_y, start_y + rows * cell_size],
                   color='#333', linewidth=1.5)
    
    def _fill_grid_cells(self, ax, spec: GridPuzzleSpec, cell_size: float, start_x: float, start_y: float):
        """Grid kataklarini to'ldirish"""
        rows, cols = spec.grid_size
        cells = spec.cells if spec.cells else []
        
        for i in range(rows):
            for j in range(cols):
                x = start_x + j * cell_size + cell_size / 2
                y = start_y + (rows - i - 1) * cell_size + cell_size / 2
                
                idx = i * cols + j
                if idx < len(cells):
                    value = cells[idx]
                    if value == "?" or value is None:
                        draw_unknown_marker(ax, (x, y), marker_type="x", size=cell_size * 0.2)
                    else:
                        ax.text(x, y, str(value), fontsize=12, ha='center', va='center',
                               fontweight='bold', color='#333')
                else:
                    ax.text(x, y, "?", fontsize=12, ha='center', va='center',
                           color='#999')
    
    def _render_vertical_arithmetic(self, spec: VerticalArithmeticSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Vertical arithmetic render - Academic style"""
        fig, ax = setup_figure(4, 5, 150)
        
        nums = spec.numbers
        n_count = len(nums)
        
        # Draw numbers with proper alignment
        for i, val in enumerate(nums):
            y_pos = 0.8 - i * 0.15
            draw_label(ax, 0.8, y_pos, str(val), fontsize=24, ha='right', fontweight='normal')
            
        # Draw operation symbol
        if spec.operation:
            draw_label(ax, 0.35, 0.8 - (n_count - 1) * 0.15, spec.operation, fontsize=24, ha='center')
            
        # Draw line
        if spec.has_line:
            ax.plot([0.3, 0.9], [0.8 - (n_count - 0.5) * 0.15, 0.8 - (n_count - 0.5) * 0.15], 
                   color=DEFAULT_LINE_COLOR, lw=2)
            
        # Draw result or unknown
        res_y = 0.8 - (n_count + 0.2) * 0.15
        if spec.result is not None:
            draw_label(ax, 0.8, res_y, str(spec.result), fontsize=26, ha='right', fontweight='bold')
        else:
            draw_label(ax, 0.8, res_y, "?", fontsize=26, ha='right', fontweight='bold', color='red')
            
        return self._finalize_render(fig, spec, start_time)

    def _render_flow_diagram(self, spec: FlowDiagramSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Flow diagram render - Using professional boxes and arrows"""
        fig, ax = setup_figure(10, 4, 150)
        
        for i, step in enumerate(spec.steps):
            x, y = i * 2.5 + 1, 2.0
            
            # Use rounded boxes for flow nodes
            draw_rounded_box(ax, x-0.8, y-0.5, 1.6, 1.0, 
                             content=step.get("text", ""), 
                             fill_color=FILL_COLORS["light_gray"], 
                             border_color=DEFAULT_LINE_COLOR)
            
            if i < len(spec.steps) - 1:
                # Use professional arrows
                draw_arrow(ax, x+0.9, y, x+1.6, y, 
                          linewidth=1.5, style="->")
                
        return self._finalize_render(fig, spec, start_time)

    def _render_chain_operations(self, spec: ChainOperationsSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Chain operations render - Textbook style circles and symbols"""
        fig, ax = setup_figure(12, 3, 150)
        
        for i, val in enumerate(spec.values):
            x = i * 2.5 + 1
            
            # Use chain nodes (circles)
            draw_chain_node(ax, x, 1.5, radius=0.6, 
                           content=str(val) if val is not None else "?",
                           fill_color=FILL_COLORS["white"])
            
            if i < len(spec.operations):
                op = spec.operations[i]
                # Operation label above arrow
                draw_label(ax, x + 1.25, 1.9, op, fontsize=16, fontweight='bold', color='blue')
                # Professional arrow
                draw_arrow(ax, x+0.7, 1.5, x+1.8, 1.5, linewidth=1.5)
                
        return self._finalize_render(fig, spec, start_time)

    def _render_rebus_puzzle(self, spec: RebusPuzzleSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Rebus puzzle render"""
        fig, ax = setup_figure(8, 6, 150)
        
        ax.text(0.5, 0.7, spec.equation_text, transform=ax.transAxes, fontsize=28, ha='center', family='serif')
        
        if spec.symbols_map:
            y_start = 0.4
            for i, (sym, val) in enumerate(spec.symbols_map.items()):
                ax.text(0.3, y_start - i*0.1, f"{sym} = ?", transform=ax.transAxes, fontsize=20, ha='left')
                
        if spec.question_text:
            ax.text(0.5, 0.1, spec.question_text, transform=ax.transAxes, fontsize=16, ha='center', color='darkgreen', style='italic')
            
        return self._finalize_render(fig, spec, start_time)

    def _finalize_render(self, fig, spec, start_time) -> Tuple[bytes, RenderMetadata]:
        """Bufferga yozish va cleanup"""
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=spec.dpi, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        image_bytes = buf.getvalue()
        plt.close(fig)
        
        metadata = RenderMetadata(
            render_time_ms=(time.time() - start_time) * 1000,
            width=spec.width,
            height=spec.height,
            signature=spec.render_signature
        )
        return image_bytes, metadata

    def _render_fallback(self, spec: PuzzleRenderSpec, metadata: RenderMetadata) -> Tuple[bytes, RenderMetadata]:
        """Fallback render - sodda ko'rinish"""
        fig, ax = setup_figure(6, 4, 100)
        
        ax.text(0.5, 0.7, "Puzzle", transform=ax.transAxes,
               fontsize=24, ha='center', fontweight='bold')
        ax.text(0.5, 0.4, spec.topic or "Savol", transform=ax.transAxes,
               fontsize=14, ha='center')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        image_bytes = buf.getvalue()
        plt.close(fig)
        
        return image_bytes, metadata


puzzle_renderer = PuzzleRenderer()
