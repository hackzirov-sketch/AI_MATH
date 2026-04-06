"""
services/pdf_generator.py — SENIOR PDF LAYOUT ENGINE

A4-ready, professional quiz PDF generation system.

Features:
- Automatic page breaks
- Consistent spacing and margins
- Image scaling and centering
- Text wrapping
- Professional layout
"""

import io
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether, HRFlowable
)
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from services.cache_manager import cache_manager
from services.observability_runtime import log_event, observe_pdf_size, set_memory_usage
from services.cache_manager import get_process_memory_usage_mb

logger = logging.getLogger(__name__)

A4_WIDTH, A4_HEIGHT = A4
MARGIN_LEFT = 2 * cm
MARGIN_RIGHT = 2 * cm
MARGIN_TOP = 2.5 * cm
MARGIN_BOTTOM = 2 * cm

CONTENT_WIDTH = A4_WIDTH - MARGIN_LEFT - MARGIN_RIGHT


class PDFGenerator:
    """
    Professional PDF Generator for Quiz Platform.
    
    Layout Strategy:
    - A4 page size with consistent margins
    - Header on first page only
    - Automatic page break handling
    - Questions kept together with options
    - Images centered and scaled appropriately
    - Answer sheet formatted separately
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or str(cache_manager.pdf_temp_dir)
        os.makedirs(self.temp_dir, exist_ok=True)
        self._styles = self._create_styles()

    def _compressed_canvas(self, *args, **kwargs):
        kwargs.setdefault("pageCompression", 1)
        return canvas.Canvas(*args, **kwargs)
    
    def _create_styles(self) -> Dict:
        """Create consistent paragraph styles"""
        styles = getSampleStyleSheet()
        
        self._styles = {
            'header': ParagraphStyle(
                'Header',
                fontName='Helvetica-Bold',
                fontSize=18,
                textColor=colors.HexColor('#1A237E'),
                alignment=TA_CENTER,
                spaceAfter=8
            ),
            'subheader': ParagraphStyle(
                'SubHeader',
                fontName='Helvetica',
                fontSize=12,
                textColor=colors.HexColor('#3949AB'),
                alignment=TA_CENTER,
                spaceAfter=6
            ),
            'meta': ParagraphStyle(
                'Meta',
                fontName='Helvetica',
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                alignment=TA_LEFT,
                spaceAfter=4
            ),
            'question_meta': ParagraphStyle(
                'QuestionMeta',
                fontName='Helvetica',
                fontSize=8,
                textColor=colors.HexColor('#546E7A'),
                alignment=TA_LEFT,
                spaceAfter=4,
                leading=10
            ),
            'question': ParagraphStyle(
                'Question',
                fontName='Helvetica-Bold',
                fontSize=11,
                textColor=colors.HexColor('#1565C0'),
                spaceBefore=12,
                spaceAfter=8,
                leading=14
            ),
            'option': ParagraphStyle(
                'Option',
                fontName='Helvetica',
                fontSize=10,
                textColor=colors.black,
                leftIndent=20,
                spaceAfter=4,
                leading=12
            ),
            'answer_title': ParagraphStyle(
                'AnswerTitle',
                fontName='Helvetica-Bold',
                fontSize=20,
                textColor=colors.HexColor('#1B5E20'),
                alignment=TA_CENTER,
                spaceAfter=15
            ),
            'answer_item': ParagraphStyle(
                'AnswerItem',
                fontName='Helvetica',
                fontSize=10,
                textColor=colors.black,
                spaceAfter=4
            ),
            'footer': ParagraphStyle(
                'Footer',
                fontName='Helvetica',
                fontSize=8,
                textColor=colors.gray,
                alignment=TA_CENTER
            )
        }
        
        return self._styles
    
    def generate_test_pdf(
        self, 
        grade: int, 
        difficulty: str, 
        subject: str,
        questions: List[Dict],
        teacher_name: str = "",
        time_limit: int = 0,
        requested_topic: str = "",
    ) -> str:
        """
        Generate professional A4 test PDF.
        
        Layout:
        - Header with title, difficulty, date
        - Questions with numbered format
        - Options in 2-column layout
        - Images properly scaled and centered
        - Page numbers in footer
        """
        filepath = str(cache_manager.reserve_file_path("pdf_temp", f"test_{grade}_", ".pdf"))
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM
        )
        
        elements = []
        
        elements.extend(self._build_header(grade, difficulty, subject, teacher_name, time_limit, requested_topic))
        
        for i, q in enumerate(questions):
            question_elements = self._build_question_block(i + 1, q)
            elements.extend(question_elements)
        
        doc.build(elements, canvasmaker=self._compressed_canvas)
        size_bytes = os.path.getsize(filepath)
        observe_pdf_size("test", size_bytes)
        set_memory_usage("pdf_test", get_process_memory_usage_mb())
        log_event("pdf_built", kind="test", path=filepath, size_bytes=size_bytes, question_count=len(questions))
        return filepath
    
    def _build_header(
        self, 
        grade: int, 
        difficulty: str, 
        subject: str,
        teacher_name: str,
        time_limit: int,
        requested_topic: str = "",
    ) -> List:
        """Build document header"""
        elements = []
        
        elements.append(Paragraph(
            f"{grade}-SINF {subject.upper()}",
            self._styles['header']
        ))
        
        elements.append(Paragraph(
            f"{self._get_difficulty_text(difficulty).upper()} DARSLAR UCHUN TEST",
            self._styles['subheader']
        ))
        
        meta_parts = []
        if teacher_name:
            meta_parts.append(f"O'qituvchi: {teacher_name}")
        if requested_topic:
            meta_parts.append(f"Mavzu: {requested_topic}")
        else:
            meta_parts.append("Mavzu: Avtomatik tanlangan")
        meta_parts.append(f"Sana: {datetime.now().strftime('%d.%m.%Y')}")
        if time_limit > 0:
            meta_parts.append(f"Vaqt: {time_limit} daqiqa")
        
        for meta in meta_parts:
            elements.append(Paragraph(meta, self._styles['meta']))
        
        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(
            width="100%", 
            thickness=2, 
            color=colors.HexColor('#3949AB'),
            spaceAfter=15
        ))
        
        return elements
    
    def _build_question_block(self, num: int, question: Dict) -> List:
        """Build a question block with text, options, and optional image"""
        elements = []
        
        question_text = question.get('question', question.get('question_text', ''))
        elements.append(Paragraph(
            f"<b>{num}.</b> {question_text}",
            self._styles['question']
        ))

        meta_parts = []
        if question.get('topic'):
            meta_parts.append(f"Mavzu: {question['topic']}")
        if question.get('source'):
            meta_parts.append(f"Manba: {question['source']}")
        if meta_parts:
            elements.append(Paragraph(" | ".join(meta_parts), self._styles['question_meta']))
        
        if 'image_bytes' in question and question['image_bytes']:
            img_elements = self._build_image(question['image_bytes'], CONTENT_WIDTH * 0.7)
            elements.extend(img_elements)
        
        options = question.get('options', {})
        if options:
            elements.extend(self._build_options(options))
        
        elements.append(Spacer(1, 10))
        
        return elements
    
    def _build_options(self, options: Dict) -> List:
        """Build options in 2-column table layout"""
        elements = []
        
        option_items = []
        for label, value in options.items():
            option_items.append(Paragraph(
                f"<b>{label})</b> {value}",
                self._styles['option']
            ))
        
        if len(option_items) <= 2:
            for opt in option_items:
                elements.append(opt)
        else:
            table_data = []
            for idx in range(0, len(option_items), 2):
                row = option_items[idx:idx + 2]
                if len(row) < 2:
                    row.append(Spacer(1, 1))
                table_data.append(row)
            col_width = CONTENT_WIDTH / 2 - 10
            
            table = Table(table_data, colWidths=[col_width, col_width])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _build_image(self, image_bytes: bytes, max_width: float) -> List:
        """Build properly scaled and centered image"""
        elements = []
        
        try:
            img_reader = ImageReader(io.BytesIO(image_bytes))
            original_width, original_height = img_reader.getSize()
            
            aspect = original_height / original_width
            display_width = min(max_width, original_width)
            display_height = display_width * aspect
            
            if display_height > 6 * cm:
                display_height = 6 * cm
                display_width = display_height / aspect
            
            img = Image(img_reader, width=display_width, height=display_height)
            img.hAlign = 'CENTER'
            
            elements.append(Spacer(1, 5))
            elements.append(img)
            elements.append(Spacer(1, 5))
            
        except Exception as e:
            elements.append(Paragraph(
                f"[Rasm mavjud emas]",
                self._styles['option']
            ))
        
        return elements
    
    def _get_difficulty_text(self, difficulty: str) -> str:
        texts = {
            "oson": "Oson",
            "o'rta": "O'rta",
            "qiyin": "Qiyin"
        }
        return texts.get(difficulty, difficulty)
    
    def generate_answers_pdf(
        self,
        grade: int,
        difficulty: str,
        subject: str,
        questions: List[Dict],
        requested_topic: str = "",
    ) -> str:
        """Generate answer sheet PDF"""
        filepath = str(cache_manager.reserve_file_path("pdf_temp", f"answers_{grade}_", ".pdf"))
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM
        )
        
        elements = []
        
        elements.append(Paragraph(
            f"{grade}-SINF {subject.upper()}",
            self._styles['answer_title']
        ))
        
        elements.append(Paragraph("JAVOBLAR", self._styles['answer_title']))
        if requested_topic:
            elements.append(Paragraph(f"Mavzu: {requested_topic}", self._styles['meta']))
        elements.append(Spacer(1, 20))
        
        answers_data = []
        row = []
        for i, q in enumerate(questions):
            answer_label = q.get('correct', q.get('correct_label', '?'))
            row.append(f"<b>{i + 1}. {answer_label}</b>")
            
            if len(row) == 4:
                answers_data.append(row)
                row = []
        
        if row:
            while len(row) < 4:
                row.append("")
            answers_data.append(row)
        
        col_width = (CONTENT_WIDTH - 30) / 4
        table = Table(answers_data, colWidths=[col_width] * 4)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2E7D32')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F5E9')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#A5D6A7')),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        elements.append(Paragraph(
            "<b>To'liq javoblar ro'yxati:</b>",
            self._styles['subheader']
        ))
        elements.append(Spacer(1, 10))
        
        for i, q in enumerate(questions):
            answer_label = q.get('correct', q.get('correct_label', '?'))
            answer_value = q.get('correct_value', q.get('answer', ''))
            
            elements.append(Paragraph(
                f"<b>{i + 1}.</b> {answer_label}) {answer_value}",
                self._styles['answer_item']
            ))
        
        doc.build(elements, canvasmaker=self._compressed_canvas)
        size_bytes = os.path.getsize(filepath)
        observe_pdf_size("answers", size_bytes)
        set_memory_usage("pdf_answers", get_process_memory_usage_mb())
        log_event("pdf_built", kind="answers", path=filepath, size_bytes=size_bytes, question_count=len(questions))
        return filepath
    
    def generate_batch_with_images(
        self,
        grade: int,
        difficulty: str,
        subject: str,
        questions: List[Dict],
        teacher_name: str = ""
    ) -> Tuple[str, List[Tuple[str, bytes]]]:
        """
        Generate test PDF with embedded images.
        Returns (pdf_path, image_files) tuple.
        """
        filepath = str(cache_manager.reserve_file_path("pdf_temp", f"test_{grade}_", ".pdf"))
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM
        )
        
        elements = []
        elements.extend(self._build_header(grade, difficulty, subject, teacher_name, 0, ""))
        
        image_refs = []
        
        for i, q in enumerate(questions):
            block = self._build_question_block(i + 1, q)
            elements.extend(block)
            
            if 'image_bytes' in q and q['image_bytes']:
                img_id = f"img_{i}"
                image_refs.append((img_id, q['image_bytes']))
        
        doc.build(elements, canvasmaker=self._compressed_canvas)
        
        return filepath, image_refs
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up old temp PDF files"""
        cache_manager.cleanup_directory("pdf_temp", ttl_seconds=max_age_hours * 3600)


pdf_generator = PDFGenerator()
