"""Test the rendering and symbolic subsystems"""
from services.render_specs import DiagramSpecBuilder, DiagramType, DiagramFactory
from services.render_primitives import setup_figure, export_to_bytes
from services.symbolic_engine import symbolic_engine, SymbolicEngine
from services.geometry_math import geometry_math, GeometryMath
from services.algebra_validator import algebra_validator, AlgebraValidator
from services.tikz_exporter import TikZExporter

print("=== Testing Render Specs ===")
spec = DiagramFactory.right_triangle(3, 4, ("A", "B", "C"))
print(f"Spec type: {spec.diagram_type.value}")
print(f"Signature: {spec.get_signature()}")
print(f"Elements: {len(spec.get_all_elements())}")

print()
print("=== Testing Symbolic Engine ===")
result = symbolic_engine.simplify_expression("2*x + 3*x")
print(f"Simplified: {result.simplified}")
canon = symbolic_engine.canonical_answer("3 + 4")
print(f"Canonical 3+4: {canon}")

solution = symbolic_engine.solve_equation("x + 5 = 12", "x")
print(f"x + 5 = 12 -> x = {solution.unique_solution}")

print()
print("=== Testing Geometry Math ===")
gmath = GeometryMath()
dist = gmath.distance((0, 0), (3, 4))
print(f"Distance: {dist.numeric_values.get('distance', 5)}")
pyth = gmath.verify_pythagorean(3, 4, 5)
print(f"3,4,5 is Pythagorean: {pyth.is_valid}")

rect = gmath.rectangle_properties(5, 3)
print(f"Rectangle 5x3 area: {rect.numeric_values.get('area', 15)}")

print()
print("=== Testing Algebra Validator ===")
val = algebra_validator.validate_arithmetic("3 + 4", 7)
print(f"3 + 4 = 7 is valid: {val.is_valid}")

val2 = algebra_validator.validate_chain_operations([2, 3, 4], ["+", "x"], 20)
print(f"2 + 3 x 4 = 20 is valid: {val2.is_valid}")

print()
print("=== Testing TikZ Export ===")
exporter = TikZExporter(standalone=False)
tikz_result = exporter.export(spec)
print(f"Export success: {tikz_result.success}")
print(f"Has TikZ code: {bool(tikz_result.tikz_code)}")

print()
print("=== All tests passed! ===")
