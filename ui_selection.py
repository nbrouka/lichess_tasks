"""
Mixin for selected puzzles panel in Lichess Puzzle Viewer.
"""

import logging
import os
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from board_renderer import render_puzzle
from constants import t

LOG_PATH = Path(__file__).parent / "docx_export.log"
logger = logging.getLogger("docx_export")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_handler)


class PuzzleSelectionMixin:
    def _add_to_selected(self) -> None:
        if self.current_index is None or not self.filtered_puzzles:
            return
        puzzle = self.filtered_puzzles[self.current_index]

        if any(p.fen == puzzle.fen for p in self.selected_puzzles):
            return

        self.selected_puzzles.append(puzzle)

        square_size = 28
        thumb = render_puzzle(puzzle.fen, puzzle.moves, square_size=square_size, move_index=1, show_coordinates=False)
        photo = ImageTk.PhotoImage(thumb)

        row = len(self.selected_puzzles) - 1
        wrapper = tk.Frame(self.selected_inner, borderwidth=0, padx=0, pady=0)
        wrapper.grid(row=row, column=0, sticky="nw", padx=4, pady=4)

        img_label = tk.Label(wrapper, image=photo, borderwidth=0)
        img_label.image = photo
        img_label.pack(side=tk.TOP)

        del_btn = tk.Button(
            wrapper,
            text="✕",
            width=3,
            height=1,
            command=lambda p=puzzle, w=wrapper: self._remove_from_selected(p, w),
        )
        del_btn.pack(side=tk.TOP, fill=tk.X)

        self.selected_inner.grid_rowconfigure(row, weight=0, minsize=thumb.size[1] + 20)
        self.selected_inner.grid_columnconfigure(0, weight=0, minsize=thumb.size[0])
        self.selected_inner.update_idletasks()
        self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
        self._update_selected_title()

    def _remove_from_selected(self, puzzle, wrapper) -> None:
        if puzzle in self.selected_puzzles:
            self.selected_puzzles.remove(puzzle)
        wrapper.destroy()
        self.selected_inner.update_idletasks()
        self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
        self._update_selected_title()

    def _update_selected_title(self) -> None:
        self.selected_title_label.config(text=f"{t('selected_title')} ({len(self.selected_puzzles)})")

    def _on_selected_canvas_resize(self, event) -> None:
        self.selected_canvas.itemconfig(self._selected_window_id, width=event.width)

    def _create_sheets_dialog(self) -> None:
        logger.info("Open DOCX export dialog, selected puzzles count=%d", len(self.selected_puzzles))
        if not self.selected_puzzles:
            messagebox.showinfo(t("about_title"), "Нет выбранных задач.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Создать листы")
        dialog.geometry("420x220")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Тема:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        topic_entry = ttk.Entry(dialog)
        topic_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        topic_entry.focus_set()

        path_var = tk.StringVar()

        def choose_path():
            path = filedialog.asksaveasfilename(
                defaultextension=".docx",
                filetypes=[("DOCX files", "*.docx")],
                initialfile="puzzles.docx",
                parent=dialog,
            )
            if path:
                path_var.set(path)

        ttk.Label(dialog, text="Сохранить в:").pack(anchor=tk.W, padx=10)
        path_frame = ttk.Frame(dialog)
        path_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        path_entry = ttk.Entry(path_frame, textvariable=path_var, state="readonly")
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="...", width=3, command=choose_path).pack(side=tk.LEFT, padx=(5, 0))

        def save():
            topic = topic_entry.get().strip()
            path = path_var.get().strip()
            if not path:
                messagebox.showwarning("Внимание", "Выберите место для сохранения.", parent=dialog)
                return
            try:
                logger.info("Start DOCX generation path=%s topic=%s puzzles=%d", path, topic, len(self.selected_puzzles))
                self._create_sheets_docx(path, topic)
                logger.info("DOCX generated successfully path=%s", path)
                messagebox.showinfo("Готово", f"Файл сохранён: {path}", parent=dialog)
                dialog.destroy()
            except Exception as exc:
                logger.exception("DOCX generation failed path=%s error=%s", path, exc)
                messagebox.showerror("Ошибка", str(exc), parent=dialog)

        ttk.Button(dialog, text="Сохранить", command=save).pack(pady=(0, 10))

    def _create_sheets_docx(self, path: str, topic: str) -> None:
        from docx import Document
        from docx.shared import Cm, Emu, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        logger.info("DOCX export started path=%s topic=%s total_puzzles=%d", path, topic, len(self.selected_puzzles))
        doc = Document()
        section = doc.sections[0]
        section.top_margin = Cm(1.0)
        section.bottom_margin = Cm(1.0)
        section.left_margin = Cm(1.0)
        section.right_margin = Cm(1.0)

        puzzles = self.selected_puzzles

        def set_cell_border(cell, **kwargs):
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
                edge_data = kwargs.get(edge)
                if edge_data:
                    tag = 'w:{}'.format(edge)
                    element = OxmlElement(tag)
                    element.set(qn('w:val'), str(edge_data.get('val', 'nil')))
                    element.set(qn('w:sz'), str(edge_data.get('sz', 0)))
                    element.set(qn('w:space'), '0')
                    element.set(qn('w:color'), str(edge_data.get('color', 'auto')))
                    tcBorders.append(element)
            tcPr.append(tcBorders)

        def set_row_height(row, height_twips):
            tr = row._tr
            trPr = tr.get_or_add_trPr()
            trHeight = OxmlElement('w:trHeight')
            trHeight.set(qn('w:val'), str(height_twips))
            trHeight.set(qn('w:hRule'), 'atLeast')
            trPr.append(trHeight)

        def set_cell_margins(cell, top=20, bottom=20, left=20, right=20):
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcMar = OxmlElement('w:tcMar')
            for edge, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
                elem = OxmlElement('w:{}'.format(edge))
                elem.set(qn('w:w'), str(val))
                elem.set(qn('w:type'), 'dxa')
                tcMar.append(elem)
            tcPr.append(tcMar)

        temp_files = []
        try:
            for page_idx in range(0, len(puzzles), 12):
                page_puzzles = puzzles[page_idx:page_idx + 12]
                sheet_num = page_idx // 12 + 1
                logger.info("Processing page %d puzzles=%d", sheet_num, len(page_puzzles))

                if page_idx > 0:
                    doc.add_page_break()

                header_table = doc.add_table(rows=1, cols=2)
                header_table.autofit = False
                header_table.columns[0].width = Cm(3.5)
                header_table.columns[1].width = Cm(15)

                cell_left = header_table.cell(0, 0)
                cell_left.text = f"Лист {sheet_num}"
                cell_left.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                cell_left.paragraphs[0].paragraph_format.space_after = Pt(0)

                cell_center = header_table.cell(0, 1)
                cell_center.text = topic
                cell_center.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell_center.paragraphs[0].paragraph_format.space_after = Pt(0)

                for row in header_table.rows:
                    for cell in row.cells:
                        set_cell_border(cell, top={"val": "nil", "sz": 0}, bottom={"val": "nil", "sz": 0}, left={"val": "nil", "sz": 0}, right={"val": "nil", "sz": 0})

                table = doc.add_table(rows=4, cols=3)
                table.autofit = False
                table.allow_autofit = False
                table.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for col in table.columns:
                    col.width = Cm(6.33)

                for row in table.rows:
                    set_row_height(row, 2600)
                    for cell in row.cells:
                        set_cell_margins(cell, top=0, bottom=10, left=0, right=0)
                        set_cell_border(cell, top={"val": "nil", "sz": 0}, bottom={"val": "nil", "sz": 0}, left={"val": "nil", "sz": 0}, right={"val": "nil", "sz": 0})

                for i, puzzle in enumerate(page_puzzles):
                    row_idx = i // 3
                    col_idx = i % 3
                    cell = table.cell(row_idx, col_idx)

                    global_idx = page_idx + i + 1
                    logger.debug("Rendering puzzle %d/%d puzzle_id=%s", global_idx, len(puzzles), puzzle.puzzle_id)
                    img = render_puzzle(puzzle.fen, puzzle.moves, square_size=28, move_index=1, show_coordinates=False)
                    pixels = img.load()
                    original_pixel = pixels[0, 0]
                    pixels[0, 0] = (
                        original_pixel[0],
                        original_pixel[1],
                        (original_pixel[2] + global_idx) % 256,
                    )
                    fd, img_path = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    img.save(img_path)
                    temp_files.append(img_path)
                    logger.debug("Saved temporary image %s size=%s", img_path, img.size)

                    p0 = cell.paragraphs[0]
                    p0.paragraph_format.space_after = Pt(0)
                    run = p0.add_run()
                    run.add_picture(img_path, width=Emu(2000000))
                    run.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    run.font.size = Pt(9)
                    run.font.name = 'Cambria'

                    p = cell.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(4)
                    p.paragraph_format.line_spacing = Pt(6)
                    color_text = "Ход белых" if puzzle.color == "w" else "Ход черных"
                    p.add_run(f"№{global_idx}. {color_text}")

            logger.info("Saving document path=%s", path)
            doc.save(path)
            logger.info("DOCX saved successfully path=%s", path)
        finally:
            for p in temp_files:
                try:
                    os.unlink(p)
                except OSError:
                    pass
