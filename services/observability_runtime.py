from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional


try:
    import structlog
except Exception:
    structlog = None

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
except Exception:
    Counter = Gauge = Histogram = None
    start_http_server = None


_prometheus_started = False
_structlog_configured = False
_standard_logger = logging.getLogger("ai_math")
_structured_logger = structlog.get_logger("ai_math") if structlog else None

GENERATION_DURATION_MS = Histogram(
    "ai_math_generation_duration_ms",
    "Generation duration in milliseconds",
    ["stage"],
) if Histogram else None
MEMORY_USAGE_MB = Gauge(
    "ai_math_memory_usage_mb",
    "Current process memory usage in MB",
    ["component"],
) if Gauge else None
CACHE_CLEANUP_TOTAL = Counter(
    "ai_math_cache_cleanup_total",
    "Cache cleanup operations",
    ["cache", "status"],
) if Counter else None
FAILURE_TOTAL = Counter(
    "ai_math_failure_total",
    "Tracked failure events",
    ["stage"],
) if Counter else None
PDF_SIZE_BYTES = Histogram(
    "ai_math_pdf_size_bytes",
    "PDF output size in bytes",
    ["kind"],
) if Histogram else None


def configure_observability(log_level: int | str = logging.INFO) -> None:
    global _prometheus_started
    global _structlog_configured

    if structlog and not _structlog_configured:
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
        )
        _structlog_configured = True

    metrics_port = os.getenv("PROMETHEUS_PORT", "").strip()
    if metrics_port and start_http_server and not _prometheus_started:
        start_http_server(int(metrics_port))
        _prometheus_started = True
        _standard_logger.log(log_level, "Prometheus metrics server started on port %s", metrics_port)


def log_event(event: str, **kwargs: Any) -> None:
    payload = {"event": event, **kwargs}
    if _structured_logger is not None:
        _structured_logger.info(event, **kwargs)
        return
    _standard_logger.info("trace=%s", payload)


def observe_duration(stage: str, duration_ms: float) -> None:
    if GENERATION_DURATION_MS:
        GENERATION_DURATION_MS.labels(stage=stage).observe(max(duration_ms, 0.0))


def observe_pdf_size(kind: str, size_bytes: int) -> None:
    if PDF_SIZE_BYTES:
        PDF_SIZE_BYTES.labels(kind=kind).observe(max(size_bytes, 0))


def set_memory_usage(component: str, memory_mb: Optional[float]) -> None:
    if memory_mb is None or MEMORY_USAGE_MB is None:
        return
    MEMORY_USAGE_MB.labels(component=component).set(memory_mb)


def increment_cache_cleanup(cache: str, status: str = "success") -> None:
    if CACHE_CLEANUP_TOTAL:
        CACHE_CLEANUP_TOTAL.labels(cache=cache, status=status).inc()


def increment_failure(stage: str) -> None:
    if FAILURE_TOTAL:
        FAILURE_TOTAL.labels(stage=stage).inc()
