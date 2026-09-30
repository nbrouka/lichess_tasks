"""
Точка входа приложения Lichess Puzzle Viewer.
"""

from ui import PuzzleApp
import tkinter as tk


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    try:
        root.state("zoomed")
    except tk.TclError:
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}")
    app = PuzzleApp(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
