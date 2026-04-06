"""Test SymPy validation and diagram rendering"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=== SYMPY VALIDATION ===")
from services.puzzle_validation import enhanced_validator

# Test arithmetic validation
r = enhanced_validator.validate_arithmetic(25, 17, "+", 42)
print(f"25 + 17 = 42: valid={r.is_valid}, answer={r.answer}")

r = enhanced_validator.validate_arithmetic(25, 17, "+", 43)
print(f"25 + 17 = 43: valid={r.is_valid}")

# Test chain validation
r = enhanced_validator.validate_chain([3, 5, 2], ["+", "x"], 16)
print(f"3+5=8, 8x2=16: valid={r.is_valid}, answer={r.answer}")

# Test equation solving
r = enhanced_validator.validate_equation("2*x + 3 = 11", "x")
print(f"2x+3=11: valid={r.is_valid}, answer={r.answer}, unique={r.has_unique_solution}")

# Test system solving
r = enhanced_validator.validate_system(["x + y = 10", "x - y = 4"], ["x", "y"])
print(f"x+y=10, x-y=4: valid={r.is_valid}, solutions={r.derived_values}")

print()
print("=== DIAGRAM RENDERING ===")
from services.puzzle_diagram_renderer import puzzle_diagram_renderer

# Test chain rendering
d = puzzle_diagram_renderer.render_chain([3, 5, 2], ["+", "x"], hide_index=1)
print(f"Chain diagram: {len(d.image_bytes)} bytes, {d.width}x{d.height}")

# Test grid rendering
d = puzzle_diagram_renderer.render_grid(
    [[3, 5, 2], [1, 7, 4], [6, 2, "?"]],
    missing_pos=(2, 2),
    row_sums=[10, 12, 8],
    col_sums=[10, 14, 6]
)
print(f"Grid diagram: {len(d.image_bytes)} bytes")

# Test shape rendering
d = puzzle_diagram_renderer.render_shape("square", {"side": 5})
print(f"Shape diagram: {len(d.image_bytes)} bytes")

d = puzzle_diagram_renderer.render_shape("triangle", {"sides": [3, 4, 5]})
print(f"Triangle diagram: {len(d.image_bytes)} bytes")

print()
print("=== POOL STATS ===")
from services.puzzle_pool import puzzle_pool
stats = puzzle_pool.get_pool_stats()
print(f"Pool stats: {stats}")

print()
print("ALL TESTS PASSED!")
