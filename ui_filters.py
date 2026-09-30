"""
Mixin for filter widgets, filter application, and stats in Lichess Puzzle Viewer.
"""

import tkinter as tk
from tkinter import ttk
import threading
from typing import Optional

from constants import (
    THEME_RU_TO_EN, COLOR_RU_TO_EN, t,
    FILTER_PAGE_SIZE, FILTER_DEBOUNCE_MS,
)


class PuzzleFiltersMixin:
    def _add_filter_entry(self, parent: ttk.Frame, label: str, key: str) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(8, 0))
        entry = ttk.Entry(parent)
        entry.pack(fill=tk.X)
        self.filter_widgets[key] = entry

    def _add_spin_filter(
        self, parent: ttk.Frame, label: str, key: str,
        from_: int, to: int,
    ) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(5, 0))
        spin = ttk.Spinbox(parent, from_=from_, to=to, width=10)
        spin.pack(anchor=tk.W)
        self.filter_widgets[key] = spin

    def _add_scale_filter(
        self, parent: ttk.Frame, label: str,
        min_key: str, max_key: str,
        from_: int, to: int, default: int,
        explanation: str = "",
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(8, 0))

        header = ttk.Frame(frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text=label).pack(side=tk.LEFT)
        if explanation:
            ttk.Label(header, text=explanation, foreground="gray").pack(side=tk.LEFT, padx=(5, 0))

        min_var = tk.IntVar(value=from_)
        max_var = tk.IntVar(value=to)
        default_var = tk.IntVar(value=default)

        min_scale = ttk.Scale(
            frame, from_=from_, to=to, orient=tk.HORIZONTAL,
            variable=min_var, command=lambda v: self._on_scale(min_key, min_var, min_label),
        )
        min_scale.pack(fill=tk.X)
        min_label = ttk.Label(frame, text=f"от {from_}")
        min_label.pack(anchor=tk.W)

        max_scale = ttk.Scale(
            frame, from_=from_, to=to, orient=tk.HORIZONTAL,
            variable=max_var, command=lambda v: self._on_scale(max_key, max_var, max_label),
        )
        max_scale.pack(fill=tk.X)
        max_label = ttk.Label(frame, text=f"до {to}")
        max_label.pack(anchor=tk.W)

        self.filter_widgets[min_key] = min_var
        self.filter_widgets[max_key] = max_var
        self._scale_defaults[min_key] = (from_, min_var, min_label)
        self._scale_defaults[max_key] = (to, max_var, max_label)
        self._scale_bounds[min_key] = (from_, to)
        self._scale_bounds[max_key] = (from_, to)

    def _add_exact_scale_filter(
        self, parent: ttk.Frame, label: str,
        key: str,
        from_: int, to: int, default: int,
        explanation: str = "",
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(8, 0))

        header = ttk.Frame(frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text=label).pack(side=tk.LEFT)
        if explanation:
            ttk.Label(header, text=explanation, foreground="gray").pack(side=tk.LEFT, padx=(5, 0))

        enabled_var = tk.BooleanVar(value=False)
        var = tk.IntVar(value=default)

        toggle_btn = ttk.Button(
            frame, text=t("toggle_filter_on"),
            command=lambda: self._toggle_moves_filter(toggle_btn, scale, enabled_var),
        )
        toggle_btn.pack(anchor=tk.W, pady=(4, 0))

        scale = ttk.Scale(
            frame, from_=from_, to=to, orient=tk.HORIZONTAL,
            variable=var, state=tk.DISABLED,
        )
        scale.pack(fill=tk.X, pady=(4, 0))
        value_label = ttk.Label(frame, text=t("scale_equals", value=default))
        value_label.pack(anchor=tk.W)

        def on_value_change(*_args) -> None:
            value = int(float(var.get()))
            value = max(from_, min(to, value))
            var.set(value)
            value_label.config(text=t("scale_equals", value=value))

        scale.configure(command=on_value_change)
        var.trace_add("write", on_value_change)

        self.filter_widgets[key] = var
        self.filter_widgets[f"{key}_enabled"] = enabled_var
        self.filter_widgets[f"{key}_scale"] = scale
        self.filter_widgets[f"{key}_toggle"] = toggle_btn
        self._scale_defaults[key] = (default, var, value_label)
        self._scale_bounds[key] = (from_, to)

    def _toggle_moves_filter(self, button, scale, var):
        if var.get():
            var.set(False)
            scale.configure(state=tk.DISABLED)
            button.configure(text=t("toggle_filter_on"))
        else:
            var.set(True)
            scale.configure(state=tk.NORMAL)
            button.configure(text=t("toggle_filter_off"))

    def _on_scale(self, key: str, var: tk.IntVar, label: ttk.Label) -> None:
        value = int(float(var.get()))
        bound_min, bound_max = self._scale_bounds[key]
        value = max(bound_min, min(bound_max, value))
        var.set(value)

        if key.endswith("_min"):
            label.config(text=f"от {value}")
        else:
            label.config(text=f"до {value}")

    def _init_filters(self) -> None:
        pass

    def _bind_events(self) -> None:
        self.themes_listbox.bind("<Double-Button-1>", lambda e: self._apply_filter())

    def _get_filter_values(self) -> dict:
        themes = [self.themes_listbox.get(i) for i in self.themes_listbox.curselection()]
        themes = [t.split(" (")[0] for t in themes]
        themes = [THEME_RU_TO_EN.get(t, t) for t in themes]

        moves_exact = self.filter_widgets.get("moves_exact")
        moves_enabled = self.filter_widgets.get("moves_exact_enabled")
        if moves_exact is not None and moves_enabled is not None and moves_enabled.get():
            moves_value = int(float(moves_exact.get()))
            bound_min, bound_max = self._scale_bounds["moves_exact"]
            moves_value = max(bound_min, min(bound_max, moves_value))
            moves_exact = moves_value
        else:
            moves_exact = None

        return {
            "rating_min": None,
            "rating_max": None,
            "popularity_min": None,
            "popularity_max": None,
            "nb_plays_min": None,
            "nb_plays_max": None,
            "moves_exact": moves_exact,
            "themes": themes if themes else None,
            "color": self._invert_color(COLOR_RU_TO_EN.get(self.filter_widgets["color"].get().strip())) or None,
            "user_themes": [self.filter_widgets["user_themes"].get()] if self.filter_widgets["user_themes"].get() else None,
        }

    def _invert_color(self, color: Optional[str]) -> Optional[str]:
        """Inverts the selected color because the stored `Color` field in the
        database represents the *opponent's* color, i.e. the side that just moved
        and left the puzzle position.  Selecting "Ход белых" in the UI means
        white is to move, so we must filter by `Color = 'b'` (black just moved),
        and vice versa."""
        if color == "w":
            return "b"
        if color == "b":
            return "w"
        return None

    def _apply_filter(self) -> None:
        if getattr(self, "_filter_thread", None) and self._filter_thread.is_alive():
            return

        if getattr(self, "_filter_after_id", None):
            self.root.after_cancel(self._filter_after_id)

        def _do_apply():
            self._filter_values = self._get_filter_values()
            self._filter_offset = 0
            self._set_filtering_status(True)
            self.root.update_idletasks()

            def run():
                puzzles, count = self.db.filter_puzzles(
                    **self._filter_values,
                    limit=FILTER_PAGE_SIZE,
                    offset=0,
                    return_total=True,
                )
                self.root.after(0, lambda: self._on_filter_complete(puzzles, count))

            self._filter_thread = threading.Thread(target=run, daemon=True)
            self._filter_thread.start()

        self._filter_after_id = self.root.after(FILTER_DEBOUNCE_MS, _do_apply)

    def _set_filtering_status(self, active: bool) -> None:
        if active:
            self._filtering_dots = 0
            self._update_filtering_dots()
        else:
            if getattr(self, "_filtering_dots_id", None):
                self.root.after_cancel(self._filtering_dots_id)

    def _update_filtering_dots(self) -> None:
        self._filtering_dots = (self._filtering_dots + 1) % 4
        dots = "." * self._filtering_dots
        self.status_label.config(text=f"{t('status_filtering')}{dots}")
        if self._filtering_dots > 0:
            self._filtering_dots_id = self.root.after(250, self._update_filtering_dots)

    def _on_filter_complete(self, puzzles, count: int) -> None:
        self._set_filtering_status(False)

        self.filtered_puzzles = puzzles
        self._filter_total = count
        self._filter_offset = len(puzzles)
        self.current_index = 0 if puzzles else None
        self.count_label.config(text=t("found_label", count=count))
        if puzzles:
            self._show_puzzle(0)
            self.status_label.config(text=t("status_loaded", count=len(puzzles), total=count))
            self._update_stats()
        else:
            self._clear_display()
            self.status_label.config(text=t("status_not_found"))

    def _load_more_puzzles(self) -> None:
        if not self._filter_values:
            return
        if getattr(self, "_load_more_thread", None) and self._load_more_thread.is_alive():
            return

        self.status_label.config(text=t("status_loading"))
        self.root.update_idletasks()

        def run():
            new_puzzles = self.db.filter_puzzles(
                **self._filter_values,
                limit=FILTER_PAGE_SIZE,
                offset=self._filter_offset,
            )
            self.root.after(0, lambda: self._on_more_loaded(new_puzzles))

        self._load_more_thread = threading.Thread(target=run, daemon=True)
        self._load_more_thread.start()

    def _on_more_loaded(self, new_puzzles) -> None:
        if not new_puzzles:
            self.status_label.config(text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total))
            self._update_stats()
            return
        self.filtered_puzzles.extend(new_puzzles)
        self._filter_offset += len(new_puzzles)
        self.status_label.config(
            text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total)
        )
        self._update_stats()
        if self.current_index is None:
            self.current_index = 0
            self._show_puzzle(0)

    def _update_stats(self) -> None:
        stats = self.db.get_stats(self._filter_values)
        moves_stats = ", ".join(
            f"{moves}: {cnt}" for moves, cnt in sorted(stats["by_moves"].items())
        )

        white = stats["white"]
        black = stats["black"]
        if self._filter_values.get("color"):
            white, black = black, white

        text = (
            f"{t('stats_white', white=white)}\n"
            f"{t('stats_black', black=black)}\n"
            f"{t('stats_by_moves', moves=moves_stats)}"
        )
        self.stats_label.config(text=text)

    def _reset_filters(self) -> None:
        for key, widget in self.filter_widgets.items():
            if isinstance(widget, tk.IntVar):
                default_value, var, label = self._scale_defaults[key]
                var.set(default_value)
                if key == "moves_exact":
                    label.config(text=t("scale_equals", value=default_value))
            elif isinstance(widget, tk.BooleanVar) and key.endswith("_enabled"):
                widget.set(False)
                scale_key = key.replace("_enabled", "")
                scale_widget = self.filter_widgets.get(f"{scale_key}_scale")
                toggle_widget = self.filter_widgets.get(f"{scale_key}_toggle")
                if scale_widget is not None:
                    scale_widget.configure(state=tk.DISABLED)
                if toggle_widget is not None:
                    toggle_widget.configure(text=t("toggle_filter_on"))
            elif isinstance(widget, ttk.Combobox):
                widget.set("")
        self.themes_listbox.selection_clear(0, tk.END)
        self.filtered_puzzles = []
        self.selected_puzzles = []
        for widget in self.selected_inner.winfo_children():
            widget.destroy()
        self.current_index = None
        self._filter_values = {}
        self._filter_total = 0
        self._filter_offset = 0
        self._solution_step = 0
        self._clear_display()
        self.count_label.config(text=t("found_label", count=0))
        self.stats_label.config(text="")
        self.status_label.config(text=t("status_reset"))
        self._update_selected_title()
