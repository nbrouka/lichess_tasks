"""
Mixin for CSV import and progress UI in Lichess Puzzle Viewer.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading

from constants import t, PROGRESS_WINDOW_GEOMETRY


class PuzzleImportMixin:
    def _start_import(self) -> None:
        """Запускает импорт CSV в SQLite в фоновом потоке."""
        if self._import_in_progress:
            messagebox.showinfo(t("about_title"), t("msg_import_running"))
            return

        self._import_in_progress = True
        self.status_label.config(text=t("status_import_started"))

        progress_win = tk.Toplevel(self.root)
        progress_win.title(t("progress_title"))
        progress_win.geometry(PROGRESS_WINDOW_GEOMETRY)
        progress_win.transient(self.root)
        progress_win.grab_set()
        progress_win.resizable(True, True)
        self._progress_win = progress_win

        info_label = ttk.Label(
            progress_win,
            text=t("progress_importing", filename=Path(self.db.csv_path).name),
        )
        info_label.pack(pady=(10, 5), anchor=tk.W, padx=10)

        progress_bar = ttk.Progressbar(progress_win, mode="determinate")
        progress_bar.pack(fill=tk.X, padx=20, pady=5)

        status_label = ttk.Label(progress_win, text=t("progress_preparing"))
        status_label.pack(pady=(0, 10))

        total_lines = sum(
            1 for _ in open(self.db.csv_path, "r", encoding="utf-8")
        ) - 1
        progress_bar["maximum"] = total_lines

        def progress_callback(current: int) -> None:
            def update_ui():
                if not progress_win.winfo_exists():
                    return
                progress_bar["value"] = current
                pct = int(current / total_lines * 100) if total_lines > 0 else 0
                status_label.config(
                    text=t("progress_pct", pct=pct, current=current, total_lines=total_lines)
                )
                self.status_label.config(
                    text=t("progress_pct", pct=pct, current=current, total_lines=total_lines)
                )
                progress_win.update_idletasks()

            self.root.after(0, update_ui)

        def status_callback(text: str) -> None:
            def update_ui():
                if not progress_win.winfo_exists():
                    return
                status_label.config(text=text)
                self.status_label.config(text=text)
                progress_win.update_idletasks()

            self.root.after(0, update_ui)

        def run_import():
            try:
                self.db.import_csv(progress_callback=progress_callback, status_callback=status_callback)
                self.root.after(0, self._on_db_ready)
                self.root.after(0, lambda: messagebox.showinfo(
                    t("about_title"), t("msg_import_success")
                ))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror(
                    t("msg_import_error"), str(exc)
                ))
            finally:
                self.root.after(0, progress_win.destroy)
                self.root.after(0, lambda: setattr(self, "_import_in_progress", False))
                self.root.after(0, lambda: self.status_label.config(text=t("status_import_complete")))

        threading.Thread(target=run_import, daemon=True).start()
