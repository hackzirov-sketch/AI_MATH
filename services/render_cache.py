from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Dict, Optional, Tuple

from services.cache_manager import cache_manager


logger = logging.getLogger(__name__)

RENDERER_VERSION = "2.0"
CACHE_VERSION = "v2"
_MB = 1024 * 1024


class LRUCache:
    def __init__(self, max_items: int = 96, max_bytes: int = 64 * _MB):
        self.max_items = max_items
        self.max_bytes = max_bytes
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._current_bytes = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: str, value: bytes) -> None:
        value_size = len(value)
        with self._lock:
            if key in self._cache:
                old_value = self._cache.pop(key)
                self._current_bytes -= len(old_value)

            while self._cache and (
                len(self._cache) >= self.max_items or self._current_bytes + value_size > self.max_bytes
            ):
                _, removed = self._cache.popitem(last=False)
                self._current_bytes -= len(removed)

            if value_size > self.max_bytes:
                return

            self._cache[key] = value
            self._current_bytes += value_size

    def delete(self, key: str) -> None:
        with self._lock:
            if key not in self._cache:
                return
            removed = self._cache.pop(key)
            self._current_bytes -= len(removed)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._current_bytes = 0

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def total_bytes(self) -> int:
        with self._lock:
            return self._current_bytes


class RenderCache:
    def __init__(
        self,
        memory_max_items: int = 96,
        memory_max_bytes_mb: int = 64,
        disk_max_file_mb: int = 8,
    ):
        self._cache = LRUCache(
            max_items=memory_max_items,
            max_bytes=memory_max_bytes_mb * _MB,
        )
        self._metadata: Dict[str, Dict[str, object]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "total_renders": 0,
            "disk_hits": 0,
            "memory_hits": 0,
        }
        self._disk_max_file_bytes = disk_max_file_mb * _MB
        self._lock = threading.Lock()

    def _generate_cache_key(
        self,
        spec_dict: Dict,
        style_preset: str,
        width: float,
        height: float,
        dpi: int,
    ) -> str:
        payload = {
            "cache_version": CACHE_VERSION,
            "renderer_version": RENDERER_VERSION,
            "style_preset": style_preset,
            "width": round(float(width), 4),
            "height": round(float(height), 4),
            "dpi": int(dpi),
            "spec": spec_dict,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str, separators=(",", ":"))
        return serialized

    def get(self, spec_dict: Dict, style_preset: str, width: float, height: float, dpi: int) -> Optional[bytes]:
        cache_key = self._generate_cache_key(spec_dict, style_preset, width, height, dpi)
        cached = self._cache.get(cache_key)

        with self._lock:
            if cached is not None:
                self._stats["hits"] += 1
                self._stats["memory_hits"] += 1
                if cache_key in self._metadata:
                    self._metadata[cache_key]["access_count"] = int(self._metadata[cache_key].get("access_count", 0)) + 1
                return cached

        disk_path = cache_manager.build_hashed_file_path("renders", cache_key, ".png")
        cached = cache_manager.read_bytes(disk_path)
        if cached is None:
            with self._lock:
                self._stats["misses"] += 1
            return None

        self._cache.set(cache_key, cached)
        with self._lock:
            self._stats["hits"] += 1
            self._stats["disk_hits"] += 1
            metadata = self._metadata.setdefault(cache_key, {})
            metadata["access_count"] = int(metadata.get("access_count", 0)) + 1
            metadata["size_bytes"] = len(cached)
            metadata["disk_path"] = str(disk_path)
        return cached

    def set(self, cache_key_data: Tuple[Dict, str, float, float, int], image_bytes: bytes) -> None:
        if not image_bytes:
            return

        spec_dict, style_preset, width, height, dpi = cache_key_data
        cache_key = self._generate_cache_key(spec_dict, style_preset, width, height, dpi)
        self._cache.set(cache_key, image_bytes)

        disk_path = None
        if len(image_bytes) <= self._disk_max_file_bytes:
            disk_path = cache_manager.write_bytes("renders", cache_key, image_bytes, ".png")

        with self._lock:
            self._metadata[cache_key] = {
                "cached_at": time.time(),
                "access_count": 1,
                "size_bytes": len(image_bytes),
                "disk_path": str(disk_path) if disk_path else None,
            }
            self._stats["total_renders"] += 1

        if cache_manager.get_directory_size_bytes("renders") > cache_manager.policies["renders"].max_size_mb * _MB:
            cache_manager.cleanup_directory("renders")

    def get_stats(self) -> Dict[str, object]:
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests else 0.0
            memory_usage_bytes = self._cache.total_bytes()
            disk_usage_bytes = cache_manager.get_directory_size_bytes("renders")
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "memory_hits": self._stats["memory_hits"],
                "disk_hits": self._stats["disk_hits"],
                "hit_rate_percent": round(hit_rate, 2),
                "total_renders": self._stats["total_renders"],
                "cache_size": self._cache.size(),
                "memory_usage_mb": round(memory_usage_bytes / _MB, 3),
                "disk_usage_mb": round(disk_usage_bytes / _MB, 3),
            }

    def clear(self) -> None:
        self._cache.clear()
        with self._lock:
            self._metadata.clear()
            self._stats = {
                "hits": 0,
                "misses": 0,
                "total_renders": 0,
                "disk_hits": 0,
                "memory_hits": 0,
            }
        cache_manager.cleanup_directory("renders", ttl_seconds=0, max_size_mb=0)
        logger.info("trace=%s", {"event": "render_cache_cleared"})

    def cleanup_old_entries(self, max_age_seconds: int = 86400) -> None:
        cache_manager.cleanup_directory("renders", ttl_seconds=max_age_seconds)


render_cache = RenderCache()
