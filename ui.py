"""
Графический интерфейс приложения Lichess Puzzle Viewer на Tkinter.
"""

import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading
import time
import json
from pathlib import Path
from typing import List, Optional

from database import PuzzleDatabase, Puzzle
from constants import (
    DEFAULT_CSV_PATH, DB_FILENAME, THEME_TRANSLATIONS, t,
    WINDOW_MINSIZE, FILTERS_PANEL_WIDTH, SELECTED_PANEL_WIDTH,
    EXCLUDE_THEMES_LISTBOX_HEIGHT, THEMES_LISTBOX_HEIGHT,
    COMBOBOX_WIDTH, COLOR_COMBOBOX_WIDTH,
    ICON_WINDOWS, ICON_LINUX,
    FILTER_PAGE_SIZE,
    SESSION_FILE,
)

logger = logging.getLogger(__name__)

from ui_puzzle_view import PuzzleViewMixin
from ui_filters import PuzzleFiltersMixin
from ui_themes import PuzzleThemesMixin
from ui_selection import PuzzleSelectionMixin
from ui_import import PuzzleImportMixin


class PuzzleApp(
    PuzzleViewMixin,
    PuzzleFiltersMixin,
    PuzzleThemesMixin,
    PuzzleSelectionMixin,
    PuzzleImportMixin,
):
    def __init__(self, root: tk.Tk, db_path: str = DB_FILENAME, csv_path: str = DEFAULT_CSV_PATH):
        self.root = root
        self.root.title(t("app_title"))
        self.root.minsize(*WINDOW_MINSIZE)
        self._puzzle_details_text = ""

        self.db = PuzzleDatabase(db_path=db_path, csv_path=csv_path)

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
        self._selected_photos: List[ImageTk.PhotoImage] = []
        self._selected_item_ids: List[int] = []
        self._pending_last_puzzle_id = None
        self._pending_selected_ids = []
        self._pending_current_index = None
        self._pending_goto_target = None
        self._restoring_session = False

        self._build_menu()
        self._build_layout()
        self._init_filters()
        self._bind_events()
        self._load_themes_data()

        # БД может быть уже готова, если файл существует
        self._reset_filters()

        if self.db.is_imported():
            self._on_db_ready()
            self.root.after(0, self._restore_session)
        else:
            self.status_label.config(text=t("status_db_not_ready"))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Меню
    # ------------------------------------------------------------------
    def _set_window_icon(self) -> None:
        """
        Устанавливает иконку окна приложения.

        На Windows использует .ico, на Linux - .png через iconphoto.
        Файлы иконок должны лежать в корне проекта.
        """
        icon_path = Path(ICON_WINDOWS if os.name == "nt" else ICON_LINUX)
        if not icon_path.exists():
            return
        try:
            if icon_path.suffix.lower() == ".ico":
                self.root.iconbitmap(str(icon_path))
            else:
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                self._selected_photos.append(photo)
        except Exception:
            pass

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=t("menu_open_csv"), command=self._open_csv)
        file_menu.add_command(label=t("menu_import_csv"), command=self._start_import)
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_exit"), command=self.root.quit)
        menubar.add_cascade(label=t("menu_file"), menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label=t("menu_user_themes"), command=self._delete_user_themes_dialog)
        menubar.add_cascade(label=t("menu_edit"), menu=edit_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=t("menu_about"), command=self._show_about)
        menubar.add_cascade(label=t("menu_help"), menu=help_menu)

        self.root.config(menu=menubar)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        """
        Строит основной layout приложения.

        Левая панель: фильтры.
        Центр: доска, описание задачи, навигация.
        Правая панель: выбранные задачи.
        """
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # Левая панель: фильтры
        left = ttk.Frame(main, width=FILTERS_PANEL_WIDTH)
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
            values=["", t("color_white"), t("color_black")], state="readonly", width=COLOR_COMBOBOX_WIDTH,
        )
        color_cb.pack(anchor=tk.W)
        self.filter_widgets["color"] = color_cb

        ttk.Label(left, text=t("category_label")).pack(anchor=tk.W, pady=(8, 0))
        self.category_cb = ttk.Combobox(
            left, textvariable=self._category_var,
            state="readonly", width=COMBOBOX_WIDTH,
        )
        self.category_cb.pack(anchor=tk.W)
        self.category_cb.bind("<<ComboboxSelected>>", lambda e: self._on_category_selected())

        ttk.Label(left, text=t("themes_label")).pack(anchor=tk.W, pady=(8, 0))
        themes_frame = ttk.Frame(left)
        themes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.themes_listbox = tk.Listbox(
            themes_frame, selectmode=tk.EXTENDED, height=THEMES_LISTBOX_HEIGHT, exportselection=False,
        )
        themes_scroll = ttk.Scrollbar(themes_frame, orient=tk.VERTICAL, command=self.themes_listbox.yview)
        self.themes_listbox.configure(yscrollcommand=themes_scroll.set)
        self.themes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        themes_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(left, text=t("user_themes_label")).pack(anchor=tk.W, pady=(8, 0))
        self.user_themes_var = tk.StringVar(value="")
        self.user_themes_cb = ttk.Combobox(
            left, textvariable=self.user_themes_var,
            state="readonly", width=COMBOBOX_WIDTH,
        )
        self.user_themes_cb.pack(anchor=tk.W)
        self.user_themes_cb.bind("<<ComboboxSelected>>", lambda e: self._on_user_theme_selected())
        self.filter_widgets["user_themes"] = self.user_themes_cb

        ttk.Label(left, text="Исключить:").pack(anchor=tk.W, pady=(8, 0))
        exclude_frame = ttk.Frame(left)
        exclude_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.exclude_themes_listbox = tk.Listbox(
            exclude_frame, selectmode=tk.EXTENDED, height=EXCLUDE_THEMES_LISTBOX_HEIGHT, exportselection=False,
        )
        exclude_scroll = ttk.Scrollbar(exclude_frame, orient=tk.VERTICAL, command=self.exclude_themes_listbox.yview)
        self.exclude_themes_listbox.configure(yscrollcommand=exclude_scroll.set)
        self.exclude_themes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        exclude_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        exclude_btn_frame = ttk.Frame(left)
        exclude_btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(exclude_btn_frame, text="Выбрать все", command=self._exclude_all_user_themes).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2)
        )
        ttk.Button(exclude_btn_frame, text="Снять все", command=self._exclude_none_user_themes).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0)
        )

        # Кнопки фильтров
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text=t("apply_btn"), command=self._apply_filter).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2)
        )
        ttk.Button(btn_frame, text=t("reset_btn"), command=self._reset_filters_and_save).pack(
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
        self.image_label.configure(anchor="center")
        self.image_label.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        details_frame = ttk.Frame(center)
        details_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        details_btn = ttk.Button(details_frame, text="См. детали задачи", command=self._show_puzzle_details)
        self.details_btn = details_btn
        details_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        goto_frame = ttk.Frame(details_frame)
        goto_frame.pack(side=tk.RIGHT)

        ttk.Label(goto_frame, text=t("goto_puzzle_label")).pack(side=tk.LEFT, padx=(0, 2))
        self.goto_entry = ttk.Entry(goto_frame, width=5)
        self.goto_entry.pack(side=tk.LEFT, padx=(0, 2))
        self.goto_entry.bind("<Return>", lambda e: self._goto_puzzle())
        ttk.Button(goto_frame, text=t("goto_puzzle_btn"), command=self._goto_puzzle).pack(side=tk.LEFT)

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

        right = ttk.Frame(main, width=SELECTED_PANEL_WIDTH)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        right.pack_propagate(False)

        self.selected_title_label = ttk.Label(right, text=t("selected_title"))
        self.selected_title_label.pack(anchor=tk.W, pady=(0, 5))
        selected_frame = ttk.Frame(right)
        selected_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(selected_frame, orient=tk.VERTICAL)
        self.selected_canvas = tk.Canvas(selected_frame, yscrollcommand=scrollbar.set, borderwidth=0, highlightthickness=0)
        scrollbar.configure(command=self.selected_canvas.yview)
        self.selected_inner = tk.Frame(self.selected_canvas, borderwidth=0, padx=0, pady=0)
        self.selected_inner.bind(
            "<Configure>",
            lambda e: self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all")),
        )
        self._selected_window_id = self.selected_canvas.create_window((0, 0), window=self.selected_inner, anchor="nw")
        self.selected_canvas.bind("<Configure>", self._on_selected_canvas_resize)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.selected_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.create_sheets_btn = ttk.Button(right, text="Создать листы", command=self._create_sheets_dialog)
        self.create_sheets_btn.pack(fill=tk.X, pady=(5, 0))

    # ------------------------------------------------------------------
    # Импорт БД
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
        dialog = tk.Toplevel(self.root)
        dialog.title(t("about_title"))
        dialog.geometry("360x180")
        dialog.transient(self.root)
        dialog.grab_set()

        text = tk.Text(dialog, wrap=tk.WORD, relief=tk.FLAT)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", t("about_text"))
        text.config(state=tk.DISABLED)

    def _puzzle_to_dict(self, puzzle: Puzzle) -> dict:
        return {
            "puzzle_id": puzzle.puzzle_id,
            "fen": puzzle.fen,
            "moves": puzzle.moves,
            "rating": puzzle.rating,
            "rating_deviation": puzzle.rating_deviation,
            "popularity": puzzle.popularity,
            "nb_plays": puzzle.nb_plays,
            "themes": puzzle.themes,
            "game_url": puzzle.game_url,
            "opening_tags": puzzle.opening_tags,
            "daily_date": puzzle.daily_date,
            "color": puzzle.color,
        }

    def _dict_to_puzzle(self, data: dict) -> Puzzle:
        return Puzzle(**data)

    def _save_session(self) -> None:
        data = {
            "filters": getattr(self, "_filter_values", {}),
            "last_puzzle_id": None,
            "selected_ids": [],
            "filter_offset": getattr(self, "_filter_offset", 0),
            "filter_total": getattr(self, "_filter_total", 0),
            "current_index": self.current_index,
        }
        if self.current_index is not None and getattr(self, "filtered_puzzles", []):
            data["last_puzzle_id"] = self.filtered_puzzles[self.current_index].puzzle_id
        data["selected_ids"] = [p.puzzle_id for p in getattr(self, "selected_puzzles", [])]
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _restore_session(self) -> None:
        if not self.db.is_imported():
            return
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.status_label.config(text=t("status_ready"))
            return

        self._restoring_session = True
        self.status_label.config(text=t("status_loading"))
        self._clear_display()
        self.root.update_idletasks()

        filters = data.get("filters") or {}
        has_active_filters = any(
            v is not None and v != "" and v != [] for v in filters.values()
        )
        logger.info("Restoring session: has_active_filters=%s", has_active_filters)
        if has_active_filters:
            logger.info("Restoring session with filters: %s", filters)
            self._set_filter_values(filters)
            self._pending_last_puzzle_id = data.get("last_puzzle_id")
            self._pending_selected_ids = data.get("selected_ids", [])
            self._pending_current_index = data.get("current_index")
            self._apply_filter()
            logger.info("_restore_session: _apply_filter scheduled")
        else:
            logger.info("Restoring session without filters")
            self._load_selected_from_session(data.get("selected_ids", []))
            last_puzzle_id = data.get("last_puzzle_id")
            if last_puzzle_id:
                saved_index = data.get("current_index")
                for i, p in enumerate(self.filtered_puzzles):
                    if p.puzzle_id == last_puzzle_id:
                        self._show_puzzle(i)
                        break
                else:
                    puzzle = self.db.get_puzzle_by_id(last_puzzle_id)
                    if puzzle:
                        self.filtered_puzzles = [puzzle]
                        self._filter_total = data.get("filter_total") or self.db.get_puzzle_count() or 1
                        self.current_index = 0
                        self._show_puzzle(0)
                        if saved_index is not None:
                            self.current_index = saved_index
                            self.status_label.config(
                                text=t("puzzle_info", index=saved_index + 1, total=self._filter_total)
                            )
                            if hasattr(self, "details_btn"):
                                self.details_btn.config(text=f"См. детали задачи №{saved_index + 1}")
            self._restoring_session = False
            logger.info("_restore_session completed (no filters path)")
            self.status_label.config(text=t("status_ready"))

    def _set_filter_values(self, values: dict) -> None:
        color = values.get("color")
        if color:
            ui_color = self._color_stored_to_ui(color)
            if ui_color:
                self.filter_widgets["color"].set(ui_color)
        else:
            self.filter_widgets["color"].set("")

        moves_exact = values.get("moves_exact")
        moves_enabled = self.filter_widgets.get("moves_exact_enabled")
        moves_var = self.filter_widgets.get("moves_exact")
        if moves_exact is not None and moves_enabled is not None and moves_var is not None:
            moves_enabled.set(True)
            moves_var.set(moves_exact)
            scale = self.filter_widgets.get("moves_exact_scale")
            toggle = self.filter_widgets.get("moves_exact_toggle")
            if scale is not None:
                scale.configure(state=tk.NORMAL)
            if toggle is not None:
                toggle.configure(text=t("toggle_filter_off"))
        else:
            if moves_enabled is not None:
                moves_enabled.set(False)
            scale = self.filter_widgets.get("moves_exact_scale")
            toggle = self.filter_widgets.get("moves_exact_toggle")
            if scale is not None:
                scale.configure(state=tk.DISABLED)
            if toggle is not None:
                toggle.configure(text=t("toggle_filter_on"))

        category = values.get("category")
        if category:
            self._category_var.set(category)
            self.category_cb.set(category)
            self._on_category_selected()
        else:
            self._category_var.set("")
            self.category_cb.set("")
            self._reset_themes_listbox_to_all()

        self.themes_listbox.selection_clear(0, tk.END)
        themes = values.get("themes") or []
        for en_theme in themes:
            ru_name = THEME_TRANSLATIONS.get(en_theme, en_theme)
            for i in range(self.themes_listbox.size()):
                item = self.themes_listbox.get(i)
                if item.startswith(f"{ru_name} ("):
                    self.themes_listbox.selection_set(i)
                    break

        self.exclude_themes_listbox.selection_clear(0, tk.END)
        exclude_themes = values.get("exclude_user_themes") or []
        for theme_name in exclude_themes:
            for i in range(self.exclude_themes_listbox.size()):
                item = self.exclude_themes_listbox.get(i)
                if item == theme_name or item.startswith(f"{theme_name} ("):
                    self.exclude_themes_listbox.selection_set(i)
                    break

        user_themes = values.get("user_themes") or []
        if user_themes:
            user_theme_name = user_themes[0]
            display = f"{user_theme_name} ({self.db.get_user_theme_puzzle_count(user_theme_name)})"
            self.filter_widgets["user_themes"].set(display)
        else:
            self.filter_widgets["user_themes"].set("")

    def _color_stored_to_ui(self, color: Optional[str]) -> Optional[str]:
        if color == "w":
            return t("color_black")
        if color == "b":
            return t("color_white")
        return None

    def _load_selected_from_session(self, selected_ids: list) -> None:
        if not selected_ids:
            return
        for pid in selected_ids:
            puzzle = self.db.get_puzzle_by_id(pid)
            if puzzle and not any(p.fen == puzzle.fen for p in self.selected_puzzles):
                self.selected_puzzles.append(puzzle)
                self._create_selected_widget(puzzle)
        self._update_selected_title()
        self.selected_inner.update_idletasks()
        self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))

    def _on_close(self) -> None:
        self._save_session()
        self.destroy()

    def _show_puzzle_details(self) -> None:
        if self.current_index is None or not self.filtered_puzzles:
            messagebox.showinfo(t("about_title"), t("msg_select_puzzle"))
            return

        puzzle = self.filtered_puzzles[self.current_index]
        actual_color = "b" if puzzle.color == "w" else "w"
        color_text = t("color_white") if actual_color == "w" else t("color_black")
        theme_count = len(puzzle.themes)
        details = (
            f"PuzzleId: {puzzle.puzzle_id}\n"
            f"Rating: {puzzle.rating}  |  Popularity: {puzzle.popularity}  |  Plays: {puzzle.nb_plays}\n"
            f"{t('color_label')} {color_text}\n"
            f"Themes ({theme_count}): {', '.join(THEME_TRANSLATIONS.get(theme, theme) for theme in puzzle.themes)}\n"
            f"Opening: {', '.join(puzzle.opening_tags)}\n"
            f"Solution: {puzzle.solution}\n"
            f"FEN: {puzzle.fen}\n"
        )
        if puzzle.game_url:
            details += f"Game: {puzzle.game_url}\n"

        dialog = tk.Toplevel(self.root)
        dialog.title("Детали задачи")
        dialog.geometry("520x360")
        dialog.configure(padx=10, pady=10)
        dialog.transient(self.root)
        dialog.grab_set()

        text = tk.Text(dialog, wrap=tk.WORD, relief=tk.FLAT)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", details)

        if puzzle.game_url:
            url_start = text.search(puzzle.game_url, "1.0", stopindex="end")
            if url_start:
                url_end = f"{url_start}+{len(puzzle.game_url)}c"
                text.tag_add("url", url_start, url_end)
                text.tag_config("url", foreground="blue", underline=True)
                text.tag_bind("url", "<Button-1>", lambda event, url=puzzle.game_url: self._open_url(url))
                text.config(cursor="hand2")

        text.config(state=tk.DISABLED)

    def _goto_puzzle(self) -> None:
        if not getattr(self, "_filter_total", 0):
            messagebox.showinfo(t("about_title"), t("status_not_found"))
            return

        raw = self.goto_entry.get().strip()
        if not raw:
            return

        try:
            num = int(raw)
        except ValueError:
            messagebox.showwarning(t("about_title"), t("goto_puzzle_invalid"))
            return

        total = self._filter_total
        if num < 1 or num > total:
            messagebox.showwarning(
                t("about_title"),
                f"{t('goto_puzzle_invalid')} (1-{total})",
            )
            return

        target_index = num - 1
        self.goto_entry.delete(0, tk.END)

        # If a goto is already running, queue this one instead of dropping it.
        if getattr(self, "_goto_thread", None) and self._goto_thread.is_alive():
            self._pending_goto_target = target_index
            self.status_label.config(text=t("status_loading"))
            return

        self._pending_goto_target = None
        self._start_goto_load(target_index)

    def _start_goto_load(self, target_index: int) -> None:
        self.status_label.config(text=t("status_loading"))
        self.root.update_idletasks()

        def run():
            try:
                needed = target_index + 1
                offset = len(self.filtered_puzzles)
                limit = needed - offset

                batch = self.db.filter_puzzles(
                    **self._filter_values,
                    limit=limit,
                    offset=offset,
                    return_total=False,
                )
                self.filtered_puzzles = list(self.filtered_puzzles) + list(batch)
                self._filter_offset = len(self.filtered_puzzles)

                if target_index < len(self.filtered_puzzles):
                    self.root.after(0, lambda: self._on_goto_loaded(target_index))
                else:
                    self.root.after(0, lambda: self.status_label.config(text=t("status_not_found")))
            except Exception as exc:
                logger.exception("Goto puzzle failed: %s", exc)
                self.root.after(0, lambda: self.status_label.config(text=f"Error: {exc}"))

        self._goto_thread = threading.Thread(target=run, daemon=True)
        self._goto_thread.start()

    def _on_goto_loaded(self, target_index: int) -> None:
        self.status_label.config(
            text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total)
        )
        if target_index < len(self.filtered_puzzles):
            self._show_puzzle(target_index)
            self._save_session()
        else:
            self.status_label.config(text=t("status_not_found"))

        # If a new goto was requested while this one was loading, run it now.
        pending = self._pending_goto_target
        self._pending_goto_target = None
        if pending is not None and pending != target_index:
            self._start_goto_load(pending)

    def _open_url(self, url: str) -> None:
        import webbrowser
        webbrowser.open(url)

    def _delete_user_themes_dialog(self) -> None:
        user_themes = self.db.get_user_themes()
        if not user_themes:
            messagebox.showinfo(t("delete_user_themes_title"), t("msg_no_user_themes"))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(t("delete_user_themes_title"))
        dialog.geometry("400x420")
        dialog.minsize(360, 320)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=t("delete_user_themes_select")).pack(anchor=tk.W, padx=10, pady=(10, 0))

        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 10))
        listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED, exportselection=False)
        scroll = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scroll.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        for theme in user_themes:
            listbox.insert(tk.END, theme)

        def on_delete():
            selected = [listbox.get(i) for i in listbox.curselection()]
            if not selected:
                messagebox.showinfo(t("delete_user_themes_title"), t("msg_no_user_themes"), parent=dialog)
                return
            self.db.delete_user_themes(selected)
            self._refresh_user_themes()
            self._refresh_exclude_user_themes()
            if getattr(self, "_filter_values", {}).get("user_themes"):
                active = [t for t in self._filter_values["user_themes"] if t in self.db.get_user_themes()]
                if not active:
                    self.user_themes_var.set("")
                    self.user_themes_cb.set("")
            if getattr(self, "_filter_values", {}).get("exclude_user_themes"):
                active_exclude = [t for t in self._filter_values["exclude_user_themes"] if t in self.db.get_user_themes()]
                if not active_exclude:
                    self.exclude_themes_listbox.selection_clear(0, tk.END)
            messagebox.showinfo(t("delete_user_themes_title"), t("msg_user_themes_deleted", count=len(selected)), parent=dialog)
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text=t("delete_user_themes_btn"), command=on_delete).pack(fill=tk.X)


    # ------------------------------------------------------------------
    # Завершение
    # ------------------------------------------------------------------
    def destroy(self) -> None:
        self._save_session()
        self.db.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    _app = PuzzleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
