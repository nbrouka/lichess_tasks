"""
Точка входа приложения Lichess Puzzle Viewer.
"""

import logging
import threading
import tkinter as tk
from ui import PuzzleApp
from log_archive import rotate, prune
from constants import APP_LOG_FILE


def _run_log_archive() -> None:
    """
    Фоновый архиватор логов.

    Запускается один раз при старте приложения в отдельном daemon-потоке.
    Архивирует docx_export.log, если он превышает порог размера,
    и удаляет старые архивы старше RETENTION_DAYS.
    """
    try:
        rotate()
        prune()
    except Exception:
        pass


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(APP_LOG_FILE, encoding="utf-8")],
    )
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    try:
        root.state("zoomed")
    except tk.TclError:
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}")
    # Архивирование логов запускаем до создания интерфейса,
    # чтобы не блокировать главный поток при старте.
    threading.Thread(target=_run_log_archive, daemon=True).start()
    app = PuzzleApp(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
