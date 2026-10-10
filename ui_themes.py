"""
Mixin for theme/category loading and selection in Lichess Puzzle Viewer.
"""

import logging
import threading
import tkinter as tk
from pathlib import Path
import json
from typing import Optional

from constants import CATEGORY_TRANSLATIONS, THEME_TRANSLATIONS, t, get_themes_file

logger = logging.getLogger(__name__)


class PuzzleThemesMixin:
    def _load_themes_data(self) -> None:
        path = Path(get_themes_file())
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
                for theme in cat.get("themes", []):
                    themes[theme.get("name", "")] = theme
                self.themes_data[ru_name] = themes
        except Exception:
            pass

    def _on_category_selected(self, event=None) -> None:
        """
        При выборе категории заполняет список стандартных тем.

        Если выбрана пользовательская тема, сбрасываем её, чтобы не было
        конфликта между стандартными и пользовательскими темами.
        """
        if self.user_themes_var.get():
            self.user_themes_var.set("")
            self.user_themes_cb.set("")

        self._themes_listbox_scope = "category"
        self._populate_themes_listbox()

    def _populate_themes_listbox(self, theme_counts: Optional[dict] = None) -> None:
        """Заполняет список тем текущей области (все темы или категория).

        Счётчики берём из кэша UI: GROUP BY по 27M строк puzzle_themes занимает
        ~1.3 с, поэтому при старте он считается в фоне
        (_schedule_theme_counts_refresh), а список тем появляется сразу.
        """
        if theme_counts is None:
            theme_counts = getattr(self, "_theme_counts_cache", None) or {}
        scope = getattr(self, "_themes_listbox_scope", "all")

        if scope == "category":
            cat_themes = self.themes_data.get(self._category_var.get(), {})
            items = list(cat_themes.values())
        else:
            items = [
                {"id": theme_id, "name": THEME_TRANSLATIONS.get(theme_id, theme_id)}
                for theme_id in sorted(getattr(self, "_available_theme_ids", set()))
            ]

        self.themes_listbox.delete(0, tk.END)
        for data in items:
            theme_id = data.get("id", "")
            if scope == "category" and self._available_theme_ids \
                    and theme_id not in self._available_theme_ids:
                continue
            ru_name = THEME_TRANSLATIONS.get(theme_id, data.get("name", ""))
            count = theme_counts.get(theme_id, 0)
            display = f"{ru_name} ({count})" if count else ru_name
            self.themes_listbox.insert(tk.END, display)

    def _schedule_theme_counts_refresh(self) -> None:
        """Считает счётчики тем в фоне и обновляет список, сохраняя выделение.

        GROUP BY по всей таблице puzzle_themes на старте блокировал появление
        окна на ~1.3 с. Теперь список тем заполняется сразу, а счётчики
        дорисовываются, когда посчитаются. Воркер только пишет результат в
        атрибут — применять его и трогать Tk может только главный поток
        (поллер ниже), иначе закрытие окна во время расчёта роняет процесс.
        """
        if not self.db.is_imported():
            return
        if getattr(self, "_theme_counts_thread", None) and self._theme_counts_thread.is_alive():
            self._theme_counts_pending = True
            return
        self._theme_counts_pending = False
        self._theme_counts_result = None
        self._theme_counts_done = False

        def run():
            if getattr(self, "_shutting_down", False):
                return
            try:
                counts = self.db.get_theme_counts()
            except Exception:
                logger.exception("get_theme_counts failed")
                counts = None
            self._theme_counts_result = counts
            self._theme_counts_done = True

        self._theme_counts_thread = threading.Thread(target=run, daemon=True)
        self._theme_counts_thread.start()
        self._poll_theme_counts()

    def _poll_theme_counts(self) -> None:
        """Забирает результат подсчёта в главном потоке (без Tk из воркера)."""
        if getattr(self, "_theme_counts_done", False):
            self._theme_counts_done = False
            counts = self._theme_counts_result
            self._theme_counts_result = None
            self._on_theme_counts_ready(counts)
            return
        thread = getattr(self, "_theme_counts_thread", None)
        if thread is not None and thread.is_alive():
            self.root.after(100, self._poll_theme_counts)

    def _on_theme_counts_ready(self, counts) -> None:
        if counts is not None:
            self._theme_counts_cache = counts
            selected = list(self.themes_listbox.curselection())
            self._populate_themes_listbox(counts)
            for index in selected:
                self.themes_listbox.selection_set(index)
        if getattr(self, "_theme_counts_pending", False):
            self._schedule_theme_counts_refresh()

    def _on_db_ready(self) -> None:
        """
        Вызывается после завершения импорта БД.

        Заполняет список стандартных тем, обновляет категории,
        сбрасывает выбранные темы и заполняет пользовательские темы.
        """
        themes = self.db.get_all_themes()
        self._available_theme_ids = set(themes)
        self.status_label.config(text=t("status_db_ready"))

        self._refresh_user_themes()
        self._refresh_exclude_user_themes()

        filtered_categories = []
        filtered_themes_data = {}
        for cat_name, cat_themes in self.themes_data.items():
            available = {}
            for name, data in cat_themes.items():
                theme_id = data.get("id", "")
                if theme_id in self._available_theme_ids:
                    available[name] = data
            if available:
                filtered_categories.append(cat_name)
                filtered_themes_data[cat_name] = available

        self.themes_data = filtered_themes_data
        self.category_cb["values"] = filtered_categories
        self._category_var.set("")

        # Счётчики тем считаются в фоне: GROUP BY по puzzle_themes занимает
        # ~1.3 с и блокировал появление окна на старте.
        self._reset_themes_listbox_to_all()
        self._schedule_theme_counts_refresh()

    def _refresh_user_themes(self) -> None:
        user_themes = self.db.get_user_themes()
        themes_with_counts = []
        for theme in user_themes:
            count = self.db.get_user_theme_puzzle_count(theme)
            display = f"{theme} ({count})" if count else theme
            themes_with_counts.append(display)
        self.user_themes_cb["values"] = [""] + themes_with_counts
        self.user_themes_var.set("")

    def _on_standard_theme_selected(self, event=None) -> None:
        if self.themes_listbox.curselection():
            self.user_themes_var.set("")
            self.user_themes_cb.set("")

    def _on_user_theme_selected(self, event=None) -> None:
        value = self.user_themes_var.get()
        if value:
            self._category_var.set("")
            self.category_cb.set("")
            self.themes_listbox.selection_clear(0, tk.END)
            self.exclude_themes_listbox.selection_clear(0, tk.END)

    def _on_exclude_user_theme_selected(self, event=None) -> None:
        if self.exclude_themes_listbox.curselection():
            self.user_themes_var.set("")
            self.user_themes_cb.set("")

    def _reset_themes_listbox_to_all(self, theme_counts: Optional[dict] = None) -> None:
        self._themes_listbox_scope = "all"
        self._populate_themes_listbox(theme_counts)

    def _refresh_exclude_user_themes(self) -> None:
        user_themes = self.db.get_user_themes()
        self.exclude_themes_listbox.delete(0, tk.END)
        for theme in user_themes:
            count = self.db.get_user_theme_puzzle_count(theme)
            display = f"{theme} ({count})" if count else theme
            self.exclude_themes_listbox.insert(tk.END, display)

    def _exclude_all_user_themes(self) -> None:
        self.exclude_themes_listbox.selection_set(0, tk.END)

    def _exclude_none_user_themes(self) -> None:
        self.exclude_themes_listbox.selection_clear(0, tk.END)
