"""
Mixin for theme/category loading and selection in Lichess Puzzle Viewer.
"""

import tkinter as tk
from pathlib import Path
import json

from constants import CATEGORY_TRANSLATIONS, THEME_TRANSLATIONS, CATEGORY_RU_TO_EN, t


class PuzzleThemesMixin:
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
        if self.user_themes_var.get():
            self.user_themes_var.set("")
            self.user_themes_cb.set("")

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

    def _on_db_ready(self) -> None:
        themes = self.db.get_all_themes()
        self._available_theme_ids = set(themes)
        self.themes_listbox.delete(0, tk.END)
        for theme in sorted(themes):
            display = THEME_TRANSLATIONS.get(theme, theme)
            self.themes_listbox.insert(tk.END, display)
        self.status_label.config(text=t("status_db_ready"))

        self._refresh_user_themes()
        self._refresh_exclude_user_themes()

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

    def _refresh_user_themes(self) -> None:
        user_themes = self.db.get_user_themes()
        self.user_themes_cb["values"] = [""] + user_themes
        self.user_themes_var.set("")

    def _on_standard_theme_selected(self, event=None) -> None:
        if self.themes_listbox.curselection():
            self.user_themes_var.set("")
            self.user_themes_cb.set("")

    def _on_user_theme_selected(self, event=None) -> None:
        if self.user_themes_var.get():
            self._category_var.set("")
            self.category_cb.set("")
            self.themes_listbox.selection_clear(0, tk.END)
            self.exclude_themes_listbox.selection_clear(0, tk.END)

    def _on_exclude_user_theme_selected(self, event=None) -> None:
        if self.exclude_themes_listbox.curselection():
            self.user_themes_var.set("")
            self.user_themes_cb.set("")

    def _reset_themes_listbox_to_all(self) -> None:
        self.themes_listbox.delete(0, tk.END)
        for theme in sorted(getattr(self, "_available_theme_ids", set())):
            display = THEME_TRANSLATIONS.get(theme, theme)
            self.themes_listbox.insert(tk.END, display)

    def _refresh_exclude_user_themes(self) -> None:
        user_themes = self.db.get_user_themes()
        self.exclude_themes_listbox.delete(0, tk.END)
        for theme in user_themes:
            self.exclude_themes_listbox.insert(tk.END, theme)

    def _exclude_all_user_themes(self) -> None:
        self.exclude_themes_listbox.selection_set(0, tk.END)

    def _exclude_none_user_themes(self) -> None:
        self.exclude_themes_listbox.selection_clear(0, tk.END)
