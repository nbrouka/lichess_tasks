"""
Mixin for puzzle display, navigation, and solution stepping in Lichess Puzzle Viewer.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Optional

from PIL import Image, ImageTk

from database import Puzzle
from board_renderer import render_puzzle, save_png
from constants import THEME_TRANSLATIONS, t


class PuzzleViewMixin:
    def _show_puzzle(self, index: int) -> None:
        if not self.filtered_puzzles or index < 0 or index >= len(self.filtered_puzzles):
            return
        self.current_index = index
        puzzle = self.filtered_puzzles[index]
        self._solution_step = 1
        self._update_solution_board(puzzle)
        self._update_solution_step_label(puzzle)
        self._update_info_text(puzzle)

        self.status_label.config(
            text=t("puzzle_info", index=index + 1, total=self._filter_total)
        )

    def _update_solution_board(self, puzzle: Puzzle) -> None:
        img = render_puzzle(puzzle.fen, puzzle.moves, move_index=self._solution_step)
        photo = ImageTk.PhotoImage(img)
        self.image_label.configure(image=photo, text="")
        self.image_label.image = photo

    def _update_solution_step_label(self, puzzle: Puzzle) -> None:
        total_steps = len(puzzle.moves.split()) if puzzle.moves else 0
        self.solution_step_label.config(text=f"{self._solution_step} / {total_steps}")

    def _update_info_text(self, puzzle: Puzzle) -> None:
        actual_color = "b" if puzzle.color == "w" else "w"
        color_text = t("color_white") if actual_color == "w" else t("color_black")
        theme_count = len(puzzle.themes)
        info = (
            f"PuzzleId: {puzzle.puzzle_id}\n"
            f"Rating: {puzzle.rating}  |  Popularity: {puzzle.popularity}  |  Plays: {puzzle.nb_plays}\n"
            f"{t('color_label')} {color_text}\n"
            f"Themes ({theme_count}): {', '.join(THEME_TRANSLATIONS.get(t, t) for t in puzzle.themes)}\n"
            f"Opening: {', '.join(puzzle.opening_tags)}\n"
            f"Solution: {puzzle.solution}\n"
            f"FEN: {puzzle.fen}\n"
        )
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", info)

        if puzzle.game_url:
            self.info_text.insert(tk.END, "Game: ")
            link_start = self.info_text.index(tk.INSERT)
            self.info_text.insert(tk.END, puzzle.game_url)
            link_end = self.info_text.index(tk.INSERT)
            self.info_text.tag_add("link", link_start, link_end)
            self.info_text.tag_config("link", foreground="blue", underline=True)
            self.info_text.tag_bind("link", "<Button-1>", lambda e, url=puzzle.game_url: self._open_url(url))

        self.info_text.config(state=tk.DISABLED)

    def _open_url(self, url: str) -> None:
        import webbrowser
        webbrowser.open(url)

    def _prev_solution_step(self) -> None:
        if self.current_index is None or not self.filtered_puzzles:
            return
        puzzle = self.filtered_puzzles[self.current_index]
        if self._solution_step > 1:
            self._solution_step -= 1
            self._update_solution_board(puzzle)
            self._update_solution_step_label(puzzle)

    def _next_solution_step(self) -> None:
        if self.current_index is None or not self.filtered_puzzles:
            return
        puzzle = self.filtered_puzzles[self.current_index]
        move_list = puzzle.moves.split()
        if self._solution_step < len(move_list):
            self._solution_step += 1
            self._update_solution_board(puzzle)
            self._update_solution_step_label(puzzle)

    def _go_to_solution_start(self) -> None:
        if self.current_index is None or not self.filtered_puzzles:
            return
        self._solution_step = 1
        puzzle = self.filtered_puzzles[self.current_index]
        self._update_solution_board(puzzle)
        self._update_solution_step_label(puzzle)

    def _go_to_solution_end(self) -> None:
        if self.current_index is None or not self.filtered_puzzles:
            return
        puzzle = self.filtered_puzzles[self.current_index]
        move_list = puzzle.moves.split()
        self._solution_step = len(move_list)
        self._update_solution_board(puzzle)
        self._update_solution_step_label(puzzle)

    def _clear_display(self) -> None:
        self.image_label.configure(image="", text=t("no_data"))
        self.image_label.image = None
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", t("no_data"))
        self.info_text.config(state=tk.DISABLED)

    def _prev_puzzle(self) -> None:
        if self.current_index is not None and self.current_index > 0:
            self._show_puzzle(self.current_index - 1)

    def _next_puzzle(self) -> None:
        if self.current_index is None:
            return
        if self.current_index < len(self.filtered_puzzles) - 1:
            self._show_puzzle(self.current_index + 1)
        elif self._filter_offset < self._filter_total:
            self._load_more_puzzles()
            if self.current_index is not None and self.current_index < len(self.filtered_puzzles) - 1:
                self._show_puzzle(self.current_index + 1)

    def _save_png(self) -> None:
        if self.current_index is None:
            messagebox.showinfo(t("about_title"), t("msg_select_puzzle"))
            return
        puzzle = self.filtered_puzzles[self.current_index]
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            initialfile=f"{puzzle.puzzle_id}.png",
        )
        if path:
            img = render_puzzle(puzzle.fen, puzzle.moves)
            save_png(img, path)
            messagebox.showinfo(t("about_title"), t("msg_saved", path=path))
