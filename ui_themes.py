"""
Mixin for theme/category loading and selection in Lichess Puzzle Viewer.
"""

import tkinter as tk
from pathlib import Path
import json
from typing import Optional

from constants import CATEGORY_TRANSLATIONS, THEME_TRANSLATIONS, t, get_themes_file


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

        category = self._category_var.get()
        cat_themes = self.themes_data.get(category, {})

        theme_counts = {}
        if self.db.is_imported():
            theme_counts = self.db.get_theme_counts()

        self.themes_listbox.delete(0, tk.END)
        for data in cat_themes.values():
            theme_id = data.get("id", "")
            if self._available_theme_ids and theme_id not in self._available_theme_ids:
                continue
            ru_name = THEME_TRANSLATIONS.get(theme_id, data.get("name", ""))
            count = theme_counts.get(theme_id, 0)
            display = f"{ru_name} ({count})" if count else ru_name
            self.themes_listbox.insert(tk.END, display)

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

        theme_counts = {}
        if self.db.is_imported():
            theme_counts = self.db.get_theme_counts()

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

        self._reset_themes_listbox_to_all(theme_counts)

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
        self.themes_listbox.delete(0, tk.END)
        if theme_counts is None:
            theme_counts = self.db.get_theme_counts() if self.db.is_imported() else {}
        for theme in sorted(getattr(self, "_available_theme_ids", set())):
            count = theme_counts.get(theme, 0)
            display = THEME_TRANSLATIONS.get(theme, theme)
            if count:
                display = f"{display} ({count})"
            self.themes_listbox.insert(tk.END, display)

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
