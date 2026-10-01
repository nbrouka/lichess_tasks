"""
Графический интерфейс приложения Lichess Puzzle Viewer на Tkinter.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import json
import os
from pathlib import Path
from typing import List, Optional

from database import PuzzleDatabase, Puzzle
from constants import (
    APP_NAME, VERSION, DEFAULT_CSV_PATH, DB_FILENAME,
    BOARD_SIZE, COLOR_LIGHT, COLOR_DARK,
    THEME_TRANSLATIONS, THEME_RU_TO_EN,
    CATEGORY_TRANSLATIONS, CATEGORY_RU_TO_EN,
    UI_TRANSLATIONS, LANG, t, COLOR_RU_TO_EN,
    WINDOW_GEOMETRY, WINDOW_MINSIZE,
    FILTERS_PANEL_WIDTH, SELECTED_PANEL_WIDTH,
    EXCLUDE_THEMES_LISTBOX_HEIGHT,
    THEMES_LISTBOX_HEIGHT,
    ICON_WINDOWS, ICON_LINUX,
)

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
        self._set_window_icon()

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

        self._build_menu()
        self._build_layout()
        self._init_filters()
        self._bind_events()
        self._reset_filters()
        self._load_themes_data()

        # БД может быть уже готова, если файл существует
        if self.db.is_imported():
            self._on_db_ready()
        else:
            self.status_label.config(text=t("status_db_not_ready"))

    def _set_window_icon(self) -> None:
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

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=t("menu_about"), command=self._show_about)
        menubar.add_cascade(label=t("menu_help"), menu=help_menu)

        self.root.config(menu=menubar)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
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
            state="readonly", width=35,
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
        messagebox.showinfo(
            t("about_title"),
            t("about_text"),
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
