import os
import random
import io
import base64
import hashlib
import logging
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon, Rectangle, Arc, Wedge
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PuzzleCategory(Enum):
    CHAIN = "chain"
    GRID = "grid"
    REBUS = "rebus"
    SHAPE = "shape"
    FLOWCHART = "flowchart"
    MIXED = "mixed"


@dataclass
class PuzzleOutput:
    """
    Unified puzzle output format.
    
    Har bir puzzle uchun:
    - puzzle_text: matn ko'rinishida
    - visual_spec: diagram ma'lumotlari
    - correct_answer: to'g'ri javob
    - options: A, B, C, D variantlar
    - correct_label: to'g'ri variant harfi
    - explanation: tushuntirish
    - difficulty: qiyinlik darajasi
    - category: puzzle turi
    - diagram_bytes: PNG rasm (optional)
    - equations: matematik ifodalar
    - uniqueness_signature: noyob imzo
    """
    puzzle_text: str
    visual_spec: Dict[str, Any]
    correct_answer: Any
    options: Dict[str, Any]
    correct_label: str
    explanation: str
    difficulty: str
    category: str
    grade: int
    equations: List[str]
    uniqueness_signature: str
    diagram_bytes: Optional[bytes] = None
    internal_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "text": self.puzzle_text,
            "answer": self.correct_answer,
            "options": self.options,
            "correct": self.correct_label,
            "explanation": self.explanation,
            "difficulty": self.difficulty,
            "category": self.category,
            "grade": self.grade,
            "equations": self.equations,
            "signature": self.uniqueness_signature,
            "has_diagram": self.diagram_bytes is not None,
        }

class PuzzlePool:
    LOGIC_GRID_TEMPLATES = []
    CROSSWORD_TEMPLATES = []
    LABYRINTH_TEMPLATES = []
    SCALE_TEMPLATES = []
    
    PUZZLE_TYPES = ["logic_grid", "crossword", "labyrinth", "scale"]
    
    def __init__(self, pool_dir: str = "temp_puzzles"):
        self.pool_dir = pool_dir
        self._init_templates()
    
    def _init_templates(self):
        self.LOGIC_GRID_TEMPLATES = self._generate_logic_grid_templates()
        self.CROSSWORD_TEMPLATES = self._generate_crossword_templates()
        self.LABYRINTH_TEMPLATES = self._generate_labyrinth_templates()
        self.SCALE_TEMPLATES = self._generate_scale_templates()
    
    def _generate_logic_grid_templates(self) -> List[Dict]:
        templates = []
        
        patterns = [
            [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            [[1, 1, 0], [0, 1, 1], [1, 0, 1]],
            [[1, 0, 1], [1, 1, 0], [0, 1, 1]],
            [[0, 1, 1], [1, 0, 1], [1, 1, 0]],
            [[1, 1, 1], [1, 0, 0], [0, 1, 0]],
            [[0, 0, 1], [1, 0, 0], [0, 1, 1]],
            [[1, 0, 0], [1, 0, 1], [0, 1, 1]],
            [[0, 1, 0], [0, 0, 1], [1, 1, 0]],
            [[1, 1, 0], [1, 0, 1], [0, 1, 1]],
            [[0, 0, 0], [1, 1, 1], [0, 1, 0]],
            [[1, 0, 1], [0, 0, 1], [1, 1, 0]],
            [[0, 1, 1], [1, 0, 0], [1, 1, 0]],
            [[1, 1, 1], [0, 1, 0], [1, 0, 1]],
            [[0, 0, 1], [1, 1, 0], [1, 0, 1]],
            [[1, 0, 1], [1, 1, 0], [0, 0, 1]],
            [[0, 1, 0], [1, 0, 1], [1, 0, 0]],
            [[1, 1, 0], [0, 1, 0], [1, 0, 1]],
            [[0, 0, 1], [0, 1, 0], [1, 1, 1]],
            [[1, 0, 0], [0, 1, 1], [1, 0, 1]],
            [[0, 1, 1], [1, 0, 0], [0, 1, 1]],
        ]
        
        for i, pattern in enumerate(patterns):
            templates.append({
                "id": f"logic_grid_{i+1}",
                "pattern": pattern,
                "type": "3x3_grid"
            })
        
        for i in range(30):
            size = random.choice([3, 4])
            pattern = [[random.randint(0, 1) for _ in range(size)] for _ in range(size)]
            templates.append({
                "id": f"logic_grid_{i+21}",
                "pattern": pattern,
                "type": f"{size}x{size}_grid"
            })
        
        return templates
    
    def _generate_crossword_templates(self) -> List[Dict]:
        templates = []
        
        words = [
            ["MATEMATIKA", "SON", "GEOMETRIYA"],
            ["ALGEBRA", "TENGLAMA", "FORMULA"],
            ["UCHBURCHAK", "AYLANA", "KVADRAT"],
            ["TRAKTRISA", "TRAPETSIYA", "PARALELLOGRAMM"],
            ["HOSILA", "INTEGRAL", "LIMIT"],
            ["SINUS", "KOSINUS", "TANGENS"],
            ["PERIMETR", "YUZ A", "HAJM"],
            ["PROGRESSIYA", "ARIFMETIKA", "GEOMETRIYA"],
            ["EHTIMOLLIK", "KOMBINATORIKA", "VARIANT"],
            ["LOGARIFM", "EKSPONENT", "DISKRIMINANT"],
            ["MEDIAN", "BISSEKTRISA", "BALANDLIK"],
            ["PYTAGOR", "VIETA", "STEWART"],
            ["PIRAMIDA", "PRIZMA", "SILINDR"],
            ["KONUS", "SHAR", "KUB"],
            ["FRAKSIYA", "SURAT", "MAXRAJ"],
            ["MODUL", "KOORDINATA", "VEKTOR"],
            ["TENGSIZLIK", "SISTEMA", "MATRISA"],
            ["OPERATOR", "FUNKSIYA", "GRAFIK"],
            ["MANTIQ", "SET", "KIRISH"],
            ["CHIQISH", "YUL", "Maze"]
        ]
        
        for i, word_list in enumerate(words):
            templates.append({
                "id": f"crossword_{i+1}",
                "words": word_list,
                "type": "simple_crossword"
            })
        
        for i in range(30):
            word_list = random.sample([
                "SALOM", "KITOB", "QALAM", "RUCHKA", "DAFTAR",
                "MAKTAB", "USTOZ", "SHOGIRD", "BILIM", "FAN",
                "SONLAR", "QOSHISH", "AYIRISH", "KOPAYTIRISH",
                "BOLISH", "NATIJ A", "JAVOB", "MASALA", "YECHIM"
            ], 3)
            templates.append({
                "id": f"crossword_{i+21}",
                "words": word_list,
                "type": "random_crossword"
            })
        
        return templates
    
    def _generate_labyrinth_templates(self) -> List[Dict]:
        templates = []
        
        mazes = [
            {
                "grid": [
                    [1, 1, 1, 1],
                    [0, 0, 0, 1],
                    [1, 1, 0, 1],
                    [1, 1, 0, 0]
                ],
                "start": (1, 0),
                "end": (3, 3)
            },
            {
                "grid": [
                    [1, 0, 1, 1],
                    [1, 0, 0, 1],
                    [1, 1, 0, 1],
                    [0, 0, 0, 1]
                ],
                "start": (0, 0),
                "end": (3, 3)
            },
            {
                "grid": [
                    [1, 1, 1, 1],
                    [1, 0, 0, 0],
                    [1, 1, 1, 0],
                    [0, 0, 0, 0]
                ],
                "start": (0, 0),
                "end": (3, 3)
            },
            {
                "grid": [
                    [1, 0, 0, 1],
                    [0, 0, 1, 1],
                    [1, 1, 0, 0],
                    [1, 1, 1, 1]
                ],
                "start": (0, 0),
                "end": (2, 3)
            },
            {
                "grid": [
                    [0, 1, 1, 1],
                    [1, 0, 0, 1],
                    [1, 1, 0, 0],
                    [1, 1, 1, 0]
                ],
                "start": (0, 0),
                "end": (3, 3)
            },
        ]
        
        for i, maze in enumerate(mazes):
            templates.append({
                "id": f"labyrinth_{i+1}",
                "maze": maze,
                "type": "4x4_maze"
            })
        
        for size in [3, 4, 5]:
            for _ in range(15):
                grid = [[1 if random.random() > 0.35 else 0 for _ in range(size)] for _ in range(size)]
                grid[0][0] = 1
                grid[-1][-1] = 1
                
                templates.append({
                    "id": f"labyrinth_{size}x{size}_{_}",
                    "maze": {"grid": grid, "start": (0, 0), "end": (size-1, size-1)},
                    "type": f"{size}x{size}_maze"
                })
        
        return templates
    
    def _generate_scale_templates(self) -> List[Dict]:
        templates = []
        
        scale_data = [
            {"left": [3, 5], "right": [8], "balanced": False},
            {"left": [4, 6], "right": [10], "balanced": False},
            {"left": [2, 8], "right": [5, 5], "balanced": True},
            {"left": [7], "right": [3, 4], "balanced": True},
            {"left": [1, 9], "right": [5, 5], "balanced": True},
            {"left": [6, 2], "right": [4, 4], "balanced": True},
            {"left": [10], "right": [5, 5], "balanced": True},
            {"left": [3, 3, 3], "right": [9], "balanced": True},
            {"left": [4, 2], "right": [6], "balanced": True},
            {"left": [8, 1], "right": [9], "balanced": True},
            {"left": [2, 4], "right": [3, 3], "balanced": True},
            {"left": [5, 5], "right": [10], "balanced": False},
            {"left": [1, 7], "right": [4, 4], "balanced": True},
            {"left": [6, 3], "right": [9], "balanced": True},
            {"left": [2, 2, 2], "right": [6], "balanced": True},
            {"left": [3, 7], "right": [5, 5], "balanced": True},
            {"left": [8], "right": [4, 4], "balanced": True},
            {"left": [1, 1, 1], "right": [3], "balanced": True},
            {"left": [4, 5], "right": [9], "balanced": True},
            {"left": [2, 6], "right": [4, 4], "balanced": True},
        ]
        
        for i, data in enumerate(scale_data):
            templates.append({
                "id": f"scale_{i+1}",
                "left": data["left"],
                "right": data["right"],
                "balanced": data["balanced"],
                "type": "balance_scale"
            })
        
        for i in range(30):
            left_count = random.randint(1, 3)
            right_count = random.randint(1, 3)
            left = [random.randint(1, 10) for _ in range(left_count)]
            right = [random.randint(1, 10) for _ in range(right_count)]
            
            left_sum = sum(left)
            right_sum = sum(right)
            balanced = left_sum == right_sum
            
            templates.append({
                "id": f"scale_{i+21}",
                "left": left,
                "right": right,
                "balanced": balanced,
                "type": "balance_scale"
            })
        
        return templates
    
    def get_random_puzzle(self, puzzle_type: str = None) -> Dict:
        if puzzle_type is None:
            puzzle_type = random.choice(self.PUZZLE_TYPES)
        
        if puzzle_type == "logic_grid":
            return random.choice(self.LOGIC_GRID_TEMPLATES)
        elif puzzle_type == "crossword":
            return random.choice(self.CROSSWORD_TEMPLATES)
        elif puzzle_type == "labyrinth":
            return random.choice(self.LABYRINTH_TEMPLATES)
        elif puzzle_type == "scale":
            return random.choice(self.SCALE_TEMPLATES)
        
        return random.choice(self.LOGIC_GRID_TEMPLATES)
    
    def get_random_image(self, puzzle_type: str = None) -> bytes:
        puzzle = self.get_random_puzzle(puzzle_type)
        
        if puzzle["type"] in ["3x3_grid", "4x4_grid", "5x5_grid"] or "x" in puzzle["type"]:
            return self.draw_logic_grid(puzzle["pattern"])
        elif puzzle["type"] in ["simple_crossword", "random_crossword"]:
            return self.draw_crossword(puzzle["words"])
        elif "maze" in puzzle["type"]:
            return self.draw_labyrinth(puzzle["maze"]["grid"], puzzle["maze"]["start"], puzzle["maze"]["end"])
        elif puzzle["type"] == "balance_scale":
            return self.draw_scale(puzzle["left"], puzzle["right"])
        
        return self.draw_logic_grid([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    
    def draw_logic_grid(self, pattern: List[List[int]], figsize: Tuple[int, int] = (6, 6)) -> bytes:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_xlim(-0.5, len(pattern[0]) + 0.5)
        ax.set_ylim(-0.5, len(pattern) + 0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        
        for i, row in enumerate(pattern):
            for j, cell in enumerate(row):
                x, y = j, len(pattern) - i - 1
                
                rect = FancyBboxPatch(
                    (x - 0.45, y - 0.45), 0.9, 0.9,
                    boxstyle="round,pad=0.02,rounding_size=0.1",
                    facecolor='#E8F5E9' if cell == 1 else '#FFEBEE',
                    edgecolor='#4CAF50' if cell == 1 else '#F44336',
                    linewidth=2
                )
                ax.add_patch(rect)
                
                if cell == 1:
                    circle = Circle((x, y), 0.2, color='#4CAF50', zorder=2)
                    ax.add_patch(circle)
                else:
                    ax.plot([x - 0.2, x + 0.2], [y + 0.2, y - 0.2], color='#F44336', linewidth=2, zorder=2)
                    ax.plot([x - 0.2, x + 0.2], [y - 0.2, y + 0.2], color='#F44336', linewidth=2, zorder=2)
        
        ax.set_title("Mantiqiy qatorni to'ldiring", fontsize=14, fontweight='bold', pad=10)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        img_bytes = buf.getvalue()
        plt.close()
        
        return img_bytes
    
    def draw_crossword(self, words: List[str], figsize: Tuple[int, int] = (8, 6)) -> bytes:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_xlim(-1, 17)
        ax.set_ylim(-4, 2)
        ax.set_aspect('equal')
        ax.axis('off')
        
        ax.add_patch(FancyBboxPatch((-0.5, -0.5), 11, 2.5,
                                     boxstyle="round,pad=0.05",
                                     facecolor='white', edgecolor='#333',
                                     linewidth=2))
        
        ax.text(5, 1.2, "KROSSVORD", ha='center', va='center',
                fontsize=14, fontweight='bold', color='#333')
        
        start_y = -0.3
        for i, word in enumerate(words):
            y = start_y - i * 0.6
            
            box = FancyBboxPatch((0.5, y - 0.2), 2, 0.4,
                                  boxstyle="round,pad=0.02",
                                  facecolor='#FFF9C4', edgecolor='#FBC02D',
                                  linewidth=1.5)
            ax.add_patch(box)
            ax.text(1.5, y, f"{i+1}.", ha='center', va='center', fontsize=10, fontweight='bold')
            
            word_box = FancyBboxPatch((3, y - 0.2), len(word) * 0.5 + 0.5, 0.4,
                                       boxstyle="round,pad=0.02",
                                       facecolor='#E3F2FD', edgecolor='#2196F3',
                                       linewidth=1.5)
            ax.add_patch(word_box)
            ax.text(3.5 + len(word) * 0.25, y, word, ha='left', va='center',
                    fontsize=10, fontweight='bold', color='#1565C0')
            
            underline = plt.Line2D([3, 3 + len(word) * 0.5 + 0.3], [y - 0.25, y - 0.25],
                                    color='#333', linewidth=1)
            ax.add_line(underline)
        
        ax.text(13, 0, "So'zlarni\ntoping va\njoylashtiring",
                ha='center', va='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='#F3E5F5', edgecolor='#9C27B0', linewidth=2),
                color='#7B1FA2')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        img_bytes = buf.getvalue()
        plt.close()
        
        return img_bytes
    
    def draw_labyrinth(self, grid: List[List[int]], start: Tuple[int, int], end: Tuple[int, int],
                       figsize: Tuple[int, int] = (6, 6)) -> bytes:
        fig, ax = plt.subplots(figsize=figsize)
        
        rows, cols = len(grid), len(grid[0])
        ax.set_xlim(-0.5, cols + 0.5)
        ax.set_ylim(-0.5, rows + 0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        
        for i in range(rows):
            for j in range(cols):
                x, y = j, rows - i - 1
                
                if grid[i][j] == 1:
                    rect = Rectangle((x - 0.45, y - 0.45), 0.9, 0.9,
                                     facecolor='#37474F', edgecolor='#263238',
                                     linewidth=1)
                    ax.add_patch(rect)
                else:
                    rect = Rectangle((x - 0.45, y - 0.45), 0.9, 0.9,
                                     facecolor='#ECEFF1', edgecolor='#90A4AE',
                                     linewidth=1)
                    ax.add_patch(rect)
        
        ax.add_patch(Circle((start[0], rows - start[1] - 1), 0.2,
                            facecolor='#4CAF50', edgecolor='#2E7D32', linewidth=2, zorder=3))
        ax.text(start[0], rows - start[1] - 1, "S", ha='center', va='center',
                fontsize=8, fontweight='bold', color='white', zorder=4)
        
        ax.add_patch(Circle((end[0], rows - end[1] - 1), 0.2,
                            facecolor='#F44336', edgecolor='#C62828', linewidth=2, zorder=3))
        ax.text(end[0], rows - end[1] - 1, "C", ha='center', va='center',
                fontsize=8, fontweight='bold', color='white', zorder=4)
        
        ax.set_title("LABIRINT", fontsize=14, fontweight='bold', pad=10)
        
        ax.text(cols / 2, -0.8, "S = Kirish    C = Chiqish", ha='center',
                fontsize=10, color='#555')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        img_bytes = buf.getvalue()
        plt.close()
        
        return img_bytes
    
    def draw_scale(self, left_weights: List[int], right_weights: List[int],
                   figsize: Tuple[int, int] = (8, 6)) -> bytes:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_xlim(-1, 9)
        ax.set_ylim(-1, 7)
        ax.set_aspect('equal')
        ax.axis('off')
        
        ax.plot([4, 4], [0, 6], color='#5D4037', linewidth=4)
        
        base = FancyBboxPatch((2.5, -0.5), 3, 0.5,
                               boxstyle="round,pad=0.05",
                               facecolor='#795548', edgecolor='#4E342E',
                               linewidth=2)
        ax.add_patch(base)
        
        ax.plot([1, 7], [5.5, 5.5], color='#5D4037', linewidth=3)
        
        left_tilt = 0
        right_tilt = 0
        left_sum = sum(left_weights)
        right_sum = sum(right_weights)
        
        if left_sum > right_sum:
            left_tilt = -0.3
        elif right_sum > left_sum:
            right_tilt = -0.3
        
        left_pan_x = 1.5 + left_tilt
        right_pan_x = 6.5 + right_tilt
        pan_y = 5
        
        ax.plot([left_pan_x, left_pan_x], [5.5, pan_y + 0.3], color='#5D4037', linewidth=2)
        ax.plot([right_pan_x, right_pan_x], [5.5, pan_y + 0.3], color='#5D4037', linewidth=2)
        
        left_pan = FancyBboxPatch((left_pan_x - 1, pan_y - 0.5), 2, 0.3,
                                    boxstyle="round,pad=0.02",
                                    facecolor='#8D6E63', edgecolor='#5D4037',
                                    linewidth=2)
        ax.add_patch(left_pan)
        
        right_pan = FancyBboxPatch((right_pan_x - 1, pan_y - 0.5), 2, 0.3,
                                     boxstyle="round,pad=0.02",
                                     facecolor='#8D6E63', edgecolor='#5D4037',
                                     linewidth=2)
        ax.add_patch(right_pan)
        
        left_spacing = 1.8 / max(len(left_weights), 1)
        for i, w in enumerate(left_weights):
            cx = left_pan_x - 0.7 + left_spacing * (i + 0.5)
            circle = Circle((cx, pan_y - 0.8), 0.25, facecolor='#F44336',
                            edgecolor='#C62828', linewidth=2)
            ax.add_patch(circle)
            ax.text(cx, pan_y - 0.8, str(w), ha='center', va='center',
                   fontsize=8, fontweight='bold', color='white')
        
        right_spacing = 1.8 / max(len(right_weights), 1)
        for i, w in enumerate(right_weights):
            cx = right_pan_x - 0.7 + right_spacing * (i + 0.5)
            circle = Circle((cx, pan_y - 0.8), 0.25, facecolor='#2196F3',
                            edgecolor='#1565C0', linewidth=2)
            ax.add_patch(circle)
            ax.text(cx, pan_y - 0.8, str(w), ha='center', va='center',
                   fontsize=8, fontweight='bold', color='white')
        
        balance_status = "Muvojan" if left_sum == right_sum else ("Chap tomon og'ir" if left_sum > right_sum else "O'ng tomon og'ir")
        
        ax.text(4, 6.5, "TAROZINI MUVOZANATLANG", ha='center', va='center',
               fontsize=12, fontweight='bold', color='#333')
        
        status_color = '#4CAF50' if left_sum == right_sum else '#FF9800'
        ax.text(4, -0.8, f"Yig'indilar: Chap={left_sum} | O'ng={right_sum} | {balance_status}",
               ha='center', va='center', fontsize=10, color=status_color, fontweight='bold')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        img_bytes = buf.getvalue()
        plt.close()
        
        return img_bytes
    
    def generate_logic_puzzle(self, grade: int = 5, difficulty: str = "oson") -> Dict:
        """
        LOGIC PUZZLE GENERATOR
        
        Generates non-trivial puzzle questions with clear logical rules.
        """
        puzzle_types = [
            "arithmetic_sequence",
            "shape_pattern", 
            "odd_one_out",
            "symbol_relation",
            "number_grid"
        ]
        
        puzzle_type = random.choice(puzzle_types)
        
        if puzzle_type == "arithmetic_sequence":
            return self._generate_arithmetic_sequence_puzzle(grade, difficulty)
        elif puzzle_type == "shape_pattern":
            return self._generate_shape_pattern_puzzle(grade, difficulty)
        elif puzzle_type == "odd_one_out":
            return self._generate_odd_one_out_puzzle(grade, difficulty)
        elif puzzle_type == "symbol_relation":
            return self._generate_symbol_relation_puzzle(grade, difficulty)
        else:
            return self._generate_number_grid_puzzle(grade, difficulty)
    
    def _generate_arithmetic_sequence_puzzle(self, grade: int, difficulty: str) -> Dict:
        """Arithmetic sequence puzzle generator"""
        if difficulty == "oson":
            start = random.randint(1, 10)
            step = random.randint(2, 5)
            length = 4
        elif difficulty == "o'rta":
            start = random.randint(5, 20)
            step = random.randint(3, 7)
            length = 5
        else:
            start = random.randint(10, 30)
            step = random.randint(5, 10)
            length = 6
        
        sequence = [start + i * step for i in range(length)]
        missing_pos = random.randint(1, length - 2)
        correct_answer = sequence[missing_pos]
        sequence[missing_pos] = "?"
        
        options = self._generate_numeric_options(correct_answer, difficulty)
        correct_label = self._get_correct_label(options, correct_answer)
        
        question_text = f"Ketma-ketlikni davom ettiring: " + ", ".join(str(x) for x in sequence)
        
        return {
            "question_text": question_text,
            "answer": str(correct_answer),
            "correct_label": correct_label,
            "options": options,
            "topic": "arithmetic_sequence",
            "rule_description": f"Arifmetik progressiya: a₁={start}, d={step}",
            "grade": grade,
            "difficulty": difficulty,
            "requires_image": False
        }
    
    def _generate_shape_pattern_puzzle(self, grade: int, difficulty: str) -> Dict:
        """Shape pattern puzzle generator"""
        shapes = ["uchburchak", "kvadrat", "doira", "romb"]
        
        if difficulty == "oson":
            pattern = shapes[:3]
            rule = "shakllar ketma-ket takrorlanadi"
        elif difficulty == "o'rta":
            pattern = shapes[:4]
            rule = "har 2-shakldan keyin boshqa shakl keladi"
        else:
            pattern = shapes * 2
            rule = "shakllar ma'lum tartibda takrorlanadi"
        
        missing_pos = random.randint(0, len(pattern) - 1)
        correct_answer = pattern[missing_pos]
        shown_pattern = pattern.copy()
        shown_pattern[missing_pos] = "?"
        
        options = {label: shape for label, shape in zip(["A", "B", "C", "D"], 
                   random.sample(shapes + [correct_answer], 4))}
        if correct_answer not in options.values():
            options["A"] = correct_answer
        
        correct_label = [k for k, v in options.items() if v == correct_answer][0]
        
        question_text = f"Quyidagi shakllar ketma-ketligida '?' o'rniga qaysi shakl keladi?\n" + " → ".join(str(x) for x in shown_pattern)
        
        return {
            "question_text": question_text,
            "answer": correct_answer,
            "correct_label": correct_label,
            "options": options,
            "topic": "shape_pattern",
            "rule_description": rule,
            "grade": grade,
            "difficulty": difficulty,
            "requires_image": True
        }
    
    def _generate_odd_one_out_puzzle(self, grade: int, difficulty: str) -> Dict:
        """Odd one out puzzle generator"""
        if difficulty == "oson":
            numbers = [random.randint(2, 20) for _ in range(4)]
            correct = random.choice(numbers)
            options = {f"{chr(65+i)}": num for i, num in enumerate(numbers)}
        elif difficulty == "o'rta":
            base = random.randint(5, 15)
            numbers = [base * i for i in range(1, 5)]
            odd = numbers.pop(random.randint(0, 3))
            numbers.append(odd + random.randint(1, 5))
            options = {f"{chr(65+i)}": num for i, num in enumerate(numbers)}
            correct = odd + random.randint(1, 5)
        else:
            base = random.randint(2, 5)
            numbers = [base ** i for i in range(1, 5)]
            odd = random.choice([3, 5, 7])
            numbers.append(odd)
            options = {f"{chr(65+i)}": num for i, num in enumerate(numbers)}
            correct = odd
        
        correct_label = [k for k, v in options.items() if v == correct][0]
        
        question_text = f"Qaysi son qolganlardan farq qiladi?\n" + " ".join(str(v) for v in options.values())
        
        return {
            "question_text": question_text,
            "answer": str(correct),
            "correct_label": correct_label,
            "options": options,
            "topic": "odd_one_out",
            "rule_description": "Barcha sonlar ma'lum qoida bo'yicha bog'langan, bittasi esa emas",
            "grade": grade,
            "difficulty": difficulty,
            "requires_image": False
        }
    
    def _generate_symbol_relation_puzzle(self, grade: int, difficulty: str) -> Dict:
        """Symbol relation puzzle generator"""
        if difficulty == "oson":
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            result = a + b
            symbol = "+"
        elif difficulty == "o'rta":
            a = random.randint(2, 15)
            b = random.randint(2, 10)
            result = a * b
            symbol = "×"
        else:
            a = random.randint(5, 20)
            b = random.randint(3, 10)
            result = a * b + a
            symbol = "⊕"
        
        question_text = f"a {symbol} b = {result}, a = {a} bo'lsa, b = ?"
        
        options = self._generate_numeric_options(b, difficulty)
        correct_label = self._get_correct_label(options, b)
        
        return {
            "question_text": question_text,
            "answer": str(b),
            "correct_label": correct_label,
            "options": options,
            "topic": "symbol_relation",
            "rule_description": f"a {symbol} b = {result} qoidasi",
            "grade": grade,
            "difficulty": difficulty,
            "requires_image": False
        }
    
    def _generate_number_grid_puzzle(self, grade: int, difficulty: str) -> Dict:
        """Number grid puzzle generator"""
        if difficulty == "oson":
            size = 3
            rule_type = "row_sum"
        elif difficulty == "o'rta":
            size = random.choice([3, 4])
            rule_type = random.choice(["row_sum", "col_sum", "diagonal"])
        else:
            size = 4
            rule_type = random.choice(["row_sum", "magic_square", "pattern"])
        
        if rule_type == "row_sum":
            row_sum = random.randint(10, 20)
            numbers = [[random.randint(1, row_sum-2) for _ in range(size-1)] for _ in range(size)]
            for row in numbers:
                row.append(row_sum - sum(row))
            missing = (random.randint(0, size-1), size-1)
            correct = numbers[missing[0]][missing[1]]
            numbers[missing[0]][missing[1]] = "?"
            rule_desc = f"Har bir satr yig'indisi {row_sum} ga teng"
        
        elif rule_type == "col_sum":
            col_sum = random.randint(15, 30)
            numbers = [[random.randint(1, col_sum-2) for _ in range(size)] for _ in range(size-1)]
            last_row = [col_sum - sum(numbers[i][j] for i in range(size-1)) for j in range(size)]
            numbers.append(last_row)
            missing = (size-1, random.randint(0, size-1))
            correct = last_row[missing[1]]
            numbers[missing[0]][missing[1]] = "?"
            rule_desc = f"Har bir ustun yig'indisi {col_sum} ga teng"
        
        else:
            numbers = [[0]*size for _ in range(size)]
            for i in range(size):
                for j in range(size):
                    numbers[i][j] = random.randint(1, 9)
            missing = (random.randint(0, size-1), random.randint(0, size-1))
            correct = numbers[missing[0]][missing[1]]
            numbers[missing[0]][missing[1]] = "?"
            rule_desc = "Jadvalda ma'lum bir qoida bor"
        
        grid_text = "\n".join([" ".join(str(x) for x in row) for row in numbers])
        question_text = f"Quyidagi jadvalda '?' o'rniga qanday son keladi?\n{grid_text}"
        
        options = self._generate_numeric_options(correct, difficulty)
        correct_label = self._get_correct_label(options, correct)
        
        return {
            "question_text": question_text,
            "answer": str(correct),
            "correct_label": correct_label,
            "options": options,
            "topic": "number_grid",
            "rule_description": rule_desc,
            "grade": grade,
            "difficulty": difficulty,
            "requires_image": True
        }
    
    def _generate_numeric_options(self, correct: float, difficulty: str) -> Dict[str, float]:
        """Generate numeric options with distractors"""
        options = {}
        labels = ["A", "B", "C", "D"]
        
        values = [correct]
        
        if difficulty == "oson":
            variations = [
                correct + random.randint(1, 5),
                correct + random.randint(6, 15),
                correct - random.randint(1, min(5, int(correct)))
            ]
        elif difficulty == "o'rta":
            variations = [
                correct + random.uniform(1, 3),
                correct - random.uniform(1, 3),
                correct + random.randint(5, 10)
            ]
        else:
            variations = [
                correct + random.uniform(-5, 5),
                correct * random.uniform(0.8, 1.2),
                correct + random.uniform(-10, 10)
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
    
    def _get_correct_label(self, options: Dict[str, float], correct: float) -> str:
        """Get label for correct answer"""
        for label, value in options.items():
            if abs(value - correct) < 0.01 or int(value) == int(correct):
                return label
        return "A"
    
    def generate_placeholders(self, output_dir: str = None) -> Dict[str, int]:
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            for ptype in self.PUZZLE_TYPES:
                os.makedirs(os.path.join(output_dir, ptype), exist_ok=True)
        
        counts = {}
        
        for i, template in enumerate(self.LOGIC_GRID_TEMPLATES[:10]):
            img = self.draw_logic_grid(template["pattern"])
            if output_dir:
                with open(os.path.join(output_dir, "logic_grid", f"{template['id']}.png"), 'wb') as f:
                    f.write(img)
            counts["logic_grid"] = counts.get("logic_grid", 0) + 1
        
        for i, template in enumerate(self.CROSSWORD_TEMPLATES[:10]):
            img = self.draw_crossword(template["words"])
            if output_dir:
                with open(os.path.join(output_dir, "crossword", f"{template['id']}.png"), 'wb') as f:
                    f.write(img)
            counts["crossword"] = counts.get("crossword", 0) + 1
        
        for i, template in enumerate(self.LABYRINTH_TEMPLATES[:10]):
            img = self.draw_labyrinth(template["maze"]["grid"], template["maze"]["start"], template["maze"]["end"])
            if output_dir:
                with open(os.path.join(output_dir, "labyrinth", f"{template['id']}.png"), 'wb') as f:
                    f.write(img)
            counts["labyrinth"] = counts.get("labyrinth", 0) + 1
        
        for i, template in enumerate(self.SCALE_TEMPLATES[:10]):
            img = self.draw_scale(template["left"], template["right"])
            if output_dir:
                with open(os.path.join(output_dir, "scale", f"{template['id']}.png"), 'wb') as f:
                    f.write(img)
            counts["scale"] = counts.get("scale", 0) + 1
        
        return counts
    
    def get_pool_stats(self) -> Dict:
        return {
            "logic_grid": len(self.LOGIC_GRID_TEMPLATES),
            "crossword": len(self.CROSSWORD_TEMPLATES),
            "labyrinth": len(self.LABYRINTH_TEMPLATES),
            "scale": len(self.SCALE_TEMPLATES),
            "total": sum([
                len(self.LOGIC_GRID_TEMPLATES),
                len(self.CROSSWORD_TEMPLATES),
                len(self.LABYRINTH_TEMPLATES),
                len(self.SCALE_TEMPLATES)
            ])
        }

    # =========================================================================
    # UNIFIED PUZZLE GENERATION API
    # =========================================================================
    
    def generate_one(
        self,
        category: Optional[str] = None,
        difficulty: str = "o'rta",
        grade: int = 5,
        with_diagram: bool = True,
    ) -> Optional[PuzzleOutput]:
        """
        Bitta puzzle generatsiya qilish (unified API).
        
        Pipeline:
        1. Template tanlash
        2. NumPy random generatsiya (nazoratli)
        3. SymPy validation (unique solution)
        4. PuzzleSpec yaratish
        5. Distractor generation
        6. Matplotlib render
        7. Output
        """
        if category is None:
            categories = ["chain", "grid", "rebus", "shape", "flowchart"]
            category = random.choice(categories)
        
        generator_map = {
            "chain": self._gen_chain_puzzle,
            "grid": self._gen_grid_puzzle,
            "rebus": self._gen_rebus_puzzle,
            "shape": self._gen_shape_puzzle,
            "flowchart": self._gen_flowchart_puzzle,
        }
        
        gen_fn = generator_map.get(category)
        if gen_fn is None:
            return None
        
        max_attempts = 15
        for _ in range(max_attempts):
            try:
                puzzle = gen_fn(difficulty, grade)
                if puzzle:
                    return puzzle
            except Exception as e:
                logger.debug(f"Generation failed: {e}")
                continue
        
        return None
    
    def generate_batch(
        self,
        count: int,
        difficulty: str = "o'rta",
        grade: int = 5,
        categories: Optional[List[str]] = None,
    ) -> List[PuzzleOutput]:
        """Batch puzzle generatsiya qilish"""
        if categories is None:
            categories = ["chain", "grid", "rebus", "shape", "flowchart"]
        
        puzzles = []
        used_sigs = set()
        max_attempts = count * 10
        
        for _ in range(max_attempts):
            if len(puzzles) >= count:
                break
            
            cat = random.choice(categories)
            puzzle = self.generate_one(cat, difficulty, grade, with_diagram=False)
            
            if puzzle and puzzle.uniqueness_signature not in used_sigs:
                used_sigs.add(puzzle.uniqueness_signature)
                puzzles.append(puzzle)
        
        return puzzles
    
    def _gen_chain_puzzle(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        """Zanjir puzzle"""
        from services.puzzle_numpy_gen import controlled_generator
        from services.puzzle_validation import enhanced_validator
        from services.smart_distractor import smart_distractor
        
        if difficulty == "oson":
            chain_len = 2
        elif difficulty == "o'rta":
            chain_len = 3
        else:
            chain_len = random.randint(3, 5)
        
        values, operations = controlled_generator.generate_chain_params(chain_len, difficulty, grade)
        
        result = values[0]
        steps = [result]
        for i, op in enumerate(operations):
            result = enhanced_validator._apply_op(result, values[i + 1], op)
            steps.append(result)
        
        if result <= 0 or result > 999:
            return None
        
        val_result = enhanced_validator.validate_chain(values, operations, result)
        if not val_result.is_valid:
            return None
        
        hide_idx = random.randint(1, len(steps) - 1)
        correct_answer = steps[hide_idx]
        
        distractor_result = smart_distractor.generate_for_chain(values, operations, correct_answer)
        
        ops_display = " → ".join([str(values[0])] + [f"{op}{values[i+1]}" for i, op in enumerate(operations)])
        
        equations = []
        for i, op in enumerate(operations):
            equations.append(f"{steps[i]} {op} {values[i+1]} = {steps[i+1]}")
        
        sig_str = f"chain_{values}_" + "_".join(operations)
        signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
        
        return PuzzleOutput(
            puzzle_text=f"Zanjirni hisoblang:\n{ops_display}",
            visual_spec={"type": "chain", "values": values, "operations": operations, "steps": steps, "hide_index": hide_idx},
            correct_answer=correct_answer,
            options=distractor_result.options,
            correct_label=distractor_result.correct_label,
            explanation=f"Ketma-ket hisoblash: {' → '.join(str(s) for s in steps)}",
            difficulty=difficulty,
            category="chain",
            grade=grade,
            equations=equations,
            uniqueness_signature=signature,
        )
    
    def _gen_grid_puzzle(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        """Jadval puzzle"""
        from services.puzzle_numpy_gen import controlled_generator
        from services.puzzle_validation import enhanced_validator
        from services.smart_distractor import smart_distractor
        
        size = 3 if difficulty != "qiyin" else random.choice([3, 4])
        min_val, max_val = (1, 9) if difficulty == "oson" else (1, 15) if difficulty == "o'rta" else (2, 20)
        
        params = controlled_generator.generate_grid_params(size, size, min_val, max_val)
        
        grid = params["grid"]
        row_sums = params["row_sums"]
        col_sums = params["col_sums"]
        missing_r, missing_c = params["missing_position"]
        correct_answer = params["missing_value"]
        
        distractor_result = smart_distractor.generate_for_grid(correct_answer, row_sum=row_sums[missing_r], col_sum=col_sums[missing_c])
        
        grid_display = ""
        for r in range(size):
            row_str = ""
            for c in range(size):
                if (r, c) == (missing_r, missing_c):
                    row_str += "[ ? ] "
                else:
                    row_str += f"[ {grid[r][c]:^3} ] "
            grid_display += row_str + f"  = {row_sums[r]}\n"
        
        sig_str = f"grid_{size}_" + "_".join(str(v) for row in grid for v in row)
        signature = hashlib.md5(sig_str.encode()).hexdigest()[:12]
        
        return PuzzleOutput(
            puzzle_text=f"Jadvaldagi ? belgisi o'rniga qaysi son turishi kerak?\n\n{grid_display}",
            visual_spec={"type": "grid", "grid": grid, "row_sums": row_sums, "col_sums": col_sums, "missing": (missing_r, missing_c)},
            correct_answer=correct_answer,
            options=distractor_result.options,
            correct_label=distractor_result.correct_label,
            explanation=f"Satr {missing_r+1} yig'indisi: {row_sums[missing_r]}. ? = {correct_answer}",
            difficulty=difficulty,
            category="grid",
            grade=grade,
            equations=[f"Satr {missing_r+1}: yig'indi = {row_sums[missing_r]}", f"Ustun {missing_c+1}: yig'indi = {col_sums[missing_c]}"],
            uniqueness_signature=signature,
        )
    
    def _gen_rebus_puzzle(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        """Rebus puzzle"""
        from services.rebus_engine import rebus_engine
        from services.smart_distractor import smart_distractor
        
        if difficulty == "oson":
            rebus = rebus_engine.generate_symbol_equation(2, difficulty, grade)
        elif difficulty == "o'rta":
            rebus = rebus_engine.generate_symbol_equation(random.choice([2, 3]), difficulty, grade)
        else:
            rebus = rebus_engine.generate_chain_rebus(random.randint(3, 4), difficulty, grade)
        
        if rebus is None:
            return None
        
        distractor_result = smart_distractor.generate_for_rebus(rebus.correct_answer, rebus.symbol_mapping)
        
        return PuzzleOutput(
            puzzle_text=f"Belgilar o'rniga qaysi sonlar turibdi?\n\n{rebus.equation_display}",
            visual_spec={"type": "rebus", "rebus_type": rebus.rebus_type, "display": rebus.equation_display, "symbols": rebus.symbol_mapping},
            correct_answer=rebus.correct_answer,
            options=distractor_result.options,
            correct_label=distractor_result.correct_label,
            explanation=rebus.explanation,
            difficulty=difficulty,
            category="rebus",
            grade=grade,
            equations=rebus.equations,
            uniqueness_signature=rebus.uniqueness_signature,
        )
    
    def _gen_shape_puzzle(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        """Shakl puzzle"""
        from services.shape_puzzle_engine import shape_puzzle_engine
        from services.smart_distractor import smart_distractor
        
        shape_types = ["triangle", "square", "rectangle", "circle"]
        if difficulty == "oson":
            shape_types = ["square", "rectangle", "circle"]
        elif grade < 4:
            shape_types = ["square", "rectangle"]
        
        shape_type = random.choice(shape_types)
        
        if shape_type == "triangle":
            puzzle = shape_puzzle_engine.generate_triangle_puzzle(difficulty, grade)
        elif shape_type == "square":
            puzzle = shape_puzzle_engine.generate_square_puzzle(difficulty, grade)
        elif shape_type == "rectangle":
            puzzle = shape_puzzle_engine.generate_rectangle_puzzle(difficulty, grade)
        else:
            puzzle = shape_puzzle_engine.generate_circle_puzzle(difficulty, grade)
        
        if puzzle is None:
            return None
        
        distractor_result = smart_distractor.generate_for_shape(puzzle.correct_answer, puzzle.shape_type, puzzle.shape_data)
        
        return PuzzleOutput(
            puzzle_text=puzzle.puzzle_text,
            visual_spec={"type": "shape", "shape_type": puzzle.shape_type, "shape_data": puzzle.shape_data},
            correct_answer=puzzle.correct_answer,
            options=distractor_result.options,
            correct_label=distractor_result.correct_label,
            explanation=puzzle.explanation,
            difficulty=difficulty,
            category="shape",
            grade=grade,
            equations=puzzle.equations,
            uniqueness_signature=puzzle.uniqueness_signature,
        )
    
    def _gen_flowchart_puzzle(self, difficulty: str, grade: int) -> Optional[PuzzleOutput]:
        """Flowchart puzzle"""
        from services.flowchart_engine import flowchart_engine
        from services.smart_distractor import smart_distractor
        
        if difficulty == "oson":
            flow = flowchart_engine.generate_linear_flow(2, difficulty, grade)
        elif difficulty == "o'rta":
            flow = flowchart_engine.generate_linear_flow(random.randint(2, 3), difficulty, grade)
        else:
            flow_type = random.choice(["linear", "branching", "multi_path"])
            if flow_type == "branching":
                flow = flowchart_engine.generate_branching_flow(difficulty, grade)
            elif flow_type == "multi_path":
                flow = flowchart_engine.generate_multi_path_flow(difficulty, grade)
            else:
                flow = flowchart_engine.generate_linear_flow(random.randint(3, 4), difficulty, grade)
        
        if flow is None:
            return None
        
        distractor_result = smart_distractor.generate_for_flowchart(flow.correct_answer, flow.operations, flow.flow_type)
        
        return PuzzleOutput(
            puzzle_text=f"Oqim diagrammasini hisoblang:\n\n{flow.puzzle_display}",
            visual_spec={"type": "flowchart", "flow_type": flow.flow_type, "nodes": [n.to_dict() for n in flow.nodes], "edges": flow.edges},
            correct_answer=flow.correct_answer,
            options=distractor_result.options,
            correct_label=distractor_result.correct_label,
            explanation=flow.explanation,
            difficulty=difficulty,
            category="flowchart",
            grade=grade,
            equations=flow.equations,
            uniqueness_signature=flow.uniqueness_signature,
        )


puzzle_pool = PuzzlePool()
