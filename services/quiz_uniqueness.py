"""
services/quiz_uniqueness.py — UNIQUENESS TRACKING

Bu modul quiz ichida takrorlanishlarni oldini oladi.

Saqlaydi:
- used_topics
- used_templates
- used_question_signatures
- used_render_signatures
- used_label_sets
- used_orientations
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from collections import Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class UniquenessStats:
    """Uniqueness statistika"""
    total_candidates_checked: int = 0
    duplicates_rejected: int = 0
    topics_used: Counter = field(default_factory=Counter)
    templates_used: Counter = field(default_factory=Counter)
    label_sets_used: Counter = field(default_factory=Counter)
    orientations_used: Counter = field(default_factory=Counter)


class QuizUniquenessSession:
    """
    Bitta quiz sessiyasi uchun uniqueness tracking.
    
    Har quiz generatsiya paytida yangi session ochiladi.
    """
    
    def __init__(self, quiz_id: Optional[str] = None):
        self.quiz_id = quiz_id or str(uuid.uuid4())[:8]
        self.session_id = f"quiz_{self.quiz_id}"
        
        self._used_topics: Set[str] = set()
        self._used_templates: Set[str] = set()
        self._used_question_signatures: Set[str] = set()
        self._used_render_signatures: Set[str] = set()
        self._used_label_sets: Set[str] = set()
        self._used_orientations: Set[str] = set()
        self._used_shapes: Set[str] = set()
        
        self._question_count_by_topic: Counter = Counter()
        self._render_count_by_signature: Counter = Counter()
        
        self.stats = UniquenessStats()
    
    def check_topic_used(self, topic: str) -> bool:
        """Topic ishlatilganmi?"""
        return topic in self._used_topics
    
    def check_template_used(self, template_id: str) -> bool:
        """Template ishlatilganmi?"""
        return template_id in self._used_templates
    
    def check_question_signature(self, signature: str) -> bool:
        """Question signature takrorlanmaganmi?"""
        return signature in self._used_question_signatures
    
    def check_render_signature(self, signature: str) -> bool:
        """Render signature takrorlanmaganmi?"""
        return signature in self._used_render_signatures
    
    def check_label_set(self, label_set: str) -> bool:
        """Label set ishlatilganmi?"""
        return label_set in self._used_label_sets
    
    def check_orientation(self, orientation: str) -> bool:
        """Orientation ishlatilganmi?"""
        return orientation in self._used_orientations
    
    def mark_topic_used(self, topic: str):
        """Topicni ishlatilgan deb belgilash"""
        self._used_topics.add(topic)
        self._question_count_by_topic[topic] += 1
        self.stats.topics_used[topic] += 1
    
    def mark_template_used(self, template_id: str):
        """Templateni ishlatilgan deb belgilash"""
        self._used_templates.add(template_id)
        self.stats.templates_used[template_id] += 1
    
    def mark_question_signature(self, signature: str):
        """Question signatureni ishlatilgan deb belgilash"""
        self._used_question_signatures.add(signature)
    
    def mark_render_signature(self, signature: str):
        """Render signatureni ishlatilgan deb belgilash"""
        self._used_render_signatures.add(signature)
        self._render_count_by_signature[signature] += 1
    
    def mark_label_set(self, label_set: str):
        """Label setni ishlatilgan deb belgilash"""
        self._used_label_sets.add(label_set)
        self.stats.label_sets_used[label_set] += 1
    
    def mark_orientation(self, orientation: str):
        """Orientationni ishlatilgan deb belgilash"""
        self._used_orientations.add(orientation)
        self.stats.orientations_used[orientation] += 1
    
    def mark_shape(self, shape: str):
        """Shape ishlatilgan deb belgilash"""
        self._used_shapes.add(shape)
    
    def can_use_topic(self, topic: str, max_per_topic: int = 3) -> bool:
        """Topic ishlatilsa bo'ladimi?"""
        if topic not in self._used_topics:
            return True
        return self._question_count_by_topic[topic] < max_per_topic
    
    def can_use_label_set(self, label_set: str, max_per_set: int = 2) -> bool:
        """Label set ishlatilsa bo'ladimi?"""
        if label_set not in self._used_label_sets:
            return True
        return self.stats.label_sets_used.get(label_set, 0) < max_per_set
    
    def can_use_orientation(self, orientation: str, max_per_orientation: int = 2) -> bool:
        """Orientation ishlatilsa bo'ladimi?"""
        if orientation not in self._used_orientations:
            return True
        return self.stats.orientations_used.get(orientation, 0) < max_per_orientation
    
    def get_topic_usage_count(self, topic: str) -> int:
        """Topic necha marta ishlatilgan?"""
        return self._question_count_by_topic.get(topic, 0)
    
    def get_available_topics(self, all_topics: List[str], max_per_topic: int = 3) -> List[str]:
        """Ishlatilmagan yoki kam ishlatilgan topiclarni qaytaradi"""
        return [t for t in all_topics if self.can_use_topic(t, max_per_topic)]
    
    def get_available_label_sets(self, all_label_sets: List[str], max_per_set: int = 2) -> List[str]:
        """Ishlatilmagan yoki kam ishlatilgan label setlarni qaytaradi"""
        return [ls for ls in all_label_sets if self.can_use_label_set(ls, max_per_set)]
    
    def get_available_orientations(self, all_orientations: List[str], max_per_orientation: int = 2) -> List[str]:
        """Ishlatilmagan yoki kam ishlatilgan orientationlarni qaytaradi"""
        return [o for o in all_orientations if self.can_use_orientation(o, max_per_orientation)]


class UniquenessChecker:
    """
    Global uniqueness tekshiruvchi.
    
    Question signature va render signature ni tekshiradi
    va ularni bir xil deb hisoblash uchun canonicalize qiladi.
    """
    
    @staticmethod
    def canonicalize_geometry_params(params: Dict) -> Dict:
        """Geometriya parametrlarini canonical ko'rinishga keltiradi"""
        canonical = {}
        for key, value in sorted(params.items()):
            if isinstance(value, (list, tuple)):
                value = tuple(sorted(value))
            elif isinstance(value, float):
                value = round(value, 2)
            canonical[key] = value
        return canonical
    
    @staticmethod
    def are_geometries_equivalent(params1: Dict, params2: Dict) -> bool:
        """Ikki geometriya parametri ekvivalentmi?"""
        c1 = UniquenessChecker.canonicalize_geometry_params(params1)
        c2 = UniquenessChecker.canonicalize_geometry_params(params2)
        return c1 == c2
    
    @staticmethod
    def are_puzzles_equivalent(params1: Dict, params2: Dict) -> bool:
        """Ikki puzzle parametri ekvivalentmi?"""
        c1 = UniquenessChecker.canonicalize_geometry_params(params1)
        c2 = UniquenessChecker.canonicalize_geometry_params(params2)
        return c1 == c2
    
    @staticmethod
    def normalize_label_set(labels: List[str]) -> Tuple[str, ...]:
        """Label setni normalizatsiya qiladi (ABC = PQR = XYZ)"""
        return tuple(sorted(labels))


class DiversityScorer:
    """
    Candidate savollarni diversity bo'yicha baholaydi.
    
    Qanchalik xilma-xil bo'lsa, shunchalik yuqori score.
    """
    
    def __init__(self, session: QuizUniquenessSession):
        self.session = session
    
    def score_candidate(self, candidate: Dict) -> float:
        """
        Candidate uchun diversity score hisoblaydi.
        
        Score balandroq = yaxshiroq (ko'proq xilma-xil)
        """
        score = 100.0
        penalties = []
        
        topic = candidate.get("topic", "")
        if not self.session.can_use_topic(topic):
            return 0.0
        
        if self.session.check_topic_used(topic):
            penalties.append(("topic", 15))
        
        template = candidate.get("template_id", "")
        if self.session.check_template_used(template):
            penalties.append(("template", 20))
        
        shape = candidate.get("shape_type", "")
        if shape in self.session._used_shapes:
            penalties.append(("shape", 25))
        
        label_set = candidate.get("label_set", "")
        if label_set in self.session._used_label_sets:
            count = self.session.stats.label_sets_used.get(label_set, 0)
            penalties.append(("label_set", 10 + count * 5))
        
        orientation = candidate.get("orientation", "")
        if orientation in self.session._used_orientations:
            count = self.session.stats.orientations_used.get(orientation, 0)
            penalties.append(("orientation", 8 + count * 4))
        
        for penalty_name, penalty_value in penalties:
            score -= penalty_value
            logger.debug(f"Penalty: {penalty_name} = {penalty_value}")
        
        return max(score, 0.0)
    
    def select_best_candidate(self, candidates: List[Dict]) -> Optional[Dict]:
        """Eng yaxshi diversity scorega ega candidateni tanlaydi"""
        if not candidates:
            return None
        
        scored = [(self.score_candidate(c), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        best_score, best_candidate = scored[0]
        
        if best_score <= 0:
            return None
        
        return best_candidate


class UniquenessManager:
    """
    Uniqueness tizimining asosiy boshqaruvchisi.
    
    Quiz sessiyalarini boshqaradi va global cache taqdim etadi.
    """
    
    def __init__(self):
        self._sessions: Dict[str, QuizUniquenessSession] = {}
        self._global_question_signatures: Set[str] = set()
    
    def create_session(self, quiz_id: Optional[str] = None) -> QuizUniquenessSession:
        """Yangi quiz sessiyasi yaratadi"""
        session = QuizUniquenessSession(quiz_id)
        self._sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[QuizUniquenessSession]:
        """Sessiyani olish"""
        return self._sessions.get(session_id)
    
    def end_session(self, session_id: str):
        """Sessiyani tugatish"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def check_global_question_signature(self, signature: str) -> bool:
        """Global miqyosda question signature takrorlanmaganmi?"""
        return signature in self._global_question_signatures
    
    def mark_global_question_signature(self, signature: str):
        """Global question signatureni belgilash"""
        self._global_question_signatures.add(signature)
    
    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """Eski sessiyalarni tozalash"""
        import time
        current_time = time.time()
        
        expired = []
        for session_id, session in self._sessions.items():
            pass
        
        for session_id in expired:
            self.end_session(session_id)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired uniqueness sessions")


uniqueness_manager = UniquenessManager()
