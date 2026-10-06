"""
PDF exporter for Lichess puzzles.
"""

import logging
import os
import tempfile

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm as _cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from board_renderer import render_puzzle
from constants import (
    PDF_MARGIN_CM,
    PDF_PUZZLES_PER_PAGE,
    PDF_COL_WIDTH_CM,
    PDF_ROW_HEIGHT_PT,
    PDF_THUMBNAIL_SQUARE_SIZE,
    current_player_color_name,
    PDF_TABLE_ROWS,
    PDF_TABLE_COLS,
    PDF_HEADER_LEFT_COL_WIDTH_CM,
    PDF_HEADER_RIGHT_COL_WIDTH_CM,
)

logger = logging.getLogger(__name__)

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", _FONT_PATH))
    _FONT_NAME = "DejaVuSans"
except Exception:
    _FONT_NAME = "Helvetica"


class PuzzlePdfExporter:
    """Exports selected puzzles to a PDF document."""

    def __init__(self, puzzles, topic: str) -> None:
        self.puzzles = puzzles
        self.topic = topic

    def export(self, path: str) -> None:
        logger.info("PDF export started path=%s topic=%s total_puzzles=%d", path, self.topic, len(self.puzzles))

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleCustom",
            parent=styles["Title"],
            fontName=_FONT_NAME,
            fontSize=18,
            leading=20,
            alignment=TA_RIGHT,
        )
        subtitle_style = ParagraphStyle(
            "SubtitleCustom",
            parent=styles["Normal"],
            fontName=_FONT_NAME,
            fontSize=12,
            leading=16,
            alignment=TA_LEFT,
        )
        caption_style = ParagraphStyle(
            "CaptionCustom",
            parent=styles["Normal"],
            fontName=_FONT_NAME,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
        )

        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            leftMargin=PDF_MARGIN_CM * _cm,
            rightMargin=PDF_MARGIN_CM * _cm,
            topMargin=PDF_MARGIN_CM * _cm,
            bottomMargin=PDF_MARGIN_CM * _cm,
        )

        story = []
        temp_files = []

        try:
            for page_idx in range(0, len(self.puzzles), PDF_PUZZLES_PER_PAGE):
                page_puzzles = self.puzzles[page_idx:page_idx + PDF_PUZZLES_PER_PAGE]
                sheet_num = page_idx // PDF_PUZZLES_PER_PAGE + 1

                if page_idx > 0:
                    story.append(PageBreak())

                header_data = [
                    [Paragraph(f"Лист {sheet_num}", subtitle_style), Paragraph(self.topic or "", title_style)],
                ]
                header_table = Table(header_data, colWidths=[PDF_HEADER_LEFT_COL_WIDTH_CM * _cm, PDF_HEADER_RIGHT_COL_WIDTH_CM * _cm])
                header_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(header_table)

                table_data = [["" for _ in range(PDF_TABLE_COLS)] for _ in range(PDF_TABLE_ROWS)]
                for i, puzzle in enumerate(page_puzzles):
                    row_idx = i // PDF_TABLE_COLS
                    col_idx = i % PDF_TABLE_COLS
                    global_idx = page_idx + i + 1
                    logger.debug("Rendering puzzle %d/%d puzzle_id=%s", global_idx, len(self.puzzles), puzzle.puzzle_id)

                    img = render_puzzle(puzzle.fen, puzzle.moves, square_size=PDF_THUMBNAIL_SQUARE_SIZE, move_index=1, show_coordinates=False)
                    fd, img_path = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    img.save(img_path)
                    temp_files.append(img_path)

                    image = Image(img_path)
                    color_text = current_player_color_name(puzzle.color)
                    caption = Paragraph(f"№{global_idx}. {color_text}", caption_style)
                    cell_content = [image, caption]
                    table_data[row_idx][col_idx] = cell_content

                col_widths = [PDF_COL_WIDTH_CM * _cm] * PDF_TABLE_COLS
                row_heights = [PDF_ROW_HEIGHT_PT] * len(table_data)
                table = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=0)
                table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(table)

            logger.info("Building PDF path=%s", path)
            doc.build(story)
            logger.info("PDF saved successfully path=%s", path)
        finally:
            for p in temp_files:
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def export_answers(self, path: str) -> None:
        """
        Creates a separate PDF with answers for all puzzles.
        """
        logger.info("PDF answers export started path=%s topic=%s total_puzzles=%d", path, self.topic, len(self.puzzles))

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleCustom",
            parent=styles["Title"],
            fontName=_FONT_NAME,
            fontSize=18,
            leading=20,
            alignment=TA_CENTER,
        )
        answer_style = ParagraphStyle(
            "AnswerCustom",
            parent=styles["Normal"],
            fontName=_FONT_NAME,
            fontSize=11,
            leading=16,
            alignment=TA_LEFT,
        )

        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            leftMargin=PDF_MARGIN_CM * _cm,
            rightMargin=PDF_MARGIN_CM * _cm,
            topMargin=PDF_MARGIN_CM * _cm,
            bottomMargin=PDF_MARGIN_CM * _cm,
        )

        story = []
        try:
            story.append(Paragraph("Ответы", title_style))
            story.append(Spacer(1, 0.5 * _cm))

            for idx, puzzle in enumerate(self.puzzles, 1):
                formatted_solution = self._format_pdf_solution(puzzle)
                color_text = current_player_color_name(puzzle.color)
                story.append(Paragraph(f"№{idx}. {color_text}: {formatted_solution}", answer_style))

            logger.info("Building PDF answers path=%s", path)
            doc.build(story)
            logger.info("PDF answers saved successfully path=%s", path)
        except Exception:
            logger.exception("Failed to build PDF answers path=%s", path)
            raise

    def export_with_answers(self, path: str) -> None:
        """
        Creates a PDF with puzzles and a following answers section.
        """
        self.export(path)
        answers_path = path.replace(".pdf", "_ответы.pdf")
        self.export_answers(answers_path)

    @staticmethod
    def _format_pdf_solution(puzzle) -> str:
        moves = puzzle.solution.split()
        if not moves:
            return ""

        is_black_first = puzzle.color == "w"
        parts = []
        move_number = 1
        i = 0

        if is_black_first:
            parts.append(f"{move_number}. ...{moves[i]}")
            i = 1
            move_number = 2

        while i < len(moves):
            if i + 1 < len(moves):
                parts.append(f"{move_number}.{moves[i]} {moves[i + 1]}")
                i += 2
            else:
                parts.append(f"{move_number}.{moves[i]}")
                i += 1
            move_number += 1

        return " ".join(parts)
