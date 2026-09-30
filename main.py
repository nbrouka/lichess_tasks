"""
Точка входа приложения Lichess Puzzle Viewer.
"""

import threading
import tkinter as tk
from ui import PuzzleApp
from log_archive import rotate, prune


def _run_log_archive() -> None:
    try:
        rotate()
        prune()
    except Exception:
        pass


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    try:
        root.state("zoomed")
    except tk.TclError:
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}")
    threading.Thread(target=_run_log_archive, daemon=True).start()
    app = PuzzleApp(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
