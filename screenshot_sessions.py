"""Скриншоты разных сценариев сессии для проверки UI."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SESSION_FILE = Path.home() / ".config" / "lichess_tasks" / "session.json"
APP_DIR = Path(__file__).parent
SCREENSHOT_DIR = APP_DIR / "screenshots"
DB_FILE = APP_DIR / "puzzles.db"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def backup_session():
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text(encoding="utf-8")
    return None


def restore_session(backup):
    if backup is None:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
    else:
        SESSION_FILE.write_text(backup, encoding="utf-8")


def take_screenshot(name):
    """Запускает приложение с заданной сессией и делает скриншот."""
    # Запускаем основной скрипт (он сам вызывает app и берёт скриншот)
    script = f"""
import tkinter as tk
import sys
import os

# Убедимся что модуль видим
sys.path.insert(0, r"{APP_DIR}")

from ui import PuzzleApp
from constants import SESSION_FILE, DB_FILENAME
from PIL import ImageGrab

root = tk.Tk()
root.withdraw()
root.update()

app = PuzzleApp(root, db_path=DB_FILENAME)
root.deiconify()
root.update()

# Ждём инициализацию
root.after(500, lambda: None)
root.update()

# Делаем скриншот
try:
    img = ImageGrab.grab()
    path = r"{SCREENSHOT_DIR / name}.png"
    img.save(path)
    print(f"Saved: {{path}}")
except Exception as e:
    print(f"Error: {{e}}")

root.destroy()
"""
    result = subprocess.run(
        ["xvfb-run", "-a", sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(APP_DIR),
        timeout=30,
    )
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])
    return result.returncode == 0


def main():
    backup = backup_session()
    try:
        scenarios = [
            ("empty_session", {
                "filters": {},
                "last_puzzle_id": None,
                "selected_ids": [],
                "filter_offset": 0,
                "filter_total": 0,
                "current_index": None,
            }),
            ("with_filters", {
                "filters": {"color": "w", "moves_exact": 3},
                "last_puzzle_id": None,
                "selected_ids": [],
                "filter_offset": 0,
                "filter_total": 0,
                "current_index": None,
            }),
            ("with_last_puzzle_id", {
                "filters": {},
                "last_puzzle_id": "00001",
                "selected_ids": [],
                "filter_offset": 0,
                "filter_total": 0,
                "current_index": None,
            }),
            ("with_selected_ids", {
                "filters": {},
                "last_puzzle_id": None,
                "selected_ids": ["00001", "00002"],
                "filter_offset": 0,
                "filter_total": 0,
                "current_index": None,
            }),
        ]

        for name, session_data in scenarios:
            SESSION_FILE.write_text(json.dumps(session_data, ensure_ascii=False), encoding="utf-8")
            print(f"Scenario: {name}")
            success = take_screenshot(name)
            print(f"  Success: {success}")
            time.sleep(0.5)

        # Missing file
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        print("Scenario: missing_file")
        success = take_screenshot("missing_file")
        print(f"  Success: {success}")

        # Corrupt file
        SESSION_FILE.write_text("{invalid json", encoding="utf-8")
        print("Scenario: corrupt_file")
        success = take_screenshot("corrupt_file")
        print(f"  Success: {{success}}")

        print("Done. Screenshots saved to:", SCREENSHOT_DIR)

    finally:
        restore_session(backup)
        print("Session restored")


if __name__ == "__main__":
    main()
