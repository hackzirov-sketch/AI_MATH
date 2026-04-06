import unittest

from services.ai_generator import (
    _build_telegram_message_link,
    _build_local_fallback_quiz,
    _get_topic_rotation_pool,
    _get_level_display,
    _infer_pattern_family,
    _is_semantic_duplicate_text,
    _normalize_age_group,
    _normalize_difficulty_level,
    _normalize_quiz_signature,
    _normalize_teacher_chat_id,
    _pick_planned_topic,
    _should_allow_duplicate,
    _should_force_local_retry,
    _should_prefer_local_channel_generation,
    _should_use_book_payload,
    _split_teacher_targets,
)
from services.topic_context_service import topic_context_service


class AiGeneratorLinkTests(unittest.TestCase):
    def test_build_message_link_for_public_channel(self):
        link = _build_telegram_message_link("@my_channel", 123)
        self.assertEqual(link, "https://t.me/my_channel/123")

    def test_build_message_link_for_private_channel(self):
        link = _build_telegram_message_link("-1009876543210", 77)
        self.assertEqual(link, "https://t.me/c/9876543210/77")

    def test_split_teacher_targets(self):
        targets = _split_teacher_targets("12345, @teacher,12345")
        self.assertEqual(targets, ["12345", "@teacher"])

    def test_normalize_teacher_chat_id(self):
        self.assertEqual(_normalize_teacher_chat_id("12345"), 12345)
        self.assertEqual(_normalize_teacher_chat_id("-12345"), -12345)
        self.assertEqual(_normalize_teacher_chat_id("@teacher"), "@teacher")

    def test_qiyin_level_keeps_hard_difficulty(self):
        self.assertEqual(_normalize_difficulty_level("Qiyin (Murakkab)"), "qiyin")
        self.assertEqual(_get_level_display("Qiyin (Murakkab)"), "Qiyin (Murakkab)")

    def test_akademik_maps_to_school_hard_band(self):
        self.assertEqual(_normalize_age_group("Akademik (Olimpiada)"), "14-17")
        self.assertEqual(_normalize_difficulty_level("Akademik (Olimpiada)"), "akademik")

    def test_book_payload_is_not_preferred_for_strict_custom_topic(self):
        self.assertFalse(_should_use_book_payload("Algebra / Matematika", "Foiz", "qiyin"))
        self.assertTrue(_should_use_book_payload("Algebra / Matematika", None, "o'rta"))

    def test_duplicate_retry_thresholds_are_capped(self):
        self.assertFalse(_should_allow_duplicate(5))
        self.assertFalse(_should_allow_duplicate(12))
        self.assertFalse(_should_force_local_retry(2, 2))
        self.assertTrue(_should_force_local_retry(3, 3))

    def test_signature_normalization_is_stable(self):
        left = _normalize_quiz_signature(" 16 ning kvadrat ildizini toping ", "Kvadrat ildiz", "Algebra / Matematika", ["4", "2", "6", "8"])
        right = _normalize_quiz_signature("16 ning kvadrat ildizini toping", "Kvadrat ildiz", "Algebra / Matematika", ["8", "6", "4", "2"])
        self.assertEqual(left, right)

    def test_semantic_duplicate_text_detects_near_match(self):
        self.assertTrue(
            _is_semantic_duplicate_text(
                "16 ning kvadrat ildizini toping.",
                "16 ning kvadrat ildizini toping",
            )
        )

    def test_equation_signature_matches_rephrased_question(self):
        left = _normalize_quiz_signature(
            "2x + 5 = 11 tenglamasini yeching",
            "Tenglama",
            "Algebra / Matematika",
            ["x = 2", "x = 3", "x = 4", "x = 5"],
        )
        right = _normalize_quiz_signature(
            "2x + 5 = 11 ga qanday qiymatga ega x?",
            "Tenglama",
            "Algebra / Matematika",
            ["2", "3", "4", "5"],
        )
        self.assertEqual(left, right)

    def test_hard_algebra_fallback_rotates_topics(self):
        first = _build_local_fallback_quiz("10-13 yosh", "Algebra / Matematika", None, None, 1, False, "qiyin")
        second = _build_local_fallback_quiz("10-13 yosh", "Algebra / Matematika", None, None, 2, False, "qiyin")
        self.assertNotEqual(first["topic"], second["topic"])

    def test_hard_algebra_first_five_fallback_topics_are_unique(self):
        topics = [
            _build_local_fallback_quiz("10-13 yosh", "Algebra / Matematika", None, None, idx, False, "qiyin")["topic"]
            for idx in range(5)
        ]
        self.assertEqual(len(topics), len(set(topics)))

    def test_pattern_family_detects_equation_template(self):
        family = _infer_pattern_family(
            "2x + 5 = 11 tenglamasini yeching",
            "Tenglama",
            "Algebra / Matematika",
        )
        self.assertEqual(family, "equation_linear")

    def test_pattern_family_distinguishes_pythagoras_subtypes(self):
        self.assertEqual(
            _infer_pattern_family(
                "Gipotenuzasi 13 va bir kateti 5 bo'lgan to'g'ri burchakli uchburchakda ikkinchi katetni toping.",
                "Pifagor teoremasi",
                "Geometriya",
            ),
            "pythagoras_missing_leg",
        )
        self.assertEqual(
            _infer_pattern_family(
                "Tomonlari 5 sm va 12 sm bo'lgan to'g'ri to'rtburchak diagonalini toping.",
                "Pifagor teoremasi",
                "Geometriya",
            ),
            "pythagoras_diagonal",
        )
        self.assertEqual(
            _infer_pattern_family(
                "Katetlari 3 va 4 bo'lgan to'g'ri burchakli uchburchakda gipotenuzaga qurilgan kvadrat yuzini toping.",
                "Pifagor teoremasi",
                "Geometriya",
            ),
            "pythagoras_square_area",
        )

    def test_pattern_family_distinguishes_new_variety_templates(self):
        self.assertEqual(
            _infer_pattern_family(
                "5:10 nisbatni sodda ko'rinishga keltiring.",
                "Nisbat va proporsiya",
                "Algebra / Matematika",
            ),
            "ratio_simplify",
        )
        self.assertEqual(
            _infer_pattern_family(
                "To'rtburchakning perimetri 24 sm. Bir tomoni 8 sm bo'lsa, ikkinchi tomoni nechaga teng?",
                "Perimetr",
                "Geometriya",
            ),
            "perimeter_missing_side",
        )
        self.assertEqual(
            _infer_pattern_family(
                "π=3 deb olib, radiusi 4 sm bo'lgan aylana uzunligini toping.",
                "Aylana",
                "Geometriya",
            ),
            "circle_circumference",
        )
        self.assertEqual(
            _infer_pattern_family(
                "Qutida 2 ta qizil, 3 ta ko'k va 1 ta yashil shar bor. Tasodifiy olingan shar qizil bo'lmaslik ehtimoli nechaga teng?",
                "Ehtimollar nazariyasi",
                "Algebra / Matematika",
            ),
            "probability_complement",
        )
        self.assertEqual(
            _infer_pattern_family(
                "4, 9, 14, 19 ketma-ketlikning ayirmasini toping.",
                "Ketma-ketlik",
                "Algebra / Matematika",
            ),
            "sequence_difference",
        )
        self.assertEqual(
            _infer_pattern_family(
                "Qaysi sonning kvadrati 81 ga teng?",
                "Kvadrat ildiz",
                "Algebra / Matematika",
            ),
            "root_inverse",
        )
        self.assertEqual(
            _infer_pattern_family(
                "Quyidagi sonlardan qaysi biri murakkab son?",
                "Tub sonlar",
                "Algebra / Matematika",
            ),
            "composite_select",
        )
        self.assertEqual(
            _infer_pattern_family(
                "Qaysi juftlikning EKUK i 24 ga teng?",
                "EKUB va EKUK",
                "Algebra / Matematika",
            ),
            "lcm_pair_choice",
        )

    def test_topic_rotation_pool_is_defined_for_algebra(self):
        pool = _get_topic_rotation_pool("Algebra / Matematika", "qiyin")
        self.assertEqual(pool[:3], ["Tenglamalar", "Kasrlar", "Foiz"])

    def test_planned_topic_avoids_last_sent_topic(self):
        topic = _pick_planned_topic("Algebra / Matematika", "qiyin", sent_count=1, slot_attempts=1, last_topic="Kasrlar")
        self.assertEqual(topic, "Foiz")

    def test_generic_algebra_channel_prefers_local_generation(self):
        self.assertTrue(_should_prefer_local_channel_generation("Algebra / Matematika"))
        self.assertFalse(_should_prefer_local_channel_generation("Algebra / Matematika", custom_topic="Foiz"))

    def test_pythagoras_local_topic_builder_produces_multiple_families(self):
        families = set()
        for idx in range(20):
            payload = topic_context_service.build_local_topic_question(
                topic="Pifagor teoremasi",
                grade=7,
                difficulty="o'rta",
                quiz_type="Geometriya",
                seed=f"pythagoras-{idx}",
            )
            families.add(_infer_pattern_family(payload["question"], payload["topic"], "Geometriya"))
        self.assertGreaterEqual(len(families), 4)

    def test_common_topics_produce_multiple_families(self):
        expectations = {
            "Kasrlar": 3,
            "Nisbat va proporsiya": 3,
            "Perimetr": 3,
            "Yuza": 3,
            "Aylana": 3,
            "Burchaklar": 3,
            "Ketma-ketlik": 3,
            "Kvadrat ildiz": 2,
            "Tub sonlar": 2,
            "EKUB va EKUK": 3,
        }
        for topic, minimum in expectations.items():
            families = set()
            for idx in range(24):
                payload = topic_context_service.build_local_topic_question(
                    topic=topic,
                    grade=7,
                    difficulty="o'rta",
                    quiz_type="Algebra / Matematika",
                    seed=f"{topic}-{idx}",
                )
                families.add(_infer_pattern_family(payload["question"], payload["topic"], "Algebra / Matematika"))
            self.assertGreaterEqual(len(families), minimum, topic)


if __name__ == "__main__":
    unittest.main()
