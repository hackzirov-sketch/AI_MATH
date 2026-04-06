import unittest

from services.math_verifier import math_verifier
from services.question_schema import QuestionItem


class MathVerifierTests(unittest.TestCase):
    def test_percentage_question_validates_deterministically(self):
        item = QuestionItem(
            id="q1",
            subject="matematika",
            topic="Foiz",
            grade=6,
            difficulty="oson",
            type="local_topic",
            question_text="80 sonining 25 foizini toping.",
            options=["10", "20", "25", "40"],
            correct_answer="20",
            explanation="Javob: 20",
            metadata={
                "validation": {
                    "type": "percentage_of",
                    "percent": 25,
                    "whole": 80,
                },
                "option_labels": ["A", "B", "C", "D"],
                "correct_label": "B",
            },
        )

        result = math_verifier.validate_question_item(item)

        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_deterministic)
        self.assertEqual(result.computed_answer, 20)
        self.assertEqual(result.matched_option_indexes, [1])

    def test_fraction_simplification_validates(self):
        item = QuestionItem(
            id="q2",
            subject="matematika",
            topic="Kasrlar",
            grade=5,
            difficulty="oson",
            type="local_topic",
            question_text="6/8 kasrni qisqartiring.",
            options=["3/4", "6/4", "3/8", "2/8"],
            correct_answer="3/4",
            explanation="Javob: 3/4",
            metadata={
                "validation": {
                    "type": "fraction_simplify",
                    "numerator": 6,
                    "denominator": 8,
                },
                "option_labels": ["A", "B", "C", "D"],
                "correct_label": "A",
            },
        )

        result = math_verifier.validate_question_item(item)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.computed_answer, "3/4")


if __name__ == "__main__":
    unittest.main()
