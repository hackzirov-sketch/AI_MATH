from __future__ import annotations

from typing import Any, Dict, List

from services.cache_manager import cache_manager, safe_cleaner_worker
from services.celery_app import celery_app
from services.knowledge_retriever import knowledge_retriever
from services.pdf_generator import pdf_generator
from services.self_improvement.engine import self_improvement_engine


def _task(*args, **kwargs):
    def decorator(func):
        if celery_app is None:
            return func
        return celery_app.task(*args, **kwargs)(func)

    return decorator


@_task(name="ai_math.rag.retrieve")
def rag_retrieve_task(topic: str, subject: str = "", grade: int | None = None, max_results: int = 4) -> Dict[str, Any]:
    return knowledge_retriever.retrieve(topic=topic, subject=subject, grade=grade, max_results=max_results).to_dict()


@_task(name="ai_math.pdf.generate_test")
def generate_test_pdf_task(request_payload: Dict[str, Any], questions: List[Dict[str, Any]]) -> str:
    return pdf_generator.generate_test_pdf(
        grade=int(request_payload.get("grade", 0)),
        difficulty=str(request_payload.get("difficulty", "")),
        subject=str(request_payload.get("subject", "")),
        questions=questions,
        teacher_name=str(request_payload.get("teacher_name", "")),
        time_limit=int(request_payload.get("time_limit", 0)),
        requested_topic=str(request_payload.get("topic", "")),
    )


@_task(name="ai_math.pdf.generate_answers")
def generate_answers_pdf_task(request_payload: Dict[str, Any], questions: List[Dict[str, Any]]) -> str:
    return pdf_generator.generate_answers_pdf(
        grade=int(request_payload.get("grade", 0)),
        difficulty=str(request_payload.get("difficulty", "")),
        subject=str(request_payload.get("subject", "")),
        questions=questions,
        teacher_name=str(request_payload.get("teacher_name", "")),
        requested_topic=str(request_payload.get("topic", "")),
    )


@_task(name="ai_math.cache.cleanup")
def cache_cleanup_task() -> Dict[str, Dict[str, object]]:
    reports = safe_cleaner_worker.run_once() if safe_cleaner_worker else cache_manager.cleanup_all()
    return {name: report.to_dict() for name, report in reports.items()}


@_task(name="ai_math.self_improvement.analyze")
def self_improvement_analysis_task(limit: int = 200) -> List[Dict[str, object]]:
    return self_improvement_engine.analyze_recent_generations(limit=limit)
