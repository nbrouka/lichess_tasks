"""
Точка входа приложения Lichess Puzzle Viewer.
"""

from ui import PuzzleApp
import tkinter as tk


def main() -> None:
    root = tk.Tk()
    app = PuzzleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
