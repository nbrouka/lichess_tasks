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
from constants import t, THUMBNAIL_SQUARE_SIZE, DOCX_DIALOG_GEOMETRY
from docx_exporter import PuzzleDocxExporter

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
        dialog.geometry(DOCX_DIALOG_GEOMETRY)
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
        exporter = PuzzleDocxExporter(self.selected_puzzles, topic)
        exporter.export(path)
