"""
services/puzzle_pdf_structure.py — PDF STRUCTURE GENERATOR

Takes GeneratedPuzzle objects and creates properly structured PDF content.
Follows: Template → Parameters → Validation → Uniqueness → Render Spec → PDF pipeline.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class PDFLayoutType(Enum):
    VERTICAL_ARITHMETIC = "vertical_arithmetic"
    HORIZONTAL_FLOW = "horizontal_flow"
    GRID_LAYOUT = "grid_layout"
    CHAIN_LAYOUT = "chain_layout"
    REBUS_LAYOUT = "rebus_layout"
    HYBRID_LAYOUT = "hybrid_layout"


@dataclass
class PDFQuestionBlock:
    """Single question block for PDF"""
    question_number: int
    question_text: str
    puzzle_data: Dict
    image_bytes: Optional[bytes] = None
    options: Optional[Dict[str, str]] = None
    has_image: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "question_number": self.question_number,
            "question_text": self.question_text,
            "puzzle_data": self.puzzle_data,
            "has_image": self.has_image,
            "options": self.options,
        }


@dataclass
class PDFLayoutRules:
    """Layout rules for PDF generation"""
    page_width_mm: float = 210.0
    page_height_mm: float = 297.0
    margin_left_mm: float = 20.0
    margin_right_mm: float = 15.0
    margin_top_mm: float = 20.0
    margin_bottom_mm: float = 15.0
    
    content_width_mm: float = 175.0
    content_height_mm: float = 262.0
    
    header_height_mm: float = 30.0
    footer_height_mm: float = 15.0
    
    question_spacing_mm: float = 15.0
    option_spacing_mm: float = 6.0
    line_spacing_pt: float = 14.0
    
    font_sizes: Dict[str, float] = field(default_factory=lambda: {
        "title": 16,
        "header": 14,
        "question": 12,
        "body": 11,
        "option": 10,
        "small": 9,
    })
    
    def get_content_width_pt(self) -> float:
        return self.content_width_mm * 2.83465
    
    def get_content_height_pt(self) -> float:
        return self.content_height_mm * 2.83465


@dataclass
class PDFTestStructure:
    """Complete test structure for PDF generation"""
    test_id: str
    subject: str
    grade: int
    difficulty: str
    teacher_name: str = ""
    time_limit: int = 0
    
    questions: List[PDFQuestionBlock] = field(default_factory=list)
    
    header_config: Dict = field(default_factory=dict)
    footer_config: Dict = field(default_factory=dict)
    pagination_config: Dict = field(default_factory=dict)
    
    layout_rules: PDFLayoutRules = field(default_factory=PDFLayoutRules)
    
    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "subject": self.subject,
            "grade": self.grade,
            "difficulty": self.difficulty,
            "question_count": len(self.questions),
            "questions": [q.to_dict() for q in self.questions],
        }


class PuzzleToPDFConverter:
    """
    Convert GeneratedPuzzle objects to PDF-ready structures.
    
    Pipeline:
    1. Parse puzzle type and structure
    2. Apply layout rules
    3. Position elements
    4. Add pagination
    5. Generate PDFQuestionBlocks
    """
    
    def __init__(self, layout_rules: Optional[PDFLayoutRules] = None):
        self.layout_rules = layout_rules or PDFLayoutRules()
        self._setup_layout_mappings()
    
    def _setup_layout_mappings(self):
        """Setup puzzle type to PDF layout mapping"""
        self.layout_mapping = {
            "vertical_arithmetic": PDFLayoutType.VERTICAL_ARITHMETIC,
            "rebus": PDFLayoutType.REBUS_LAYOUT,
            "grid_puzzle": PDFLayoutType.GRID_LAYOUT,
            "flow_diagram": PDFLayoutType.HORIZONTAL_FLOW,
            "chain_operations": PDFLayoutType.CHAIN_LAYOUT,
            "hybrid": PDFLayoutType.HYBRID_LAYOUT,
        }
    
    def convert(self, puzzle) -> PDFQuestionBlock:
        """Convert a GeneratedPuzzle to PDFQuestionBlock"""
        from services.puzzle_engine import GeneratedPuzzle
        
        if isinstance(puzzle, GeneratedPuzzle):
            return self._convert_generated_puzzle(puzzle)
        
        return self._convert_dict_puzzle(puzzle)
    
    def _convert_generated_puzzle(self, puzzle) -> PDFQuestionBlock:
        """Convert GeneratedPuzzle to PDFQuestionBlock"""
        layout_type = self.layout_mapping.get(
            puzzle.template_type.value,
            PDFLayoutType.REBUS_LAYOUT
        )
        
        question_text = self._build_question_text(puzzle, layout_type)
        puzzle_data = self._build_puzzle_data(puzzle, layout_type)
        options = self._generate_options(puzzle)
        
        return PDFQuestionBlock(
            question_number=0,
            question_text=question_text,
            puzzle_data=puzzle_data,
            options=options,
            image_bytes=puzzle.render_spec if hasattr(puzzle, 'render_spec') and puzzle.render_spec else None,
            has_image=bool(puzzle.render_spec)
        )
    
    def _convert_dict_puzzle(self, puzzle_dict: Dict) -> PDFQuestionBlock:
        """Convert dictionary puzzle to PDFQuestionBlock"""
        return PDFQuestionBlock(
            question_number=puzzle_dict.get("number", 0),
            question_text=puzzle_dict.get("question", "Savol"),
            puzzle_data=puzzle_dict.get("puzzle_data", {}),
            options=puzzle_dict.get("options"),
            image_bytes=puzzle_dict.get("image_bytes"),
            has_image=puzzle_dict.get("has_image", False)
        )
    
    def _build_question_text(self, puzzle, layout_type: PDFLayoutType) -> str:
        """Build appropriate question text based on layout type"""
        template_id = puzzle.template_id
        
        templates = {
            "addition_2digit": "Hisoblang:",
            "subtraction_2digit": "Hisoblang:",
            "multiplication_2x1": "Ko'paytiring:",
            "division_remainder": "Bo'ling:",
            "magic_square_3x3": "Jadvalni to'ldiring:",
            "row_col_sum": "Noma'lum sonni toping:",
            "single_operation": "Natija nechiga teng:",
            "double_operation": "Oxirgi natijani toping:",
            "three_step": "Zanjirdagi oxirgi sonni toping:",
            "four_step": "Zanjirdagi natijani hisoblang:",
            "letter_addition": "Harflar o'rniga qaysi sonlar turibdi:",
            "symbol_equation": "Belgi qiymatlarini toping:",
        }
        
        return templates.get(template_id, "Savolni yeching:")
    
    def _build_puzzle_data(self, puzzle, layout_type: PDFLayoutType) -> Dict:
        """Build puzzle data structure for PDF"""
        data = {
            "layout_type": layout_type.value,
            "structure": puzzle.structure,
            "equations": puzzle.equations,
            "render_spec": puzzle.render_spec.to_dict() if puzzle.render_spec else {},
            "parameters": puzzle.parameters.to_dict(),
        }
        
        if puzzle.render_spec:
            data["figure_size"] = puzzle.render_spec.figure_size
            data["element_positions"] = puzzle.render_spec.element_positions
        
        return data
    
    def _generate_options(self, puzzle) -> Dict[str, str]:
        """Generate multiple choice options"""
        correct_answer = puzzle.answer
        options = {}
        
        if isinstance(correct_answer, (int, float)):
            options["A"] = str(correct_answer)
            
            distractors = self._generate_distractors(correct_answer)
            for i, d in enumerate(distractors[:3]):
                options[chr(66 + i)] = str(d)
            
            while len(options) < 4:
                options[chr(64 + len(options) + 1)] = "Boshqa"
        else:
            options = {"A": str(correct_answer), "B": "Boshqa javob", "C": "Yana javob", "D": "To'g'ri emas"}
        
        return options
    
    def _generate_distractors(self, correct: int) -> List[int]:
        """Generate plausible wrong answers"""
        distractors = []
        
        if correct >= 10:
            distractors.append(correct + 5)
            distractors.append(correct - 5)
            distractors.append(correct + 10)
        else:
            distractors.append(correct + 1)
            distractors.append(correct + 2)
            distractors.append(max(1, correct - 1))
        
        return [d for d in distractors if d != correct and d > 0]
    
    def convert_batch(self, puzzles: List) -> List[PDFQuestionBlock]:
        """Convert multiple puzzles to PDF blocks"""
        blocks = []
        
        for i, puzzle in enumerate(puzzles):
            block = self.convert(puzzle)
            block.question_number = i + 1
            blocks.append(block)
        
        return blocks


class TestStructureGenerator:
    """
    Generate complete test structure from puzzles.
    
    Creates:
    - Header configuration
    - Question blocks with proper layout
    - Footer with pagination
    - Answer key structure
    """
    
    def __init__(self):
        self.converter = PuzzleToPDFConverter()
        self.layout_rules = PDFLayoutRules()
    
    def generate_test_structure(
        self,
        puzzles: List,
        subject: str,
        grade: int,
        difficulty: str,
        teacher_name: str = "",
        time_limit: int = 0,
        include_images: bool = True
    ) -> PDFTestStructure:
        """Generate complete test structure"""
        import hashlib
        from datetime import datetime
        
        test_id = hashlib.md5(
            f"{subject}_{grade}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        
        questions = self.converter.convert_batch(puzzles)
        
        header_config = self._generate_header_config(subject, grade, difficulty, teacher_name, time_limit)
        footer_config = self._generate_footer_config()
        pagination_config = self._generate_pagination_config()
        
        return PDFTestStructure(
            test_id=test_id,
            subject=subject,
            grade=grade,
            difficulty=difficulty,
            teacher_name=teacher_name,
            time_limit=time_limit,
            questions=questions,
            header_config=header_config,
            footer_config=footer_config,
            pagination_config=pagination_config,
            layout_rules=self.layout_rules
        )
    
    def _generate_header_config(self, subject: str, grade: int, difficulty: str, teacher: str, time: int) -> Dict:
        """Generate header configuration"""
        difficulty_text = {
            "oson": "Oson",
            "o'rta": "O'rta",
            "qiyin": "Qiyin"
        }
        
        return {
            "title": f"{subject.title()} - {grade}-sinf",
            "subtitle": f"Qiyinlik: {difficulty_text.get(difficulty, difficulty)}",
            "teacher": f"O'qituvchi: {teacher}" if teacher else "",
            "time": f"Vaqt: {time} daqiqa" if time > 0 else "",
            "date": "",
            "logo": None,
        }
    
    def _generate_footer_config(self) -> Dict:
        """Generate footer configuration"""
        return {
            "show_page_number": True,
            "show_total_pages": True,
            "format": "Bet {current} / {total}",
            "position": "bottom_center",
        }
    
    def _generate_pagination_config(self) -> Dict:
        """Generate pagination rules"""
        return {
            "questions_per_page": 5,
            "allow_break_after_question": True,
            "keep_grouped": ["grid", "chain"],
            "page_number_format": "{current}/{total}",
        }
    
    def generate_answer_key(self, test_structure: PDFTestStructure) -> Dict:
        """Generate answer key from test structure"""
        answers = []
        
        for q in test_structure.questions:
            correct_option = "A"
            correct_value = ""
            
            if q.options:
                for opt, val in q.options.items():
                    if not val.startswith("Boshqa") and not val.startswith("To'g'ri") and not val.startswith("Yana"):
                        correct_option = opt
                        correct_value = val
                        break
            
            answers.append({
                "number": q.question_number,
                "correct_option": correct_option,
                "correct_value": correct_value,
            })
        
        return {
            "test_id": test_structure.test_id,
            "subject": test_structure.subject,
            "grade": test_structure.grade,
            "answers": answers,
            "total_questions": len(answers),
        }


class PDFRenderer:
    """
    Render PDFTestStructure to actual PDF using reportlab.
    
    Responsibilities:
    - Draw header
    - Draw question blocks
    - Handle pagination
    - Insert images
    - Draw footer
    """
    
    def __init__(self, layout_rules: Optional[PDFLayoutRules] = None):
        self.layout_rules = layout_rules or PDFLayoutRules()
    
    def render(self, test_structure: PDFTestStructure) -> bytes:
        """Render test structure to PDF bytes"""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        buffer = BytesIO()
        page_width, page_height = A4
        
        c = canvas.Canvas(buffer, pagesize=A4)
        
        self._draw_header(c, test_structure, page_width, page_height)
        
        y_position = page_height - self.layout_rules.margin_top_mm * mm - self.layout_rules.header_height_mm * mm
        
        for i, question in enumerate(test_structure.questions):
            self._draw_question(c, question, page_width, y_position)
            
            y_position -= self._calculate_question_height(question)
            
            if y_position < self.layout_rules.margin_bottom_mm * mm + 20 * mm:
                self._draw_footer(c, test_structure, page_width, page_height, c._pageNumber)
                c.showPage()
                y_position = page_height - self.layout_rules.margin_top_mm * mm - self.layout_rules.header_height_mm * mm
        
        self._draw_footer(c, test_structure, page_width, page_height, c._pageNumber)
        
        c.save()
        buffer.seek(0)
        return buffer.read()
    
    def _draw_header(self, c, test_structure: PDFTestStructure, page_width: float, page_height: float):
        """Draw test header"""
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        
        header = test_structure.header_config
        
        margin = self.layout_rules.margin_left_mm * mm
        
        y = page_height - self.layout_rules.margin_top_mm * mm - 5 * mm
        
        c.setFont("Helvetica-Bold", self.layout_rules.font_sizes["title"])
        c.drawString(margin, y, header.get("title", ""))
        
        y -= 8 * mm
        c.setFont("Helvetica", self.layout_rules.font_sizes["header"])
        c.drawString(margin, y, header.get("subtitle", ""))
        
        if header.get("teacher"):
            y -= 5 * mm
            c.setFont("Helvetica", self.layout_rules.font_sizes["small"])
            c.drawString(margin, y, header.get("teacher", ""))
        
        if header.get("time"):
            y -= 4 * mm
            c.drawString(margin, y, header.get("time", ""))
        
        y -= 3 * mm
        c.setStrokeColor(colors.black)
        c.line(margin, y, page_width - self.layout_rules.margin_right_mm * mm, y)
    
    def _draw_question(self, c, question: PDFQuestionBlock, page_width: float, y_position: float):
        """Draw single question block"""
        from reportlab.lib.units import mm
        from reportlab.platypus import Image as RLImage
        from io import BytesIO
        
        margin = self.layout_rules.margin_left_mm * mm
        content_width = self.layout_rules.get_content_width_pt()
        
        y = y_position
        
        c.setFont("Helvetica-Bold", self.layout_rules.font_sizes["question"])
        c.drawString(margin, y, f"{question.question_number}. {question.question_text}")
        
        y -= 8 * mm
        
        if question.image_bytes and question.has_image:
            try:
                img = RLImage(BytesIO(question.image_bytes), width=60*mm, height=45*mm)
                img.drawOn(c, margin, y - 40*mm)
                y -= 50 * mm
            except Exception as e:
                pass
        
        puzzle_data = question.puzzle_data
        structure = puzzle_data.get("structure", "")
        
        c.setFont("Courier", self.layout_rules.font_sizes["body"])
        
        if structure:
            lines = structure.strip().split("\n")
            for line in lines:
                c.drawString(margin + 20, y, line)
                y -= 4 * mm
        
        y -= 5 * mm
        
        if question.options:
            c.setFont("Helvetica", self.layout_rules.font_sizes["option"])
            for opt, val in question.options.items():
                c.drawString(margin + 20, y, f"{opt}) {val}")
                y -= self.layout_rules.option_spacing_mm * mm
        
        y -= self.layout_rules.question_spacing_mm * mm
    
    def _calculate_question_height(self, question: PDFQuestionBlock) -> float:
        """Calculate height needed for question"""
        from reportlab.lib.units import mm
        
        base_height = 25
        structure_lines = len(question.puzzle_data.get("structure", "").split("\n"))
        option_count = len(question.options) if question.options else 0
        
        image_height = 50 if question.image_bytes and question.has_image else 0
        
        return (base_height + structure_lines * 4 + option_count * 6 + 15 + image_height) * mm
    
    def _draw_footer(self, c, test_structure: PDFTestStructure, page_width: float, page_height: float, page_num: int):
        """Draw page footer"""
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        
        footer = test_structure.footer_config
        
        y = self.layout_rules.margin_bottom_mm * mm + 5 * mm
        
        c.setFont("Helvetica", self.layout_rules.font_sizes["small"])
        c.setFillColor(colors.gray)
        
        if footer.get("show_page_number"):
            format_str = footer.get("format", "Bet {current}")
            text = format_str.replace("{current}", str(page_num)).replace("{total}", "?")
            c.drawCentredString(page_width / 2, y, text)
        
        c.setFillColor(colors.black)


puzzle_to_pdf_converter = PuzzleToPDFConverter()
test_structure_generator = TestStructureGenerator()
pdf_renderer = PDFRenderer()
