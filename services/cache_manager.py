from __future__ import annotations

import gc
import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from services.observability_runtime import increment_cache_cleanup, log_event, set_memory_usage


logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent
_CACHE_ROOT = _BASE_DIR / "data" / "cache"
_ALLOWED_SUFFIXES = {".png", ".jpg", ".pdf", ".tmp"}
_FORBIDDEN_SUFFIXES = {".py", ".json", ".yaml", ".yml", ".env", ".db", ".sqlite", ".sqlite3"}


@dataclass(frozen=True)
class CachePolicy:
    name: str
    relative_path: str
    ttl_seconds: int
    max_size_mb: int


@dataclass
class CleanupReport:
    name: str
    scanned_files: int = 0
    deleted_files: int = 0
    skipped_files: int = 0
    reclaimed_bytes: int = 0
    remaining_bytes: int = 0
    reason_counts: Dict[str, int] = field(default_factory=dict)

    def mark_reason(self, reason: str) -> None:
        self.reason_counts[reason] = self.reason_counts.get(reason, 0) + 1

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "scanned_files": self.scanned_files,
            "deleted_files": self.deleted_files,
            "skipped_files": self.skipped_files,
            "reclaimed_bytes": self.reclaimed_bytes,
            "remaining_bytes": self.remaining_bytes,
            "reason_counts": dict(self.reason_counts),
        }


class CacheManager:
    def __init__(self, root_dir: Path = _CACHE_ROOT, policies: Optional[Dict[str, CachePolicy]] = None):
        self.root_dir = Path(root_dir).resolve()
        self.policies = policies or {
            "renders": CachePolicy("renders", "renders", ttl_seconds=3600, max_size_mb=256),
            "pdf_temp": CachePolicy("pdf_temp", "pdf_temp", ttl_seconds=3600, max_size_mb=128),
            "tmp": CachePolicy("tmp", "tmp", ttl_seconds=1800, max_size_mb=64),
        }
        self._lock = threading.Lock()
        self._directories = {
            name: (self.root_dir / policy.relative_path).resolve()
            for name, policy in self.policies.items()
        }
        self.ensure_directories()

    @property
    def render_dir(self) -> Path:
        return self.get_cache_dir("renders")

    @property
    def pdf_temp_dir(self) -> Path:
        return self.get_cache_dir("pdf_temp")

    @property
    def tmp_dir(self) -> Path:
        return self.get_cache_dir("tmp")

    def ensure_directories(self) -> Dict[str, Path]:
        with self._lock:
            for directory in self._directories.values():
                directory.mkdir(parents=True, exist_ok=True)
        return dict(self._directories)

    def get_cache_dir(self, name: str) -> Path:
        if name not in self._directories:
            raise KeyError(f"Noma'lum cache papkasi: {name}")
        directory = self._directories[name]
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def reserve_file_path(self, name: str, prefix: str, suffix: str) -> Path:
        normalized_suffix = self._normalize_suffix(suffix)
        if normalized_suffix not in _ALLOWED_SUFFIXES:
            raise ValueError(f"Ruxsat etilmagan suffix: {normalized_suffix}")
        seed = f"{prefix}|{time.time_ns()}|{threading.get_ident()}".encode("utf-8")
        digest = hashlib.sha256(seed).hexdigest()[:12]
        return self.get_cache_dir(name) / f"{prefix}{digest}{normalized_suffix}"

    def build_hashed_file_path(self, name: str, cache_key: str, suffix: str) -> Path:
        normalized_suffix = self._normalize_suffix(suffix)
        if normalized_suffix not in _ALLOWED_SUFFIXES:
            raise ValueError(f"Ruxsat etilmagan suffix: {normalized_suffix}")
        digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        return self.get_cache_dir(name) / f"{digest}{normalized_suffix}"

    def write_bytes(self, name: str, cache_key: str, payload: bytes, suffix: str) -> Path:
        final_path = self.build_hashed_file_path(name, cache_key, suffix)
        temp_path = final_path.with_name(f"{final_path.name}.{threading.get_ident()}.tmp")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "wb") as handle:
            handle.write(payload)
        os.replace(temp_path, final_path)
        return final_path

    def read_bytes(self, path: Path) -> Optional[bytes]:
        try:
            if not self.is_safe_cache_file(path):
                return None
            return Path(path).read_bytes()
        except OSError:
            return None

    def is_safe_cache_path(self, path: Path | str) -> bool:
        try:
            resolved = Path(path).resolve()
        except OSError:
            return False
        for directory in self._directories.values():
            if resolved == directory or directory in resolved.parents:
                return True
        return False

    def is_safe_cache_file(self, path: Path | str) -> bool:
        try:
            resolved = Path(path).resolve()
        except OSError:
            return False
        suffix = resolved.suffix.lower()
        if suffix in _FORBIDDEN_SUFFIXES:
            return False
        if suffix not in _ALLOWED_SUFFIXES:
            return False
        return self.is_safe_cache_path(resolved)

    def delete_file(self, path: Path | str) -> bool:
        resolved = Path(path).resolve()
        if not self.is_safe_cache_file(resolved):
            logger.warning(
                "trace=%s",
                {
                    "event": "cache_delete_blocked",
                    "path": str(resolved),
                },
            )
            return False
        try:
            resolved.unlink(missing_ok=True)
            return True
        except OSError as exc:
            logger.warning(
                "trace=%s",
                {
                    "event": "cache_delete_failed",
                    "path": str(resolved),
                    "error": str(exc),
                },
            )
            return False

    def get_directory_size_bytes(self, name: str) -> int:
        total = 0
        for path in self.get_cache_dir(name).rglob("*"):
            if path.is_file() and self.is_safe_cache_file(path):
                try:
                    total += path.stat().st_size
                except OSError:
                    continue
        return total

    def cleanup_directory(
        self,
        name: str,
        ttl_seconds: Optional[int] = None,
        max_size_mb: Optional[int] = None,
    ) -> CleanupReport:
        policy = self.policies[name]
        ttl_value = policy.ttl_seconds if ttl_seconds is None else max(0, int(ttl_seconds))
        size_limit_bytes = (policy.max_size_mb if max_size_mb is None else max(0, int(max_size_mb))) * 1024 * 1024
        cache_dir = self.get_cache_dir(name)
        report = CleanupReport(name=name)
        current_time = time.time()
        safe_entries = []

        for entry in cache_dir.rglob("*"):
            if not entry.is_file():
                continue
            report.scanned_files += 1
            suffix = entry.suffix.lower()
            if suffix in _FORBIDDEN_SUFFIXES:
                report.skipped_files += 1
                report.mark_reason("forbidden_suffix")
                continue
            if suffix not in _ALLOWED_SUFFIXES:
                report.skipped_files += 1
                report.mark_reason("unsupported_suffix")
                continue
            if not self.is_safe_cache_path(entry):
                report.skipped_files += 1
                report.mark_reason("outside_allowed_dirs")
                continue
            try:
                stat = entry.stat()
            except OSError:
                report.skipped_files += 1
                report.mark_reason("stat_failed")
                continue
            safe_entries.append((entry.resolve(), stat.st_mtime, stat.st_size))

        for path, modified_at, size_bytes in list(safe_entries):
            if current_time - modified_at <= ttl_value:
                continue
            if self.delete_file(path):
                report.deleted_files += 1
                report.reclaimed_bytes += size_bytes
                report.mark_reason("ttl_expired")

        remaining_entries = []
        total_size = 0
        for path, modified_at, size_bytes in safe_entries:
            if path.exists():
                remaining_entries.append((path, modified_at, size_bytes))
                total_size += size_bytes

        if total_size > size_limit_bytes:
            for path, modified_at, size_bytes in sorted(remaining_entries, key=lambda item: item[1]):
                if total_size <= size_limit_bytes:
                    break
                if self.delete_file(path):
                    report.deleted_files += 1
                    report.reclaimed_bytes += size_bytes
                    total_size -= size_bytes
                    report.mark_reason("size_limit")

        report.remaining_bytes = max(total_size, 0)
        gc.collect()
        memory_usage = get_process_memory_usage_mb()
        set_memory_usage(f"cache_{name}", memory_usage)
        increment_cache_cleanup(name, "success")
        log_event(
            "cache_cleanup",
            cache=name,
            report=report.to_dict(),
            memory_usage_mb=memory_usage,
        )
        return report

    def cleanup_all(self) -> Dict[str, CleanupReport]:
        return {name: self.cleanup_directory(name) for name in self.policies}

    @staticmethod
    def _normalize_suffix(suffix: str) -> str:
        normalized = suffix.lower().strip()
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        return normalized


class SafeCleanerWorker:
    def __init__(self, manager: CacheManager, interval_seconds: int = 600):
        self.manager = manager
        self.interval_seconds = max(300, int(interval_seconds))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="SafeCleanerWorker",
            )
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        with self._lock:
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)

    def run_once(self) -> Dict[str, CleanupReport]:
        return self.manager.cleanup_all()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as exc:
                increment_cache_cleanup("all", "failed")
                log_event("cache_cleanup_worker_failed", error=str(exc))
            self._stop_event.wait(self.interval_seconds)


def get_process_memory_usage_mb() -> Optional[float]:
    try:
        import psutil

        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 3)
    except Exception:
        pass

    try:
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        current, _ = tracemalloc.get_traced_memory()
        return round(current / (1024 * 1024), 3)
    except Exception:
        return None


cache_manager = CacheManager()
safe_cleaner_worker = SafeCleanerWorker(
    cache_manager,
    interval_seconds=int(os.getenv("CACHE_CLEAN_INTERVAL_SECONDS", "600")),
)
