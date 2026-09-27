"""
Графический интерфейс приложения Lichess Puzzle Viewer на Tkinter.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import json
from pathlib import Path
from typing import List, Optional

from database import PuzzleDatabase, Puzzle
from board_renderer import render_puzzle, save_png
from constants import (
    APP_NAME, VERSION, DEFAULT_CSV_PATH, DB_FILENAME,
    BOARD_SIZE, COLOR_LIGHT, COLOR_DARK,
    THEME_TRANSLATIONS, THEME_RU_TO_EN,
    CATEGORY_TRANSLATIONS, CATEGORY_RU_TO_EN,
    UI_TRANSLATIONS, LANG, t, COLOR_RU_TO_EN,
)


class PuzzleApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(t("app_title"))
        self.root.geometry("1050x720")
        self.root.minsize(900, 600)

        self.db = PuzzleDatabase(db_path=DB_FILENAME, csv_path=DEFAULT_CSV_PATH)

        self.filtered_puzzles: List[Puzzle] = []
        self.current_index: Optional[int] = None
        self._import_in_progress: bool = False
        self._scale_defaults = {}
        self._scale_bounds = {}
        self.themes_data = {}
        self._category_var = tk.StringVar()
        self._available_theme_ids = set()
        self._filter_values: dict = {}
        self._filter_total: int = 0
        self._filter_offset: int = 0
        self._solution_step: int = 0
        self.selected_puzzles: List[Puzzle] = []

        self._build_menu()
        self._build_layout()
        self._init_filters()
        self._bind_events()
        self._load_themes_data()

        # БД может быть уже готова, если файл существует
        if self.db.is_imported():
            self._on_db_ready()
        else:
            self.status_label.config(text=t("status_db_not_ready"))

    # ------------------------------------------------------------------
    # Меню
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=t("menu_open_csv"), command=self._open_csv)
        file_menu.add_command(label=t("menu_import_csv"), command=self._start_import)
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_exit"), command=self.root.quit)
        menubar.add_cascade(label=t("menu_file"), menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=t("menu_about"), command=self._show_about)
        help_menu.add_command(label=t("menu_fields_help"), command=self._show_fields_help)
        menubar.add_cascade(label=t("menu_help"), menu=help_menu)

        self.root.config(menu=menubar)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # Левая панель: фильтры
        left = ttk.Frame(main, width=320)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left.pack_propagate(False)

        ttk.Label(left, text=t("filters_title"), font=("", 12, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )

        self.filter_widgets = {}
        self._add_exact_scale_filter(left, t("moves_label"), "moves_exact", 1, 20, 20, t("moves_explanation"))

        ttk.Label(left, text=t("color_label")).pack(anchor=tk.W, pady=(5, 0))
        self.color_var = tk.StringVar(value="")
        color_cb = ttk.Combobox(
            left, textvariable=self.color_var,
            values=["", t("color_white"), t("color_black")], state="readonly", width=15,
        )
        color_cb.pack(anchor=tk.W)
        self.filter_widgets["color"] = color_cb

        ttk.Label(left, text=t("category_label")).pack(anchor=tk.W, pady=(8, 0))
        self.category_cb = ttk.Combobox(
            left, textvariable=self._category_var,
            state="readonly", width=35,
        )
        self.category_cb.pack(anchor=tk.W)
        self.category_cb.bind("<<ComboboxSelected>>", lambda e: self._on_category_selected())

        ttk.Label(left, text=t("themes_label")).pack(anchor=tk.W, pady=(8, 0))
        themes_frame = ttk.Frame(left)
        themes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.themes_listbox = tk.Listbox(
            themes_frame, selectmode=tk.EXTENDED, height=10, exportselection=False,
        )
        themes_scroll = ttk.Scrollbar(themes_frame, orient=tk.VERTICAL, command=self.themes_listbox.yview)
        self.themes_listbox.configure(yscrollcommand=themes_scroll.set)
        self.themes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        themes_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки фильтров
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text=t("apply_btn"), command=self._apply_filter).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2)
        )
        ttk.Button(btn_frame, text=t("reset_btn"), command=self._reset_filters).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0)
        )

        self.count_label = ttk.Label(left, text=t("found_label", count=0))
        self.count_label.pack(anchor=tk.W, pady=(5, 0))

        main.columnconfigure(1, weight=1)

        center = ttk.Frame(main)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=1)

        self.image_label = ttk.Label(center)
        self.image_label.grid(row=0, column=0, pady=(0, 10))

        self.info_text = tk.Text(center, height=8, wrap=tk.WORD, relief=tk.FLAT)
        self.info_text.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.info_text.insert("1.0", t("no_data"))
        self.info_text.config(state=tk.DISABLED)

        sol_frame = ttk.Frame(center)
        sol_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        ttk.Button(sol_frame, text="⏪", command=self._go_to_solution_start).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        ttk.Button(sol_frame, text="◀", command=self._prev_solution_step).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        self.solution_step_label = ttk.Label(sol_frame, text="0 / 0")
        self.solution_step_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(sol_frame, text="▶", command=self._next_solution_step).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        ttk.Button(sol_frame, text="⏩", command=self._go_to_solution_end).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )

        nav_frame = ttk.Frame(center)
        nav_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        ttk.Button(nav_frame, text="Выбрать", command=self._add_to_selected).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        ttk.Button(nav_frame, text=t("prev_btn"), command=self._prev_puzzle).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        ttk.Button(nav_frame, text=t("save_png_btn"), command=self._save_png).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        ttk.Button(nav_frame, text=t("next_btn"), command=self._next_puzzle).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )

        self.status_label = ttk.Label(center, text=t("status_ready"))
        self.status_label.grid(row=4, column=0, sticky="w", pady=(5, 0))

        self.stats_label = ttk.Label(center, text="")
        self.stats_label.grid(row=5, column=0, sticky="w", pady=(2, 0))

        right = ttk.Frame(main, width=260)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        right.pack_propagate(False)

        ttk.Label(right, text=t("selected_title")).pack(anchor=tk.W, pady=(0, 5))
        selected_frame = ttk.Frame(right)
        selected_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(selected_frame, orient=tk.VERTICAL)
        self.selected_canvas = tk.Canvas(selected_frame, yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.selected_canvas.yview)
        self.selected_inner = ttk.Frame(self.selected_canvas)
        self.selected_inner.bind(
            "<Configure>",
            lambda e: self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all")),
        )
        self.selected_canvas.create_window((0, 0), window=self.selected_inner, anchor="nw")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.selected_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Виджеты фильтров
    # ------------------------------------------------------------------
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

    def _load_themes_data(self) -> None:
        path = Path("lichess_themes.json")
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.themes_data = {}
            for cat in data.get("categories", []):
                cat_name = cat.get("name", "")
                ru_name = CATEGORY_TRANSLATIONS.get(cat_name, cat_name)
                themes = {}
                for t in cat.get("themes", []):
                    themes[t.get("name", "")] = t
                self.themes_data[ru_name] = themes

            categories = [CATEGORY_TRANSLATIONS.get(cat.get("name", ""), cat.get("name", "")) for cat in data.get("categories", [])]
            self.category_cb["values"] = categories
            if categories:
                self._category_var.set(categories[0])
                self._on_category_selected()
        except Exception:
            pass

    def _on_category_selected(self, event=None) -> None:
        category = self._category_var.get()
        cat_themes = self.themes_data.get(category, {})

        self.themes_listbox.delete(0, tk.END)
        for data in cat_themes.values():
            theme_id = data.get("id", "")
            if self._available_theme_ids and theme_id not in self._available_theme_ids:
                continue
            ru_name = THEME_TRANSLATIONS.get(theme_id, data.get("name", ""))
            count = data.get("count", "")
            display = f"{ru_name} ({count})" if count else ru_name
            self.themes_listbox.insert(tk.END, display)

    # ------------------------------------------------------------------
    # Фильтрация
    # ------------------------------------------------------------------
    def _invert_color(self, color: Optional[str]) -> Optional[str]:
        if color == "w":
            return "b"
        if color == "b":
            return "w"
        return None

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
        }

    def _apply_filter(self) -> None:
        self._filter_values = self._get_filter_values()
        self._filter_offset = 0
        self.status_label.config(text=t("status_filtering"))
        self.root.update_idletasks()

        def run():
            count = self.db.count_filtered(**self._filter_values)
            puzzles = self.db.filter_puzzles(**self._filter_values, limit=100, offset=0)
            self.root.after(0, lambda: self._on_filter_complete(puzzles, count))

        threading.Thread(target=run, daemon=True).start()

    def _on_filter_complete(self, puzzles: List[Puzzle], count: int) -> None:
        self.filtered_puzzles = puzzles
        self._filter_total = count
        self._filter_offset = len(puzzles)
        self.current_index = 0 if puzzles else None
        self.count_label.config(text=t("found_label", count=count))
        if puzzles:
            self._show_puzzle(0)
            self.status_label.config(text=t("status_loaded", count=len(puzzles), total=count))
        else:
            self._clear_display()
            self.status_label.config(text=t("status_not_found"))
        self._update_stats()

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

    def _load_more_puzzles(self) -> None:
        if not self._filter_values:
            return
        self.status_label.config(text=t("status_loading"))
        self.root.update_idletasks()

        def run():
            new_puzzles = self.db.filter_puzzles(
                **self._filter_values,
                limit=100,
                offset=self._filter_offset,
            )
            self.root.after(0, lambda: self._on_more_loaded(new_puzzles))

        threading.Thread(target=run, daemon=True).start()

    def _on_more_loaded(self, new_puzzles: List[Puzzle]) -> None:
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

    # ------------------------------------------------------------------
    # Отображение задачи
    # ------------------------------------------------------------------
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

    def _add_to_selected(self) -> None:
        if self.current_index is None or not self.filtered_puzzles:
            return
        puzzle = self.filtered_puzzles[self.current_index]
        self.selected_puzzles.append(puzzle)

        thumb = render_puzzle(puzzle.fen, puzzle.moves, square_size=20)
        photo = ImageTk.PhotoImage(thumb)

        item_frame = ttk.Frame(self.selected_inner)
        item_frame.pack(fill=tk.X, pady=2)

        img_label = ttk.Label(item_frame, image=photo)
        img_label.image = photo
        img_label.pack(side=tk.LEFT)

        text_label = ttk.Label(item_frame, text=f"{puzzle.puzzle_id}\n{puzzle.rating}", justify=tk.CENTER)
        text_label.pack(side=tk.LEFT, padx=5)

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

    # ------------------------------------------------------------------
    # Импорт БД
    # ------------------------------------------------------------------
    def _start_import(self) -> None:
        """Запускает импорт CSV в SQLite в фоновом потоке."""
        if self._import_in_progress:
            messagebox.showinfo(t("about_title"), t("msg_import_running"))
            return

        self._import_in_progress = True
        self.status_label.config(text=t("status_import_started"))

        progress_win = tk.Toplevel(self.root)
        progress_win.title(t("progress_title"))
        progress_win.geometry("500x140")
        progress_win.transient(self.root)
        progress_win.grab_set()
        progress_win.resizable(True, True)
        self._progress_win = progress_win

        info_label = ttk.Label(
            progress_win,
            text=t("progress_importing", filename=Path(self.db.csv_path).name),
        )
        info_label.pack(pady=(10, 5), anchor=tk.W, padx=10)

        progress_bar = ttk.Progressbar(progress_win, mode="determinate")
        progress_bar.pack(fill=tk.X, padx=20, pady=5)

        status_label = ttk.Label(progress_win, text=t("progress_preparing"))
        status_label.pack(pady=(0, 10))

        total_lines = sum(
            1 for _ in open(self.db.csv_path, "r", encoding="utf-8")
        ) - 1
        progress_bar["maximum"] = total_lines

        def progress_callback(current: int) -> None:
            def update_ui():
                if not progress_win.winfo_exists():
                    return
                progress_bar["value"] = current
                pct = int(current / total_lines * 100) if total_lines > 0 else 0
                status_label.config(
                    text=t("progress_pct", pct=pct, current=current, total_lines=total_lines)
                )
                self.status_label.config(
                    text=t("progress_pct", pct=pct, current=current, total_lines=total_lines)
                )
                progress_win.update_idletasks()

            self.root.after(0, update_ui)

        def run_import():
            try:
                self.db.import_csv(progress_callback=progress_callback)
                self.root.after(0, self._on_db_ready)
                self.root.after(0, lambda: messagebox.showinfo(
                    t("about_title"), t("msg_import_success")
                ))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror(
                    t("msg_import_error"), str(exc)
                ))
            finally:
                self.root.after(0, progress_win.destroy)
                self.root.after(0, lambda: setattr(self, "_import_in_progress", False))
                self.root.after(0, lambda: self.status_label.config(text=t("status_import_complete")))

        threading.Thread(target=run_import, daemon=True).start()

    def _on_db_ready(self) -> None:
        themes = self.db.get_all_themes()
        self._available_theme_ids = set(themes)
        self.themes_listbox.delete(0, tk.END)
        for theme in sorted(themes):
            display = THEME_TRANSLATIONS.get(theme, theme)
            self.themes_listbox.insert(tk.END, display)
        self.status_label.config(text=t("status_db_ready"))

        filtered_categories = []
        filtered_themes_data = {}
        for cat_name, cat_themes in self.themes_data.items():
            available = {
                name: data
                for name, data in cat_themes.items()
                if data.get("id", "") in self._available_theme_ids
            }
            if available:
                filtered_categories.append(cat_name)
                filtered_themes_data[cat_name] = available

        self.themes_data = filtered_themes_data
        self.category_cb["values"] = filtered_categories
        if filtered_categories:
            self._category_var.set(filtered_categories[0])
        else:
            self._category_var.set("")
        self._on_category_selected()

    # ------------------------------------------------------------------
    # Открытие CSV
    # ------------------------------------------------------------------
    def _open_csv(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=DEFAULT_CSV_PATH,
        )
        if path:
            self.db.csv_path = path
            self._start_import()

    # ------------------------------------------------------------------
    # Справка
    # ------------------------------------------------------------------
    def _show_about(self) -> None:
        messagebox.showinfo(
            t("about_title"),
            t("about_text"),
        )

    def _show_fields_help(self) -> None:
        messagebox.showinfo(
            t("fields_title"),
            t("fields_text"),
        )

    # ------------------------------------------------------------------
    # Завершение
    # ------------------------------------------------------------------
    def destroy(self) -> None:
        self.db.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = PuzzleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
