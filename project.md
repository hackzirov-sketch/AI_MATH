# AI Math Quiz Telegram Bot - Loyiha Hujjatlashtirish

## Loyiha Maqsadi

Bu loyiha **O'zbekistondagi o'qituvchilar** uchun mo'ljallangan avtomatlashtirilgan matematika test generatori. Telegram bot orqali o'qituvchilar turli fanlar bo'yicha (Matematika, Geometriya, Algebra, Mantiq) testlar yaratishlari va PDF formatida yuklab olishlari mumkin.

---

## 2026-04 Hardening Yangilanishi

So'nggi yangilanishda tizim low-memory va limited-storage serverlar uchun kuchaytirildi.

## 2026-04 Render Deploy Yangilanishi

Loyiha Render uchun ko'p-servisli arxitekturaga moslashtirildi.

### Yangi deploy fayllari

- `render.yaml`
- `requirements-render.txt`
- `requirements-dev.txt`
- `render_web.py`
- `render_bot.py`
- `render_manage.py`
- `RENDER.md`

### Render servis bo'linishi

- `ai-math-web`
  - Flask admin panel va health endpoint
- `ai-math-bot`
  - Telegram polling worker
- `ai-math-celery`
  - RAG, PDF va render task worker
- `ai-math-beat`
  - periodik cleanup va self-improvement scheduler
- `ai-math-db`
  - Render Postgres
- `ai-math-redis`
  - Render Key Value

### Muhim deploy o'zgarishlari

- `main.py` endi import paytida botni avtomatik yoqmaydi
- web va bot entrypointlari alohida ajratildi
- `DATABASE_URL` Render Postgres uchun `postgresql+psycopg://` formatiga normalize qilinadi
- Render build `requirements-render.txt` orqali yuradi
- Celery Beat har 10 daqiqada cache cleanup, har 6 soatda self-improvement analysis yuboradi

### Yangi cache kataloglari

O'chirish mumkin bo'lgan xavfsiz papkalar:

- `data/cache/renders/`
- `data/cache/pdf_temp/`
- `data/cache/tmp/`

Aslo o'chirilmaydigan joylar:

- `prompts/`
- `templates/`
- `pools/`
- `config/`
- `.env`
- database fayllari

### Yangi modullar

- `services/cache_manager.py`
  - `CacheManager`
  - `SafeCleanerWorker`
- `services/render_cache.py`
  - hash-based render cache
- `services/render_pool.py`
  - memory-aware rendering
- `services/pdf_generator.py`
  - compressed PDF output

### Cleaner qoidalari

- faqat allowed cache papkalarda ishlaydi
- faqat `.png`, `.jpg`, `.pdf`, `.tmp` fayllarga tegadi
- `.py`, `.json`, `.yaml`, `.env`, `.db` fayllarni hech qachon o'chirmaydi
- TTL bo'yicha tozalaydi
- size limit oshsa eng eski fayllarni birinchi o'chiradi
- background worker orqali 5-10 daqiqa interval bilan ishlashi mumkin

### Memory optimizatsiyalar

- bir xil `render_signature` bo'lsa render qayta ishlatiladi
- memory pressure oshsa DPI pasayadi
- kerak bo'lsa grayscale render ishlatiladi
- image bytes optimize qilinadi
- PDF lar `data/cache/pdf_temp/` ichiga yoziladi

### Telemetry asosida topilgan zaif yo'nalishlar

1. `geometry_tbt_not_geometric_enough`
   - 14 failure
   - tavsiya: `geometry_tbt_v2`
2. `iq_syllogism_*`
   - takroriy patternlar
   - tavsiya: `iq_syllogism_topic_locked_v2`
3. `iq_evidence_reasoning_*`
   - distractor va explanation sifati past
   - tavsiya: `iq_evidence_reasoning_v2`

---

## Arxitektura Umumiy Ko'rinish

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TELEGRAM BOT LAYER                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Handler   │  │   States    │  │   Inline    │  │   Router    │        │
│  │  (Input KB) │  │  (Session)  │  │  Keyboard   │  │  (Routes)   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BUSINESS LOGIC LAYER                                │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │                        ORCHESTRATOR (TestBuilder)                   │     │
│  │   Pipeline: Generator → Validator → Uniqueness → Renderer → PDF    │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  TopicGen   │  │ GeometryPool│  │ PuzzlePool  │  │ HybridGen   │      │
│  │ (Akademik) │  │ (Geometriya)│  │ (Mantiq)    │  │ (Gibrid)    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ AcademicGen │  │  Variation  │  │  LayoutGen  │  │  Template   │      │
│  │  (Puzzles)  │  │   Engine    │  │ (Visual)    │  │  Registry   │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RENDERING LAYER                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Geometry    │  │  Puzzle     │  │   Render    │  │   Render    │        │
│  │ Renderer    │  │  Renderer   │  │   Pool      │  │  Primitives │        │
│  │ (Matplotlib)│  │ (Matplotlib)│  │  (Workers)  │  │   (Lego)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT LAYER                                      │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │                      PDF Generator (ReportLab)                      │     │
│  │   A4 Format: Test.pdf → (2s delay) → Javoblar.pdf                 │     │
│  └───────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Katalog Tuzilishi

```
AI_MATH/
│
├── bot/                          # Telegram Bot qismi
│   ├── core.py                   # Bot initialization, router registration
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── admin.py              # Admin panel, AI Test Generator button
│   │   ├── test_generator.py     # Test yaratish handler (input collection)
│   │   ├── quiz.py               # Quiz handler
│   │   └── teacher.py            # Teacher-specific handlers
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── inline.py             # Inline keyboards
│   └── states.py                 # State management
│
├── services/                      # Business Logic qismi
│   │
│   │  # === ACADEMIC PUZZLE ENGINE (YANGI) ===
│   │
│   ├── puzzle_engine.py          # ASOSIY ORCHESTRATOR
│   │   ├── TemplateRegistry      # Barcha puzzle template lar
│   │   ├── ParameterGenerator    # Sonlar va parameter generatsiya
│   │   ├── PuzzleValidator       # Tekshrish (equations, constraints)
│   │   ├── UniquenessEngine      # Takrorlanishdan saqlash
│   │   ├── RenderSpecGenerator   # Vizual chizish uchun spetsifikatsiya
│   │   └── PuzzleGenerator       # Pipeline: Template→Params→Validate→Render
│   │
│   ├── puzzle_pdf_structure.py    # PDF uchun strukturaviy generatsiya
│   │   ├── PDFQuestionBlock      # Bitta savol bloki
│   │   ├── PDFLayoutRules        # A4 layout qoidalar
│   │   ├── PDFTestStructure      # To'liq test struktura
│   │   ├── PuzzleToPDFConverter  # Puzzle → PDF block converter
│   │   ├── TestStructureGenerator # Test + Answer key generator
│   │   └── PDFRenderer           # ReportLab bilan PDF chizish
│   │
│   │  # === PUZZLE TEMPLATES ===
│   │
│   ├── puzzle_templates.py        # Academic puzzle generator
│   │   ├── VerticalArithmetic   # Qo'shish, ayirish, ko'paytirish, bo'lish
│   │   ├── FlowDiagram          # Bitta/ikki/teskari operatsiyalar
│   │   ├── ChainOperations      # 3/4/5 qadamli zanjir
│   │   ├── GridArithmetic       # Sehrli kvadrat, satr/ustun yig'indisi
│   │   └── SymbolUnknown        # Bitta/ikki belgi, tenglama sistemasi
│   │
│   ├── puzzle_layout_generator.py # Puzzle vizual layout specs
│   │   ├── LayoutBox            # Box (quti) - content, position, style
│   │   ├── LayoutArrow          # Arrow (strelka) - from/to, label
│   │   ├── PuzzleLayout         # To'liq layout - rows, arrows, annotations
│   │   └── PuzzleLayoutRenderer # Matplotlib bilan chizish
│   │
│   ├── puzzle_variation_generator.py # Template variationlari
│   │   ├── VariationRegistry    # Har bir template uchun variantlar
│   │   │   ├── VERTICAL_ARITHMETIC_VARIATIONS  # classic, with_carry, grid...
│   │   │   ├── FLOW_DIAGRAM_VARIATIONS         # vertical, horizontal, tree
│   │   │   ├── CHAIN_VARIATIONS               # linear, circular, pyramid
│   │   │   ├── GRID_VARIATIONS                # classic_3x3, latin_4x4...
│   │   │   └── SYMBOL_VARIATIONS              # simple, multiple, system
│   │   ├── PuzzleVariationGenerator # Variation tanlash, qo'llash
│   │   └── VariationDifficultyAdjuster # Qiyinlik sozlash
│   │
│   │  # === HYBRID PUZZLES ===
│   │
│   ├── hybrid_puzzle_generator.py # Gibrid puzzle lar
│   │   ├── HybridPuzzle           # Gibrid puzzle - components biriktirilgan
│   │   ├── HybridPuzzleGenerator   # 5 ta gibrid tur:
│   │   │   ├── arithmetic_chain_grid  # Arifmetik zanjir + Jadval
│   │   │   ├── flow_symbol           # Oqim diagramma + Belgi
│   │   │   ├── vertical_magic         # Vertikal + Sehrli kvadrat
│   │   │   ├── chain_equation        # Zanjir + Tenglamalar sistemasi
│   │   │   └── grid_pattern          # Jadval + Pattern recognition
│   │   └── HybridPuzzleRenderer      # Gibrid puzzle chizish
│   │
│   │  # === LEGACY PUZZLE SYSTEM ===
│   │
│   ├── puzzle_pool.py             # Eski puzzle system (logic puzzles)
│   │   ├── LogicPuzzle            # Mantiqiy grid puzzles
│   │   ├── Crossword             # Krossvord
│   │   ├── Labyrinth             # Labirint
│   │   ├── Scale                 # Tarozi puzzles
│   │   └── generate_logic_puzzle # Mantiqiy puzzle generatsiya
│   │
│   │  # === GEOMETRY SYSTEM ===
│   │
│   ├── geometry_pool.py           # Geometriya puzzle registry
│   │   ├── GeometryTopic          # 8+ mavzu
│   │   │   ├── TriangleProperties   # Burchaklar, tomonlar
│   │   │   ├── CircleProperties      # Radius, diametr, yoy
│   │   │   ├── AngleFinding          # Burchak topish
│   │   │   ├── PythagoreanTheorem    # Pifagor teoremasi
│   │   │   ├── AreaCalculation       # Yuza hisoblash
│   │   │   ├── PerimeterCalculation  # Perimetr hisoblash
│   │   │   ├── SimilarTriangles      # O'xshash uchburchaklar
│   │   │   └── Trigonometry          # Sin, cos, tan
│   │   └── GeometryQuestionGenerator # Question spec + render
│   │
│   ├── geometry_renderer.py       # Geometriya chizish
│   │   ├── BasicShapes           # Uchburchak, to'rtburchak, aylana
│   │   ├── 3DShapes              # Kub, silindr, konus
│   │   ├── Functions             # Grafik chizish
│   │   └── Trigonometry          # Burchak vizualizatsiya
│   │
│   │  # === TOPIC & QUESTION SYSTEM ===
│   │
│   ├── topic_generator.py         # Akademik mavzular (1-11 sinf)
│   │   ├── TopicsByGrade          # Har bir sinf uchun mavzular
│   │   ├── QuestionTemplates      # 500+ savol shabloni
│   │   └── generate_question      # Question generatsiya
│   │
│   │  # === VALIDATION & UNIQUENESS ===
│   │
│   ├── question_validator.py      # Question validatsiya
│   │   ├── validate_question       # Asosiy tekshirish
│   │   ├── validate_batch          # Gurux tekshirish
│   │   ├── check_equivalence      # Ekvivalentlik tekshirish
│   │   └── remove_duplicates      # Dublikatlarni olib tashlash
│   │
│   ├── quiz_uniqueness.py         # Session-based uniqueness
│   │   ├── QuizUniquenessSession  # Sessiyadagi puzzle lar
│   │   ├── UniquenessManager      # Barcha session lar
│   │   └── DiversityScorer       # Diversity hisoblash
│   │
│   │  # === RENDERING SYSTEM ===
│   │
│   ├── render_specs.py            # Unified spec dataclasses
│   │   ├── QuestionSpec          # Savol spetsifikatsiyasi
│   │   ├── ShapeSpec             # Shape spetsifikatsiyasi
│   │   ├── PuzzleSpec            # Puzzle spetsifikatsiyasi
│   │   └── DiagramSpec           # Diagramma spetsifikatsiyasi
│   │
│   ├── render_cache.py            # LRU + disk cache
│   │   ├── MemoryCache           # LRU memory cache
│   │   └── DiskCache            # Disk cache
│   │
│   ├── render_primitives.py       # Low-level drawing functions
│   │   ├── draw_box              # Box chizish
│   │   ├── draw_arrow            # Strelka chizish
│   │   ├── draw_grid             # Grid chizish
│   │   ├── draw_text             # Text chizish
│   │   └── draw_shape            # Shape chizish (lego blocks)
│   │
│   ├── render_pool.py             # Render dispatcher
│   │   ├── render_single         # Bitta spec render
│   │   ├── render_batch          # Gurux render
│   │   ├── WorkerPool            # Worker thread pool
│   │   └── fallback_render       # Xatolik bo'lsa fallback
│   │
│   │  # === PDF GENERATION ===
│   │
│   ├── pdf_generator.py           # A4 PDF yaratish
│   │   ├── generate_test_pdf     # Test.pdf yaratish
│   │   ├── generate_answers_pdf   # Javoblar.pdf yaratish
│   │   ├── PAGE_TEMPLATES        # A4 page templates
│   │   └── STYLES                # ReportLab styles
│   │
│   │  # === MAIN ORCHESTRATOR ===
│   │
│   └── test_builder.py            # ASOSIY ORCHESTRATOR
│       ├── TestRequest            # So'rov
│       ├── TestResponse           # Javob
│       ├── build_test             # Test yaratish pipeline
│       ├── suggest_topics         # Mavzu tavsiyalari
│       └── _generate_*            # Turli generator lar
│
├── config/                        # Konfiguratsiya
│   ├── __init__.py
│   └── settings.py                # Bot settings
│
├── requirements.txt               # Python dependencies
├── README.md                      # Loyiha haqida
├── AGENTS.md                      # Agent instructions
├── .env.example                   # Environment variables example
└── main.py                        # Bot entry point
```

---

## Pipeline - Asosiy Jarayon

### Test Yaratish Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        TEST YARATISH PIPELINE                            │
└──────────────────────────────────────────────────────────────────────────┘

1. HANDLER LAYER (Input Collection)
   │
   │  Foydalanuvchi → /test buyrug'i
   │
   ▼
2. STATE COLLECTION
   │
   │  Sinf → Qiyinlik → Savollar soni → Fan → Mavzu (ixtiyoriy)
   │
   ▼
3. ORCHESTRATOR (TestBuilder)
   │
   │  TestRequest yaratiladi
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │                    GENERATOR SELECTION                                │
   │                                                                      │
   │  Fan = "Matematika" + Geometriya requested                          │
   │    → Mixed generator (geometriya + akademik)                        │
   │                                                                      │
   │  Fan = "Mantiq" / "Boshqotirma"                                     │
   │    → Academic puzzles (50%) + Hybrid (20%) + Legacy (30%)            │
   │                                                                      │
   │  Fan = "Algebra" / "Geometriya" (only)                              │
   │    → Topic-based generator                                          │
   └─────────────────────────────────────────────────────────────────────┘
   │
   ▼
4. GENERATION PHASE
   │
   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │  │ AcademicGen │ │ HybridGen   │ │ GeometryPool│ │ TopicGen    │
   │  │ (Templates)│ │ (Gibrid)    │ │ (Shapes)    │ │ (Questions)│
   │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
   │
   ▼
5. VALIDATION PHASE
   │
   │  ┌─────────────────────────────────────────────────────────────────┐
   │  │  QuestionValidator                                               │
   │  │  ├── Equation validation (tenglamalar to'g'ri)                  │
   │  │  ├── Constraint validation (cheklovlar bajarilgan)             │
   │  │  ├── Uniqueness check (takrorlanish yo'q)                      │
   │  │  └── Equivalence check (ekvivalent emas)                        │
   │  └─────────────────────────────────────────────────────────────────┘
   │
   ▼
6. RENDERING PHASE
   │
   │  ┌─────────────────────────────────────────────────────────────────┐
   │  │  RenderPool                                                    │
   │  │  ├── Select renderer (Geometry / Puzzle)                       │
   │  │  ├── Create RenderSpec                                         │
   │  │  ├── Render to image (Matplotlib)                             │
   │  │  ├── Cache result (LRU + Disk)                                │
   │  │  └── Return image bytes                                        │
   │  └─────────────────────────────────────────────────────────────────┘
   │
   ▼
7. PDF GENERATION
   │
   │  ┌─────────────────────────────────────────────────────────────────┐
   │  │  Test.pdf (A4)                                                  │
   │  │  ├── Header: Fan, Sinf, Qiyinlik, O'qituvchi                  │
   │  │  ├── Questions: 1-N savollar + rasm + variantlar                │
   │  │  └── Footer: Bet raqami                                        │
   │  └─────────────────────────────────────────────────────────────────┘
   │
   │  [2 soniya kutish]
   │
   │  ┌─────────────────────────────────────────────────────────────────┐
   │  │  Javoblar.pdf (A4)                                              │
   │  │  ├── Header: Javoblar kaliti                                   │
   │  │  └── Answers: 1-N variantlar                                    │
   │  └─────────────────────────────────────────────────────────────────┘
   │
   ▼
8. DELIVERY
   │
   │  Foydalanuvchiga PDF fayllar yuboriladi
   │
   ▼
9. APPEAL HANDLING (optional)
   │
       Foydalanuvchi "Shikoyat" tugmasini bosadi
       → Admin panelda xabar ko'rinadi
```

---

## Puzzle Engine - PUZZLE_GENERATOR Pipeline

### Template Driven Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│              PUZZLE ENGINE - TEMPLATE DRIVEN ARCHITECTURE                 │
└──────────────────────────────────────────────────────────────────────────┘

1. TEMPLATE SELECTION
   │
   │  ┌──────────────────────────────────────────────────────────────┐
   │  │  TemplateRegistry                                           │
   │  │                                                              │
   │  │  VERTICAL_ARITHMETIC:                                       │
   │  │  ├── addition_2digit       (oson, 2-3 sinf)                │
   │  │  ├── subtraction_2digit    (oson, 2-3 sinf)                │
   │  │  ├── multiplication_2x1    (o'rta, 3-4 sinf)                │
   │  │  └── division_remainder    (o'rta, 4-5 sinf)               │
   │  │                                                              │
   │  │  REBUS:                                                      │
   │  │  ├── letter_addition     (o'rta, 3-5 sinf)                │
   │  │  └── symbol_equation     (qiyin, 4-7 sinf)                │
   │  │                                                              │
   │  │  GRID_PUZZLE:                                               │
   │  │  ├── magic_square_3x3    (o'rta, 3-6 sinf)                │
   │  │  ├── row_col_sum         (oson, 2-5 sinf)                 │
   │  │  └── number_pattern_grid (o'rta, 4-7 sinf)                │
   │  │                                                              │
   │  │  FLOW_DIAGRAM:                                              │
   │  │  ├── single_operation   (oson, 2-4 sinf)                  │
   │  │  ├── double_operation   (o'rta, 3-6 sinf)                 │
   │  │  └── inverse_flow       (qiyin, 4-11 sinf)                │
   │  │                                                              │
   │  │  CHAIN_OPERATIONS:                                          │
   │  │  ├── three_step         (oson, 2-5 sinf)                  │
   │  │  ├── four_step          (o'rta, 3-7 sinf)                 │
   │  │  └── five_step          (qiyin, 4-11 sinf)                │
   │  └──────────────────────────────────────────────────────────────┘
   │
   ▼
2. PARAMETER GENERATION
   │
   │  ┌──────────────────────────────────────────────────────────────┐
   │  │  ParameterGenerator                                          │
   │  │                                                              │
   │  │  Input: template, difficulty, grade                          │
   │  │                                                              │
   │  │  Output: PuzzleParameters                                    │
   │  │  ├── numbers: {a: 45, b: 32, result: 77}                    │
   │  │  ├── symbols: {A: "5", B: "8"}                              │
   │  │  ├── operations: ["+"]                                       │
   │  │  └── constraints: {no_negative: true}                         │
   │  └──────────────────────────────────────────────────────────────┘
   │
   ▼
3. PUZZLE BUILDING
   │
   │  ┌──────────────────────────────────────────────────────────────┐
   │  │  PuzzleGenerator._build_puzzle()                             │
   │  │                                                              │
   │  │  Output: GeneratedPuzzle                                     │
   │  │  ├── puzzle_id: "a3f5b2c1"                                  │
   │  │  ├── template_id: "addition_2digit"                          │
   │  │  ├── template_type: VERTICAL_ARITHMETIC                      │
   │  │  ├── difficulty: MEDIUM                                      │
   │  │  ├── parameters: {a: 45, b: 32, result: 77}                 │
   │  │  ├── structure: "   45\n + 32\n -----\n   77"                │
   │  │  ├── equations: ["45 + 32 = 77"]                             │
   │  │  ├── render_spec: RenderSpec(...)                           │
   │  │  ├── answer: 77                                              │
   │  │  └── uniqueness_signature: "abc123def456"                    │
   │  └──────────────────────────────────────────────────────────────┘
   │
   ▼
4. VALIDATION
   │
   │  ┌──────────────────────────────────────────────────────────────┐
   │  │  PuzzleValidator.validate()                                   │
   │  │                                                              │
   │  │  ├── _validate_equations()                                    │
   │  │  │   └── 45 + 32 = 77 ✓                                      │
   │  │  │                                                              │
   │  │  ├── _validate_uniqueness()                                  │
   │  │  │   └── answer is not None ✓                                │
   │  │  │                                                              │
   │  │  ├── _validate_constraints()                                 │
   │  │  │   └── no_negative: True ✓                                 │
   │  │  │                                                              │
   │  │  └── _validate_structure()                                    │
   │  │      └── structure and render_spec exist ✓                   │
   │  │                                                              │
   │  │  Result: (True, []) = VALID                                  │
   │  └──────────────────────────────────────────────────────────────┘
   │
   ▼
5. UNIQUENESS CHECK
   │
   │  ┌──────────────────────────────────────────────────────────────┐
   │  │  UniquenessEngine.is_unique()                                 │
   │  │                                                              │
   │  │  1. Check if signature exists in session                      │
   │  │  2. Generate math signature                                   │
   │  │  │   └── "vertical_arithmetic|o'rta|a:45|b:32|result:77"    │
   │  │  3. Check similarity with existing puzzles                    │
   │  │  4. If duplicate → retry generation                          │
   │  │  5. If unique → add to session                               │
   │  └──────────────────────────────────────────────────────────────┘
   │
   ▼
6. RENDER SPEC GENERATION
   │
   │  ┌──────────────────────────────────────────────────────────────┐
   │  │  RenderSpecGenerator.generate()                              │
   │  │                                                              │
   │  │  Output: RenderSpec                                          │
   │  │  ├── layout_type: "vertical"                                 │
   │  │  ├── grid_size: (5, 4)                                       │
   │  │  ├── element_positions: {num1: (2,3), num2: (2,2)...}      │
   │  │  ├── arrow_connections: []                                  │
   │  │  ├── alignment_rules: "right"                               │
   │  │  ├── spacing_rules: {col_spacing: 0.8, line_spacing: 1.0}   │
   │  │  ├── style_variant: "standard"                             │
   │  │  └── figure_size: (8, 10)                                   │
   │  └──────────────────────────────────────────────────────────────┘
   │
   ▼
7. OUTPUT
   │
       GeneratedPuzzle.to_dict() → PDFQuestionBlock → PDF
```

---

## Ma'lumotlar Tuzilishi

### TestRequest

```python
@dataclass
class TestRequest:
    grade: int                  # 1-11
    difficulty: str             # "oson", "o'rta", "qiyin"
    question_count: int        # Savollar soni
    subject: str                # "matematika", "geometriya", "mantiq"
    topic: Optional[str]        # Mavzu (ixtiyoriy)
    include_geometry: bool      # Geometriya rasmllari
    include_puzzles: bool      # Puzzle savollari
    teacher_name: str           # O'qituvchi ismi
    time_limit: int             # Vaqt cheklovi (daqiqa)
```

### GeneratedPuzzle

```python
@dataclass
class GeneratedPuzzle:
    puzzle_id: str
    template_id: str            # "addition_2digit"
    template_type: PuzzleType   # VERTICAL_ARITHMETIC
    difficulty: Difficulty      # MEDIUM
    parameters: PuzzleParameters
    structure: str               # "   45\n + 32\n -----\n   77"
    equations: List[str]        # ["45 + 32 = 77"]
    render_spec: RenderSpec     # Vizual chizish uchun
    answer: Any                 # 77
    uniqueness_signature: str   # "abc123def456"
    validation_result: bool    # True
```

### PDFTestStructure

```python
@dataclass
class PDFTestStructure:
    test_id: str
    subject: str
    grade: int
    difficulty: str
    teacher_name: str
    time_limit: int
    questions: List[PDFQuestionBlock]
    header_config: Dict
    footer_config: Dict
    pagination_config: Dict
    layout_rules: PDFLayoutRules
```

---

## Handler Flow

### Test Generator Handler

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     TEST GENERATOR HANDLER FLOW                           │
└──────────────────────────────────────────────────────────────────────────┘

Foydalanuvchi "/test" bosadi
        │
        ▼
┌─────────────────┐
│  START_STATE    │
│  /test buyrug'i │
└────────┬────────┘
         │
         ▼ [CB: "test_"]
┌─────────────────┐
│  GRADE_STATE    │
│  Sinf tanlash   │  "Qaysi sinf uchun test yaratmoqchisiz?"
│  1-11 sinf      │
└────────┬────────┘
         │
         ▼ [CB: "grade_5"]
┌─────────────────┐
│ DIFFICULTY_STATE│
│ Qiyinlik tanlash│  "Qaysi qiyinlik darajasida?"
│ Oson/O'rta/Qiyin│
└────────┬────────┘
         │
         ▼ [CB: "diff_medium"]
┌─────────────────┐
│  COUNT_STATE    │
│ Savol soni      │  "Nechta savol kerak?"
│ 5, 10, 15, 20  │
└────────┬────────┘
         │
         ▼ [CB: "count_10"]
┌─────────────────┐
│  SUBJECT_STATE   │
│ Fan tanlash     │  "Qaysi fan bo'yicha?"
│ Mat/Gebr/Mantiq │
└────────┬────────┘
         │
         ▼ [CB: "subj_math"]
┌─────────────────┐
│  TOPIC_STATE    │
│ Mavzu tanlash   │  "Mavzu tanlang (ixtiyoriy)"
│ (O'tkazib yubor)│
└────────┬────────┘
         │
         ▼ [CB: "topic_"] OR [CB: "skip_topic"]
┌─────────────────┐
│  GENERATING...   │
│ ⏳ Kutilmoqda   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TestBuilder.build_test()                            │
│                                                                         │
│  1. Session yaratish (uniqueness tracking)                              │
│  2. Savollarni generatsiya qilish                                       │
│  3. Validatsiya qilish                                                 │
│  4. PDF yaratish (Test.pdf)                                            │
│  5. Javoblar PDF yaratish (Javoblar.pdf)                               │
│  6. Javoblarni shakllantirish                                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────┐
│   COMPLETE      │
│ Natijani yuborish│
│                 │
│ 📄 Test.pdf     │  ← 2 soniya kutish
│ 📄 Javoblar.pdf │
│                 │
│ [Shikoyat] tugmasi
└─────────────────┘
```

---

## Konfiguratsiya

### Bot Sozlamalari

```python
# config/settings.py

BOT_CONFIG = {
    "token": os.getenv("BOT_TOKEN"),
    "admin_ids": [123456789],  # Admin Telegram ID lar
    "appeal_chat_id": None,    # Shikoyatlar yuboriladigan chat
}

TEST_CONFIG = {
    "max_questions": 20,
    "default_timeout": 300,    # 5 daqiqa
    "pdf_page_size": "A4",
    "pdf_margin_mm": 15,
    "question_spacing_mm": 20,
}

TOPIC_CONFIG = {
    "grades": list(range(1, 12)),
    "difficulties": ["oson", "o'rta", "qiyin"],
    "subjects": ["matematika", "algebra", "geometriya", "mantiq", "boshqotirma"],
}

PUZZLE_CONFIG = {
    "enable_hybrid": True,
    "enable_variations": True,
    "max_render_attempts": 3,
    "cache_ttl_seconds": 3600,
}
```

### Environment Variables

```bash
# .env.example
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=123456789,987654321
APPEAL_CHAT_ID=-1001234567890
DATABASE_URL=sqlite:///bot.db
LOG_LEVEL=INFO
```

---

## Kerakli Kutubxonalar

```txt
# requirements.txt

# Core
aiogram==3.4.1           # Telegram bot framework
python-dotenv==1.0.0     # Environment variables

# Rendering
matplotlib==3.8.2        # Geometriya va puzzle chizish
numpy==1.26.2            # Matplotlib uchun

# PDF
reportlab==4.0.7         # PDF yaratish

# Utils
Pillow==10.1.0          # Image processing
aiofiles==23.2.1         # Async file operations

# Caching
cachetools==5.3.2        # LRU cache
diskcache==5.6.3         # Disk-based cache

# Logging
logging==standard        # Built-in
```

---

## Foydalanish Qo'llanmasi

### Bot Buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni boshlash |
| `/test` | Yangi test yaratish |
| `/help` | Yordam |
| `/admin` | Admin panel (faqat adminlar uchun) |

### Test Yaratish Misol

```
1. /test buyrug'ini bosing
2. Sinfni tanlang: 5-sinf
3. Qiyinlikni tanlang: O'rta
4. Savollar sonini tanlang: 10 ta
5. Fanni tanlang: Matematika
6. Mavzuni tanlang: Sonlar (yoki o'tkazib yuboring)
7. Natijani kuting...
8. PDF larni yuklab oling!
```

---

## Development Instructions

### Loyihani ishga tushirish

```bash
# 1. Reponi clone qilish
git clone <repo_url>
cd AI_MATH

# 2. Virtual environment yaratish
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 4. .env faylini yaratish
cp .env.example .env
# .env fayliga BOT_TOKEN ni qo'shing

# 5. Botni ishga tushirish
python main.py
```

### Sinovdan o'tkazish

```bash
# Barcha sinovlarni ishga tushirish
pytest

# Faqat puzzle engine sini
pytest tests/test_puzzle_engine.py

# Lint tekshirish
ruff check services/

# Type tekshirish
mypy services/
```

---

## Kelajak Rejalari

- [ ] Video/tajriba ssenariylarini qo'shish
- [ ] Interaktiv geometry chizish
- [ ] Student bilimini baholash tizimi
- [ ] So'zlararo va lingvistik puzzle lar
- [ ] Blockchain bilan sertifikatlash
- [ ] Mobile ilova

---

## Aloqa

- Loyiha muallifi: [Ahmadjon Zokirov]
- Telegram: [@ahmadjon_zokirov]
- Email: [ahmadjonzokirov54@gmail.com]

---

## Litsenziya

MIT License - Batafsil ma'lumot uchun LICENSE faylini ko'ring.
