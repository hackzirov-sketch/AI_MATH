from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Iterator
from services.cache_manager import get_process_memory_usage_mb
from services.observability_runtime import log_event, observe_duration, set_memory_usage


logger = logging.getLogger(__name__)


@dataclass
class GenerationTrace:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metrics: Dict[str, float] = field(default_factory=dict)

    def log_event(self, event: str, **kwargs) -> None:
        payload = {
            "request_id": self.request_id,
            "generation_id": self.generation_id,
            **kwargs,
        }
        log_event(event, **payload)

    @contextmanager
    def timer(self, metric_name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            self.metrics[metric_name] = duration_ms
            observe_duration(metric_name, duration_ms)
            set_memory_usage(metric_name, get_process_memory_usage_mb())


def create_generation_trace() -> GenerationTrace:
    return GenerationTrace()
