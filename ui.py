"""
Графический интерфейс приложения Lichess Puzzle Viewer на Tkinter.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
from pathlib import Path
from typing import List, Optional

from database import PuzzleDatabase, Puzzle
from constants import (
    DEFAULT_CSV_PATH, DB_FILENAME, THEME_TRANSLATIONS, t,
    WINDOW_MINSIZE, FILTERS_PANEL_WIDTH, SELECTED_PANEL_WIDTH,
    EXCLUDE_THEMES_LISTBOX_HEIGHT, THEMES_LISTBOX_HEIGHT,
    COMBOBOX_WIDTH, COLOR_COMBOBOX_WIDTH,
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

        self._build_menu()
        self._build_layout()
        self._init_filters()
        self._bind_events()
        self._load_themes_data()

        # БД может быть уже готова, если файл существует
        self._reset_filters()

        if self.db.is_imported():
            self._on_db_ready()
        else:
            self.status_label.config(text=t("status_db_not_ready"))

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
        self.image_label.configure(anchor="center")
        self.image_label.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        details_btn = ttk.Button(center, text="См. детали задачи", command=self._show_puzzle_details)
        details_btn.grid(row=1, column=0, sticky="ew", pady=(0, 10))

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
        self.db.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    _app = PuzzleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
