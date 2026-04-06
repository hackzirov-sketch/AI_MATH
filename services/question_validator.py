"""
services/question_validator.py — VALIDATOR

Vazifasi:
- Duplicate savollarni tekshirish
- Noto'g'ri javoblarni tekshirish
- Format xatolarini tekshirish
- Savol sonini tekshirish
- Savol ekvivalentligini tekshirish
"""

import hashlib
import logging
import re
import math
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Validatsiya natijasi"""
    is_valid: bool = True
    duplicate_count: int = 0
    invalid_answer_count: int = 0
    format_errors: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    duplicates: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class EquivalenceResult:
    """Ekvivalenti tekshirish natijasi"""
    equivalent: bool
    reason: str
    similarity_score: float = 0.0
    differences: List[str] = field(default_factory=list)


class QuestionValidator:
    """
    Savollarni tekshirish uchun validator
    
    Tekshiradi:
    1. Majburiy maydonlar (savol matni, variantlar, to'g'ri javob)
    2. Variantlar soni (4 ta bo'lishi kerak)
    3. To'g'ri javob variantlar ichida borlig'i
    4. Duplicate savollar
    5. Savol matni uzunligi
    6. Savol ekvivalentligi (matematik)
    """
    
    REQUIRED_FIELDS = ["question", "options", "correct"]
    VALID_OPTIONS = ["A", "B", "C", "D"]
    MIN_QUESTION_LENGTH = 5
    MAX_QUESTION_LENGTH = 500
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def check_equivalence(self, q1: Dict, q2: Dict) -> EquivalenceResult:
        """
        Ikki savolning matematik ekvivalentligini tekshiradi.
        
        Qoidalar:
        - Label nomlarini e'tiborsiz qoldiradi
        - Tartib farqlarini e'tiborsiz qoldiradi
        - Haqiqiy qiymatlarni va strukturani solishtiradi
        """
        topic1 = q1.get("topic", "")
        topic2 = q2.get("topic", "")
        
        if topic1 != topic2:
            return EquivalenceResult(
                equivalent=False,
                reason=f"Turli mavzular: '{topic1}' vs '{topic2}'",
                similarity_score=0.0
            )
        
        params1 = self._extract_math_params(q1)
        params2 = self._extract_math_params(q2)
        
        if not params1 or not params2:
            return self._check_text_equivalence(q1, q2)
        
        is_equiv, reason, score, diffs = self._compare_math_params(params1, params2)
        
        return EquivalenceResult(
            equivalent=is_equiv,
            reason=reason,
            similarity_score=score,
            differences=diffs
        )
    
    def _extract_math_params(self, question: Dict) -> Dict[str, Any]:
        """Savoldan matematik parametrlarni ajratish"""
        params = {}
        
        if "question_signature" in question:
            sig = question["question_signature"]
            parts = sig.split("|")
            if len(parts) >= 3:
                for part in parts[2:]:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        params[key.strip()] = self._normalize_value(value.strip())
        
        if "template_id" in question:
            params["_template"] = question["template_id"]
        
        numeric_fields = [
            "side_ab", "side_bc", "side_ac", "side_a", "side_b", "side_c",
            "width", "height", "radius", "diameter", "area", "perimeter",
            "angle_a", "angle_b", "angle_c", "base", "height", "leg"
        ]
        
        for field in numeric_fields:
            if field in question and question[field] is not None:
                try:
                    params[field] = float(question[field])
                except (ValueError, TypeError):
                    pass
        
        return params
    
    def _normalize_value(self, value: str) -> Any:
        """Qiymatni normalizatsiya qilish"""
        value = value.strip()
        
        try:
            if "." in value:
                return round(float(value), 2)
            return int(value)
        except ValueError:
            pass
        
        if value.startswith("[") and value.endswith("]"):
            try:
                nums = [float(x.strip()) for x in value[1:-1].split(",")]
                return tuple(sorted(nums))
            except ValueError:
                pass
        
        return value
    
    def _compare_math_params(self, p1: Dict, p2: Dict) -> Tuple[bool, str, float, List[str]]:
        """Matematik parametrlarni solishtirish"""
        differences = []
        
        all_keys = set(p1.keys()) | set(p2.keys())
        all_keys.discard("_template")
        
        matching = 0
        total = len(all_keys)
        
        for key in all_keys:
            v1 = p1.get(key)
            v2 = p2.get(key)
            
            if v1 is None:
                differences.append(f"{key}: faqat 2-savolda bor ({v2})")
            elif v2 is None:
                differences.append(f"{key}: faqat 1-savolda bor ({v1})")
            elif self._values_equivalent(v1, v2):
                matching += 1
            else:
                differences.append(f"{key}: {v1} vs {v2}")
        
        score = matching / total if total > 0 else 0
        
        if score >= 0.9 and len(differences) == 0:
            return True, "Matematik jihatdan ekvivalent", score, []
        elif score >= 0.7:
            minor_diffs = [d for d in differences if "_template" not in d]
            if len(minor_diffs) <= 2:
                return True, f"Ekvivalent ({(score*100):.0f}%)", score, minor_diffs
        
        return False, f"Ekvivalsiz ({(score*100):.0f}%)", score, differences
    
    def _values_equivalent(self, v1: Any, v2: Any, tolerance: float = 0.01) -> bool:
        """Ikki qiymat ekvivalentmi"""
        if type(v1) != type(v2):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                return abs(float(v1) - float(v2)) < tolerance
            return False
        
        if isinstance(v1, (int, float)):
            return abs(v1 - v2) < tolerance
        
        if isinstance(v1, tuple) and isinstance(v2, tuple):
            if len(v1) != len(v2):
                return False
            return all(abs(a - b) < tolerance for a, b in zip(v1, v2))
        
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.lower() == v2.lower()
        
        return v1 == v2
    
    def _check_text_equivalence(self, q1: Dict, q2: Dict) -> EquivalenceResult:
        """Matn ekvivalentligini tekshirish"""
        text1 = self._normalize_question_text(q1.get("question", ""))
        text2 = self._normalize_question_text(q2.get("question", ""))
        
        ratio = SequenceMatcher(None, text1, text2).ratio()
        
        if ratio >= 0.85:
            return EquivalenceResult(
                equivalent=True,
                reason="Matn jihatdan o'xshash",
                similarity_score=ratio
            )
        
        return EquivalenceResult(
            equivalent=False,
            reason=f"Matn farqli ({(ratio*100):.0f}% o'xshash)",
            similarity_score=ratio
        )
    
    def _normalize_question_text(self, text: str) -> str:
        """Savol matnini normalizatsiya qilish"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def are_questions_equivalent(self, q1: Dict, q2: Dict) -> bool:
        """Ikki savol ekvivalentmi (qisqa tekshirish)"""
        result = self.check_equivalence(q1, q2)
        return result.equivalent
    
    def validate_batch(self, questions: List[Dict], expected_count: int) -> ValidationResult:
        """Barcha savollarni tekshirish"""
        result = ValidationResult()
        
        if not questions:
            result.is_valid = False
            result.format_errors.append("Savollar ro'yxati bo'sh")
            return result
        
        if len(questions) < expected_count:
            result.warnings.append(
                f"Yetarlicha savol yo'q: {len(questions)}/{expected_count}"
            )
        
        seen_questions: Set[str] = set()
        seen_hashes: Set[str] = set()
        
        for i, q in enumerate(questions):
            q_errors = self._validate_single_question(q, i)
            
            if q_errors:
                result.format_errors.extend(q_errors)
            
            if "question" in q:
                q_hash = self._get_question_hash(q["question"])
                
                if q_hash in seen_hashes:
                    result.duplicate_count += 1
                    result.duplicates.append(q)
                    logger.warning(f"Duplicate question found at index {i}")
                else:
                    seen_hashes.add(q_hash)
                
                q_normalized = q["question"].lower().strip()
                for seen in seen_questions:
                    if self._is_similar(q_normalized, seen):
                        result.duplicate_count += 1
                        result.duplicates.append(q)
                        logger.warning(f"Similar question found at index {i}")
                        break
                seen_questions.add(q_normalized)
        
        result.is_valid = len(result.format_errors) == 0
        
        return result
    
    def _validate_single_question(self, question: Dict, index: int) -> List[str]:
        """Bitta savolni tekshirish"""
        errors = []
        
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in question or question[field_name] is None:
                errors.append(f"[{index}] '{field_name}' maydoni yo'q")
                continue
            
            if field_name == "question":
                q_text = str(question[field_name])
                if len(q_text) < self.MIN_QUESTION_LENGTH:
                    errors.append(f"[{index}] Savol matni juda qisqa")
                elif len(q_text) > self.MAX_QUESTION_LENGTH:
                    errors.append(f"[{index}] Savol matni juda uzun")
            
            if field_name == "options":
                opts = question[field_name]
                if not isinstance(opts, dict):
                    errors.append(f"[{index}] Variantlar lug'at bo'lishi kerak")
                elif len(opts) != 4:
                    errors.append(f"[{index}] Variantlar soni 4 ta bo'lishi kerak (hozir: {len(opts)})")
                else:
                    for label in self.VALID_OPTIONS:
                        if label not in opts:
                            errors.append(f"[{index}] '{label}' variantasi yo'q")
            
            if field_name == "correct":
                correct = str(question[field_name]).upper()
                if correct not in self.VALID_OPTIONS:
                    errors.append(f"[{index}] To'g'ri javob noto'g'ri belgi: '{correct}'")
                elif "options" in question and correct not in question["options"]:
                    errors.append(f"[{index}] To'g'ri javob '{correct}' variantlar ichida yo'q")
        
        return errors
    
    def _get_question_hash(self, question_text: str) -> str:
        """Savol matnining hashini olish"""
        normalized = question_text.lower().strip()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """Ikki matn o'xshashligini tekshirish"""
        if not text1 or not text2:
            return False
        
        ratio = SequenceMatcher(None, text1, text2).ratio()
        return ratio >= self.similarity_threshold
    
    def remove_duplicates(self, questions: List[Dict]) -> List[Dict]:
        """Duplicate savollarni olib tashlash"""
        seen_hashes: Set[str] = set()
        unique_questions: List[Dict] = []
        
        for q in questions:
            if "question" not in q:
                unique_questions.append(q)
                continue
            
            q_hash = self._get_question_hash(q["question"])
            
            if q_hash not in seen_hashes:
                seen_hashes.add(q_hash)
                unique_questions.append(q)
            else:
                logger.debug(f"Removing duplicate: {q.get('question', '')[:50]}")
        
        return unique_questions
    
    def fix_common_issues(self, question: Dict) -> Dict:
        """Keng tarqalgan muammolarni tuzatish"""
        fixed = question.copy()
        
        if "options" in fixed and isinstance(fixed["options"], dict):
            for key in list(fixed["options"].keys()):
                new_key = key.upper()
                if new_key != key:
                    fixed["options"][new_key] = fixed["options"].pop(key)
        
        if "correct" in fixed:
            fixed["correct"] = str(fixed["correct"]).upper()
        
        if "question" in fixed:
            fixed["question"] = fixed["question"].strip()
        
        return fixed
    
    def validate_answer_options(self, question: Dict) -> bool:
        """To'g'ri javob variantlar ichida borlig'ini tekshirish"""
        if "correct" not in question or "options" not in question:
            return False
        
        correct = str(question["correct"]).upper()
        options = question.get("options", {})
        
        if not isinstance(options, dict):
            return False
        
        return correct in options
    
    def get_question_stats(self, questions: List[Dict]) -> Dict:
        """Savollar statistikasi"""
        return {
            "total": len(questions),
            "with_images": sum(1 for q in questions if q.get("has_image")),
            "topics": list(set(q.get("topic", "unknown") for q in questions)),
            "grades": list(set(str(q.get("grade", "?")) for q in questions)),
        }


question_validator = QuestionValidator()
