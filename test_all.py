import logging
logging.basicConfig(level=logging.WARNING)

from services.test_builder import TestBuilder, TestRequest
from services.puzzle_engine import puzzle_engine
from services.puzzle_pdf_structure import test_structure_generator, pdf_renderer

# Test 1: Puzzle engine
batch = puzzle_engine.generate_batch(2, difficulty="o'rta", grade=5)
print("1. Puzzle Engine: OK")

# Test 2: PDF generation  
test_struct = test_structure_generator.generate_test_structure(
    batch, subject="Matematika", grade=5, difficulty="o'rta",
    teacher_name="Test", time_limit=45
)
pdf_bytes = pdf_renderer.render(test_struct)
print("2. PDF Generator: OK ({})".format(len(pdf_bytes)))

# Test 3: Test builder
tb = TestBuilder()
print("3. Test Builder: OK")

print("\nBarcha testlar muvaffaqiyatli!")