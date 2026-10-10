#!/usr/bin/env python3
"""Tests for all session.json scenarios with screenshots.

Каждый сценарий:
1. Записывает тестовый session-файл во временную директорию
2. Запускает приложение с фикстурой БД и этим session-файлом
3. Делает скриншот → screenshots/
4. Проверяет, что скриншот валидный и не пустой

Реальная БД (puzzles.db) и реальный session.json НЕ используются —
приложение работает с копией фикстуры tests/fixtures/puzzles_fixture.db.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest import TestCase, main as unittest_main

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

APP_DIR = Path(__file__).parent
SCREENSHOT_DIR = APP_DIR / "screenshots"
FIXTURE_DIR = APP_DIR / "tests" / "fixtures"
FIXTURE_CSV = FIXTURE_DIR / "puzzles_fixture.csv"
FIXTURE_DB = FIXTURE_DIR / "puzzles_fixture.db"

SCREENSHOT_DIR.mkdir(exist_ok=True)


def _ensure_fixture_db(target: Path) -> None:
    """Копирует фикстуру БД или собирает её из CSV-фикстуры."""
    if FIXTURE_DB.exists():
        shutil.copy(FIXTURE_DB, target)
        return
    if not FIXTURE_CSV.exists():
        raise RuntimeError(
            f"Fixture not found: {FIXTURE_DB} / {FIXTURE_CSV}. "
            "Run: python create_fixtures.py"
        )
    sys.path.insert(0, str(APP_DIR))
    from database import PuzzleDatabase
    db = PuzzleDatabase(db_path=str(target), csv_path=str(FIXTURE_CSV))
    db.import_csv()
    db.close()


def take_screenshot(name: str, db_path: Path, session_path: Path) -> dict:
    """Запускает приложение и делает скриншот. Возвращает результат."""
    script = f"""
import tkinter as tk
import sys
import os

sys.path.insert(0, r"{APP_DIR}")

from ui import PuzzleApp
from PIL import ImageGrab

root = tk.Tk()
root.withdraw()
root.update()

app = PuzzleApp(root, db_path=r"{db_path}", session_file=r"{session_path}")
root.deiconify()
root.update()

root.after(800, lambda: None)
root.update()

try:
    img = ImageGrab.grab()
    path = r"{SCREENSHOT_DIR / name}.png"
    img.save(path)
    print(f"SAVED:{{path}}")
except Exception as e:
    print(f"ERROR:{{e}}")

root.destroy()
"""
    result = subprocess.run(
        ["xvfb-run", "-a", sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(APP_DIR),
        timeout=60,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr[:500] if result.stderr else "",
    }


def save_test_session(name: str, data: dict) -> Path:
    """Сохраняет тестовый session-файл в скриншот-папку."""
    path = SCREENSHOT_DIR / f"session_{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class TestSessionScenarios(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.mkdtemp()
        cls.db_file = Path(cls._tmp_dir) / "puzzles.db"
        _ensure_fixture_db(cls.db_file)
        cls.session_file = Path(cls._tmp_dir) / "session.json"
        # Реальные ID задач и пользовательские темы из фикстуры.
        conn = sqlite3.connect(f"file:{cls.db_file}?mode=ro", uri=True)
        try:
            cls.puzzle_ids = [
                r[0] for r in conn.execute(
                    "SELECT PuzzleId FROM puzzles ORDER BY Rating DESC"
                )
            ]
            cls.user_themes = [
                r[0] for r in conn.execute("SELECT name FROM user_themes ORDER BY id")
            ]
        finally:
            conn.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)

    def _write_session(self, data: dict):
        self.session_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _run_scenario(self, name: str, session_data: dict):
        """Запускает сценарий, проверяет скриншот и файл сессии."""
        # Сохраняем тестовый session-файл в скриншот-папку
        # name = "empty_session" → session_empty_session.json
        session_copy = dict(session_data)
        save_test_session(name, session_copy)

        # Записываем сессию во временный файл
        self._write_session(session_copy)
        res = take_screenshot(name, self.db_file, self.session_file)

        # Проверяем код возврата
        self.assertEqual(res["returncode"], 0,
                         f"Scenario '{name}' failed: stdout={res['stdout']} stderr={res['stderr']}")

        # Проверяем скриншот
        img_path = SCREENSHOT_DIR / f"{name}.png"
        self.assertTrue(img_path.exists(), f"Screenshot missing: {img_path}")
        self.assertGreater(img_path.stat().st_size, 1000,
                           f"Screenshot too small: {img_path}")

        # Валидность PNG
        if HAS_PILLOW:
            with Image.open(img_path) as img:
                self.assertIn(img.format, ("PNG",), f"Not a PNG: {img_path}")
                self.assertGreater(img.size[0], 100, "Image too narrow")
                self.assertGreater(img.size[1], 100, "Image too short")

        return res

    # ─── Пустая сессия ───
    def test_empty_session(self):
        data = {
            "filters": {},
            "last_puzzle_id": None,
            "selected_ids": [],
            "filter_offset": 0,
            "filter_total": 0,
            "current_index": None,
        }
        res = self._run_scenario("empty_session", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── Фильтры: цвет и ходов ───
    def test_session_with_filters(self):
        data = {
            "filters": {"color": "w", "moves_exact": 3},
            "last_puzzle_id": None,
            "selected_ids": [],
            "filter_offset": 0,
            "filter_total": 0,
            "current_index": None,
        }
        res = self._run_scenario("with_filters", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── last_puzzle_id ───
    def test_session_with_last_puzzle_id(self):
        data = {
            "filters": {},
            "last_puzzle_id": self.puzzle_ids[0],  # Real puzzle ID from fixture
            "selected_ids": [],
            "filter_offset": 0,
            "filter_total": 0,
            "current_index": None,
        }
        res = self._run_scenario("with_last_puzzle_id", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── selected_ids ───
    def test_session_with_selected_ids(self):
        data = {
            "filters": {},
            "last_puzzle_id": None,
            "selected_ids": self.puzzle_ids[:2],  # Real puzzle IDs from fixture
            "filter_offset": 0,
            "filter_total": 0,
            "current_index": None,
        }
        res = self._run_scenario("with_selected_ids", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── Пагинация ───
    def test_session_with_pagination(self):
        data = {
            "filters": {"themes": ["fork"]},  # Real theme from fixture
            "last_puzzle_id": None,
            "selected_ids": [],
            "filter_offset": 50,
            "filter_total": 237,  # Realistic total
            "current_index": None,
        }
        res = self._run_scenario("with_pagination", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── current_index ───
    def test_session_with_current_index(self):
        data = {
            "filters": {},
            "last_puzzle_id": self.puzzle_ids[0],  # Real puzzle ID from fixture
            "selected_ids": [],
            "filter_offset": 0,
            "filter_total": 100,
            "current_index": 42,
        }
        res = self._run_scenario("with_current_index", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── Все поля заполнены ───
    def test_session_full_data(self):
        user_theme = self.user_themes[0] if self.user_themes else "test"
        data = {
            "filters": {"color": "b", "themes": ["mate"], "user_themes": [user_theme]},
            "last_puzzle_id": self.puzzle_ids[0],  # Real puzzle ID
            "selected_ids": self.puzzle_ids[:2],  # Real puzzle IDs
            "filter_offset": 50,  # Realistic offset
            "filter_total": 1759497,  # Realistic total
            "current_index": 10,
        }
        res = self._run_scenario("full_data", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── Отсутствие файла сессии ───
    def test_missing_session_file(self):
        if self.session_file.exists():
            self.session_file.unlink()
        res = take_screenshot("missing_file", self.db_file, self.session_file)
        self.assertEqual(res["returncode"], 0,
                         f"Missing session scenario failed: {res['stderr']}")
        img = SCREENSHOT_DIR / "missing_file.png"
        self.assertTrue(img.exists())
        if HAS_PILLOW:
            with Image.open(img) as im:
                self.assertGreater(im.size[0], 100)

    # ─── Повреждённый JSON ───
    def test_corrupt_session_json(self):
        self.session_file.write_text("{invalid json", encoding="utf-8")
        res = take_screenshot("corrupt_file", self.db_file, self.session_file)
        self.assertEqual(res["returncode"], 0,
                         f"Corrupt session scenario failed: {res['stderr']}")
        img = SCREENSHOT_DIR / "corrupt_file.png"
        self.assertTrue(img.exists())
        if HAS_PILLOW:
            with Image.open(img) as im:
                self.assertGreater(im.size[0], 100)

    # ─── Фильтр только по темам ───
    def test_session_theme_filter_only(self):
        data = {
            "filters": {"themes": ["fork", "mate"]},  # Real themes from fixture
            "last_puzzle_id": None,
            "selected_ids": [],
            "filter_offset": 0,
            "filter_total": 0,
            "current_index": None,
        }
        res = self._run_scenario("theme_filter_only", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── Длинный список selected_ids ───
    def test_session_many_selected(self):
        data = {
            "filters": {},
            "last_puzzle_id": None,
            "selected_ids": self.puzzle_ids[:12],  # Real puzzle IDs from fixture
            "filter_offset": 0,
            "filter_total": 0,
            "current_index": None,
        }
        res = self._run_scenario("many_selected", data)
        self.assertIn("SAVED:", res["stdout"])

    # ─── Тестовый файл сессии должен лежать в screenshots ───
    def test_z_test_session_files_exist(self):
        """Проверяет, что все тестовые JSON-файлы сессий сохранены в screenshots/."""
        expected = [
            "session_empty_session.json",
            "session_with_filters.json",
            "session_with_last_puzzle_id.json",
            "session_with_selected_ids.json",
            "session_with_pagination.json",
            "session_with_current_index.json",
            "session_full_data.json",
            "session_theme_filter_only.json",
            "session_many_selected.json",
        ]
        missing = [f for f in expected if not (SCREENSHOT_DIR / f).exists()]
        self.assertEqual(missing, [], f"Missing test session files: {missing}")
        for f in expected:
            path = SCREENSHOT_DIR / f
            content = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("filters", content)
            self.assertIn("last_puzzle_id", content)
            self.assertIn("selected_ids", content)
            self.assertIn("filter_offset", content)
            self.assertIn("filter_total", content)
            self.assertIn("current_index", content)

    # ─── Скриншоты не пустые ───
    def test_z_screenshots_not_empty(self):
        """Проверяет, что все скриншоты имеют ненулевой размер и валидные."""
        names = [
            "empty_session", "with_filters", "with_last_puzzle_id",
            "with_selected_ids", "with_pagination", "with_current_index",
            "full_data", "theme_filter_only", "many_selected",
            "missing_file", "corrupt_file",
        ]
        missing = []
        for name in names:
            img_path = SCREENSHOT_DIR / f"{name}.png"
            if not img_path.exists():
                missing.append(name)
                continue
            if HAS_PILLOW:
                with Image.open(img_path) as img:
                    self.assertGreater(img.size[0] * img.size[1], 1000,
                                       f"Screenshot {name} too small: {img.size}")
        self.assertEqual(missing, [], f"Screenshots missing: {missing}")


if __name__ == "__main__":
    unittest_main()
