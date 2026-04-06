"""
services/test_builder.py — ORCHESTRATOR (Miya)

Bu fayl butun tizimning "miyasi":

Vazifasi:
- Qaysi generator ishlashini hal qiladi
- Savollarni yig'adi
- Javoblarni shakllantiradi
- Validatsiya qiladi
- PDF generatorga beradi

Integratsiya:
- topic_generator: Akademik savollar
- geometry_pool: Geometriya savollari (render specs bilan)
- puzzle_pool: Puzzle savollari (shu jumladan logic puzzles)
- question_validator: Validatsiya va ekvivalentlik tekshirish
- quiz_uniqueness: Uniqueness tracking
- render_pool: Renderer dispatcher
- pdf_generator: A4 PDF yaratish
"""

import random
import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from services.topic_registry import get_topics_for_grade, SUBJECT_TYPES
from services.puzzle_engine import puzzle_engine
from services.topic_generator import TopicGenerator, topic_generator
from services.pdf_generator import pdf_generator
from services.book_question_bank import book_question_bank
from services.critical_thinking_bank import critical_thinking_bank
from services.question_validator import QuestionValidator, ValidationResult, EquivalenceResult
from services.quiz_uniqueness import QuizUniquenessSession, uniqueness_manager, DiversityScorer
from services.geometry_pool import geometry_pool
from services.render_pool import render_pool
from services.hybrid_puzzle_generator import hybrid_puzzle_generator, hybrid_puzzle_renderer
from services.puzzle_pool import puzzle_pool
from services.question_schema import QuestionItem
from services.math_verifier import math_verifier
from services.rag_quiz_generator import rag_quiz_generator
from services.observability import create_generation_trace
from services.topic_context_service import topic_context_service
from services.self_improvement.engine import self_improvement_engine
from services.worker_layer import worker_layer

logger = logging.getLogger(__name__)


@dataclass
class TestRequest:
    """Test so'rovi - barcha kerakli ma'lumotlar bir joyda"""
    grade: int
    difficulty: str
    question_count: int
    subject: str
    topic: Optional[str] = None
    include_geometry: bool = True
    include_puzzles: bool = False
    teacher_name: str = ""
    time_limit: int = 0
    
    def __post_init__(self):
        self.subject = self.subject.lower().strip()
        self.difficulty = self.difficulty.lower().strip()


@dataclass
class TestResponse:
    """Test javobi - generatsiya natijasi"""
    success: bool
    questions: List[Dict] = field(default_factory=list)
    answers: List[Dict] = field(default_factory=list)
    test_pdf_path: Optional[str] = None
    answers_pdf_path: Optional[str] = None
    error_message: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    equivalence_checks: List[EquivalenceResult] = field(default_factory=list)
    request_id: Optional[str] = None
    generation_id: Optional[str] = None


class TestBuilder:
    """
    ORCHESTRATOR - Test yaratish jarayonini boshqaradi
    
    Pipeline: Request → Generator → Validator → PDF → Response
    
    Integratsiya qilingan komponentlar:
    - TopicGenerator: Akademik savollar
    - GeometryPool: Geometriya savollari
    - PuzzlePool: Logic puzzles
    - QuestionValidator: Validatsiya + ekvivalentlik
    - QuizUniqueness: Session-based uniqueness
    - RenderPool: Renderer dispatcher
    - PDFGenerator: A4 PDF
    """
    
    def __init__(self):
        self.validator = QuestionValidator()
        self.topic_generator = TopicGenerator()
        self._topic_cache = self._load_topic_suggestions()
        self.worker_layer = worker_layer
    
    def _load_topic_suggestions(self) -> Dict[str, List[str]]:
        """Fanlar bo'yicha mavzu tavsiyalari (topic_registry dan olamiz)"""
        return {
            "matematika": ["Arifmetika", "Kasrlar", "Tenglamalar", "Perimetr", "Yuza", "Geometriya"],
            "algebra": ["Ifodalar", "Tenglamalar", "Funksiyalar", "Progressiyalar"],
            "geometriya": ["Uchburchak", "To'rtburchaklar", "Aylana", "Pifagor teoremasi"],
            "ehtimollik": ["Ehtimollik", "Kombinatorika", "Tasodifiy miqdor", "Matematik statistika"],
            "mantiq": ["Mantiqiy savollar", "Boshqotirma", "Naqshlar"],
            "iq": ["Analogiya", "Ketma-ketlik", "Kodlash", "Tanqidiy tahlil", "Matn tahlili"],
            "prezident": ["Tanqidiy tahlil", "Mantiqiy xulosa", "Matn tahlili", "Tartib va joylashuv"],
        }
    
    def _topic_name_mapping(self) -> Dict[str, List[str]]:
        """Foydalanuvchi mavzu nomlari va real topic ID lar o'rtasidaqqorilama"""
        return {
            "arifmetika": ["qoshish", "ayirish", "kopaytirish", "bolish", "sonlar_0_100", "sonlar_1000"],
            "kasrlar": ["kasr_tushuncha", "surat_maxraj", "kasrlarni_solishtirish", "kasrlarni_qoshish"],
            "tenglamalar": ["noma_lum_x_topish", "tenglama_birinchi_daraja", "tenglamalar_sistemasi"],
            "perimetr": ["perimetr", "perimetr_yuza_5", "togri_tortburchak_kvadrat"],
            "yuza": ["yuza", "perimetr_yuza_5", "uchburchak_yuza"],
            "geometriya": ["shakllar", "togri_burchak", "burchak", "kesma", "uchburchak", "tortburchak"],
            "ifodalar": ["arifmetik_ifodalar", "qavsli_ifodalar", "amallar_tartibi"],
            "funksiyalar": ["funksiya_tushuncha", "funksiya_graph", "chiziqli_funksiya"],
            "progressiyalar": ["arifmetik_progressiya", "geometrik_progressiya"],
        }
    
    def _normalize_topic(self, topic: str) -> str:
        """Mavzu nomini normalize qilish"""
        topic_lower = topic.lower().strip()
        
        mapping = self._topic_name_mapping()
        for key, topics in mapping.items():
            if topic_lower == key or topic_lower in key:
                return topics[0]
        
        return topic_lower
    
    def _get_topic_ids(self, topic: str) -> List[str]:
        """Mavzu nomi bo'yicha real topic ID larni olish"""
        if not topic:
            return []
        
        topic_lower = topic.lower().strip()
        
        mapping = {
            "arifmetika": [
                "qoshish", "ayirish", "kopaytirish", "bolish",
                "qoshish_ayirish_5", "kopaytirish_ustun_5", "bolish_ustun_5",
                "amallar_tartibi_5", "kop_xonali_sonlar"
            ],
            "kasrlar": [
                "kasr_tushuncha", "surat_maxraj", "kasrlarni_solishtirish", 
                "kasrlarni_qoshish", "oddiy_kasrlar_5", "kasrlarni_qisqartirish_5",
                "kasrlarni_taqqoslash_5", "kasr_qoshish_ayirish_5",
                "kasr_kopaytirish_bolish_5", "onli_kasrlar_5"
            ],
            "kasrlar": [
                "kasr_tushuncha", "surat_maxraj", "kasrlarni_solishtirish", 
                "kasrlarni_qoshish", "oddiy_kasrlar_5", "kasrlarni_qisqartirish_5",
                "kasrlarni_taqqoslash_5", "kasr_qoshish_ayirish_5",
                "kasr_kopaytirish_bolish_5", "onli_kasrlar_5"
            ],
            "tenglamalar": [
                "noma_lum_x_topish", "tenglama_birinchi_daraja", 
                "tenglamalar_sistemasi", "tenglamalar", "harfli_ifodalar"
            ],
            "perimetr": [
                "perimetr", "perimetr_yuza_5", "togri_tortburchak_kvadrat",
                "togri_tortburchak_kvadrat_5"
            ],
            "yuza": [
                "yuza", "perimetr_yuza_5", "uchburchak_yuza"
            ],
            "geometriya": [
                "shakllar", "togri_burchak", "burchak", "kesma", "uchburchak", 
                "tortburchak", "geometriya_nuqta", "burchaklar_5",
                "uchburchak_turlari_5", "togri_tortburchak_kvadrat_5"
            ],
        }
        
        return mapping.get(topic_lower, [topic_lower])
    
    def suggest_topics(self, subject: str) -> List[str]:
        """Fanga qarab mavzu tavsiyalarini beradi"""
        subject_lower = subject.lower()
        
        suggestions: List[str] = []
        for topic in critical_thinking_bank.get_available_topics(subject=subject, limit=8):
            if topic not in suggestions:
                suggestions.append(topic)

        for key, topics in self._topic_cache.items():
            if key in subject_lower or subject_lower in key:
                for topic in topics:
                    if topic not in suggestions:
                        suggestions.append(topic)
                break
        
        if not suggestions:
            for topic in self._topic_cache.get("matematika", []):
                if topic not in suggestions:
                    suggestions.append(topic)
        
        for topic in book_question_bank.get_available_topics(subject=subject, limit=8):
            if topic not in suggestions:
                suggestions.append(topic)
        
        return suggestions[:10]

    def _resolve_quiz_type(self, request: TestRequest) -> str:
        return topic_context_service.infer_quiz_type(request.subject, request.topic)

    def _normalize_question_item(self, request: TestRequest, question: Dict) -> QuestionItem:
        return QuestionItem.from_legacy_dict(
            question,
            subject=request.subject,
            grade=request.grade,
            difficulty=request.difficulty,
        )

    def _validate_and_normalize_questions(self, request: TestRequest, questions: List[Dict]) -> List[Dict]:
        normalized_questions: List[Dict] = []
        for raw_question in questions:
            item = self._normalize_question_item(request, raw_question)
            validation = math_verifier.validate_question_item(item)
            item.metadata["validation_status"] = "deterministic_valid" if validation.is_valid and validation.is_deterministic else (
                "deterministic_failed" if validation.is_deterministic else "not_deterministic"
            )
            if validation.errors:
                item.metadata["validation_errors"] = list(validation.errors)
            if validation.warnings:
                item.metadata["validation_warnings"] = list(validation.warnings)

            if validation.is_deterministic and not validation.is_valid:
                logger.warning("Question rejected by math verifier: %s", validation.errors)
                continue

            normalized_payload = item.to_legacy_dict()
            for field_name in (
                "render_spec",
                "image_bytes",
                "has_image",
                "requires_image",
                "template_id",
                "question_signature",
                "render_signature",
                "puzzle_data",
                "template_type",
            ):
                if field_name in raw_question:
                    normalized_payload[field_name] = raw_question[field_name]
            normalized_questions.append(normalized_payload)
        return normalized_questions
    
    def build_test(self, request: TestRequest) -> TestResponse:
        """
        ASOSIY METOD - Test yaratish pipeline
        
        Pipeline:
        1. Uniqueness session yaratish
        2. Generator tanlash (akademik, geometriya, puzzle)
        3. Savollar generatsiya qilish
        4. Validatsiya qilish (shu jumladan ekvivalentlik)
        5. PDF yaratish
        6. Natijani qaytarish
        """
        trace = create_generation_trace()
        try:
            trace.log_event(
                "test_build_started",
                subject=request.subject,
                topic=request.topic or "",
                grade=request.grade,
                difficulty=request.difficulty,
                question_count=request.question_count,
            )
            
            session = uniqueness_manager.create_session()
            scorer = DiversityScorer(session)
            
            with trace.timer("generation_ms"):
                questions = self._generate_questions(request, session, scorer)
            
            if not questions:
                return TestResponse(
                    success=False,
                    error_message="Savollar generatsiya qilinmadi",
                    request_id=trace.request_id,
                    generation_id=trace.generation_id,
                )

            questions = self._validate_and_normalize_questions(request, questions)
            
            validation = self.validator.validate_batch(questions, request.question_count)
            
            equivalence_results = self._check_equivalence(questions)
            
            if validation.duplicate_count > 0:
                questions = self.validator.remove_duplicates(questions)
                logger.info(f"Duplicates removed: {validation.duplicate_count}")
            
            while len(questions) < request.question_count:
                extra_q = self._generate_single_question(request, session)
                if extra_q:
                    normalized = self._validate_and_normalize_questions(request, [extra_q])
                    questions.extend(normalized)
            
            questions = questions[:request.question_count]
            
            with trace.timer("render_ms"):
                self._render_questions(questions)
            
            with trace.timer("pdf_ms"):
                test_pdf = self._generate_test_pdf(request, questions)
                answers_pdf = self._generate_answers_pdf(request, questions)
            
            answers = []
            for i, q in enumerate(questions):
                correct = q.get('correct', q.get('correct_label', '?'))
                value = q.get('correct_value', q.get('answer', ''))
                answers.append({"number": i+1, "correct": correct, "value": value})
            
            uniqueness_manager.end_session(session.session_id)
            
            trace.log_event(
                "test_build_completed",
                generated_questions=len(questions),
                metrics=trace.metrics,
            )

            self_improvement_engine.record_generation_outcome(
                request_payload={
                    "subject": request.subject,
                    "grade": request.grade,
                    "difficulty": request.difficulty,
                    "topic": request.topic,
                },
                response_payload={
                    "success": True,
                    "questions": questions,
                    "generator_used": self._resolve_quiz_type(request),
                },
                trace_metrics=trace.metrics,
            )
            
            return TestResponse(
                success=True,
                questions=questions,
                answers=answers,
                test_pdf_path=test_pdf,
                answers_pdf_path=answers_pdf,
                validation_result=validation,
                equivalence_checks=equivalence_results,
                request_id=trace.request_id,
                generation_id=trace.generation_id,
            )
            
        except Exception as e:
            logger.error(f"Test build error: {e}")
            self_improvement_engine.record_generation_outcome(
                request_payload={
                    "subject": request.subject,
                    "grade": request.grade,
                    "difficulty": request.difficulty,
                    "topic": request.topic,
                },
                response_payload={
                    "success": False,
                    "questions": [],
                    "generator_used": self._resolve_quiz_type(request),
                    "error_message": str(e),
                },
                trace_metrics=trace.metrics,
            )
            return TestResponse(
                success=False,
                error_message=str(e),
                request_id=trace.request_id,
                generation_id=trace.generation_id,
            )
    
    def _generate_questions(self, request: TestRequest, session: QuizUniquenessSession, scorer: DiversityScorer) -> List[Dict]:
        """Savollarni generatsiya qilish"""
        questions = []
        
        subject_lower = request.subject.lower()
        is_critical_request = critical_thinking_bank.supports(subject=request.subject, topic=request.topic)
        
        if is_critical_request:
            questions = self._generate_academic_questions(request, session)
        elif subject_lower in ["boshqotirma", "mantiq", "puzzle"]:
            questions = self._generate_puzzle_questions(request, session)
        elif request.topic and not request.include_geometry:
            questions = self._generate_academic_questions(request, session)
        elif request.include_geometry and subject_lower in ["geometriya", "matematika"]:
            topic_ids = self._get_topic_ids(request.topic)
            if topic_ids:
                questions = self._generate_academic_questions(request, session)
            else:
                geo_count = min(request.question_count // 3, 3)
                acad_count = request.question_count - geo_count
                questions = self._generate_mixed_questions(request, session, scorer, geo_count, acad_count)
        else:
            questions = self._generate_academic_questions(request, session)
        
        return questions
    
    def _generate_mixed_questions(self, request: TestRequest, session: QuizUniquenessSession, 
                                  scorer: DiversityScorer, geo_count: int, acad_count: int) -> List[Dict]:
        """Aralash savollar (geometriya + akademik)"""
        questions = []
        
        for _ in range(geo_count):
            geo_question = self._generate_geometry_question(request, session)
            if geo_question:
                questions.append(geo_question)
        
        for _ in range(acad_count):
            acad_question = self._generate_academic_question(request, session)
            if acad_question:
                questions.append(acad_question)
        
        random.shuffle(questions)
        
        return questions
    
    def _generate_geometry_question(self, request: TestRequest, session: QuizUniquenessSession) -> Optional[Dict]:
        """Geometriya savoli generatsiya qilish"""
        try:
            topic = geometry_pool.generate_random_topic(session, request.grade)
            if not topic:
                return None
            
            question_spec = geometry_pool.generate_question(topic, session, request.grade, request.difficulty)
            if not question_spec:
                return None
            
            return question_spec.to_dict()
        except Exception as e:
            logger.error(f"Geometry question error: {e}")
            return None
    
    def _generate_academic_question(self, request: TestRequest, session: QuizUniquenessSession) -> Optional[Dict]:
        """Akademik savol generatsiya qilish"""
        try:
            topics = get_topics_for_grade(request.grade)
            if not topics:
                return None
            
            topic_dict = random.choice(topics)
            slug = topic_dict.get("slug")
            
            # Agar TopicGenerator da shu mavzu bo'lsa, undan foydalanamiz (tezroq va aniqroq)
            if slug and hasattr(self.topic_generator, f"generate_{slug}"):
                question = getattr(self.topic_generator, f"generate_{slug}")(request.difficulty)
            else:
                question = self.topic_generator.generate_question(
                    request.grade,
                    request.difficulty,
                    slug or topic_dict.get("title"),
                )
            
            if question:
                session.mark_topic_used(slug or "general")
            
            return question
        except Exception as e:
            logger.error(f"Academic question error: {e}")
            return None
    
    def _generate_academic_questions(self, request: TestRequest, session: QuizUniquenessSession) -> List[Dict]:
        """Akademik fanlar uchun savollar - AI orqali generatsiya"""
        try:
            questions = self._generate_book_questions(request, session)
            if len(questions) >= request.question_count:
                return questions[:request.question_count]

            if request.topic:
                remaining = request.question_count - len(questions)
                rag_questions = self._generate_rag_questions(request, remaining)
                for q in rag_questions:
                    topic = q.get("topic", "")
                    if topic:
                        session.mark_topic_used(topic)
                questions.extend(rag_questions)
                if len(questions) >= request.question_count:
                    return questions[:request.question_count]

            remaining = request.question_count - len(questions)
            if remaining > 0:
                fallback_request = TestRequest(
                    grade=request.grade,
                    difficulty=request.difficulty,
                    question_count=remaining,
                    subject=request.subject,
                    topic=request.topic,
                    include_geometry=request.include_geometry,
                    include_puzzles=request.include_puzzles,
                    teacher_name=request.teacher_name,
                    time_limit=request.time_limit,
                )
                questions.extend(self._generate_standard_academic_questions(fallback_request, session))

            return questions[:request.question_count]
        except Exception as e:
            logger.error(f"Academic questions error: {e}")
            return []

    def _generate_rag_questions(self, request: TestRequest, count: int) -> List[Dict]:
        if not request.topic or count <= 0:
            return []
        try:
            rag_payload = rag_quiz_generator.generate_questions(
                topic=request.topic,
                subject=request.subject,
                grade=request.grade,
                difficulty=request.difficulty,
                count=count,
            )
        except Exception as exc:
            logger.error("RAG question generation error: %s", exc)
            return []

        questions: List[Dict] = []
        for index, payload in enumerate(rag_payload.get("questions", []), start=1):
            option_texts = [re.sub(r"^[A-D]\)\s*", "", option).strip() for option in payload.get("options", [])]
            answer_label = str(payload.get("answer", "A")).upper()
            if len(option_texts) != 4 or answer_label not in {"A", "B", "C", "D"}:
                continue
            correct_index = ord(answer_label) - 65
            source_url = payload.get("source")
            questions.append(
                {
                    "id": f"rag_{request.grade}_{index}",
                    "number": index,
                    "type": "rag_question",
                    "question": payload.get("question", ""),
                    "question_text": payload.get("question", ""),
                    "options": {chr(65 + i): option_texts[i] for i in range(4)},
                    "correct": answer_label,
                    "correct_label": answer_label,
                    "correct_value": option_texts[correct_index],
                    "answer": option_texts[correct_index],
                    "topic": request.topic,
                    "grade": request.grade,
                    "difficulty": request.difficulty,
                    "subject": request.subject,
                    "explanation": payload.get("explanation", ""),
                    "source": source_url or "RAG",
                    "source_type": "rag_retrieval",
                    "metadata": {
                        "validation": {
                            "type": "exact_option_match",
                            "value": option_texts[correct_index],
                        },
                        "option_labels": ["A", "B", "C", "D"],
                        "correct_label": answer_label,
                    },
                    "source_info": {"url": source_url} if source_url else {},
                }
            )
        return questions

    def _generate_book_questions(self, request: TestRequest, session: QuizUniquenessSession) -> List[Dict]:
        try:
            critical_questions = critical_thinking_bank.get_test_questions(
                subject=request.subject,
                topic=request.topic,
                count=request.question_count,
                grade=request.grade,
                difficulty=request.difficulty,
            )
            critical_questions = topic_context_service.filter_matching_questions(critical_questions, request.topic)
            if critical_questions:
                for q in critical_questions:
                    topic = q.get("topic", "")
                    if topic:
                        session.mark_topic_used(topic)
                return critical_questions

            questions = book_question_bank.get_test_questions(
                subject=request.subject,
                topic=request.topic,
                count=request.question_count,
                grade=request.grade,
                difficulty=request.difficulty,
                strict_topic=bool(request.topic),
            )
            questions = topic_context_service.filter_matching_questions(questions, request.topic)
            for q in questions:
                topic = q.get("topic", "")
                if topic:
                    session.mark_topic_used(topic)
            return questions
        except Exception as e:
            logger.error(f"Book questions error: {e}")
            return []

    def _generate_standard_academic_questions(self, request: TestRequest, session: QuizUniquenessSession) -> List[Dict]:
        if request.topic:
            return self._generate_ai_questions(request, session)
        
        questions = topic_generator.generate_questions_batch(
            grade=request.grade,
            difficulty=request.difficulty,
            count=request.question_count,
            topic=request.topic
        )
        
        for q in questions:
            topic = q.get('topic', '')
            if topic:
                session.mark_topic_used(topic)
        
        return questions

    def _build_local_topic_question(self, request: TestRequest, index: int) -> Optional[Dict]:
        from services.render_specs import GeometryRenderSpec, DiagramType

        if not request.topic:
            return None

        quiz_type = self._resolve_quiz_type(request)
        payload = topic_context_service.build_local_topic_question(
            topic=request.topic,
            grade=request.grade,
            difficulty=request.difficulty,
            quiz_type=quiz_type,
            seed=f"local_{request.grade}_{request.difficulty}_{index}_{random.randint(1000, 9999)}",
        )
        options = payload.get("options") or []
        try:
            correct_idx = int(payload.get("correct_index", 0))
        except Exception:
            return None

        if len(options) != 4 or correct_idx not in range(4):
            return None

        topic = payload.get("topic", request.topic)
        question = {
            "number": index + 1,
            "question": payload.get("question", ""),
            "options": {chr(65 + j): opt for j, opt in enumerate(options)},
            "correct": chr(65 + correct_idx),
            "correct_value": options[correct_idx],
            "explanation": payload.get("explanation", ""),
            "topic": topic,
            "grade": request.grade,
            "difficulty": request.difficulty,
            "type": payload.get("source_type", "local_topic_fallback"),
            "source": payload.get("source", "Local Topic Builder"),
            "source_type": payload.get("source_type", "local_topic_fallback"),
            "metadata": dict(payload.get("metadata") or {}),
        }

        geometry_hint = payload.get("geometry_hint")
        if geometry_hint and geometry_hint != "null" and quiz_type == "Geometriya":
            question["requires_image"] = True
            question["render_spec"] = GeometryRenderSpec(
                question_id=f"local_{index + 1}_{random.randint(1000, 9999)}",
                topic=topic,
                template_id="local_topic_geometry",
                question_signature=f"local_geom_{request.grade}_{request.difficulty}_{index + 1}",
                shape_type="geometry",
                diagram_type=DiagramType.GEOMETRY,
            )

        return question
    
    def _generate_ai_questions(self, request: TestRequest, session: QuizUniquenessSession) -> List[Dict]:
        try:
            from services.ai_generator import run_ai_generation
            from services.key_manager import execute_with_rotation
            from services.render_specs import GeometryRenderSpec, DiagramType
            
            if request.grade <= 4:
                base_age = "6-9"
            elif request.grade <= 9:
                base_age = "10-13"
            else:
                base_age = "14-17"
            
            if request.difficulty.lower() == "oson":
                if request.grade <= 3:
                    age_group = "6-9"
                elif request.grade <= 7:
                    age_group = "6-9"
                else:
                    age_group = "10-13"
            elif request.difficulty.lower() == "qiyin":
                age_group = "10-13" if request.grade <= 6 else "14-17"
            else:
                age_group = base_age
            
            quiz_type = self._resolve_quiz_type(request)
            
            questions = []
            used_topics = set()
            
            for i in range(request.question_count):
                custom_topic = request.topic
                random_seed = f"test_{request.grade}_{i+1}_{random.randint(1000, 9999)}"
                
                result, error = execute_with_rotation(
                    run_ai_generation,
                    age_group,
                    quiz_type,
                    random_seed,
                    i,
                    1,
                    None,
                    custom_topic,
                    request.difficulty,
                )
                
                if not result or not isinstance(result, dict):
                    if error:
                        logger.error(f"AI generation error: {error}")
                    if custom_topic:
                        local_question = self._build_local_topic_question(request, i)
                        if local_question:
                            questions.append(local_question)
                            used_topics.add(local_question.get("topic", custom_topic))
                    continue
                
                question_text = result.get("question", "")
                options = result.get("options", [])
                try:
                    correct_idx = int(result.get("correct_index", 0))
                except Exception:
                    correct_idx = -1
                explanation = result.get("explanation", "")
                topic = result.get("topic", custom_topic)

                if len(options) != 4 or correct_idx not in range(4):
                    local_question = self._build_local_topic_question(request, i)
                    if local_question:
                        questions.append(local_question)
                        used_topics.add(local_question.get("topic", custom_topic))
                    continue

                if request.topic and not result.get("metadata"):
                    local_question = self._build_local_topic_question(request, i)
                    if local_question:
                        questions.append(local_question)
                        used_topics.add(local_question.get("topic", custom_topic))
                    continue
                
                question = {
                    "number": i + 1,
                    "question": question_text,
                    "options": {chr(65 + j): opt for j, opt in enumerate(options)},
                    "correct": chr(65 + correct_idx),
                    "correct_value": options[correct_idx],
                    "explanation": explanation,
                    "topic": topic,
                    "grade": request.grade,
                    "difficulty": request.difficulty,
                    "type": "ai_generated",
                    "source": result.get("source", "AI Generator"),
                    "source_type": result.get("source_type", "ai_generated"),
                    "metadata": dict(result.get("metadata") or {}),
                }
                
                geometry_hint = result.get("geometry_hint")
                if geometry_hint and geometry_hint != "null" and quiz_type == "Geometriya":
                    question["requires_image"] = True
                    question["render_spec"] = GeometryRenderSpec(
                            question_id=f"ai_{i+1}_{random.randint(1000, 9999)}",
                            topic=topic,
                            template_id="ai_geometry",
                            question_signature=f"ai_geom_{request.grade}_{request.difficulty}",
                            shape_type="geometry",
                            diagram_type=DiagramType.GEOMETRY
                        )              
                questions.append(question)
                used_topics.add(topic or custom_topic)
            
            if not questions:
                return self._generate_fallback_questions(request, session)

            for topic in used_topics:
                session.mark_topic_used(topic)
            
            return questions
            
        except Exception as e:
            logger.error(f"AI questions error: {e}")
            return self._generate_fallback_questions(request, session)

    def _generate_fallback_questions(self, request: TestRequest, session: QuizUniquenessSession) -> List[Dict]:
        try:
            if request.topic:
                questions = []
                for i in range(request.question_count):
                    question = self._build_local_topic_question(request, i)
                    if question:
                        questions.append(question)
                for q in questions:
                    topic = q.get('topic', '')
                    if topic:
                        session.mark_topic_used(topic)
                if questions:
                    return questions

            questions = topic_generator.generate_questions_batch(
                grade=request.grade,
                difficulty=request.difficulty,
                count=request.question_count,
                topic=request.topic
            )
            
            for q in questions:
                topic = q.get('topic', '')
                if topic:
                    session.mark_topic_used(topic)
            
            return questions
        except Exception as e:
            logger.error(f"Fallback questions error: {e}")
            return []
    
    def _generate_puzzle_questions(self, request: TestRequest, session: QuizUniquenessSession) -> List[Dict]:
        """Puzzle/mantiq savollari - yangi academic puzzle generator bilan"""
        questions = []
        
        puzzle_types = [
            ("academic", 0.5),
            ("hybrid", 0.2),
            ("logic_grid", 0.1),
            ("logic_puzzle", 0.15),
            ("crossword", 0.05),
        ]
        
        for i in range(request.question_count):
            r = random.random()
            cumulative = 0
            ptype = "academic"
            
            for pt, prob in puzzle_types:
                cumulative += prob
                if r <= cumulative:
                    ptype = pt
                    break
            
            if ptype == "academic":
                question = self._generate_academic_puzzle_question(request, i + 1)
            elif ptype == "hybrid":
                question = self._generate_hybrid_puzzle_question(request, i + 1)
            elif ptype == "logic_puzzle":
                question = puzzle_pool.generate_logic_puzzle(request.grade, request.difficulty)
                if question:
                    question["number"] = i + 1
            else:
                puzzle = puzzle_pool.get_random_puzzle(ptype)
                question = self._convert_puzzle_to_question(puzzle, ptype, i + 1)
            
            if question:
                questions.append(question)
        
        return questions
    
    def _generate_academic_puzzle_question(self, request: TestRequest, num: int) -> Optional[Dict]:
        """Academic puzzle generatsiya (vertical, flow, chain, grid, symbol)"""
        try:
            # Yangi puzzle_engine dan foydalanamiz
            puzzle = puzzle_engine.generate(
                template_type=random.choice(["vertical_arithmetic", "chain_operations", "grid_puzzle", "flow_diagram", "rebus"]),
                difficulty=request.difficulty,
                grade=request.grade
            )
            
            if not puzzle:
                return None
            
            # Option larni generatsiya qilamiz
            options = self._generate_puzzle_options(puzzle.answer, puzzle.template_id)
            
            return {
                "number": num,
                "type": f"puzzle_{puzzle.template_type.value}",
                "puzzle_data": puzzle.to_dict(),
                "question": f"Misolni yeching:",
                "puzzle_structure": puzzle.structure,
                "options": options,
                "correct": self._get_correct_option(options),
                "correct_value": str(puzzle.answer),
                "topic": puzzle.template_type.value,
                "grade": request.grade,
                "difficulty": request.difficulty,
                "template_id": puzzle.template_id,
                "render_spec": puzzle.render_spec,
                "requires_image": True # Puzzle larda rasm bo'lishi kerak
            }
        except Exception as e:
            logger.error(f"Academic puzzle error: {e}")
            return None
    
    def _generate_hybrid_puzzle_question(self, request: TestRequest, num: int) -> Optional[Dict]:
        """Hybrid puzzle generatsiya"""
        try:
            hybrid = hybrid_puzzle_generator.generate_random(request.difficulty, request.grade)
            
            if not hybrid:
                return self._generate_academic_puzzle_question(request, num)
            
            options = self._generate_puzzle_options(hybrid.final_answer, hybrid.hybrid_type)
            
            return {
                "number": num,
                "type": f"hybrid_{hybrid.hybrid_type}",
                "puzzle_data": hybrid.to_dict(),
                "question": f"Gibrid puzzle ni yeching:",
                "hybrid_structure": self._format_hybrid_structure(hybrid),
                "options": options,
                "correct": self._get_correct_option(options),
                "correct_value": str(hybrid.final_answer),
                "topic": "hybrid",
                "grade": request.grade,
                "difficulty": request.difficulty,
            }
        except Exception as e:
            logger.error(f"Hybrid puzzle error: {e}")
            return self._generate_academic_puzzle_question(request, num)
    
    def _format_hybrid_structure(self, hybrid) -> str:
        """Hybrid puzzle strukturasini formatlash"""
        parts = []
        for comp in hybrid.components:
            comp_type = comp.get("type", "")
            if comp_type == "chain_operations":
                parts.append(f"Zanjir: {comp.get('content', '')}")
            elif comp_type == "grid_arithmetic":
                grid = comp.get("grid", [])
                if grid:
                    grid_str = "\n".join([" ".join(str(c) for c in row) for row in grid])
                    parts.append(f"Jadval:\n{grid_str}")
            elif comp_type == "flow_diagram":
                parts.append(f"Oqim: {comp.get('content', '')}")
            elif comp_type == "symbol_unknown":
                parts.append(f"Belgi: {comp.get('equation', '')}")
            elif comp_type == "equation_system":
                parts.append(f"Tenglamalar:\n{comp.get('eq1', '')}\n{comp.get('eq2', '')}")
        return "\n\n".join(parts)
    
    def _generate_puzzle_options(self, correct_answer: Any, puzzle_type: str) -> Dict[str, str]:
        """Puzzle uchun option larni generatsiya qilish"""
        if isinstance(correct_answer, int):
            correct = correct_answer
            distractors = self._generate_numeric_distractors(correct)
        elif isinstance(correct_answer, str):
            parts = correct_answer.replace(" ", "").split(",")
            if len(parts) == 2 and all(p.split("=")[1].isdigit() for p in parts if "=" in p):
                correct = correct_answer
                distractors = [f"x={random.randint(1,20)}, y={random.randint(1,20)}",
                              f"x={random.randint(1,20)}, y={random.randint(1,20)}",
                              f"x={random.randint(1,20)}, y={random.randint(1,20)}"]
            else:
                return {"A": correct_answer, "B": "Boshqa", "C": "Boshqa", "D": "Boshqa"}
        else:
            return {"A": str(correct_answer), "B": "Boshqa", "C": "Boshqa", "D": "Boshqa"}
        
        options = {"A": str(correct)}
        for i, d in enumerate(distractors[:3]):
            options[chr(66 + i)] = str(d)
        
        while len(options) < 4:
            options[chr(64 + len(options) + 1)] = "Boshqa"
        
        return options
    
    def _generate_numeric_distractors(self, correct: int) -> List[int]:
        """To'g'ri javobga yaqin distractors generatsiya"""
        distractors = []
        
        if correct >= 10:
            distractors.append(correct + random.randint(5, 15))
            distractors.append(correct - random.randint(5, 15))
        else:
            distractors.append(correct + random.randint(1, 5))
            distractors.append(max(1, correct - random.randint(1, 5)))
        
        distractors = [d for d in distractors if d != correct and d > 0]
        
        return distractors[:3]
    
    def _get_correct_option(self, options: Dict[str, str]) -> str:
        """Options ichidan to'g'ri javob option harfini topish"""
        if not options:
            return "A"
        
        # Birinchi optionni default qilib qo'yamiz
        correct_opt = list(options.keys())[0]
        
        # To'g'ri javobni topish
        for opt, val in options.items():
            if val and not val.startswith("Boshqa"):
                correct_opt = opt
                break
        
        return correct_opt
    
    def _convert_puzzle_to_question(self, puzzle: Dict, ptype: str, num: int) -> Dict:
        """Puzzle ni savol formatiga o'tkazish"""
        question_text = self._get_puzzle_question(ptype)
        
        options = {
            "A": "Ha, to'g'ri",
            "B": "Yo'q, noto'g'ri",
            "C": "Aniq emas",
            "D": "Boshqa javob"
        }
        
        correct = self._get_puzzle_answer(puzzle, ptype)
        
        question = {
            "number": num,
            "type": ptype,
            "puzzle_data": puzzle,
            "question": question_text,
            "options": options,
            "correct": correct,
            "correct_value": str(puzzle),
            "topic": "puzzle",
            "grade": 5,
            "difficulty": "oson"
        }
        
        if ptype in ["logic_grid", "labyrinth"]:
            try:
                img = puzzle_pool.get_random_image(ptype)
                question["has_image"] = True
                question["image_bytes"] = img
            except Exception:
                pass
        
        return question
    
    def _check_equivalence(self, questions: List[Dict]) -> List[EquivalenceResult]:
        """Savollarning ekvivalentligini tekshirish"""
        results = []
        
        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):
                result = self.validator.check_equivalence(questions[i], questions[j])
                if result.equivalent:
                    results.append(result)
        
        return results
    
    def _render_questions(self, questions: List[Dict]):
        """Savollarni render qilish (agar kerak bo'lsa)"""
        specs_to_render = []
        
        for q in questions:
            if q.get('render_spec') and q.get('requires_image'):
                specs_to_render.append((q, q['render_spec']))
        
        if specs_to_render:
            specs = [spec for _, spec in specs_to_render]
            batch_result = render_pool.render_batch(specs)
            
            for i, (q, spec) in enumerate(specs_to_render):
                for result in batch_result.results:
                    if result.spec.question_id == spec.question_id:
                        if result.success:
                            q['image_bytes'] = result.image_bytes
                            q['has_image'] = True
                        break
    
    def _generate_single_question(self, request: TestRequest, session: QuizUniquenessSession) -> Optional[Dict]:
        """Bitta savol generatsiya qilish"""
        try:
            critical_questions = critical_thinking_bank.get_test_questions(
                subject=request.subject,
                topic=request.topic,
                count=1,
                grade=request.grade,
                difficulty=request.difficulty,
            )
            critical_questions = topic_context_service.filter_matching_questions(critical_questions, request.topic)
            if critical_questions:
                topic = critical_questions[0].get("topic", "")
                if topic:
                    session.mark_topic_used(topic)
                return critical_questions[0]

            book_questions = book_question_bank.get_test_questions(
                subject=request.subject,
                topic=request.topic,
                count=1,
                grade=request.grade,
                difficulty=request.difficulty,
                strict_topic=bool(request.topic),
            )
            book_questions = topic_context_service.filter_matching_questions(book_questions, request.topic)
            if book_questions:
                topic = book_questions[0].get("topic", "")
                if topic:
                    session.mark_topic_used(topic)
                return book_questions[0]

            if request.topic:
                local_question = self._build_local_topic_question(request, 0)
                if local_question:
                    topic = local_question.get("topic", "")
                    if topic:
                        session.mark_topic_used(topic)
                    return local_question

            topics = topic_generator.get_topics_by_grade(request.grade)
            if not topics:
                return None
            
            topic = random.choice(topics)
            question = topic_generator.generate_question(request.grade, request.difficulty, topic)
            
            if question:
                session.mark_topic_used(topic)
            
            return question
        except Exception as e:
            logger.error(f"Single question error: {e}")
            return None
    
    def _get_puzzle_question(self, ptype: str) -> str:
        """Puzzle turi bo'yicha savol matni"""
        questions = {
            "logic_grid": "Quyidagi mantiqiy qatorni to'ldiring:",
            "crossword": "Berilgan so'zlarni krossvordga joylashtiring:",
            "labyrinth": "Labirintdan to'g'ri yo'lni toping:",
            "scale": "Tarozi muvozanatda bo'lishi uchun qaysi tomon og'irroq?"
        }
        return questions.get(ptype, "Savolni hal qiling:")
    
    def _get_puzzle_answer(self, puzzle: Dict, ptype: str) -> str:
        """Puzzle javobini aniqlash"""
        if "scale" in ptype:
            balanced = puzzle.get("balanced", False)
            return "A" if balanced else "B"
        
        if "grid" in ptype:
            pattern = puzzle.get("pattern", [])
            if pattern and len(pattern) > 0:
                return "A" if pattern[0][0] == 1 else "B"
        
        return random.choice(["A", "B", "C", "D"])
    
    def _generate_test_pdf(self, request: TestRequest, questions: List[Dict]) -> Optional[str]:
        """Test PDF yaratish"""
        try:
            return pdf_generator.generate_test_pdf(
                grade=request.grade,
                difficulty=request.difficulty,
                subject=request.subject,
                questions=questions,
                teacher_name=request.teacher_name,
                time_limit=request.time_limit,
                requested_topic=request.topic or "",
            )
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return None
    
    def _generate_answers_pdf(self, request: TestRequest, questions: List[Dict]) -> Optional[str]:
        """Javoblar PDF yaratish"""
        try:
            return pdf_generator.generate_answers_pdf(
                grade=request.grade,
                difficulty=request.difficulty,
                subject=request.subject,
                questions=questions,
                requested_topic=request.topic or "",
            )
        except Exception as e:
            logger.error(f"Answers PDF error: {e}")
            return None
    
    def get_test_preview(self, request: TestRequest) -> str:
        """Test oldindan ko'rish uchun text"""
        topics = topic_generator.get_topics_by_grade(request.grade)
        suggestions = topics[:5] if topics else []
        
        return (
            f"📋 <b>Test parametrlari:</b>\n\n"
            f"• Sinf: {request.grade}\n"
            f"• Qiyinlik: {request.difficulty}\n"
            f"• Savollar: {request.question_count} ta\n"
            f"• Fan: {request.subject}\n"
            f"• Mavzular: {', '.join(suggestions) if suggestions else 'Avtomatik'}\n"
        )


test_builder = TestBuilder()
