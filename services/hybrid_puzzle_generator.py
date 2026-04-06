"""
services/hybrid_puzzle_generator.py — HYBRID PUZZLE GENERATOR

Bu modul bir nechta puzzle strukturalarini birlashtirgan
gibrid puzzle larni generatsiya qiladi.

Hybrid turlari:
1. Arithmetic Chain + Grid (arifmetik zanjir + jadval)
2. Flow + Symbol (oqim + belgi)
3. Vertical + Magic Square (vertikal + sehrli kvadrat)
4. Chain + Equation System (zanjir + tenglama sistemasi)
"""

import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class HybridPuzzle:
    """Gibrid puzzle - bir nechta strukturalarni birlashtiradi"""
    hybrid_type: str
    components: List[Dict[str, Any]]
    final_answer: Any
    uniqueness_signature: str
    combined_equations: List[str]
    difficulty: str
    
    def to_dict(self) -> Dict:
        return {
            "hybrid_type": self.hybrid_type,
            "components": self.components,
            "final_answer": self.final_answer,
            "uniqueness_signature": self.uniqueness_signature,
            "combined_equations": self.combined_equations,
            "difficulty": self.difficulty,
        }


class HybridPuzzleGenerator:
    """
    Gibrid puzzle generator.
    Ikki yoki undan ko'p puzzle turini birlashtiradi.
    """
    
    HYBRID_TYPES = {
        "arithmetic_chain_grid": {
            "name": "Arifmetik Zanjir + Jadval",
            "components": ["chain_operations", "grid_arithmetic"],
            "difficulty_range": ("o'rta", "qiyin"),
            "grade_range": (3, 11),
        },
        "flow_symbol": {
            "name": "Oqim Diagramma + Belgi",
            "components": ["flow_diagram", "symbol_unknown"],
            "difficulty_range": ("o'rta", "o'rta"),
            "grade_range": (3, 11),
        },
        "vertical_magic": {
            "name": "Vertikal Arifmetika + sehrli Kvadrat",
            "components": ["vertical_arithmetic", "grid_arithmetic"],
            "difficulty_range": ("o'rta", "qiyin"),
            "grade_range": (2, 11),
        },
        "chain_equation": {
            "name": "Zanjir + Tenglamalar Sistemi",
            "components": ["chain_operations", "symbol_unknown"],
            "difficulty_range": ("qiyin", "qiyin"),
            "grade_range": (4, 11),
        },
        "grid_pattern": {
            "name": "Jadval + Pattern",
            "components": ["grid_arithmetic", "chain_operations"],
            "difficulty_range": ("o'rta", "qiyin"),
            "grade_range": (3, 11),
        },
    }
    
    def __init__(self):
        from .puzzle_templates import AcademicPuzzleGenerator
        self.puzzle_gen = AcademicPuzzleGenerator()
    
    def generate(self, hybrid_type: str, difficulty: str, grade: int) -> Optional[HybridPuzzle]:
        """Gibrid puzzle generatsiya qilish"""
        hybrid_config = self.HYBRID_TYPES.get(hybrid_type)
        
        if not hybrid_config:
            return None
        
        if difficulty not in hybrid_config["difficulty_range"]:
            difficulty = hybrid_config["difficulty_range"][0]
        
        generator_method = f"_generate_{hybrid_type}"
        if hasattr(self, generator_method):
            return getattr(self, generator_method)(difficulty, grade)
        
        return None
    
    def generate_random(self, difficulty: str, grade: int) -> Optional[HybridPuzzle]:
        """Tasodifiy gibrid puzzle generatsiya"""
        suitable_types = [
            ht for ht, config in self.HYBRID_TYPES.items()
            if config["grade_range"][0] <= grade <= config["grade_range"][1]
        ]
        
        if not suitable_types:
            return None
        
        for _ in range(10):
            hybrid_type = random.choice(suitable_types)
            result = self.generate(hybrid_type, difficulty, grade)
            if result:
                return result
        
        for hybrid_type in suitable_types:
            result = self.generate(hybrid_type, difficulty, grade)
            if result:
                return result
        
        return None
    
    def _generate_arithmetic_chain_grid(self, difficulty: str, grade: int) -> HybridPuzzle:
        """Arifmetik zanjir + jadval kombinatsiyasi"""
        chain_puzzle = self.puzzle_gen.generate("chain_operations", difficulty, grade)
        if not chain_puzzle:
            return None
        
        grid_values = chain_puzzle.filled_values.get("steps", [])
        if len(grid_values) < 4:
            grid_values = [10, 20, 30, 40]
        
        grid_size = 2
        grid = [
            [grid_values[0], grid_values[1]],
            [grid_values[2], grid_values[3]],
        ]
        
        row_sums = [sum(row) for row in grid]
        col_sums = [grid[0][c] + grid[1][c] for c in range(grid_size)]
        total_sum = sum(row_sums)
        
        components = [
            {
                "type": "chain_operations",
                "content": chain_puzzle.puzzle_structure,
                "values": chain_puzzle.filled_values,
            },
            {
                "type": "grid_arithmetic",
                "grid": grid,
                "row_sums": row_sums,
                "col_sums": col_sums,
                "total_sum": total_sum,
            },
        ]
        
        combined_equations = chain_puzzle.equations.copy()
        combined_equations.append(f"Jadval yig'indisi: {total_sum}")
        
        return HybridPuzzle(
            hybrid_type="arithmetic_chain_grid",
            components=components,
            final_answer=total_sum,
            uniqueness_signature=chain_puzzle.uniqueness_signature + "_chain_grid",
            combined_equations=combined_equations,
            difficulty=difficulty,
        )
    
    def _generate_flow_symbol(self, difficulty: str, grade: int) -> HybridPuzzle:
        """Oqim diagramma + belgi kombinatsiyasi"""
        flow_puzzle = self.puzzle_gen.generate("flow_diagram", difficulty, grade)
        if not flow_puzzle:
            return None
        
        values = flow_puzzle.filled_values
        x = values.get("x", 10)
        y = values.get("y", 5)
        op1 = values.get("op1", values.get("op", "+"))
        step1 = values.get("step1", x + y)
        
        symbol = random.choice(["□", "△", "○"])
        unknown_value = random.randint(1, min(step1 - 1, 20))
        equation_result = step1 + unknown_value
        
        components = [
            {
                "type": "flow_diagram",
                "content": flow_puzzle.puzzle_structure,
                "values": values,
            },
            {
                "type": "symbol_unknown",
                "equation": f"{step1} + {symbol} = {equation_result}",
                "symbol": symbol,
                "unknown_value": unknown_value,
            },
        ]
        
        combined_equations = flow_puzzle.equations.copy()
        combined_equations.append(f"{step1} + {unknown_value} = {equation_result}")
        
        return HybridPuzzle(
            hybrid_type="flow_symbol",
            components=components,
            final_answer=unknown_value,
            uniqueness_signature=flow_puzzle.uniqueness_signature + "_flow_symbol",
            combined_equations=combined_equations,
            difficulty=difficulty,
        )
    
    def _generate_vertical_magic(self, difficulty: str, grade: int) -> HybridPuzzle:
        """Vertikal arifmetika + sehrli kvadrat"""
        vertical_puzzle = self.puzzle_gen.generate("vertical_arithmetic", difficulty, grade)
        if not vertical_puzzle:
            return None
        
        values = vertical_puzzle.filled_values
        result = values.get("result", values.get("a", 10) + values.get("b", 5))
        
        magic_sum = result
        numbers = list(range(1, 10))
        random.shuffle(numbers)
        
        grid = [
            [numbers[0], numbers[1], numbers[2]],
            [numbers[3], numbers[4], numbers[5]],
            [numbers[6], numbers[7], numbers[8]],
        ]
        
        components = [
            {
                "type": "vertical_arithmetic",
                "content": vertical_puzzle.puzzle_structure,
                "values": values,
            },
            {
                "type": "magic_square",
                "grid": grid,
                "magic_sum": magic_sum,
                "grid_text": f"Veryg'i yig'indisi: {magic_sum}",
            },
        ]
        
        combined_equations = vertical_puzzle.equations.copy()
        combined_equations.append(f"Sehrli kvadrat yig'indisi: {magic_sum}")
        
        missing_row = random.randint(0, 2)
        missing_col = random.randint(0, 2)
        missing_value = grid[missing_row][missing_col]
        
        return HybridPuzzle(
            hybrid_type="vertical_magic",
            components=components,
            final_answer=missing_value,
            uniqueness_signature=vertical_puzzle.uniqueness_signature + "_vertical_magic",
            combined_equations=combined_equations,
            difficulty=difficulty,
        )
    
    def _generate_chain_equation(self, difficulty: str, grade: int) -> HybridPuzzle:
        """Zanjir + tenglama sistemasi"""
        chain_puzzle = self.puzzle_gen.generate("chain_operations", difficulty, grade)
        if not chain_puzzle:
            chain_puzzle = self.puzzle_gen.generate("chain_operations", "o'rta", grade)
        if not chain_puzzle:
            chain_puzzle = self.puzzle_gen.generate("chain_operations", "oson", grade)
        if not chain_puzzle:
            return None
        
        steps = chain_puzzle.filled_values.get("steps", [10, 15, 30, 45])
        if len(steps) < 2:
            steps = [10, 20, 40, 80]
        
        x = random.randint(10, 50)
        y = random.randint(5, 30)
        
        sym1, sym2 = random.sample(["□", "△", "○"], 2)
        
        components = [
            {
                "type": "chain_operations",
                "content": chain_puzzle.puzzle_structure,
                "values": chain_puzzle.filled_values,
            },
            {
                "type": "equation_system",
                "eq1": f"{sym1} + {sym2} = {x + y}",
                "eq2": f"{sym1} - {sym2} = {x - y}",
                "symbols": [sym1, sym2],
                "values": [x, y],
            },
        ]
        
        combined_equations = chain_puzzle.equations.copy()
        combined_equations.append(f"{sym1} + {sym2} = {x + y}")
        combined_equations.append(f"{sym1} - {sym2} = {x - y}")
        
        return HybridPuzzle(
            hybrid_type="chain_equation",
            components=components,
            final_answer=f"{sym1}={x}, {sym2}={y}",
            uniqueness_signature=chain_puzzle.uniqueness_signature + "_chain_eq",
            combined_equations=combined_equations,
            difficulty=difficulty,
        )
    
    def _generate_grid_pattern(self, difficulty: str, grade: int) -> HybridPuzzle:
        """Jadval + pattern recognition"""
        grid_puzzle = self.puzzle_gen.generate("grid_arithmetic", difficulty, grade)
        if not grid_puzzle:
            grid_puzzle = self.puzzle_gen.generate("grid_arithmetic", "o'rta", grade)
        if not grid_puzzle:
            grid_puzzle = self.puzzle_gen.generate("grid_arithmetic", "oson", grade)
        if not grid_puzzle:
            return None
        
        grid = grid_puzzle.filled_values.get("grid", [[1, 2, 3], [4, 5, 6], [7, 8, "?"]])
        
        pattern_type = random.choice(["add_n", "multiply_n", "fibonacci"])
        
        if pattern_type == "add_n":
            n = random.randint(2, 5)
            sequence = [i * n for i in range(1, 5)]
            next_value = 5 * n
            pattern_desc = f"+{n} qoidasi"
        elif pattern_type == "multiply_n":
            n = random.randint(2, 3)
            sequence = [n ** i for i in range(1, 5)]
            next_value = n ** 5
            pattern_desc = f"×{n} qoidasi"
        else:
            sequence = [1, 1, 2, 3]
            next_value = 5
            pattern_desc = "Fibonacci"
        
        components = [
            {
                "type": "grid_arithmetic",
                "content": grid_puzzle.puzzle_structure,
                "grid": grid,
            },
            {
                "type": "pattern",
                "sequence": sequence,
                "next_value": next_value,
                "pattern_desc": pattern_desc,
            },
        ]
        
        combined_equations = grid_puzzle.equations.copy()
        combined_equations.append(f"Pattern: {pattern_desc}")
        
        return HybridPuzzle(
            hybrid_type="grid_pattern",
            components=components,
            final_answer=next_value,
            uniqueness_signature=grid_puzzle.uniqueness_signature + "_grid_pattern",
            combined_equations=combined_equations,
            difficulty=difficulty,
        )
    
    def get_hybrid_types(self) -> List[str]:
        """Barcha gibrid turlar ro'yxati"""
        return list(self.HYBRID_TYPES.keys())
    
    def get_hybrid_info(self, hybrid_type: str) -> Optional[Dict]:
        """Gibrid turi haqida ma'lumot"""
        return self.HYBRID_TYPES.get(hybrid_type)


class HybridPuzzleRenderer:
    """
    Gibrid puzzle larni vizual tarzda chizish.
    """
    
    def __init__(self):
        from .puzzle_layout_generator import PuzzleLayoutRenderer
        self.layout_renderer = PuzzleLayoutRenderer()
    
    def render(self, hybrid_puzzle: HybridPuzzle, difficulty: str = "medium") -> Tuple[Any, Dict]:
        """Gibrid puzzle ni chizish"""
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
        
        fig = plt.figure(figsize=(14, 8))
        gs = GridSpec(1, 2, figure=fig, wspace=0.3)
        
        component_figs = []
        
        for i, component in enumerate(hybrid_puzzle.components):
            comp_type = component.get("type", "")
            
            if comp_type == "chain_operations":
                fig_single, _ = self._render_chain_component(component, difficulty)
            elif comp_type == "grid_arithmetic":
                fig_single, _ = self._render_grid_component(component, difficulty)
            elif comp_type == "flow_diagram":
                fig_single, _ = self._render_flow_component(component, difficulty)
            elif comp_type == "symbol_unknown":
                fig_single, _ = self._render_symbol_component(component, difficulty)
            elif comp_type == "vertical_arithmetic":
                fig_single, _ = self._render_vertical_component(component, difficulty)
            elif comp_type == "equation_system":
                fig_single, _ = self._render_equation_component(component, difficulty)
            elif comp_type == "pattern":
                fig_single, _ = self._render_pattern_component(component, difficulty)
            else:
                fig_single = plt.figure(figsize=(6, 4))
            
            component_figs.append(fig_single)
        
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])
        
        for i, component in enumerate(hybrid_puzzle.components):
            ax = ax1 if i == 0 else ax2
            comp_type = component.get("type", "")
            
            if comp_type == "chain_operations":
                self._draw_chain_on_ax(ax, component)
            elif comp_type == "grid_arithmetic":
                self._draw_grid_on_ax(ax, component)
            elif comp_type == "flow_diagram":
                self._draw_flow_on_ax(ax, component)
            elif comp_type == "symbol_unknown":
                self._draw_symbol_on_ax(ax, component)
            elif comp_type == "equation_system":
                self._draw_equation_on_ax(ax, component)
            elif comp_type == "pattern":
                self._draw_pattern_on_ax(ax, component)
        
        for cf in component_figs:
            plt.close(cf)
        
        fig.suptitle(hybrid_puzzle.hybrid_type.replace("_", " ").title(), fontsize=14, fontweight='bold')
        
        return fig, hybrid_puzzle.to_dict()
    
    def _render_chain_component(self, component: Dict, difficulty: str):
        return self.layout_renderer.render(type('obj', (object,), {'template_type': 'chain_operations', 'puzzle_structure': component.get('content', ''), 'filled_values': component.get('values', {}), 'equations': []})(), difficulty)
    
    def _render_grid_component(self, component: Dict, difficulty: str):
        return self.layout_renderer.render(type('obj', (object,), {'template_type': 'grid_arithmetic', 'puzzle_structure': '', 'filled_values': {'grid': component.get('grid', [[]])}, 'equations': []})(), difficulty)
    
    def _render_flow_component(self, component: Dict, difficulty: str):
        return self.layout_renderer.render(type('obj', (object,), {'template_type': 'flow_diagram', 'puzzle_structure': component.get('content', ''), 'filled_values': component.get('values', {}), 'equations': []})(), difficulty)
    
    def _render_symbol_component(self, component: Dict, difficulty: str):
        return self.layout_renderer.render(type('obj', (object,), {'template_type': 'symbol_unknown', 'puzzle_structure': component.get('equation', ''), 'filled_values': {'symbol': component.get('symbol', '?')}, 'equations': [component.get('equation', '')]})(), difficulty)
    
    def _render_vertical_component(self, component: Dict, difficulty: str):
        return self.layout_renderer.render(type('obj', (object,), {'template_type': 'vertical_arithmetic', 'puzzle_structure': component.get('content', ''), 'filled_values': component.get('values', {}), 'equations': []})(), difficulty)
    
    def _render_equation_component(self, component: Dict, difficulty: str):
        return self.layout_renderer.render(type('obj', (object,), {'template_type': 'symbol_unknown', 'puzzle_structure': f"{component.get('eq1', '')}\n{component.get('eq2', '')}", 'filled_values': {}, 'equations': [component.get('eq1', ''), component.get('eq2', '')]})(), difficulty)
    
    def _render_pattern_component(self, component: Dict, difficulty: str):
        return self.layout_renderer.render(type('obj', (object,), {'template_type': 'chain_operations', 'puzzle_structure': str(component.get('sequence', [])) + " → ?", 'filled_values': {'values': component.get('sequence', [])}, 'equations': []})(), difficulty)
    
    def _draw_chain_on_ax(self, ax, component: Dict):
        values = component.get("values", {})
        sequence = values.get("values", values.get("steps", [10, 20, 40]))
        ops = values.get("ops", ["+", "×", "-"])
        
        y_pos = 0.5
        for i, val in enumerate(sequence):
            x = i * 1.5
            ax.add_patch(plt.Rectangle((x, y_pos - 0.3), 1, 0.6, facecolor='#E3F2FD', edgecolor='#2196F3', linewidth=2))
            ax.text(x + 0.5, y_pos, str(val), ha='center', va='center', fontsize=12, fontweight='bold')
            
            if i < len(sequence) - 1:
                ax.annotate("", xy=(x + 1.1, y_pos), xytext=(x + 1, y_pos),
                           arrowprops=dict(arrowstyle="->", color="#666666"))
                ax.text(x + 1.05, y_pos + 0.25, ops[i], ha='center', va='center', fontsize=10, color="#666666")
        
        ax.set_xlim(-0.5, len(sequence) * 1.5)
        ax.set_ylim(-0.5, 1.5)
        ax.axis('off')
        ax.set_title("Zanjir operatsiyalar", fontsize=12, fontweight='bold')
    
    def _draw_grid_on_ax(self, ax, component: Dict):
        grid = component.get("grid", [[1, 2], [3, 4]])
        
        for r, row in enumerate(grid):
            for c, cell in enumerate(row):
                x = c * 1.2
                y = len(grid) - r - 1
                
                color = '#FFECB3' if cell == "?" else '#E3F2FD'
                edge_color = '#FF6F00' if cell == "?" else '#2196F3'
                
                ax.add_patch(plt.Rectangle((x, y), 1, 1, facecolor=color, edgecolor=edge_color, linewidth=2))
                ax.text(x + 0.5, y + 0.5, str(cell), ha='center', va='center', fontsize=14, fontweight='bold')
        
        ax.set_xlim(-0.2, len(grid[0]) * 1.2 + 0.2)
        ax.set_ylim(-0.2, len(grid) + 0.2)
        ax.axis('off')
        ax.set_title("Jadval", fontsize=12, fontweight='bold')
    
    def _draw_flow_on_ax(self, ax, component: Dict):
        values = component.get("values", {})
        x = values.get("x", 10)
        op = values.get("op1", values.get("op", "+"))
        y = values.get("y", 5)
        result = values.get("result", 0)
        
        boxes = [(x, "X"), (f"{op} {y}", "Op1")]
        if result:
            boxes.append((result, "Result"))
        
        for i, (val, label) in enumerate(boxes):
            bx = i * 2
            ax.add_patch(plt.Rectangle((bx, 0), 1.5, 1, facecolor='#E3F2FD', edgecolor='#2196F3', linewidth=2, boxstyle="round,pad=0.1"))
            ax.text(bx + 0.75, 0.5, str(val), ha='center', va='center', fontsize=11, fontweight='bold')
            
            if i < len(boxes) - 1:
                ax.annotate("", xy=(bx + 1.6, 0.5), xytext=(bx + 1.5, 0.5),
                           arrowprops=dict(arrowstyle="->", color="#666666"))
        
        ax.set_xlim(-0.5, len(boxes) * 2)
        ax.set_ylim(-0.5, 2)
        ax.axis('off')
        ax.set_title("Oqim diagramma", fontsize=12, fontweight='bold')
    
    def _draw_symbol_on_ax(self, ax, component: Dict):
        equation = component.get("equation", "? = ?")
        ax.text(0.5, 0.5, equation, ha='center', va='center', fontsize=16, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='#FFECB3', edgecolor='#FF6F00', linewidth=2))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_title("Belgi topish", fontsize=12, fontweight='bold')
    
    def _draw_equation_on_ax(self, ax, component: Dict):
        eq1 = component.get("eq1", "")
        eq2 = component.get("eq2", "")
        
        ax.text(0.5, 0.7, eq1, ha='center', va='center', fontsize=14, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='#E3F2FD', edgecolor='#2196F3', linewidth=2))
        ax.text(0.5, 0.3, eq2, ha='center', va='center', fontsize=14, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='#E3F2FD', edgecolor='#2196F3', linewidth=2))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_title("Tenglama sistemasi", fontsize=12, fontweight='bold')
    
    def _draw_pattern_on_ax(self, ax, component: Dict):
        sequence = component.get("sequence", [1, 2, 4, 8])
        pattern_desc = component.get("pattern_desc", "")
        
        for i, val in enumerate(sequence):
            x = i * 1.2
            ax.add_patch(plt.Circle((x + 0.4, 0.5), 0.4, facecolor='#E8F5E9', edgecolor='#4CAF50', linewidth=2))
            ax.text(x + 0.4, 0.5, str(val), ha='center', va='center', fontsize=12, fontweight='bold', color='#2E7D32')
            
            if i < len(sequence) - 1:
                ax.annotate("", xy=(x + 0.85, 0.5), xytext=(x + 0.8, 0.5),
                           arrowprops=dict(arrowstyle="->", color="#666666"))
        
        ax.text(len(sequence) * 1.2 + 0.2, 0.5, "?", ha='center', va='center', fontsize=16, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='#FFECB3', edgecolor='#FF6F00', linewidth=2))
        
        ax.set_xlim(-0.5, len(sequence) * 1.2 + 1.5)
        ax.set_ylim(-0.5, 1.5)
        ax.axis('off')
        ax.set_title(f"Pattern: {pattern_desc}", fontsize=12, fontweight='bold')


hybrid_puzzle_generator = HybridPuzzleGenerator()
hybrid_puzzle_renderer = HybridPuzzleRenderer()
