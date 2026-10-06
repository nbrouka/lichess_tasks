"""
Mixin for selected puzzles panel in Lichess Puzzle Viewer.
"""

import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from PIL import ImageTk

from board_renderer import render_puzzle
from constants import t, THUMBNAIL_SQUARE_SIZE, DOCX_DIALOG_GEOMETRY, current_player_color_name, DOCX_ANSWER_MARGIN_CM, DOCX_ANSWER_SPACE_AFTER_PT, DELETE_BUTTON_WIDTH, DELETE_BUTTON_HEIGHT
from database import Puzzle
from docx_exporter import PuzzleDocxExporter
from pdf_exporter import PuzzlePdfExporter
from docx import Document
from docx.shared import Cm, Pt

LOG_PATH = Path(__file__).parent / "docx_export.log"
logger = logging.getLogger("docx_export")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_handler)


class PuzzleSelectionMixin:
    def _add_to_selected(self) -> None:
        """
        Добавляет текущую задачу в панель выбранных.

        - Не добавляет дубликаты по FEN.
        - Создаёт миниатюру доски и кнопку удаления.
        - Обновляет scrollregion канваса, чтобы появилась прокрутка.
        """
        if self.current_index is None or not self.filtered_puzzles:
            return
        puzzle = self.filtered_puzzles[self.current_index]

        if any(p.fen == puzzle.fen for p in self.selected_puzzles):
            return

        self.selected_puzzles.append(puzzle)

        square_size = THUMBNAIL_SQUARE_SIZE
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
            width=DELETE_BUTTON_WIDTH,
            height=DELETE_BUTTON_HEIGHT,
            command=lambda p=puzzle, w=wrapper: self._remove_from_selected(p, w),
        )
        del_btn.pack(side=tk.TOP, fill=tk.X)

        self.selected_inner.grid_rowconfigure(row, weight=0, minsize=thumb.size[1] + 20)
        self.selected_inner.grid_columnconfigure(0, weight=0, minsize=thumb.size[0])
        self.selected_inner.update_idletasks()
        self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
        self._update_selected_title()

    def _update_selected_title(self) -> None:
        self.selected_title_label.config(text=f"{t('selected_title')} ({len(self.selected_puzzles)})")

    def _on_selected_canvas_resize(self, event: tk.Event) -> None:
        """
        Обновляет ширину внутреннего окна при изменении размера канваса.

        Нужно, чтобы скроллбар работал корректно при изменении размера окна.
        """
        self.selected_canvas.itemconfig(self._selected_window_id, width=event.width)

    def _create_sheets_dialog(self) -> None:
        """
        Открывает диалог экспорта выбранных задач в PDF.

        Пользователь вводит тему и выбирает путь для сохранения.
        После экспорта тема автоматически сохраняется в пользовательские темы БД.
        """
        logger.info("Open PDF export dialog, selected puzzles count=%d", len(self.selected_puzzles))
        if not self.selected_puzzles:
            messagebox.showinfo(t("about_title"), t("msg_no_selected_puzzles"))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Создать PDF")
        dialog.geometry(DOCX_DIALOG_GEOMETRY)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Тема:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        topic_entry = ttk.Entry(dialog)
        topic_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        topic_entry.focus_set()

        pdf_path_var = tk.StringVar()

        def choose_pdf_path():
            topic = topic_entry.get().strip()
            default_name = f"{topic}.pdf" if topic else "puzzles.pdf"
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=default_name,
                parent=dialog,
            )
            if path:
                pdf_path_var.set(path)

        ttk.Label(dialog, text="Сохранить PDF в:").pack(anchor=tk.W, padx=10)
        pdf_path_frame = ttk.Frame(dialog)
        pdf_path_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        pdf_path_entry = ttk.Entry(pdf_path_frame, textvariable=pdf_path_var, state="readonly")
        pdf_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(pdf_path_frame, text="...", width=3, command=choose_pdf_path).pack(side=tk.LEFT, padx=(5, 0))

        def save():
            topic = topic_entry.get().strip()
            pdf_path = pdf_path_var.get().strip()
            if not pdf_path:
                messagebox.showwarning("Внимание", "Выберите место для сохранения.", parent=dialog)
                return
            try:
                logger.info("Start PDF generation path=%s topic=%s puzzles=%d", pdf_path, topic, len(self.selected_puzzles))
                self._create_sheets_pdf(pdf_path, topic)
                logger.info("PDF generated successfully path=%s", pdf_path)
                messagebox.showinfo("Готово", f"Файл сохранён: {pdf_path}", parent=dialog)
                dialog.destroy()
                self._clear_selection()
            except Exception as exc:
                logger.exception("Generation failed path=%s error=%s", pdf_path, exc)
                messagebox.showerror("Ошибка", str(exc), parent=dialog)

        ttk.Button(dialog, text="Сохранить", command=save).pack(pady=(0, 10))

    def _remove_from_selected(self, puzzle: Puzzle, wrapper: tk.Frame) -> None:
        """
        Удаляет задачу из выбранных и разрушает соответствующий виджет.
        """
        if puzzle in self.selected_puzzles:
            self.selected_puzzles.remove(puzzle)
        wrapper.destroy()
        self.selected_inner.update_idletasks()
        self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
        self._update_selected_title()

    def _create_sheets_docx(self, path: str, topic: str) -> None:
        """
        Creates DOCX with puzzles and separate DOCX with answers.

        Also saves topic to user themes DB if specified.
        """
        puzzles = list(self.selected_puzzles)
        exporter = PuzzleDocxExporter(puzzles, topic)
        exporter.export(path)

        answers_path = path.replace(".docx", "_ответы.docx")
        self._create_answers_docx(answers_path, topic, puzzles)

        if topic:
            self._save_topic_to_db(topic)

    def _create_sheets_pdf(self, path: str, topic: str) -> None:
        puzzles = list(self.selected_puzzles)
        exporter = PuzzlePdfExporter(puzzles, topic)
        exporter.export_with_answers(path)

        if topic:
            self._save_topic_to_db(topic)

    def _create_answers_docx(self, path: str, topic: str, puzzles: list) -> None:
        """
        Создаёт DOCX с ответами для всех задач.

        В файле указывается номер задачи, цвет хода и форматированное решение.
        """
        logger.info("Creating answers DOCX path=%s puzzles=%d", path, len(puzzles))

        doc = Document()
        section = doc.sections[0]
        section.top_margin = Cm(DOCX_ANSWER_MARGIN_CM)
        section.bottom_margin = Cm(DOCX_ANSWER_MARGIN_CM)
        section.left_margin = Cm(DOCX_ANSWER_MARGIN_CM)
        section.right_margin = Cm(DOCX_ANSWER_MARGIN_CM)

        doc.add_paragraph(f"Тема: {topic}")

        for idx, puzzle in enumerate(puzzles, 1):
            formatted_solution = self._format_answers_solution(puzzle)
            color_text = current_player_color_name(puzzle.color)
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(DOCX_ANSWER_SPACE_AFTER_PT)
            p.add_run(f"№{idx}. {color_text}: {formatted_solution}")

        doc.save(path)

    def _save_topic_to_db(self, topic: str) -> None:
        """
        Сохраняет тему в пользовательские темы и связывает с выбранными задачами.
        """
        theme_id = self.db.get_or_create_user_theme(topic)
        puzzle_ids = [p.puzzle_id for p in self.selected_puzzles]
        self.db.link_puzzles_to_user_theme(theme_id, puzzle_ids)
        self._refresh_user_themes()
        self._refresh_exclude_user_themes()

    def _format_answers_solution(self, puzzle: Puzzle) -> str:
        """
        Форматирует решение для файла ответов.

        Если черные ходят первыми, добавляет "..." после номера хода.
        """
        moves = puzzle.moves.split()
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

    def _clear_selection(self) -> None:
        self.selected_puzzles.clear()
        for widget in self.selected_inner.winfo_children():
            widget.destroy()
        self.selected_inner.update_idletasks()
        self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
        self._update_selected_title()
