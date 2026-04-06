"""
services/render_pool.py — RENDER DISPATCHER

Render job queue, worker pool, cache, fallback va batch rendering.

Bu renderning dispatcher qismi.
"""

import copy
import gc
import io
import os
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
import threading

from services.render_specs import (
    RenderSpec, GeometryRenderSpec, PuzzleRenderSpec, RenderMetadata, RenderResult,
    TriangleSpec, RectangleSpec, CircleSpec, TrapezoidSpec, StylePreset
)
from services.render_cache import render_cache
from services.cache_manager import get_process_memory_usage_mb
from services.puzzle_renderer import puzzle_renderer

logger = logging.getLogger(__name__)

RENDER_TIMEOUT_SECONDS = 5
MAX_WORKERS = int(os.getenv("AI_MATH_RENDER_MAX_WORKERS", "2"))
RENDER_SOFT_LIMIT_MB = int(os.getenv("AI_MATH_RENDER_SOFT_LIMIT_MB", "192"))
RENDER_HARD_LIMIT_MB = int(os.getenv("AI_MATH_RENDER_HARD_LIMIT_MB", "256"))


@dataclass
class RenderJob:
    """Render job - bitta render vazifasi"""
    job_id: str
    spec: RenderSpec
    priority: int = 0


@dataclass
class BatchRenderResult:
    """Batch render natijasi"""
    results: List[RenderResult]
    total_time_ms: float
    cache_hits: int
    cache_misses: int
    fallbacks: int


class RenderPool:
    """
    Render dispatcher va worker pool.
    
    Vazifalari:
    - Job qabul qilish
    - Batch dedup
    - Cache tekshirish
    - Worker poolga berish
    - Timeout nazorati
    - Fallback qo'llash
    - Metadata qaytarish
    """
    
    def __init__(self, max_workers: int = MAX_WORKERS):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._active_jobs: Dict[str, RenderJob] = {}
        self._lock = threading.Lock()

    def _get_style_preset(self, spec: Any) -> str:
        style_preset = getattr(spec, "style_preset", None)
        if hasattr(style_preset, "value"):
            return style_preset.value
        if style_preset:
            return str(style_preset)
        return "exam_clean"

    def _get_canvas_size(self, spec: Any) -> Tuple[float, float]:
        figure_size = getattr(spec, "figure_size", None)
        if isinstance(figure_size, (tuple, list)) and len(figure_size) == 2:
            return float(figure_size[0]), float(figure_size[1])
        width = getattr(spec, "width", 8) or 8
        height = getattr(spec, "height", 6) or 6
        return float(width), float(height)

    def _get_dpi(self, spec: Any) -> int:
        return int(getattr(spec, "dpi", 150) or 150)

    def _get_render_signature(self, spec: Any) -> str:
        return (
            getattr(spec, "render_signature", "")
            or getattr(spec, "question_signature", "")
            or getattr(spec, "question_id", "")
        )

    def _resolve_render_profile(self, spec: Any) -> Dict[str, Any]:
        width, height = self._get_canvas_size(spec)
        dpi = self._get_dpi(spec)
        grayscale = False
        max_dimension = 1600
        memory_usage = get_process_memory_usage_mb()
        pixel_count = max(int(width * dpi), 1) * max(int(height * dpi), 1)

        if pixel_count > 2_500_000:
            dpi = min(dpi, 120)
            max_dimension = 1400

        if memory_usage is not None and memory_usage >= RENDER_HARD_LIMIT_MB:
            dpi = min(dpi, 96)
            grayscale = True
            max_dimension = 1100
        elif memory_usage is not None and memory_usage >= RENDER_SOFT_LIMIT_MB:
            dpi = min(dpi, 110)
            grayscale = True
            max_dimension = 1400

        return {
            "width": width,
            "height": height,
            "dpi": dpi,
            "grayscale": grayscale,
            "max_dimension": max_dimension,
            "memory_usage_mb": memory_usage,
        }

    def _build_adapted_spec(self, spec: Any, profile: Dict[str, Any]) -> Any:
        adapted = copy.deepcopy(spec)
        if hasattr(adapted, "dpi"):
            adapted.dpi = profile["dpi"]
        if hasattr(adapted, "width"):
            adapted.width = profile["width"]
        if hasattr(adapted, "height"):
            adapted.height = profile["height"]
        if hasattr(adapted, "figure_size"):
            adapted.figure_size = (profile["width"], profile["height"])
        if profile["grayscale"] and hasattr(adapted, "style_preset"):
            adapted.style_preset = StylePreset.PRINT_BLACK_WHITE
        return adapted

    def _build_cache_spec(self, spec: Any, profile: Dict[str, Any]) -> Dict[str, Any]:
        spec_dict = spec.to_dict() if hasattr(spec, "to_dict") else {}
        spec_dict["_render_profile"] = {
            "dpi": profile["dpi"],
            "grayscale": profile["grayscale"],
            "max_dimension": profile["max_dimension"],
        }
        return spec_dict

    def _optimize_image_bytes(self, image_bytes: bytes, grayscale: bool, max_dimension: int) -> bytes:
        try:
            from PIL import Image, ImageOps

            with Image.open(io.BytesIO(image_bytes)) as image:
                image.load()
                if grayscale:
                    image = ImageOps.grayscale(image)
                elif image.mode not in ("RGB", "RGBA", "L"):
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

                if max(image.size) > max_dimension:
                    resampling = getattr(Image, "Resampling", Image).LANCZOS
                    image.thumbnail((max_dimension, max_dimension), resampling)

                output = io.BytesIO()
                image.save(output, format="PNG", optimize=True, compress_level=9)
                optimized = output.getvalue()
                output.close()
                return optimized
        except Exception:
            return image_bytes
        finally:
            gc.collect()

    def _clone_result_for_spec(self, result: RenderResult, spec: Any) -> RenderResult:
        metadata = RenderMetadata(**result.metadata.to_dict())
        return RenderResult(
            spec=spec,
            image_bytes=result.image_bytes,
            metadata=metadata,
            success=result.success,
            error_message=result.error_message,
            image_path=result.image_path,
            tikz_source=result.tikz_source,
            warnings=list(result.warnings),
            errors=list(result.errors),
        )

    def _stringify_hint_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return str(value)

    def _build_geometry_hint(self, spec: GeometryRenderSpec) -> Optional[str]:
        shape = (getattr(spec, "shape_type", "") or "").strip().lower()
        if not shape:
            return None

        supported = {
            "triangle",
            "right_triangle",
            "isosceles_triangle",
            "equilateral_triangle",
            "obtuse_triangle",
            "rectangle",
            "square",
            "circle",
            "trapezoid",
            "rhombus",
            "parallelogram",
            "hexagon",
            "coordinate",
            "number_line",
            "bar_chart",
            "pie_chart",
            "clock",
            "grid",
            "scale",
            "pythagoras",
            "heron",
            "sin_cos",
            "vector",
            "homothety",
            "crossword",
            "labyrinth",
        }
        if shape not in supported:
            return None

        parts = [shape]

        if isinstance(spec, TriangleSpec):
            values = {
                "bottom": spec.side_ab,
                "left": spec.side_bc,
                "right": spec.side_ac,
                "angle_a": spec.angle_a,
                "angle_b": spec.angle_b,
                "angle_c": spec.angle_c,
            }
            for key, value in values.items():
                if value:
                    parts.append(f"{key}={self._stringify_hint_value(value)}")
            for key, value in spec.measurements.items():
                if value and key not in {"a", "b", "c"}:
                    parts.append(f"{key}={self._stringify_hint_value(value)}")
        elif isinstance(spec, RectangleSpec):
            values = {
                "bottom": spec.width,
                "left": spec.height,
                "diagonal": spec.diagonal,
                "area": spec.area,
                "perimeter": spec.perimeter,
            }
            for key, value in values.items():
                if value:
                    parts.append(f"{key}={self._stringify_hint_value(value)}")
        elif isinstance(spec, CircleSpec):
            values = {
                "radius_1": spec.radius,
                "diameter": spec.diameter,
                "area": spec.area,
                "circumference": spec.circumference,
            }
            for key, value in values.items():
                if value:
                    parts.append(f"{key}={self._stringify_hint_value(value)}")
        elif isinstance(spec, TrapezoidSpec):
            values = {
                "bottom": spec.base1,
                "top": spec.base2,
                "height": spec.height,
            }
            for key, value in values.items():
                if value:
                    parts.append(f"{key}={self._stringify_hint_value(value)}")
        elif shape == "coordinate":
            parts.extend(["x1=0", "y1=0", "x2=3", "y2=4"])
        elif shape == "number_line":
            parts.extend(["start=0", "end=10", "mark1=4", "mark2=7"])

        return "|".join(parts)

    def _render_geometry(self, spec: GeometryRenderSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        width, height = self._get_canvas_size(spec)
        dpi = self._get_dpi(spec)
        hint = self._build_geometry_hint(spec)

        if hint:
            from services.geometry_renderer import create_diagram

            media_path = create_diagram(hint)
            if media_path and os.path.exists(media_path) and not media_path.lower().endswith(".mp4"):
                try:
                    with open(media_path, "rb") as f:
                        image_bytes = f.read()
                finally:
                    try:
                        os.remove(media_path)
                    except OSError:
                        pass

                metadata = RenderMetadata(
                    render_time_ms=(time.time() - start_time) * 1000,
                    cache_hit=False,
                    width=width,
                    height=height,
                    dpi=dpi,
                    signature=self._get_render_signature(spec),
                )
                return image_bytes, metadata

        return self._render_generic(spec, start_time)
    
    def render_single(self, spec: RenderSpec) -> RenderResult:
        """Bitta spec render qilish"""
        profile = self._resolve_render_profile(spec)
        adapted_spec = self._build_adapted_spec(spec, profile)
        width = profile["width"]
        height = profile["height"]
        dpi = profile["dpi"]
        style_preset = self._get_style_preset(adapted_spec)
        style_cache_key = f"{style_preset}|gray={int(profile['grayscale'])}"
        signature = self._get_render_signature(spec)
        cache_spec = self._build_cache_spec(adapted_spec, profile)
        cache_key = (cache_spec, style_cache_key, width, height, dpi)
        cached = render_cache.get(cache_spec, style_cache_key, width, height, dpi)
        
        if cached:
            logger.info(
                "trace=%s",
                {
                    "event": "render_cache_hit",
                    "signature": signature,
                    "memory_usage_mb": profile["memory_usage_mb"],
                    "image_kb": round(len(cached) / 1024, 3),
                },
            )
            metadata = RenderMetadata(
                render_time_ms=0,
                cache_hit=True,
                width=width,
                height=height,
                dpi=dpi,
                signature=signature,
            )
            return RenderResult(
                spec=spec,
                image_bytes=cached,
                metadata=metadata,
                success=True
            )
        
        start_time = time.time()
        
        try:
            if isinstance(adapted_spec, PuzzleRenderSpec):
                image_bytes, metadata = puzzle_renderer.render(adapted_spec)
            elif isinstance(adapted_spec, GeometryRenderSpec):
                image_bytes, metadata = self._render_geometry(adapted_spec, start_time)
            else:
                image_bytes, metadata = self._render_generic(adapted_spec, start_time)

            optimized_bytes = self._optimize_image_bytes(
                image_bytes,
                grayscale=profile["grayscale"],
                max_dimension=profile["max_dimension"],
            )
            metadata.render_time_ms = (time.time() - start_time) * 1000
            metadata.width = width
            metadata.height = height
            metadata.dpi = dpi
            metadata.signature = signature

            render_cache.set(cache_key, optimized_bytes)
            logger.info(
                "trace=%s",
                {
                    "event": "render_complete",
                    "signature": signature,
                    "render_time_ms": round(metadata.render_time_ms, 3),
                    "memory_usage_mb": get_process_memory_usage_mb(),
                    "image_kb": round(len(optimized_bytes) / 1024, 3),
                    "grayscale": profile["grayscale"],
                    "dpi": dpi,
                },
            )
            
            return RenderResult(
                spec=spec,
                image_bytes=optimized_bytes,
                metadata=metadata,
                success=True
            )
        
        except Exception as e:
            logger.error(f"Render error: {e}")
            metadata = RenderMetadata(
                render_time_ms=(time.time() - start_time) * 1000,
                fallback_used=True,
                fallback_reason=str(e)
            )
            fallback_bytes, fallback_meta = self._render_fallback(spec)
            fallback_meta.fallback_used = True
            fallback_meta.fallback_reason = str(e)
            
            return RenderResult(
                spec=spec,
                image_bytes=fallback_bytes,
                metadata=fallback_meta,
                success=False,
                error_message=str(e)
            )
    
    def _render_generic(self, spec: RenderSpec, start_time: float) -> Tuple[bytes, RenderMetadata]:
        """Generic render"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        width, height = self._get_canvas_size(spec)
        dpi = self._get_dpi(spec)
        fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.axis("off")
        
        ax.text(0.5, 0.5, f"Render: {getattr(spec, 'topic', '')}",
               transform=ax.transAxes, fontsize=16, ha='center')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        image_bytes = buf.getvalue()
        buf.close()
        plt.close(fig)
        
        metadata = RenderMetadata(
            render_time_ms=(time.time() - start_time) * 1000,
            cache_hit=False,
            width=width,
            height=height,
            dpi=dpi,
            signature=self._get_render_signature(spec),
        )
        
        return image_bytes, metadata
    
    def _render_fallback(self, spec: RenderSpec) -> Tuple[bytes, RenderMetadata]:
        """Fallback render - minimal sodda rasm"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("#f8f8f8")
        ax.axis("off")
        
        ax.text(0.5, 0.7, "⚠️", transform=ax.transAxes,
               fontsize=32, ha='center', va='center')
        ax.text(0.5, 0.3, "Rasm mavjud emas",
               transform=ax.transAxes, fontsize=10, ha='center', va='center')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        image_bytes = buf.getvalue()
        buf.close()
        plt.close(fig)
        
        metadata = RenderMetadata(
            render_time_ms=0,
            fallback_used=True,
            fallback_reason="render_error"
        )
        
        return image_bytes, metadata
    
    def render_batch(self, specs: List[RenderSpec]) -> BatchRenderResult:
        """Batch render - bir nechta specni parallel render qilish"""
        start_time = time.time()
        
        unique_specs = []
        seen_signatures = set()
        signature_to_specs: Dict[str, List[RenderSpec]] = {}
        
        for spec in specs:
            signature = self._get_render_signature(spec)
            signature_to_specs.setdefault(signature, []).append(spec)
            if signature not in seen_signatures:
                unique_specs.append(spec)
                seen_signatures.add(signature)
        
        results: List[RenderResult] = []
        cache_hits = 0
        cache_misses = 0
        fallbacks = 0
        rendered_by_signature: Dict[str, RenderResult] = {}
        
        futures = {}
        for spec in unique_specs:
            future = self._executor.submit(self.render_single, spec)
            futures[future] = self._get_render_signature(spec)
        
        try:
            for future in as_completed(futures, timeout=RENDER_TIMEOUT_SECONDS):
                try:
                    result = future.result()
                    signature = futures[future]
                    rendered_by_signature[signature] = result
                    
                    if result.metadata.cache_hit:
                        cache_hits += 1
                    else:
                        cache_misses += 1
                    
                    if result.metadata.fallback_used:
                        fallbacks += 1
                
                except Exception as e:
                    logger.error(f"Future error: {e}")
                    fallbacks += 1
        except FuturesTimeoutError:
            logger.error("Batch render timeout: %s seconds", RENDER_TIMEOUT_SECONDS)
            fallbacks += 1

        for spec in specs:
            signature = self._get_render_signature(spec)
            base_result = rendered_by_signature.get(signature)
            if base_result:
                if base_result.spec is spec:
                    results.append(base_result)
                else:
                    results.append(self._clone_result_for_spec(base_result, spec))
                continue

            fallback_bytes, fallback_meta = self._render_fallback(spec)
            fallback_meta.fallback_used = True
            fallback_meta.fallback_reason = "missing_batch_result"
            results.append(
                RenderResult(
                    spec=spec,
                    image_bytes=fallback_bytes,
                    metadata=fallback_meta,
                    success=False,
                    error_message="missing_batch_result",
                )
            )
        
        return BatchRenderResult(
            results=results,
            total_time_ms=(time.time() - start_time) * 1000,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            fallbacks=fallbacks
        )
    
    def render_with_timeout(self, spec: RenderSpec, timeout: float = RENDER_TIMEOUT_SECONDS) -> RenderResult:
        """Timeout bilan render"""
        future = self._executor.submit(self.render_single, spec)
        
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.warning(f"Render timeout for {spec.question_id}")
            return RenderResult(
                spec=spec,
                image_bytes=self._render_timeout_fallback(spec),
                metadata=RenderMetadata(
                    render_time_ms=timeout * 1000,
                    fallback_used=True,
                    fallback_reason="timeout"
                ),
                success=False,
                error_message="Render timeout"
            )
    
    def _render_timeout_fallback(self, spec: RenderSpec) -> bytes:
        """Timeout fallback"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("#fff3cd")
        ax.axis("off")
        
        ax.text(0.5, 0.5, "⏱️ Timeout",
               transform=ax.transAxes, fontsize=16, ha='center')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        image_bytes = buf.getvalue()
        buf.close()
        plt.close(fig)
        return image_bytes
    
    def get_cache_stats(self) -> Dict:
        """Cache statistikasini olish"""
        return render_cache.get_stats()
    
    def shutdown(self):
        """Executor ni to'xtatish"""
        self._executor.shutdown(wait=True)


render_pool = RenderPool()
