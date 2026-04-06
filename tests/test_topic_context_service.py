import unittest

from services.topic_context_service import topic_context_service


class TopicContextServiceTests(unittest.TestCase):
    def test_infer_quiz_type_from_geometry_topic(self):
        quiz_type = topic_context_service.infer_quiz_type("matematika", "Pifagor teoremasi")
        self.assertEqual(quiz_type, "Geometriya")

    def test_topic_match_detects_overlap(self):
        self.assertTrue(
            topic_context_service.topic_matches(
                "Kasrlarni qisqartirish",
                "Oddiy kasrlarni qisqartirish",
                "6/8 kasrni qisqartiring.",
            )
        )

    def test_local_topic_question_is_topic_faithful(self):
        payload = topic_context_service.build_local_topic_question(
            topic="Foiz",
            grade=6,
            difficulty="oson",
            quiz_type="Algebra / Matematika",
            seed="unit-test",
        )
        self.assertEqual(payload["topic"], "Foiz")
        self.assertEqual(len(payload["options"]), 4)
        self.assertIn("foiz", payload["question"].lower())

    def test_hard_topic_question_scales_with_difficulty(self):
        payload = topic_context_service.build_local_topic_question(
            topic="Foiz",
            grade=8,
            difficulty="qiyin",
            quiz_type="Algebra / Matematika",
            seed="hard-foiz",
        )
        self.assertEqual(payload["topic"], "Foiz")
        self.assertTrue("foiz" in payload["question"].lower() or "%" in payload["question"])
        self.assertTrue(
            "sonning o'zini toping" in payload["question"].lower()
            or "o'sish" in payload["question"].lower()
            or "kamay" in payload["question"].lower()
        )

    def test_root_topic_builder_supports_square_root(self):
        payload = topic_context_service.build_local_topic_question(
            topic="Kvadrat ildiz",
            grade=7,
            difficulty="oson",
            quiz_type="Algebra / Matematika",
            seed="root-topic",
        )
        lowered = payload["question"].lower()
        self.assertTrue("ildiz" in lowered or "kvadrati" in lowered)
        self.assertEqual(len(payload["options"]), 4)

    def test_root_topic_builder_hard_square_root_is_not_trivial_clone(self):
        payload = topic_context_service.build_local_topic_question(
            topic="Kvadrat ildiz",
            grade=8,
            difficulty="qiyin",
            quiz_type="Algebra / Matematika",
            seed="root-hard-topic",
        )
        lowered = payload["question"].lower()
        self.assertTrue("ildiz" in lowered or "kvadrati" in lowered)
        self.assertTrue(
            "ifoda" in lowered
            or "kvadrati" in lowered
        )


if __name__ == "__main__":
    unittest.main()
