import unittest

from services.knowledge_retriever import KnowledgeRetriever


class KnowledgeRetrieverTests(unittest.TestCase):
    def setUp(self):
        self.retriever = KnowledgeRetriever()

    def test_clean_html_content_removes_noise(self):
        html = """
        <html>
          <body>
            <nav>Menu Privacy Policy Subscribe</nav>
            <p>Pifagor teoremasi to'g'ri burchakli uchburchak uchun ishlaydi.</p>
            <p>a^2 + b^2 = c^2 formula uning asosiy ifodasidir.</p>
            <p>Cookie policy and related articles</p>
          </body>
        </html>
        """

        cleaned = self.retriever._clean_html_content(html)

        self.assertIn("Pifagor teoremasi", cleaned)
        self.assertIn("a^2 + b^2 = c^2", cleaned)
        self.assertNotIn("Privacy Policy", cleaned)

    def test_structure_content_extracts_formulas_and_facts(self):
        content = (
            "Pifagor teoremasi bu to'g'ri burchakli uchburchak tomonlari orasidagi bog'lanishdir. "
            "a^2 + b^2 = c^2 formula ishlatiladi. "
            "Masalan, a=3 va b=4 bo'lsa, c=5 bo'ladi."
        )

        structured = self.retriever._structure_content(content)

        self.assertTrue(structured.definitions)
        self.assertTrue(structured.formulas)
        self.assertTrue(structured.examples)


if __name__ == "__main__":
    unittest.main()
