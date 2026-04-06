import unittest

from services.knowledge_retriever import RetrievalResult, SourceDocument, StructuredKnowledge, knowledge_retriever
from services.rag_quiz_generator import rag_quiz_generator


class RagQuizGeneratorTests(unittest.TestCase):
    def test_generate_questions_from_retrieved_content(self):
        original_retrieve = knowledge_retriever.retrieve

        def fake_retrieve(topic: str, subject: str = "", grade: int | None = None, max_results: int = 4):
            return RetrievalResult(
                content=(
                    "Pifagor teoremasi bu to'g'ri burchakli uchburchak tomonlari orasidagi bog'lanishdir. "
                    "c = sqrt(a**2 + b**2). "
                    "Masalan, a=3 va b=4 bo'lsa, c=5 bo'ladi."
                ),
                sources=[
                    SourceDocument(
                        title="Wikipedia",
                        url="https://example.com/pifagor",
                        content=(
                            "Pifagor teoremasi bu to'g'ri burchakli uchburchak tomonlari orasidagi bog'lanishdir. "
                            "c = sqrt(a**2 + b**2)."
                        ),
                        source_type="wikipedia",
                        rank_score=0.9,
                        metadata={"snippet": "c = sqrt(a**2 + b**2)."},
                    )
                ],
                confidence=0.88,
                structured=StructuredKnowledge(
                    definitions=["Pifagor teoremasi bu to'g'ri burchakli uchburchak tomonlari orasidagi bog'lanishdir."],
                    formulas=["c = sqrt(a**2 + b**2)"],
                    rules=[],
                    examples=["Masalan, a=3 va b=4 bo'lsa, c=5 bo'ladi."],
                    important_facts=["Pifagor teoremasi to'g'ri burchakli uchburchak uchun qo'llanadi."],
                ),
                query=f"{topic} {subject}".strip(),
            )

        knowledge_retriever.retrieve = fake_retrieve
        try:
            payload = rag_quiz_generator.generate_questions(
                topic="Pifagor teoremasi",
                subject="geometriya",
                grade=8,
                difficulty="o'rta",
                count=2,
            )
        finally:
            knowledge_retriever.retrieve = original_retrieve

        self.assertTrue(payload["questions"])
        self.assertGreater(payload["confidence"], 0.5)


if __name__ == "__main__":
    unittest.main()
