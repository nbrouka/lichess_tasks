#!/usr/bin/env python3
"""Tests for Lichess Puzzle Viewer filters, translations, and theme parsing."""

import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import tkinter as tk
from tkinter import ttk
from PIL import Image
from docx import Document

from constants import (
    UI_TRANSLATIONS,
    LANG,
    t,
    THEME_TRANSLATIONS,
    THEME_RU_TO_EN,
    CATEGORY_TRANSLATIONS,
    CATEGORY_RU_TO_EN,
    COLOR_RU_TO_EN,
)
from parse_themes import parse_themes, clean
from database import PuzzleDatabase, Puzzle
from ui import PuzzleApp


THEME_HTML_SNIPPET = """
<h2 id="puzzle:phases">Phases</h2>
<div class="puzzle-themes__list puzzle-phases">
  <a class="puzzle-themes__link" href="/training/opening">
    <span>
      <h3>Opening<em class="puzzle-themes__count">321,447</em></h3>
      <span>A tactic during the first phase of the game.</span>
    </span>
  </a>
  <a class="puzzle-themes__link" href="/training/middlegame">
    <span>
      <h3>Middlegame<em class="puzzle-themes__count">2,917,156</em></h3>
      <span>A tactic during the second phase of the game.</span>
    </span>
  </a>
</div>
"""


class TestThemeParser(unittest.TestCase):
    def test_parse_themes_returns_categories(self):
        data = parse_themes(THEME_HTML_SNIPPET)
        self.assertIn("categories", data)
        self.assertEqual(len(data["categories"]), 1)

    def test_parse_themes_extracts_theme_fields(self):
        data = parse_themes(THEME_HTML_SNIPPET)
        themes = data["categories"][0]["themes"]
        self.assertEqual(len(themes), 2)
        self.assertEqual(themes[0]["id"], "opening")
        self.assertEqual(themes[0]["name"], "Opening")
        self.assertEqual(themes[0]["count"], "321,447")
        self.assertEqual(themes[0]["description"], "A tactic during the first phase of the game.")

    def test_clean_strips_tags(self):
        self.assertEqual(clean("<b>Bold</b>"), "Bold")
        self.assertEqual(clean("  spaced  "), "spaced")


class TestThemeTranslations(unittest.TestCase):
    def test_theme_translation_keys_non_empty(self):
        self.assertGreaterEqual(len(THEME_TRANSLATIONS), 1)

    def test_theme_roundtrip_ru_en(self):
        for en, ru in THEME_TRANSLATIONS.items():
            self.assertEqual(THEME_RU_TO_EN[ru], en)

    def test_category_translation_keys_non_empty(self):
        self.assertGreaterEqual(len(CATEGORY_TRANSLATIONS), 1)

    def test_category_roundtrip_ru_en(self):
        for en, ru in CATEGORY_TRANSLATIONS.items():
            self.assertEqual(CATEGORY_RU_TO_EN[ru], en)

    def test_color_roundtrip(self):
        self.assertEqual(COLOR_RU_TO_EN["Ход белых"], "w")
        self.assertEqual(COLOR_RU_TO_EN["Ход черных"], "b")


class TestUITranslations(unittest.TestCase):
    def test_ru_language_default(self):
        self.assertEqual(LANG, "ru")

    def test_required_keys_exist_in_ru(self):
        required = [
            "app_title",
            "menu_file",
            "menu_help",
            "filters_title",
            "moves_label",
            "color_label",
            "category_label",
            "themes_label",
            "apply_btn",
            "reset_btn",
            "found_label",
            "prev_btn",
            "save_png_btn",
            "next_btn",
            "status_ready",
            "status_filtering",
            "status_loaded",
            "status_not_found",
            "status_reset",
            "status_import_started",
            "status_import_complete",
            "status_db_ready",
            "status_db_not_ready",
            "puzzle_info",
            "no_data",
            "toggle_filter_on",
            "toggle_filter_off",
            "scale_equals",
            "progress_pct",
        ]
        ru = UI_TRANSLATIONS["ru"]
        for key in required:
            self.assertIn(key, ru)
            self.assertTrue(ru[key])

    def test_required_keys_exist_in_en(self):
        required = [
            "app_title",
            "menu_file",
            "menu_help",
            "filters_title",
            "moves_label",
            "color_label",
            "category_label",
            "themes_label",
            "apply_btn",
            "reset_btn",
            "found_label",
            "prev_btn",
            "save_png_btn",
            "next_btn",
            "status_ready",
            "status_filtering",
            "status_loaded",
            "status_not_found",
            "status_reset",
            "status_import_started",
            "status_import_complete",
            "status_db_ready",
            "status_db_not_ready",
            "puzzle_info",
            "no_data",
            "toggle_filter_on",
            "toggle_filter_off",
            "scale_equals",
            "progress_pct",
        ]
        en = UI_TRANSLATIONS["en"]
        for key in required:
            self.assertIn(key, en)
            self.assertTrue(en[key])

    def test_format_keys_present(self):
        for lang in ("ru", "en"):
            self.assertIn("{count}", UI_TRANSLATIONS[lang]["found_label"])
            self.assertIn("{index}", UI_TRANSLATIONS[lang]["puzzle_info"])
            self.assertIn("{total}", UI_TRANSLATIONS[lang]["puzzle_info"])
            self.assertIn("{pct}", UI_TRANSLATIONS[lang]["progress_pct"])


class TestFilterCombinations(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = PuzzleApp(self.root)

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            self.root.destroy()

    def test_get_filter_values_color_white(self):
        self.app.filter_widgets["color"].set("Ход белых")
        values = self.app._get_filter_values()
        self.assertEqual(values["color"], "b")

    def test_get_filter_values_color_black(self):
        self.app.filter_widgets["color"].set("Ход черных")
        values = self.app._get_filter_values()
        self.assertEqual(values["color"], "w")

    def test_get_filter_values_color_empty(self):
        self.app.filter_widgets["color"].set("")
        values = self.app._get_filter_values()
        self.assertIsNone(values["color"])

    def test_get_filter_values_moves_disabled(self):
        values = self.app._get_filter_values()
        self.assertIsNone(values["moves_exact"])

    def test_category_filter_updates_listbox(self):
        self.app._category_var.set("Фазы")
        self.app._on_category_selected()
        self.assertEqual(self.app.themes_listbox.size(), 9)
        all_items = [self.app.themes_listbox.get(i) for i in range(self.app.themes_listbox.size())]
        self.assertTrue(
            any(item.startswith("Дебют (") and item.endswith(")") for item in all_items),
            msg=f"Expected 'Дебют (count)' in {all_items}",
        )
        debut_item = next(item for item in all_items if item.startswith("Дебют ("))
        expected_count = self.app.db.get_theme_counts().get("opening", 0)
        self.assertEqual(debut_item, f"Дебют ({expected_count})")

    def test_category_filter_hides_missing_themes(self):
        self.app._available_theme_ids = {"opening", "middlegame", "endgame"}
        self.app._category_var.set("Фазы")
        self.app._on_category_selected()
        self.assertEqual(self.app.themes_listbox.size(), 3)

    def test_empty_categories_removed_after_db_ready(self):
        self.app.themes_data = {
            "Рекомендуемые": {"healthyMix": {"id": "healthyMix", "name": "Healthy mix", "count": "123"}},
            "Фазы": {
                "opening": {"id": "opening", "name": "Opening", "count": "321,447"},
                "middlegame": {"id": "middlegame", "name": "Middlegame", "count": "2,917,156"},
                "endgame": {"id": "endgame", "name": "Endgame", "count": "3,165,937"},
            },
        }
        with patch.object(self.app.db, "get_all_themes", return_value=["opening", "middlegame", "endgame"]):
            self.app._on_db_ready()
        self.assertNotIn("Рекомендуемые", self.app.category_cb["values"])
        self.assertIn("Фазы", self.app.category_cb["values"])

    def test_apply_filter_does_not_raise(self):
        from unittest.mock import patch

        call_count = [0]

        def limited_after(ms, func, *args):
            call_count[0] += 1
            if call_count[0] <= 4:
                return func()
            return None

        with patch.object(self.app.root, "after", limited_after), \
             patch.object(self.app.root, "after_cancel", lambda id: None), \
             patch.object(threading, "Thread", lambda **kwargs: type("FakeThread", (), {"start": lambda self: None})()):
            self.app._apply_filter()

    def test_pagination_loads_more_when_at_end(self):
        PuzzleMock = type('Puzzle', (), {
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'moves': 'e2e4 e7e5',
            'color': 'w',
            'puzzle_id': 'test',
            'rating': 1500,
            'popularity': 80,
            'nb_plays': 100,
            'themes': ['opening'],
            'opening_tags': ['Italian Game'],
            'game_url': 'http://example.com',
            'solution': 'e7e5',
        })
        self.app.filtered_puzzles = [PuzzleMock()]
        self.app.current_index = 0
        self.app._filter_total = 150
        self.app._filter_offset = 1
        self.app._filter_values = {"color": "b"}

        def fake_filter(**kwargs):
            return [PuzzleMock()] * 99

        self.app.db.filter_puzzles = fake_filter

        original_after = self.app.root.after
        def immediate_after(ms, func, *args):
            return func()

        class FakeThread:
            def __init__(self, target=None, daemon=None):
                self._target = target
            def start(self):
                if self._target:
                    self._target()

        with patch.object(self.app, "_show_puzzle", lambda index: None), \
             patch.object(self.app.root, "after", immediate_after), \
             patch.object(threading, "Thread", FakeThread):
            self.app._next_puzzle()

        self.assertEqual(len(self.app.filtered_puzzles), 100)
        self.assertEqual(self.app._filter_offset, 100)

    def test_stats_displayed_after_filter(self):
        PuzzleMock = type('Puzzle', (), {
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'moves': 'e2e4 e7e5',
            'color': 'w',
            'puzzle_id': 'test',
            'rating': 1500,
            'popularity': 80,
            'nb_plays': 100,
            'themes': ['opening'],
            'opening_tags': ['Italian Game'],
            'game_url': 'http://example.com',
            'solution': 'e7e5',
        })
        self.app._filter_values = {"color": "w"}
        self.app._filter_total = 10
        self.app._filter_offset = 2
        self.app.filtered_puzzles = [PuzzleMock(), PuzzleMock()]

        with patch.object(self.app, "_show_puzzle", lambda index: None), \
             patch.object(self.app.db, "get_stats", return_value={"white": 5, "black": 3, "by_moves": {1: 5, 2: 3}}):
            self.app._update_stats()

        text = self.app.stats_label.cget("text")
        self.assertIn("Ход белых: 3", text)
        self.assertIn("Ход черных: 5", text)

    def test_solution_navigation(self):
        PuzzleMock = type('Puzzle', (), {
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'moves': 'e2e4 e7e5 g1f3',
            'color': 'w',
            'puzzle_id': 'test',
            'rating': 1500,
            'popularity': 80,
            'nb_plays': 100,
            'themes': ['opening'],
            'opening_tags': ['Italian Game'],
            'game_url': 'http://example.com',
            'solution': 'e7e5 g1f3',
        })
        self.app.filtered_puzzles = [PuzzleMock()]
        self.app.current_index = 0

        with patch.object(self.app, "_update_solution_board") as mock_board, \
             patch.object(self.app, "_update_solution_step_label") as mock_label, \
             patch.object(self.app, "_update_info_text") as mock_info:
            self.app._show_puzzle(0)

        self.assertEqual(self.app._solution_step, 1)
        mock_board.assert_called_once()
        mock_label.assert_called_once()
        mock_info.assert_called_once()

        with patch.object(self.app, "_update_solution_board") as mock_board, \
             patch.object(self.app, "_update_solution_step_label") as mock_label:
            self.app._next_solution_step()

        self.assertEqual(self.app._solution_step, 2)
        mock_board.assert_called_once()
        mock_label.assert_called_once()

        with patch.object(self.app, "_update_solution_board") as mock_board, \
             patch.object(self.app, "_update_solution_step_label") as mock_label:
            self.app._prev_solution_step()

        self.assertEqual(self.app._solution_step, 1)
        mock_board.assert_called_once()
        mock_label.assert_called_once()

        with patch.object(self.app, "_update_solution_board") as mock_board, \
             patch.object(self.app, "_update_solution_step_label") as mock_label:
            self.app._go_to_solution_start()

        self.assertEqual(self.app._solution_step, 1)
        mock_board.assert_called_once()
        mock_label.assert_called_once()

        with patch.object(self.app, "_update_solution_board") as mock_board, \
             patch.object(self.app, "_update_solution_step_label") as mock_label:
            self.app._go_to_solution_end()

        self.assertEqual(self.app._solution_step, 3)
        mock_board.assert_called_once()
        mock_label.assert_called_once()

    def test_clickable_game_url(self):
        PuzzleMock = type('Puzzle', (), {
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'moves': 'e2e4 e7e5',
            'color': 'w',
            'puzzle_id': 'test',
            'rating': 1500,
            'popularity': 80,
            'nb_plays': 100,
            'themes': ['opening'],
            'opening_tags': ['Italian Game'],
            'game_url': 'http://example.com',
            'solution': 'e7e5',
        })
        self.app.filtered_puzzles = [PuzzleMock()]
        self.app.current_index = 0

        with patch('webbrowser.open') as mock_open:
            self.app._update_info_text(PuzzleMock())
            tags = self.app.info_text.tag_names()
            self.assertIn('link', tags)
            self.app._open_url('http://example.com')
            mock_open.assert_called_once_with('http://example.com')

    def test_add_to_selected(self):
        PuzzleMock = type('Puzzle', (), {
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'moves': 'e2e4 e7e5',
            'color': 'w',
            'puzzle_id': 'test123',
            'rating': 1500,
            'popularity': 80,
            'nb_plays': 100,
            'themes': ['opening'],
            'opening_tags': ['Italian Game'],
            'game_url': 'http://example.com',
            'solution': 'e7e5',
        })
        self.app.filtered_puzzles = [PuzzleMock()]
        self.app.current_index = 0
        self.app.selected_puzzles = []

        with patch('ui_selection.render_puzzle', return_value=Image.new('RGB', (80, 80), '#FFF')):
            self.app._add_to_selected()

        self.assertEqual(len(self.app.selected_puzzles), 1)
        self.assertEqual(len(self.app.selected_inner.winfo_children()), 1)

        added_puzzle = self.app.selected_puzzles[0]
        wrapper = self.app.selected_inner.winfo_children()[0]
        self.app._remove_from_selected(added_puzzle, wrapper)
        self.assertEqual(len(self.app.selected_puzzles), 0)
        self.assertEqual(len(self.app.selected_inner.winfo_children()), 0)


class TestDatabaseFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = ":memory:"
        cls.csv_path = os.path.join(cls.temp_dir, "test.csv")

    def setUp(self):
        self.db = PuzzleDatabase(db_path=self.db_path, csv_path=self.csv_path)

    def tearDown(self):
        self.db.conn.close()

    def _write_csv(self, rows):
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            f.write("PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags,DailyDate\n")
            for row in rows:
                f.write(row + "\n")

    def test_filter_by_color(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3,1600,25,90,200,motif,http://example.com,Scandinavian Defense,2023-01-02",
        ])
        self.db.import_csv()
        puzzles = self.db.filter_puzzles(color="w", limit=10)
        self.assertEqual(len(puzzles), 1)
        self.assertEqual(puzzles[0].puzzle_id, "00001")

    def test_filter_by_theme(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3,1600,25,90,200,motif fork,http://example.com,Scandinavian Defense,2023-01-02",
        ])
        self.db.import_csv()
        puzzles = self.db.filter_puzzles(themes=["fork"], limit=10)
        self.assertEqual(len(puzzles), 1)
        self.assertEqual(puzzles[0].puzzle_id, "00002")

    def test_filter_by_moves_exact(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3 e4e5 e5e4,1600,25,90,200,motif,http://example.com,Scandinavian Defense,2023-01-02",
        ])
        self.db.import_csv()
        puzzles = self.db.filter_puzzles(moves_exact=1, limit=10)
        self.assertEqual(len(puzzles), 1)
        self.assertEqual(puzzles[0].puzzle_id, "00001")

    def test_combined_filters(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3 e4e5 e5e4,1600,25,90,200,motif fork,http://example.com,Scandinavian Defense,2023-01-02",
        ])
        self.db.import_csv()
        puzzles = self.db.filter_puzzles(color="b", themes=["fork"], moves_exact=2, limit=10)
        self.assertEqual(len(puzzles), 1)
        self.assertEqual(puzzles[0].puzzle_id, "00002")

    def test_get_stats_counts_colors(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3,1600,25,90,200,motif,http://example.com,Scandinavian Defense,2023-01-02",
        ])
        self.db.import_csv()
        stats = self.db.get_stats()
        self.assertEqual(stats["white"], 1)
        self.assertEqual(stats["black"], 1)

    def test_get_stats_counts_moves(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3 e4e5 e5e4,1600,25,90,200,motif fork,http://example.com,Scandinavian Defense,2023-01-02",
        ])
        self.db.import_csv()
        stats = self.db.get_stats()
        self.assertEqual(stats["by_moves"][1], 1)
        self.assertEqual(stats["by_moves"][2], 1)

    def test_get_stats_counts_user_themes(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5 g1f3,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3 e4e5 e5e4,1600,25,90,200,motif fork,http://example.com,Scandinavian Defense,2023-01-02",
            "00003,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5 g1f3,1700,20,95,300,opening,http://example.com,Italian Game,2023-01-03",
        ])
        self.db.import_csv()
        self.db.get_or_create_user_theme("Моя тема")
        theme_id = self.db.get_or_create_user_theme("Моя тема")
        self.db.link_puzzles_to_user_theme(theme_id, ["00001", "00003"])

        stats = self.db.get_stats({"user_themes": ["Моя тема"]})
        self.assertEqual(stats["white"], 1)
        self.assertEqual(stats["black"], 1)
        self.assertEqual(stats["by_moves"][1], 2)

    def test_filter_exclude_user_themes(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5 g1f3,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3 e4e5 e5e4,1600,25,90,200,motif fork,http://example.com,Scandinavian Defense,2023-01-02",
            "00003,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5 g1f3,1700,20,95,300,opening,http://example.com,Italian Game,2023-01-03",
        ])
        self.db.import_csv()
        self.db.get_or_create_user_theme("Моя тема")
        theme_id = self.db.get_or_create_user_theme("Моя тема")
        self.db.link_puzzles_to_user_theme(theme_id, ["00001", "00003"])

        puzzles = self.db.filter_puzzles(exclude_user_themes=["Моя тема"], limit=10)
        self.assertEqual(len(puzzles), 1)
        self.assertEqual(puzzles[0].puzzle_id, "00002")

    def test_verify_import_returns_report(self):
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5 g1f3,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3 e4e5 e5e4,1600,25,90,200,motif fork,http://example.com,Scandinavian Defense,2023-01-02",
            "00003,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5 g1f3,1700,20,95,300,opening,http://example.com,Italian Game,2023-01-03",
        ])
        self.db.import_csv()
        report = self.db.verify_import(self.db.csv_path)
        self.assertEqual(report["local_total"], 3)
        self.assertEqual(report["csv_total"], 3)
        self.assertTrue(report["matches"])
        self.assertEqual(report["mismatches"], 0)


class TestDocxExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = ":memory:"
        cls.csv_path = os.path.join(cls.temp_dir, "test.csv")

    def setUp(self):
        self.db = PuzzleDatabase(db_path=self.db_path, csv_path=self.csv_path)
        self._write_csv([
            "00001,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,1500,30,80,100,opening,http://example.com,Italian Game,2023-01-01",
            "00002,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3,1600,25,90,200,motif,http://example.com,Scandinavian Defense,2023-01-02",
            "00003,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5,1700,20,95,300,opening,http://example.com,Italian Game,2023-01-03",
            "00004,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5 g1f3,1800,35,70,400,motif fork,http://example.com,Italian Game,2023-01-04",
            "00005,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 e2e4,1900,40,60,500,opening,http://example.com,Scandinavian Defense,2023-01-05",
            "00006,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,2000,45,50,600,motif,http://example.com,Italian Game,2023-01-06",
            "00007,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3 b8c6,2100,50,40,700,opening,http://example.com,Scandinavian Defense,2023-01-07",
            "00008,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5,2200,55,30,800,motif fork,http://example.com,Italian Game,2023-01-08",
            "00009,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,2300,60,20,900,opening,http://example.com,Italian Game,2023-01-09",
            "00010,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 e2e4,2400,65,10,1000,motif,http://example.com,Scandinavian Defense,2023-01-10",
            "00011,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,2500,70,5,1100,opening,http://example.com,Italian Game,2023-01-11",
            "00012,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5,2600,75,3,1200,motif fork,http://example.com,Italian Game,2023-01-12",
            "00013,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,2700,80,2,1300,opening,http://example.com,Scandinavian Defense,2023-01-13",
            "00014,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3,2800,85,1,1400,motif,http://example.com,Italian Game,2023-01-14",
            "00015,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5,2900,90,0,1500,opening,http://example.com,Italian Game,2023-01-15",
            "00016,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,3000,95,0,1600,motif fork,http://example.com,Scandinavian Defense,2023-01-16",
            "00017,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 e2e4,3100,100,0,1700,opening,http://example.com,Italian Game,2023-01-17",
            "00018,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5,3200,10,0,1800,motif,http://example.com,Italian Game,2023-01-18",
            "00019,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,3300,15,0,1900,opening,http://example.com,Scandinavian Defense,2023-01-19",
            "00020,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 g1f3,3400,20,0,2000,motif fork,http://example.com,Italian Game,2023-01-20",
            "00021,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5,3500,25,0,2100,opening,http://example.com,Italian Game,2023-01-21",
            "00022,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,3600,30,0,2200,motif,http://example.com,Scandinavian Defense,2023-01-22",
            "00023,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1,e7e5 e2e4,3700,35,0,2300,opening,http://example.com,Italian Game,2023-01-23",
            "00024,rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e6 0 1,e7e5,3800,40,0,2400,motif fork,http://example.com,Italian Game,2023-01-24",
            "00025,rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1,e2e4 e7e5,3900,45,0,2500,opening,http://example.com,Scandinavian Defense,2023-01-25",
        ])
        self.db.import_csv()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = PuzzleApp(self.root, db_path=self.db_path, csv_path=self.csv_path)

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            self.root.destroy()
        self.db.conn.close()

    def _write_csv(self, rows):
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            f.write("PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags,DailyDate\n")
            for row in rows:
                f.write(row + "\n")

    def _load_puzzles_from_db(self, limit=25):
        cursor = self.db.conn.execute(
            "SELECT PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes, GameUrl, OpeningTags, DailyDate, Color FROM puzzles LIMIT ?",
            (limit,),
        )
        puzzles = []
        for row in cursor.fetchall():
            puzzles.append(Puzzle(
                puzzle_id=row[0],
                fen=row[1],
                moves=row[2],
                rating=row[3],
                rating_deviation=row[4],
                popularity=row[5],
                nb_plays=row[6],
                themes=row[7].split() if row[7] else [],
                game_url=row[8],
                opening_tags=row[9].split(',') if row[9] else [],
                daily_date=row[10],
                color=row[11],
            ))
        return puzzles

    def test_12_puzzles_fit_one_page(self):
        puzzles = self._load_puzzles_from_db(12)
        self.app.selected_puzzles = puzzles
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            with patch('ui_selection.render_puzzle', return_value=Image.new('RGB', (224, 224), '#FFF')):
                self.app._create_sheets_docx(path, "Test Topic")
            doc = Document(path)
            self.assertEqual(len(doc.tables), 2)
            table = doc.tables[1]
            self.assertEqual(len(table.rows), 4)
            self.assertEqual(len(table.columns), 3)
            captions = []
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if text:
                        captions.append(text)
            self.assertEqual(len(captions), 12)
            for idx, caption in enumerate(captions, 1):
                self.assertIn(f"№{idx}.", caption)
                expected = "Ход белых" if puzzles[idx - 1].color == "b" else "Ход черных"
                self.assertIn(expected, caption)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_25_puzzles_create_three_pages(self):
        puzzles = self._load_puzzles_from_db(25)
        self.app.selected_puzzles = puzzles
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            with patch('ui_selection.render_puzzle', return_value=Image.new('RGB', (224, 224), '#FFF')):
                self.app._create_sheets_docx(path, "Test Topic")
            doc = Document(path)
            self.assertEqual(len(doc.tables), 6)
            page1_table = doc.tables[1]
            page2_table = doc.tables[3]
            page3_table = doc.tables[5]
            self.assertEqual(len(page1_table.rows), 4)
            self.assertEqual(len(page2_table.rows), 4)
            self.assertEqual(len(page3_table.rows), 4)
            captions = []
            for table in [page1_table, page2_table, page3_table]:
                for row in table.rows:
                    for cell in row.cells:
                        text = cell.text.strip()
                        if text:
                            captions.append(text)
            self.assertEqual(len(captions), 25)
            for idx, caption in enumerate(captions, 1):
                self.assertIn(f"№{idx}.", caption)
                expected = "Ход белых" if puzzles[idx - 1].color == "b" else "Ход черных"
                self.assertIn(expected, caption)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_answers_docx_has_all_solutions(self):
        puzzles = self._load_puzzles_from_db(12)
        self.app.selected_puzzles = puzzles
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        answers_path = path.replace(".docx", "_ответы.docx")
        try:
            with patch('ui_selection.render_puzzle', return_value=Image.new('RGB', (224, 224), '#FFF')):
                self.app._create_sheets_docx(path, "Test Topic")

            self.assertTrue(os.path.exists(answers_path))
            doc = Document(answers_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            self.assertEqual(len(paragraphs), 13)
            for idx, paragraph in enumerate(paragraphs[1:], 1):
                self.assertIn(f"№{idx}.", paragraph)
                expected_color = "Ход белых" if puzzles[idx - 1].color == "b" else "Ход черных"
                self.assertIn(expected_color, paragraph)
                for move in puzzles[idx - 1].solution.split():
                    self.assertIn(move, paragraph)
        finally:
            for p in [path, answers_path]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_topic_saved_to_db_after_export(self):
        puzzles = self._load_puzzles_from_db(3)
        self.app.selected_puzzles = puzzles
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            with patch('ui_selection.render_puzzle', return_value=Image.new('RGB', (224, 224), '#FFF')):
                self.app._create_sheets_docx(path, "Мой пользовательский лист")

            cursor = self.app.db.conn.cursor()
            cursor.execute("SELECT id, name FROM user_themes WHERE name = ?", ("Мой пользовательский лист",))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            theme_id = row[0]
            self.assertEqual(row[1], "Мой пользовательский лист")

            cursor.execute(
                "SELECT puzzle_id FROM puzzle_user_themes WHERE theme_id = ?",
                (theme_id,),
            )
            linked_ids = [r[0] for r in cursor.fetchall()]
            expected_ids = [p.puzzle_id for p in puzzles]
            self.assertEqual(sorted(linked_ids), sorted(expected_ids))

            self.assertEqual(self.app.user_themes_var.get(), "")
            self.assertTrue(
                any("Мой пользовательский лист" in v for v in self.app.user_themes_cb["values"]),
                msg=f"Expected theme in values, got {self.app.user_themes_cb['values']}",
            )
        finally:
            if os.path.exists(path):
                os.unlink(path)
            answers_path = path.replace(".docx", "_ответы.docx")
            if os.path.exists(answers_path):
                os.unlink(answers_path)

    def test_selecting_user_theme_resets_standard_filters(self):
        self.app._category_var.set("Фазы")
        self.app.category_cb.set("Фазы")
        self.app._on_category_selected()
        self.app.themes_listbox.selection_set(0)
        self.app.exclude_themes_listbox.insert(tk.END, "Theme A")
        self.app.exclude_themes_listbox.selection_set(0)
        self.app.user_themes_var.set("Моя тема")

        self.app._on_user_theme_selected()

        self.assertEqual(self.app._category_var.get(), "")
        self.assertEqual(self.app.category_cb.get(), "")
        self.assertEqual(self.app.themes_listbox.curselection(), ())
        self.assertEqual(self.app.exclude_themes_listbox.curselection(), ())

    def test_selecting_empty_user_theme_does_not_reset_standard_filters(self):
        self.app._category_var.set("Фазы")
        self.app.category_cb.set("Фазы")
        self.app._on_category_selected()
        self.app.themes_listbox.selection_set(0)
        self.app.user_themes_var.set("")

        self.app._on_user_theme_selected()

        self.assertEqual(self.app._category_var.get(), "Фазы")
        self.assertEqual(self.app.category_cb.get(), "Фазы")
        self.assertEqual(self.app.themes_listbox.curselection(), (0,))

    def test_reset_filters_clears_exclude_user_themes(self):
        self.app.exclude_themes_listbox.insert(tk.END, "Theme A")
        self.app.exclude_themes_listbox.insert(tk.END, "Theme B")
        self.app.exclude_themes_listbox.selection_set(0, 1)

        self.app._reset_filters()

        self.assertEqual(self.app.exclude_themes_listbox.curselection(), ())

    def test_selecting_exclude_user_theme_resets_standard_filters(self):
        self.app._category_var.set("Фазы")
        self.app.category_cb.set("Фазы")
        self.app._on_category_selected()
        self.app.themes_listbox.selection_set(0)
        self.app.exclude_themes_listbox.insert(tk.END, "Theme A")
        self.app.exclude_themes_listbox.selection_set(0)
        self.app.exclude_themes_listbox.update_idletasks()
        self.assertEqual(self.app.exclude_themes_listbox.curselection(), (0,))

        self.app._on_exclude_user_theme_selected()

        self.assertEqual(self.app._category_var.get(), "Фазы")
        self.assertEqual(self.app.category_cb.get(), "Фазы")
        self.assertEqual(self.app.themes_listbox.curselection(), (0,))
        self.assertEqual(self.app.user_themes_var.get(), "")


class TestLogArchive(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rotate_skips_small_log(self):
        from log_archive import rotate

        Path("docx_export.log").write_text("small log")
        rotate()
        self.assertTrue(Path("docx_export.log").exists())
        self.assertFalse(any(Path(".").glob("*.gz")))

    def test_rotate_archives_large_log(self):
        from log_archive import rotate

        data = "x" * (5 * 1024 * 1024 + 1)
        Path("docx_export.log").write_text(data)
        rotate()
        self.assertFalse(Path("docx_export.log").exists())
        archives = list(Path(".").glob("docx_export-*.log.gz"))
        self.assertEqual(len(archives), 1)
        self.assertGreater(archives[0].stat().st_size, 0)

    def test_prune_removes_old_archives(self):
        from log_archive import prune, rotate

        Path("docx_export.log").write_text("x" * (5 * 1024 * 1024 + 1))
        rotate()
        archive = list(Path(".").glob("docx_export-*.log.gz"))[0]
        old_time = time.time() - 11 * 86400
        os.utime(archive, (old_time, old_time))
        prune()
        self.assertFalse(archive.exists())

    def test_prune_keeps_recent_archives(self):
        from log_archive import prune, rotate

        Path("docx_export.log").write_text("x" * (5 * 1024 * 1024 + 1))
        rotate()
        archive = list(Path(".").glob("docx_export-*.log.gz"))[0]
        prune()
        self.assertTrue(archive.exists())


if __name__ == "__main__":
    unittest.main()
