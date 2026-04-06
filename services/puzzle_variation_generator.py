"""
services/puzzle_variation_generator.py — TEMPLATE VARIATION GENERATOR

Bu modul mavjud puzzle template lardan yangi variatsiyalar yaratadi.
Har bir template turi uchun bir nechta vizual variantlar mavjud.
"""

import random
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum


class VariationType(Enum):
    VISUAL_STYLE = "visual_style"
    NUMBER_RANGE = "number_range"
    STRUCTURE = "structure"
    COMPLEXITY = "complexity"


@dataclass
class PuzzleVariation:
    """Puzzle variatsiyasi"""
    variation_id: str
    variation_type: VariationType
    base_template: str
    visual_config: Dict
    number_config: Dict
    difficulty_modifier: float


class VariationRegistry:
    """Har bir template turi uchun variatsiyalar ro'yxati"""
    
    VERTICAL_ARITHMETIC_VARIATIONS = {
        "classic": {
            "visual_config": {
                "box_style": "rounded",
                "line_style": "solid",
                "show_carry": False,
                "alignment": "right",
            },
            "number_config": {
                "digit_range": (2, 2),
                "result_range": None,
            }
        },
        "with_carry": {
            "visual_config": {
                "box_style": "rounded",
                "line_style": "solid",
                "show_carry": True,
                "carry_position": "top_right",
                "alignment": "right",
            },
            "number_config": {
                "digit_range": (2, 2),
                "require_carry": True,
                "result_range": None,
            }
        },
        "grid_style": {
            "visual_config": {
                "box_style": "square",
                "line_style": "thick",
                "show_carry": False,
                "alignment": "center",
                "grid_lines": True,
            },
            "number_config": {
                "digit_range": (2, 2),
                "result_range": None,
            }
        },
        "empty_answer": {
            "visual_config": {
                "box_style": "rounded",
                "line_style": "dashed",
                "show_carry": False,
                "alignment": "right",
                "answer_blank": True,
            },
            "number_config": {
                "digit_range": (2, 2),
                "result_range": None,
            }
        },
    }
    
    FLOW_DIAGRAM_VARIATIONS = {
        "vertical": {
            "visual_config": {
                "direction": "vertical",
                "arrow_style": "simple",
                "box_style": "rounded",
                "show_operations": True,
            },
            "number_config": {
                "step_count": (2, 3),
            }
        },
        "horizontal": {
            "visual_config": {
                "direction": "horizontal",
                "arrow_style": "arrow_head",
                "box_style": "rectangle",
                "show_operations": True,
            },
            "number_config": {
                "step_count": (2, 4),
            }
        },
        "tree": {
            "visual_config": {
                "direction": "branching",
                "arrow_style": "branch",
                "box_style": "diamond",
                "show_operations": False,
            },
            "number_config": {
                "step_count": (2, 3),
            }
        },
    }
    
    CHAIN_VARIATIONS = {
        "linear": {
            "visual_config": {
                "layout": "horizontal",
                "connector": "arrow",
                "number_style": "boxed",
                "show_steps": True,
            },
            "number_config": {
                "chain_length": (3, 5),
            }
        },
        "circular": {
            "visual_config": {
                "layout": "circular",
                "connector": "arc",
                "number_style": "circle",
                "show_steps": True,
            },
            "number_config": {
                "chain_length": (4, 6),
            }
        },
        "pyramid": {
            "visual_config": {
                "layout": "pyramid",
                "connector": "diagonal",
                "number_style": "triangle",
                "show_steps": True,
            },
            "number_config": {
                "chain_length": (3, 4),
            }
        },
    }
    
    GRID_VARIATIONS = {
        "classic_3x3": {
            "visual_config": {
                "grid_size": (3, 3),
                "cell_style": "square",
                "show_sum": True,
                "sum_position": "right",
                "borders": "full",
            },
            "number_config": {
                "cell_range": (1, 9),
                "sum_range": (15, 30),
            }
        },
        "latin_4x4": {
            "visual_config": {
                "grid_size": (4, 4),
                "cell_style": "square",
                "show_sum": False,
                "sum_position": None,
                "borders": "inner_only",
            },
            "number_config": {
                "cell_range": (1, 4),
                "use_unique": True,
            }
        },
        "sum_rows_cols": {
            "visual_config": {
                "grid_size": (4, 4),
                "cell_style": "rounded",
                "show_sum": True,
                "sum_position": "bottom_right",
                "borders": "partial",
            },
            "number_config": {
                "cell_range": (1, 9),
                "sum_range": (10, 20),
            }
        },
    }
    
    SYMBOL_VARIATIONS = {
        "simple": {
            "visual_config": {
                "symbol_style": "shape",
                "show_equation": True,
                "answer_format": "single",
            },
            "number_config": {
                "unknown_count": 1,
            }
        },
        "multiple": {
            "visual_config": {
                "symbol_style": "letter",
                "show_equation": True,
                "answer_format": "multiple",
            },
            "number_config": {
                "unknown_count": (2, 3),
            }
        },
        "system": {
            "visual_config": {
                "symbol_style": "variable",
                "show_equation": True,
                "answer_format": "pair",
            },
            "number_config": {
                "unknown_count": 2,
                "require_substitution": True,
            }
        },
    }


class PuzzleVariationGenerator:
    """
    Puzzle template variatsiyalarini generatsiya qiluvchi.
    """
    
    def __init__(self):
        self.registry = VariationRegistry()
        self.active_variations: Dict[str, List[str]] = {}
    
    def get_variations(self, template_type: str) -> Dict[str, PuzzleVariation]:
        """Template turi uchun barcha variatsiyalarni olish"""
        if template_type == "vertical_arithmetic":
            return self._build_vertical_variations()
        elif template_type == "flow_diagram":
            return self._build_flow_variations()
        elif template_type == "chain_operations":
            return self._build_chain_variations()
        elif template_type == "grid_arithmetic":
            return self._build_grid_variations()
        elif template_type == "symbol_unknown":
            return self._build_symbol_variations()
        return {}
    
    def _build_vertical_variations(self) -> Dict[str, PuzzleVariation]:
        """Vertical arithmetic variatsiyalari"""
        result = {}
        for vid, config in VariationRegistry.VERTICAL_ARITHMETIC_VARIATIONS.items():
            result[vid] = PuzzleVariation(
                variation_id=vid,
                variation_type=VariationType.VISUAL_STYLE,
                base_template="vertical_arithmetic",
                visual_config=config["visual_config"],
                number_config=config["number_config"],
                difficulty_modifier=0.0 if vid != "with_carry" else 0.2
            )
        return result
    
    def _build_flow_variations(self) -> Dict[str, PuzzleVariation]:
        """Flow diagram variatsiyalari"""
        result = {}
        for vid, config in VariationRegistry.FLOW_DIAGRAM_VARIATIONS.items():
            result[vid] = PuzzleVariation(
                variation_id=vid,
                variation_type=VariationType.VISUAL_STYLE,
                base_template="flow_diagram",
                visual_config=config["visual_config"],
                number_config=config["number_config"],
                difficulty_modifier={"vertical": 0.0, "horizontal": 0.1, "tree": 0.2}.get(vid, 0.0)
            )
        return result
    
    def _build_chain_variations(self) -> Dict[str, PuzzleVariation]:
        """Chain operation variatsiyalari"""
        result = {}
        for vid, config in VariationRegistry.CHAIN_VARIATIONS.items():
            result[vid] = PuzzleVariation(
                variation_id=vid,
                variation_type=VariationType.STRUCTURE,
                base_template="chain_operations",
                visual_config=config["visual_config"],
                number_config=config["number_config"],
                difficulty_modifier={"linear": 0.0, "circular": 0.15, "pyramid": 0.2}.get(vid, 0.0)
            )
        return result
    
    def _build_grid_variations(self) -> Dict[str, PuzzleVariation]:
        """Grid arithmetic variatsiyalari"""
        result = {}
        for vid, config in VariationRegistry.GRID_VARIATIONS.items():
            result[vid] = PuzzleVariation(
                variation_id=vid,
                variation_type=VariationType.STRUCTURE,
                base_template="grid_arithmetic",
                visual_config=config["visual_config"],
                number_config=config["number_config"],
                difficulty_modifier={"classic_3x3": 0.0, "latin_4x4": 0.2, "sum_rows_cols": 0.1}.get(vid, 0.0)
            )
        return result
    
    def _build_symbol_variations(self) -> Dict[str, PuzzleVariation]:
        """Symbol unknown variatsiyalari"""
        result = {}
        for vid, config in VariationRegistry.SYMBOL_VARIATIONS.items():
            result[vid] = PuzzleVariation(
                variation_id=vid,
                variation_type=VariationType.COMPLEXITY,
                base_template="symbol_unknown",
                visual_config=config["visual_config"],
                number_config=config["number_config"],
                difficulty_modifier={"simple": 0.0, "multiple": 0.15, "system": 0.3}.get(vid, 0.0)
            )
        return result
    
    def select_variation(self, template_type: str, difficulty: str) -> Optional[PuzzleVariation]:
        """Qiyinlikka qarab variatsiya tanlash"""
        variations = self.get_variations(template_type)
        
        if not variations:
            return None
        
        difficulty_map = {
            "oson": [v for v in variations.values() if v.difficulty_modifier <= 0.1],
            "o'rta": [v for v in variations.values() if 0.0 <= v.difficulty_modifier <= 0.2],
            "qiyin": [v for v in variations.values() if v.difficulty_modifier >= 0.1],
        }
        
        suitable = difficulty_map.get(difficulty, variations.values())
        
        if not suitable:
            suitable = list(variations.values())
        
        return random.choice(suitable)
    
    def apply_variation(self, puzzle, variation: PuzzleVariation) -> Dict:
        """Puzzle ga variatsiya qo'llash"""
        return {
            "original_puzzle": puzzle,
            "variation": variation,
            "visual_config": variation.visual_config,
            "number_config": variation.number_config,
        }
    
    def generate_diverse_set(self, template_type: str, count: int, difficulty: str) -> List[Dict]:
        """Bitta template turidan turli variatsiyalar bilan set yaratish"""
        variations = self.get_variations(template_type)
        result = []
        
        variation_list = list(variations.values())
        
        for i in range(count):
            variation = variation_list[i % len(variation_list)]
            result.append({
                "variation": variation,
                "index": i,
            })
        
        return result


class VariationDifficultyAdjuster:
    """
    Variatsiya qiyinligini sozlash.
    Asosiy qiyinlik + variation modifier = yakuniy qiyinlik.
    """
    
    BASE_DIFFICULTY_WEIGHTS = {
        "oson": 1.0,
        "o'rta": 2.0,
        "qiyin": 3.0,
    }
    
    def __init__(self):
        self.weights = self.BASE_DIFFICULTY_WEIGHTS.copy()
    
    def calculate_difficulty(self, base: str, modifier: float) -> str:
        """Yakuniy qiyinlikni hisoblash"""
        base_weight = self.weights.get(base, 2.0)
        final_weight = base_weight + modifier
        
        if final_weight <= 1.5:
            return "oson"
        elif final_weight <= 2.5:
            return "o'rta"
        else:
            return "qiyin"
    
    def scale_numbers(self, numbers: List[int], base_difficulty: str, target_difficulty: str) -> List[int]:
        """Sonni qiyinlikka qarab o'zgartirish"""
        if base_difficulty == target_difficulty:
            return numbers
        
        if target_difficulty == "oson":
            return [min(n, 20) for n in numbers]
        elif target_difficulty == "qiyin":
            return [n * 2 if n < 50 else n for n in numbers]
        
        return numbers


variation_generator = PuzzleVariationGenerator()
difficulty_adjuster = VariationDifficultyAdjuster()
