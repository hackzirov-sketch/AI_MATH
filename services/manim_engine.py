"""
services/manim_engine.py
Manim o'rnatilmagan bo'lsa — matplotlib fallbackga o'tadi, crash bo'lmaydi.

Tuzatishlar:
- Render tugagandan keyin manim chiqindi papkalarini (videos/, partial/) tozalash
- temp_videos papkasi absolyut yo'l bilan yaratiladi
"""

import os
import shutil
import threading
import uuid
from services.cache_manager import cache_manager

manim_lock = threading.Lock()

# temp_videos ning mutlaq yo'li
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMP_VIDEOS_DIR = os.path.join(str(cache_manager.tmp_dir), "videos")


def _cleanup_manim_artifacts(media_dir: str) -> None:
    """
    Manim render qoldirgan keraksiz papkalarni o'chiradi:
      media_dir/videos/  — har bir render uchun yaratilgan subdirektoriya
      media_dir/partial_movie_files/ — render davomidagi fragmentlar
    """
    for subdir in ("videos", "partial_movie_files", "Tex", "texts"):
        path = os.path.join(media_dir, subdir)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)


def create_manim_video(hint: str) -> str | None:
    """Manim o'rnatilmagan bo'lsa None qaytaradi (xavfsiz)."""
    try:
        from manim import (
            BLACK,
            DOWN,
            LEFT,
            ORIGIN,
            RED,
            RIGHT,
            UP,
            WHITE,
            Circle,
            Create,
            Dot,
            Line,
            MathTex,
            Polygon,
            Scene,
            Square,
            Text,
            Write,
            config,
        )
    except ImportError:
        return None  # ← Manim yo'q — matplotlib ishlaydi

    class AutoGeometryScene(Scene):
        def __init__(self, hint_text: str, **kwargs):
            super().__init__(**kwargs)
            self.hint_text = hint_text.lower()

        def construct(self):
            MathTex.set_default(color=BLACK)
            Text.set_default(color=BLACK)

            if "triangle" in self.hint_text:
                pts = [LEFT * 1.5 + DOWN, RIGHT * 2 + DOWN, UP * 1.5]
                shape = Polygon(*pts, color=BLACK)
                label_a = Text("A", font_size=24).next_to(pts[0], DOWN + LEFT)
                label_b = Text("B", font_size=24).next_to(pts[1], DOWN + RIGHT)
                label_c = Text("C", font_size=24).next_to(pts[2], UP)
                x_val = Text("x", font_size=32, color=RED).move_to(
                    RIGHT * 0.5 + UP * 0.2
                )
                self.play(Create(shape), run_time=1.5)
                self.play(Write(label_a), Write(label_b), Write(label_c), run_time=1)
                self.wait(0.5)
                self.play(Write(x_val))

            elif "circle" in self.hint_text:
                shape = Circle(radius=2, color=BLACK)
                center_dot = Dot(color=BLACK)
                radius_line = Line(start=ORIGIN, end=RIGHT * 2, color=BLACK)
                o_label = Text("O", font_size=24).next_to(center_dot, DOWN)
                r_val = Text("r = ?", font_size=28, color=RED).next_to(radius_line, UP)
                self.play(Create(shape), run_time=1)
                self.play(Create(center_dot), Write(o_label))
                self.play(Create(radius_line))
                self.play(Write(r_val))

            else:
                shape = Square(side_length=3, color=BLACK)
                q_text = Text("?", font_size=40, color=RED)
                self.play(Create(shape), run_time=1.2)
                self.play(Write(q_text))

            self.wait(1)

    os.makedirs(_TEMP_VIDEOS_DIR, exist_ok=True)
    output_filename = f"geom_{uuid.uuid4().hex[:8]}"

    with manim_lock:
        config.background_color = WHITE
        config.pixel_height = 480
        config.pixel_width = 480
        config.frame_rate = 15
        config.verbosity = "CRITICAL"
        config.media_dir = _TEMP_VIDEOS_DIR

        scene = AutoGeometryScene(hint)
        scene.render()

        expected = os.path.join(
            config.media_dir, "videos", "480p15", "AutoGeometryScene.mp4"
        )
        final = os.path.join(_TEMP_VIDEOS_DIR, f"{output_filename}.mp4")

        if os.path.exists(expected):
            os.rename(expected, final)
            # Render chiqindilarini tozalash (videos/, partial_movie_files/, Tex/)
            _cleanup_manim_artifacts(config.media_dir)
            return final
        else:
            # Render muvaffaqiyatsiz — chiqindilarni baribir tozalaymiz
            _cleanup_manim_artifacts(config.media_dir)

    return None
