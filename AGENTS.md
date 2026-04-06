# AI Math Bot - Agent Instructions

## Project Overview

This is an AI-powered math quiz generator for Uzbek teachers. Teachers can generate math tests via Telegram bot and download them as PDFs.

## Architecture

### Directory Structure
```
AI_MATH/
├── bot/                    # Telegram bot handlers
│   ├── core.py            # Bot initialization
│   └── handlers/          # User input handlers
│
├── services/              # Business logic
│   ├── test_builder.py    # MAIN ORCHESTRATOR
│   ├── puzzle_engine.py   # PUZZLE ENGINE (Template-driven)
│   ├── pdf_structure.py   # PDF layout generator
│   ├── geometry_pool.py   # Geometry questions
│   ├── topic_generator.py # Academic topics
│   └── render_pool.py     # Image rendering
│
├── config/               # Configuration
└── main.py               # Entry point
```

## Key Components

### 1. TestBuilder (Orchestrator)
- Entry point: `services/test_builder.py`
- Coordinates all generators
- Pipeline: Request → Generator → Validator → PDF

### 2. PuzzleEngine (NEW - Template-Driven)
- Location: `services/puzzle_engine.py`
- Template Registry: 15+ templates
- Pipeline: Template → Parameters → Validation → Uniqueness → RenderSpec

### 3. PDF Structure Generator
- Location: `services/puzzle_pdf_structure.py`
- Converts puzzles to PDF-ready structures
- A4 format with proper layout

## Puzzle Types

### Academic Puzzles
- **Vertical Arithmetic**: addition, subtraction, multiplication, division
- **Flow Diagrams**: single, double, inverse operations
- **Chain Operations**: 3, 4, 5 step chains
- **Grid Puzzles**: magic square, row/col sums, patterns
- **Rebus**: letter addition, symbol equations

### Hybrid Puzzles
- arithmetic_chain_grid (Zanjir + Jadval)
- flow_symbol (Oqim + Belgi)
- vertical_magic (Vertikal + Sehrli kvadrat)
- chain_equation (Zanjir + Tenglamalar)
- grid_pattern (Jadval + Pattern)

## Important Rules

### When Writing Code
1. **DO NOT add comments** unless explicitly requested
2. Follow existing code style and patterns
3. Use Uzbek language for questions
4. Use matplotlib for rendering (NOT HuggingFace API)
5. Always test after writing

### File Naming
- Use snake_case: `puzzle_engine.py`, `test_builder.py`
- Classes: PascalCase: `PuzzleGenerator`, `TestBuilder`
- Constants: UPPER_SNAKE_CASE

### Testing Commands
```bash
# Syntax check
python -m py_compile services/*.py

# Test imports
python -c "from services.test_builder import test_builder"

# Generate sample PDF
python -c "
from services.puzzle_engine import puzzle_engine
from services.puzzle_pdf_structure import test_structure_generator, pdf_renderer
batch = puzzle_engine.generate_batch(5, difficulty='o\\'rta', grade=5)
test_struct = test_structure_generator.generate_test_structure(batch, subject='Matematika', grade=5, difficulty='o\\'rta')
pdf_bytes = pdf_renderer.render(test_struct)
with open('test.pdf', 'wb') as f: f.write(pdf_bytes)
"
```

## Critical Fixes Applied

1. **puzzle_engine.py recursion** - Added max_attempts loop instead of recursive call
2. **puzzle_engine.py equation validation** - Fixed split with multiple "=" signs
3. **pdf_generator.py** - Fixed duplicate textColor parameter
4. **puzzle_templates.py** - Fixed typo `{video}` → removed extra line
5. **hybrid_puzzle_generator.py** - Fixed import statement, added fallback generation
6. **pdf_structure.py** - Fixed missing imports in _draw_header/_draw_footer

## Current State (March 2026)

### Completed
✅ Template-driven puzzle engine
✅ PDF structure generator
✅ Academic puzzles (15+ templates)
✅ Hybrid puzzles (5 types)
✅ Variation system
✅ Layout generator

### Testing
Run the test pipeline:
```bash
python -c "
import logging
logging.disable(logging.WARNING)

from services.puzzle_engine import puzzle_engine
from services.puzzle_pdf_structure import test_structure_generator, pdf_renderer

batch = puzzle_engine.generate_batch(5, difficulty='o\\'rta', grade=5)
test_struct = test_structure_generator.generate_test_structure(
    batch, subject='Matematika', grade=5, difficulty='o\\'rta',
    teacher_name='Test Teacher', time_limit=45
)
pdf_bytes = pdf_renderer.render(test_struct)
print(f'PDF: {len(pdf_bytes)} bytes')
with open('test_output.pdf', 'wb') as f:
    f.write(pdf_bytes)
print('Done!')
"
```

## Questions?

Check `project.md` for full documentation.
