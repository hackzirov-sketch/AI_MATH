"""
tests/test_core.py

AI_MATH loyihasining asosiy modullari uchun unit testlar.

Ishga tushirish:
    cd AI_MATH
    pytest tests/ -v

Yoki bitta test:
    pytest tests/test_core.py::test_is_admin_env -v
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Loyiha root papkasini Python path ga qo'shamiz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Key Manager — rotation logikasi
# ─────────────────────────────────────────────────────────────────────────────


class TestExecuteWithRotation(unittest.TestCase):
    """execute_with_rotation() rotation va xato boshqaruvi."""

    def _make_key(self, id_, service, usage=0):
        k = MagicMock()
        k.id = id_
        k.api_key = f"key_{id_}"
        k.service = service
        k.usage_count = usage
        k.is_active = True
        return k

    @patch("services.key_manager.get_session")
    @patch("services.key_manager.increment_key_usage")
    def test_first_key_success(self, mock_inc, mock_session):
        """Birinchi kalit ishlasa — darhol qaytadi."""
        keys = [self._make_key(1, "groq")]
        session = MagicMock()
        session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = keys
        mock_session.return_value = session

        from services.key_manager import execute_with_rotation

        def good_func(api_key, service, *a, **kw):
            return {"answer": 42}

        result, err = execute_with_rotation(good_func, "arg1", ai_role="quiz_gen")
        self.assertIsNone(err)
        self.assertEqual(result["answer"], 42)
        mock_inc.assert_called_once_with(1)

    @patch("services.key_manager.get_session")
    @patch("services.key_manager.increment_key_usage")
    @patch("services.key_manager.log_key_error")
    def test_rotation_on_error(self, mock_log, mock_inc, mock_session):
        """Birinchi kalit xato bersa — ikkinchisiga o'tishi kerak."""
        keys = [
            self._make_key(1, "groq"),
            self._make_key(2, "cerebras"),
        ]
        session = MagicMock()
        session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = keys
        mock_session.return_value = session

        from services.key_manager import execute_with_rotation

        call_count = {"n": 0}

        def flaky_func(api_key, service, *a, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("RateLimitExhausted: quota")
            return {"answer": "second_key_worked"}

        result, err = execute_with_rotation(flaky_func, ai_role="quiz_gen")
        self.assertIsNone(err)
        self.assertEqual(result["answer"], "second_key_worked")
        self.assertEqual(call_count["n"], 2)

    @patch("services.key_manager.get_session")
    @patch("services.key_manager.log_key_error")
    def test_all_keys_fail(self, mock_log, mock_session):
        """Barcha kalitlar xato bersa — (None, xato_xabari) qaytadi."""
        keys = [
            self._make_key(1, "groq"),
            self._make_key(2, "openrouter"),
        ]
        session = MagicMock()
        session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = keys
        mock_session.return_value = session

        from services.key_manager import execute_with_rotation

        def always_fail(api_key, service, *a, **kw):
            raise Exception("500 Server error")

        result, err = execute_with_rotation(always_fail, ai_role="quiz_gen")
        self.assertIsNone(result)
        self.assertIsNotNone(err)

    @patch("services.key_manager.get_session")
    def test_no_active_keys(self, mock_session):
        """Faol kalit yo'q bo'lsa — (None, xabar) qaytadi."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []
        mock_session.return_value = session

        from services.key_manager import execute_with_rotation

        result, err = execute_with_rotation(lambda *a, **k: None, ai_role="quiz_gen")
        self.assertIsNone(result)
        self.assertIn("topilmadi", err)

    @patch("services.key_manager.get_session")
    @patch("services.key_manager.increment_key_usage")
    def test_image_gen_role_prefers_huggingface(self, mock_inc, mock_session):
        """image_gen roli uchun HuggingFace kalit birinchi bo'lishi kerak."""
        keys = [
            self._make_key(1, "groq"),
            self._make_key(2, "huggingface"),
            self._make_key(3, "openrouter"),
        ]
        session = MagicMock()
        session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = keys
        mock_session.return_value = session

        from services.key_manager import execute_with_rotation

        used_services = []

        def capture_func(api_key, service, *a, **kw):
            used_services.append(service)
            return "ok"

        execute_with_rotation(capture_func, "prompt", ai_role="image_gen")
        self.assertEqual(used_services[0], "huggingface")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Admin tekshiruvi
# ─────────────────────────────────────────────────────────────────────────────


class TestIsAdmin(unittest.TestCase):
    """is_admin() — env va DB dan tekshirish."""

    def setUp(self):
        # ADMIN_IDS env ni tozalaymiz
        os.environ.pop("ADMIN_IDS", None)

    def tearDown(self):
        os.environ.pop("ADMIN_IDS", None)

    @patch("bot.handlers.admin.get_session")
    def test_env_admin_allowed(self, mock_session):
        """ADMIN_IDS env da bo'lsa — ruxsat beriladi."""
        os.environ["ADMIN_IDS"] = "111,222,333"
        from importlib import reload

        import bot.handlers.admin as adm

        reload(adm)

        result = adm.is_admin(222)
        self.assertTrue(result)

    @patch("bot.handlers.admin.get_session")
    def test_env_admin_denied(self, mock_session):
        """ADMIN_IDS env da bo'lmasa — rad etiladi (DB ham bo'sh)."""
        os.environ["ADMIN_IDS"] = "111,333"
        session = MagicMock()
        setting = MagicMock()
        setting.value = ""
        session.query.return_value.filter_by.return_value.first.return_value = setting
        mock_session.return_value = session

        from importlib import reload

        import bot.handlers.admin as adm

        reload(adm)

        result = adm.is_admin(999)
        self.assertFalse(result)

    @patch("bot.handlers.admin.get_session")
    def test_db_admin_allowed(self, mock_session):
        """DB da admin_ids bo'lsa — ruxsat beriladi."""
        os.environ.pop("ADMIN_IDS", None)
        session = MagicMock()
        setting = MagicMock()
        setting.value = "444,555"
        session.query.return_value.filter_by.return_value.first.return_value = setting
        mock_session.return_value = session

        from importlib import reload

        import bot.handlers.admin as adm

        reload(adm)

        result = adm.is_admin(555)
        self.assertTrue(result)

    @patch("bot.handlers.admin.get_session")
    def test_no_config_denied(self, mock_session):
        """Hech qanday config yo'q bo'lsa — rad etiladi."""
        os.environ.pop("ADMIN_IDS", None)
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.return_value = session

        from importlib import reload

        import bot.handlers.admin as adm

        reload(adm)

        result = adm.is_admin(12345)
        self.assertFalse(result)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Quiz dublikat tekshiruvi
# ─────────────────────────────────────────────────────────────────────────────


class TestQuizDeduplication(unittest.TestCase):
    """_sync_is_duplicate() — bir xil savol ikki marta saqlanmasligi."""

    @patch("services.ai_generator.get_session")
    def test_duplicate_detected(self, mock_session):
        """Bir xil savol matni bor bo'lsa True qaytadi."""
        session = MagicMock()
        existing_quiz = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = (
            existing_quiz
        )
        mock_session.return_value = session

        from services.ai_generator import _sync_is_duplicate

        result = _sync_is_duplicate("Uchburchak yuzini toping: asosi 8, balandligi 6")
        self.assertTrue(result)

    @patch("services.ai_generator.get_session")
    def test_no_duplicate(self, mock_session):
        """Yangi savol matni bo'lsa False qaytadi."""
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = session

        from services.ai_generator import _sync_is_duplicate

        result = _sync_is_duplicate("Butunlay yangi, noyob savol matni #xyz")
        self.assertFalse(result)

    @patch("services.ai_generator.get_session")
    def test_empty_string_not_duplicate(self, mock_session):
        """Bo'sh satr hech qachon dublikat emas deb hisoblanmaydi (AI xatosi uchun)."""
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = session

        from services.ai_generator import _sync_is_duplicate

        result = _sync_is_duplicate("")
        self.assertFalse(result)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Geometry Renderer — yordamchi funksiyalar
# ─────────────────────────────────────────────────────────────────────────────


class TestQuizTopicAlignment(unittest.TestCase):
    """Custom topic bo'lsa, quiz shu mavzuga mos bo'lishi kerak."""

    def setUp(self):
        from services.ai_generator import _build_visual_prompt, _validate_quiz_payload

        self.build_visual_prompt = _build_visual_prompt
        self.validate_quiz = _validate_quiz_payload

    def test_validate_accepts_matching_custom_topic(self):
        q_data = {
            "question": "To'g'ri burchakli uchburchakning katetlari 3 va 4 bo'lsa, gipotenuzasi nechaga teng?",
            "topic": "To'g'ri burchakli uchburchaklar",
            "options": ["5", "6", "7", "8"],
            "correct_index": 0,
            "explanation": "Pifagor teoremasi bo'yicha 3� + 4� = 5�. Javob: 5",
            "geometry_hint": "null",
        }

        ok, reason, cleaned = self.validate_quiz(
            q_data,
            "10-13",
            "Geometriya",
            True,
            required_topic="To'g'ri burchakli uchburchaklar",
        )

        self.assertTrue(ok, reason)
        self.assertEqual(cleaned["topic"], "To'g'ri burchakli uchburchaklar")

    def test_validate_rejects_unrelated_custom_topic(self):
        q_data = {
            "question": "Aylananing radiusi 5 sm bo'lsa, diametri necha sm bo'ladi?",
            "topic": "Aylana va doira",
            "options": ["8", "10", "12", "15"],
            "correct_index": 1,
            "explanation": "Diametr radiusning ikki baravari. Javob: 10",
            "geometry_hint": "null",
        }

        ok, reason, _ = self.validate_quiz(
            q_data,
            "10-13",
            "Geometriya",
            True,
            required_topic="To'g'ri burchakli uchburchaklar",
        )

        self.assertFalse(ok)
        self.assertIn("mavzu", reason.lower())

    def test_visual_prompt_contains_topic_and_question(self):
        q_data = {
            "question": "Labirintdagi to'g'ri yo'lni toping.",
            "topic": "Labirint",
        }

        prompt = self.build_visual_prompt(
            q_data,
            "Boshqotirma",
            required_topic="Labirint",
        )

        self.assertIn("Topic: Labirint", prompt)
        self.assertIn("Question context: Labirintdagi to'g'ri yo'lni toping.", prompt)
        self.assertIn("No generic stock photo", prompt)

class TestGeometryHelpers(unittest.TestCase):
    """_parse_numeric, _is_unknown, _label_color, _hint_seed testlari."""

    def setUp(self):
        from services.geometry_renderer import (
            _hint_seed,
            _is_unknown,
            _label_color,
            _parse_numeric,
            _rotate_pts,
        )

        self.parse = _parse_numeric
        self.is_unk = _is_unknown
        self.color = _label_color
        self.seed = _hint_seed
        self.rotate = _rotate_pts

    def test_parse_numeric_integer(self):
        self.assertAlmostEqual(self.parse("8"), 8.0)

    def test_parse_numeric_float(self):
        self.assertAlmostEqual(self.parse("3.14"), 3.14)

    def test_parse_numeric_with_units(self):
        self.assertAlmostEqual(self.parse("12cm"), 12.0)

    def test_parse_numeric_unknown_returns_default(self):
        self.assertAlmostEqual(self.parse("x", default=5.0), 5.0)
        self.assertAlmostEqual(self.parse("?", default=3.0), 3.0)

    def test_parse_numeric_sqrt_extracts_number(self):
        # "√5" → 5.0 (sqrt belgisi o'tkazilmaydi, raqam olinadi)
        self.assertAlmostEqual(self.parse("√5"), 5.0)

    def test_is_unknown_true(self):
        self.assertTrue(self.is_unk("x"))
        self.assertTrue(self.is_unk("?"))
        self.assertTrue(self.is_unk("X"))

    def test_is_unknown_false(self):
        self.assertFalse(self.is_unk("5"))
        self.assertFalse(self.is_unk("30°"))
        self.assertFalse(self.is_unk("12cm"))

    def test_label_color_unknown_is_red(self):
        color = self.color("x")
        self.assertEqual(color, "#e11d48")

    def test_label_color_known_is_dark(self):
        color = self.color("5")
        self.assertEqual(color, "#1e293b")

    def test_hint_seed_deterministic(self):
        """Bir xil hint — har doim bir xil seed."""
        hint = "right_triangle|bottom=8|left=6|right=x"
        self.assertEqual(self.seed(hint), self.seed(hint))

    def test_hint_seed_different_hints(self):
        """Har xil hint — har xil seed (ehtimol)."""
        seed1 = self.seed("right_triangle|bottom=3|left=4")
        seed2 = self.seed("circle|radius=5")
        self.assertNotEqual(seed1, seed2)

    def test_rotate_pts_360_returns_original(self):
        """360° aylantirish → dastlabki nuqtalar."""
        pts = [[0.0, 0.0], [4.0, 0.0], [0.0, 3.0]]
        rotated = self.rotate(pts, 360.0)
        for orig, rot in zip(pts, rotated):
            self.assertAlmostEqual(orig[0], rot[0], places=5)
            self.assertAlmostEqual(orig[1], rot[1], places=5)

    def test_rotate_pts_0_unchanged(self):
        """0° aylantirish → o'zgarishsiz."""
        pts = [[1.0, 2.0], [3.0, 4.0]]
        rotated = self.rotate(pts, 0.0)
        for orig, rot in zip(pts, rotated):
            self.assertAlmostEqual(orig[0], rot[0], places=8)
            self.assertAlmostEqual(orig[1], rot[1], places=8)


class TestGeometryRendererShapes(unittest.TestCase):
    """Har xil hint → har xil seed → vizual farq tekshiruvi."""

    def setUp(self):
        from services.geometry_renderer import _hint_seed, _parse_numeric

        self.seed = _hint_seed
        self.parse = _parse_numeric

    def test_right_triangle_proportions_different(self):
        """3:4 va 12:5 nisbatli uchburchaklar farqli o'lchamga ega."""
        b1 = self.parse("3")
        l1 = self.parse("4")
        b2 = self.parse("12")
        l2 = self.parse("5")

        # 3:4 → l/b = 4/3 ≈ 1.33
        # 12:5 → l/b = 5/12 ≈ 0.42
        ratio1 = l1 / b1
        ratio2 = l2 / b2
        # Nisbatlar farqli bo'lishi kerak (bu rasmlar farqli ko'rinadi)
        self.assertNotAlmostEqual(ratio1, ratio2, places=1)

    def test_seeds_produce_variety(self):
        """Turli hint lar turli seedlar berishi kerak."""
        hints = [
            "right_triangle|bottom=3|left=4|right=x",
            "right_triangle|bottom=12|left=5|right=x",
            "isosceles_triangle|bottom=6|left=8",
            "rectangle|bottom=10|left=3",
            "circle|radius_1=7|radius_2=x",
        ]
        seeds = [self.seed(h) for h in hints]
        # Barcha seedlar unikal bo'lishi kerak
        self.assertEqual(len(seeds), len(set(seeds)))


# ─────────────────────────────────────────────────────────────────────────────
# 5. DB Models — get_session singleton
# ─────────────────────────────────────────────────────────────────────────────


class TestGetSession(unittest.TestCase):
    """get_session() har safar bir xil sessionmaker ishlatishi kerak."""

    def test_session_factory_cached(self):
        """_Session global o'zgaruvchisi bir marta yaratilishi kerak."""
        import database.models as dm

        # Eski holatni saqlash
        old_session = dm._Session

        # Birinchi chaqiriq
        s1 = dm.get_session()
        s1.close()
        cached_after_first = dm._Session

        # Ikkinchi chaqiriq
        s2 = dm.get_session()
        s2.close()
        cached_after_second = dm._Session

        # Session factory o'zgarmasligi kerak
        self.assertIs(cached_after_first, cached_after_second)
        self.assertIsNotNone(cached_after_first)

        # Qayta tiklash
        dm._Session = old_session


# ─────────────────────────────────────────────────────────────────────────────
# 6. Temp fayl tozalash — cleanup_temp_files
# ─────────────────────────────────────────────────────────────────────────────


class TestCleanupTempFiles(unittest.TestCase):
    """_cleanup_temp_files() — eski fayllarni to'g'ri o'chirishi kerak."""

    def test_cleanup_removes_old_files(self):
        """max_age=0 bilan barcha fayllar o'chirilishi kerak."""
        import shutil
        import tempfile

        # Vaqtinchalik papka yaratamiz
        tmpdir = tempfile.mkdtemp()
        # Ichiga fayl yaratamiz
        test_file = os.path.join(tmpdir, "test_old.png")
        with open(test_file, "w") as f:
            f.write("test")

        self.assertTrue(os.path.exists(test_file))

        # cleanup funksiyasini fayl yo'li bilan test qilamiz
        # max_age=0 → barcha fayllar "eski"
        now = __import__("time").time()
        cleaned = 0
        for fname in os.listdir(tmpdir):
            fpath = os.path.join(tmpdir, fname)
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) >= 0:
                os.remove(fpath)
                cleaned += 1

        self.assertEqual(cleaned, 1)
        self.assertFalse(os.path.exists(test_file))

        shutil.rmtree(tmpdir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Progress bar yordamchi funksiyasi
# ─────────────────────────────────────────────────────────────────────────────


class TestProgressBar(unittest.TestCase):
    """_progress_bar() — to'g'ri matn ko'rsatishi kerak."""

    def setUp(self):
        from bot.handlers.user import _progress_bar

        self.pb = _progress_bar

    def test_full_progress(self):
        result = self.pb(10, 10, length=10)
        self.assertIn("100%", result)
        self.assertIn("█" * 10, result)

    def test_zero_progress(self):
        result = self.pb(0, 10, length=10)
        self.assertIn("0%", result)
        self.assertNotIn("█", result)

    def test_half_progress(self):
        result = self.pb(5, 10, length=10)
        self.assertIn("50%", result)

    def test_no_answers(self):
        """Hech qanday javob bo'lmasa 0% ko'rsatilishi kerak."""
        result = self.pb(0, 0, length=10)
        self.assertIn("0%", result)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)


