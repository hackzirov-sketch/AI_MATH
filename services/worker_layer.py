from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.celery_app import celery_app
from services.worker_tasks import (
    cache_cleanup_task,
    generate_answers_pdf_task,
    generate_test_pdf_task,
    rag_retrieve_task,
    self_improvement_analysis_task,
)


@dataclass
class TaskHandle:
    task_id: str
    status: str
    result: Any = None


class WorkerLayer:
    def __init__(self, use_celery: Optional[bool] = None):
        if use_celery is None:
            use_celery = celery_app is not None
        self.use_celery = bool(use_celery and celery_app is not None)

    def dispatch_rag_retrieval(self, topic: str, subject: str = "", grade: int | None = None, max_results: int = 4) -> TaskHandle:
        if self.use_celery and hasattr(rag_retrieve_task, "delay"):
            task = rag_retrieve_task.delay(topic=topic, subject=subject, grade=grade, max_results=max_results)
            return TaskHandle(task_id=task.id, status="queued")
        result = rag_retrieve_task(topic=topic, subject=subject, grade=grade, max_results=max_results)
        return TaskHandle(task_id=str(uuid.uuid4()), status="completed", result=result)

    def dispatch_test_pdf(self, request_payload: Dict[str, Any], questions: List[Dict[str, Any]]) -> TaskHandle:
        if self.use_celery and hasattr(generate_test_pdf_task, "delay"):
            task = generate_test_pdf_task.delay(request_payload=request_payload, questions=questions)
            return TaskHandle(task_id=task.id, status="queued")
        result = generate_test_pdf_task(request_payload=request_payload, questions=questions)
        return TaskHandle(task_id=str(uuid.uuid4()), status="completed", result=result)

    def dispatch_answers_pdf(self, request_payload: Dict[str, Any], questions: List[Dict[str, Any]]) -> TaskHandle:
        if self.use_celery and hasattr(generate_answers_pdf_task, "delay"):
            task = generate_answers_pdf_task.delay(request_payload=request_payload, questions=questions)
            return TaskHandle(task_id=task.id, status="queued")
        result = generate_answers_pdf_task(request_payload=request_payload, questions=questions)
        return TaskHandle(task_id=str(uuid.uuid4()), status="completed", result=result)

    def dispatch_cache_cleanup(self) -> TaskHandle:
        if self.use_celery and hasattr(cache_cleanup_task, "delay"):
            task = cache_cleanup_task.delay()
            return TaskHandle(task_id=task.id, status="queued")
        result = cache_cleanup_task()
        return TaskHandle(task_id=str(uuid.uuid4()), status="completed", result=result)

    def dispatch_self_improvement_analysis(self, limit: int = 200) -> TaskHandle:
        if self.use_celery and hasattr(self_improvement_analysis_task, "delay"):
            task = self_improvement_analysis_task.delay(limit=limit)
            return TaskHandle(task_id=task.id, status="queued")
        result = self_improvement_analysis_task(limit=limit)
        return TaskHandle(task_id=str(uuid.uuid4()), status="completed", result=result)


worker_layer = WorkerLayer()
