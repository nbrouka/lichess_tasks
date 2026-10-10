"""
Mixin for filter widgets, filter application, and stats in Lichess Puzzle Viewer.
"""

import logging
import tkinter as tk
from tkinter import ttk
import threading
from typing import Optional

from constants import (
    THEME_RU_TO_EN, COLOR_RU_TO_EN, t,
    FILTER_PAGE_SIZE, FILTER_DEBOUNCE_MS,
)

logger = logging.getLogger(__name__)


class PuzzleFiltersMixin:
    def _add_filter_entry(self, parent: ttk.Frame, label: str, key: str) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(8, 0))
        entry = ttk.Entry(parent)
        entry.pack(fill=tk.X)
        self.filter_widgets[key] = entry

    def _add_spin_filter(
        self, parent: ttk.Frame, label: str, key: str,
        from_: int, to: int,
    ) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(5, 0))
        spin = ttk.Spinbox(parent, from_=from_, to=to, width=10)
        spin.pack(anchor=tk.W)
        self.filter_widgets[key] = spin

    def _add_scale_filter(
        self, parent: ttk.Frame, label: str,
        min_key: str, max_key: str,
        from_: int, to: int, default: int,
        explanation: str = "",
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(8, 0))

        header = ttk.Frame(frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text=label).pack(side=tk.LEFT)
        if explanation:
            ttk.Label(header, text=explanation, foreground="gray").pack(side=tk.LEFT, padx=(5, 0))

        min_var = tk.IntVar(value=from_)
        max_var = tk.IntVar(value=to)

        min_scale = ttk.Scale(
            frame, from_=from_, to=to, orient=tk.HORIZONTAL,
            variable=min_var, command=lambda v: self._on_scale(min_key, min_var, min_label),
        )
        min_scale.pack(fill=tk.X)
        min_label = ttk.Label(frame, text=f"от {from_}")
        min_label.pack(anchor=tk.W)

        max_scale = ttk.Scale(
            frame, from_=from_, to=to, orient=tk.HORIZONTAL,
            variable=max_var, command=lambda v: self._on_scale(max_key, max_var, max_label),
        )
        max_scale.pack(fill=tk.X)
        max_label = ttk.Label(frame, text=f"до {to}")
        max_label.pack(anchor=tk.W)

        self.filter_widgets[min_key] = min_var
        self.filter_widgets[max_key] = max_var
        self._scale_defaults[min_key] = (from_, min_var, min_label)
        self._scale_defaults[max_key] = (to, max_var, max_label)
        self._scale_bounds[min_key] = (from_, to)
        self._scale_bounds[max_key] = (from_, to)

    def _add_exact_scale_filter(
        self, parent: ttk.Frame, label: str,
        key: str,
        from_: int, to: int, default: int,
        explanation: str = "",
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(8, 0))

        header = ttk.Frame(frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text=label).pack(side=tk.LEFT)
        if explanation:
            ttk.Label(header, text=explanation, foreground="gray").pack(side=tk.LEFT, padx=(5, 0))

        enabled_var = tk.BooleanVar(value=False)
        var = tk.IntVar(value=default)

        toggle_btn = ttk.Button(
            frame, text=t("toggle_filter_on"),
            command=lambda: self._toggle_moves_filter(toggle_btn, scale, enabled_var),
        )
        toggle_btn.pack(anchor=tk.W, pady=(4, 0))

        scale = ttk.Scale(
            frame, from_=from_, to=to, orient=tk.HORIZONTAL,
            variable=var, state=tk.DISABLED,
        )
        scale.pack(fill=tk.X, pady=(4, 0))
        value_label = ttk.Label(frame, text=t("scale_equals", value=default))
        value_label.pack(anchor=tk.W)

        def on_value_change(*_args) -> None:
            value = int(float(var.get()))
            value = max(from_, min(to, value))
            var.set(value)
            value_label.config(text=t("scale_equals", value=value))

        scale.configure(command=on_value_change)
        var.trace_add("write", on_value_change)

        self.filter_widgets[key] = var
        self.filter_widgets[f"{key}_enabled"] = enabled_var
        self.filter_widgets[f"{key}_scale"] = scale
        self.filter_widgets[f"{key}_toggle"] = toggle_btn
        self._scale_defaults[key] = (default, var, value_label)
        self._scale_bounds[key] = (from_, to)

    def _toggle_moves_filter(self, button, scale, var):
        if var.get():
            var.set(False)
            scale.configure(state=tk.DISABLED)
            button.configure(text=t("toggle_filter_on"))
        else:
            var.set(True)
            scale.configure(state=tk.NORMAL)
            button.configure(text=t("toggle_filter_off"))

    def _on_scale(self, key: str, var: tk.IntVar, label: ttk.Label) -> None:
        value = int(float(var.get()))
        bound_min, bound_max = self._scale_bounds[key]
        value = max(bound_min, min(bound_max, value))
        var.set(value)

        if key.endswith("_min"):
            label.config(text=f"от {value}")
        else:
            label.config(text=f"до {value}")

    def _init_filters(self) -> None:
        pass

    def _bind_events(self) -> None:
        self.themes_listbox.bind("<Double-Button-1>", lambda e: self._apply_filter())
        self.themes_listbox.bind("<<ListboxSelect>>", lambda e: self._on_standard_theme_selected())
        self.exclude_themes_listbox.bind("<<ListboxSelect>>", lambda e: self._on_exclude_user_theme_selected())

    def _get_filter_values(self) -> dict:
        themes = [self.themes_listbox.get(i) for i in self.themes_listbox.curselection()]
        themes = [t.split(" (")[0] for t in themes]
        themes = [THEME_RU_TO_EN.get(t, t) for t in themes]

        exclude_themes = [self.exclude_themes_listbox.get(i) for i in self.exclude_themes_listbox.curselection()]
        exclude_themes = [t.split(" (")[0] for t in exclude_themes]

        moves_exact = self.filter_widgets.get("moves_exact")
        moves_enabled = self.filter_widgets.get("moves_exact_enabled")
        if moves_exact is not None and moves_enabled is not None and moves_enabled.get():
            moves_value = int(float(moves_exact.get()))
            bound_min, bound_max = self._scale_bounds["moves_exact"]
            moves_value = max(bound_min, min(bound_max, moves_value))
            moves_exact = moves_value
        else:
            moves_exact = None

        user_theme_value = self.filter_widgets["user_themes"].get()
        user_theme_name = user_theme_value.split(" (")[0] if user_theme_value else ""

        return {
            "rating_min": None,
            "rating_max": None,
            "popularity_min": None,
            "popularity_max": None,
            "nb_plays_min": None,
            "nb_plays_max": None,
            "moves_exact": moves_exact,
            "themes": themes if themes else None,
            "color": self._invert_color(COLOR_RU_TO_EN.get(self.filter_widgets["color"].get().strip())) or None,
            "user_themes": [user_theme_name] if user_theme_name else None,
            "exclude_user_themes": exclude_themes if exclude_themes else None,
        }

    def _invert_color(self, color: Optional[str]) -> Optional[str]:
        """Inverts the selected color because the stored `Color` field in the
        database represents the *opponent's* color, i.e. the side that just moved
        and left the puzzle position.  Selecting "Ход белых" in the UI means
        white is to move, so we must filter by `Color = 'b'` (black just moved),
        and vice versa."""
        if color == "w":
            return "b"
        if color == "b":
            return "w"
        return None

    def _apply_filter(self) -> None:
        """
        Запускает фильтрацию с debounce.

        - Если предыдущая фильтрация ещё выполняется, новая не стартует.
        - Предыдущий отложенный вызов отменяется, чтобы не было дублирования.
        - Сама фильтрация выполняется в фоновом потоке, чтобы не заморозить UI.
        - После завершения результат возвращается в основной поток через `root.after`.
        """
        if getattr(self, "_filter_thread", None) and self._filter_thread.is_alive():
            return

        if getattr(self, "_filter_after_id", None):
            self.root.after_cancel(self._filter_after_id)

        def _do_apply():
            try:
                self._filter_values = self._get_filter_values()
                self._filter_offset = 0
                self._set_filtering_status(True)
                self.root.update_idletasks()

                def run():
                    try:
                        puzzles, count = self.db.filter_puzzles(
                            **self._filter_values,
                            limit=FILTER_PAGE_SIZE,
                            offset=0,
                            return_total=True,
                        )
                        self.root.after(0, lambda: self._on_filter_complete(puzzles, count))
                    except Exception:
                        self.root.after(0, lambda: self._on_filter_complete([], 0))

                self._filter_thread = threading.Thread(target=run, daemon=True)
                self._filter_thread.start()
            except Exception:
                if getattr(self, "_restoring_session", False):
                    self._restoring_session = False
                    self._save_session()

        # Debounce: реальный запуск откладывается на FILTER_DEBOUNCE_MS.
        self._filter_after_id = self.root.after(FILTER_DEBOUNCE_MS, _do_apply)

    def _set_filtering_status(self, active: bool) -> None:
        self._filtering_active = active
        if active:
            self._filtering_dots = 0
            self._start_status_dots(t("status_filtering"))
            self.stats_label.config(text="")
            self.count_label.config(text=t("found_label", count=0))
        else:
            self._stop_status_dots()

    def _start_status_dots(self, base_text: str) -> None:
        """Анимирует точки после статусного текста (Фильтрация/Загрузка).

        Одна общая анимация для всех «долгих» состояний: повторный вызов
        переключает базовый текст, поэтому «Фильтрация» и «Загрузка»
        не конфликтуют между собой.
        """
        after_id = getattr(self, "_status_dots_id", None)
        if after_id:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
        self._status_dots_base = base_text
        self._status_dots_count = 0
        self._status_dots_active = True
        self._tick_status_dots()

    def _stop_status_dots(self) -> None:
        """Останавливает анимацию точек (финальный текст задаёт вызывающий)."""
        self._status_dots_active = False
        after_id = getattr(self, "_status_dots_id", None)
        if after_id:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
            self._status_dots_id = None

    def _tick_status_dots(self) -> None:
        if not getattr(self, "_status_dots_active", False):
            return
        if getattr(self, "_status_dots_ticking", False):
            # Защита от реентерабельности: если after() выполняет колбэк
            # синхронно (например, в тестах), повторный вход halted бы в
            # бесконечную рекурсию.
            return
        self._status_dots_ticking = True
        try:
            self._status_dots_count = (self._status_dots_count + 1) % 4
            dots = "." * self._status_dots_count
            self.status_label.config(text=f"{self._status_dots_base}{dots}")
            self._status_dots_id = self.root.after(250, self._tick_status_dots)
        finally:
            self._status_dots_ticking = False

    def _on_filter_complete(self, puzzles, count: int) -> None:
        logger.info("_on_filter_complete: puzzles=%d, count=%d", len(puzzles), count)
        self._set_filtering_status(False)

        self.filtered_puzzles = puzzles
        self._filter_total = count
        self._filter_offset = len(puzzles)
        self.current_index = 0 if puzzles else None
        self.count_label.config(text=t("found_label", count=count))
        if puzzles:
            if not getattr(self, "_restoring_session", False):
                self._show_puzzle(0)
                self.status_label.config(text=t("status_loaded", count=len(puzzles), total=count))
                self._update_stats()
        else:
            self._clear_display()
            self.status_label.config(text=t("status_not_found"))

        pending_last_puzzle_id = getattr(self, "_pending_last_puzzle_id", None)
        pending_selected_ids = getattr(self, "_pending_selected_ids", []) or []
        self._pending_last_puzzle_id = None
        self._pending_selected_ids = []
        logger.info("_on_filter_complete: pending_last_puzzle_id=%s filter_values=%s", pending_last_puzzle_id, getattr(self, "_filter_values", None))

        if pending_selected_ids:
            self._load_selected_from_session(pending_selected_ids)

        if pending_last_puzzle_id and self.filtered_puzzles:
            for i, p in enumerate(self.filtered_puzzles):
                if p.puzzle_id == pending_last_puzzle_id:
                    self._show_puzzle(i)
                    self._restoring_session = False
                    self._save_session()
                    self.status_label.config(
                        text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total)
                    )
                    self._update_stats()
                    return

        logger.info("_on_filter_complete: checking _load_until_found condition pending=%s filter_values=%s", pending_last_puzzle_id, getattr(self, "_filter_values", None))
        if pending_last_puzzle_id and self._filter_values:
            saved_index = getattr(self, "_pending_current_index", None)
            logger.info("_on_filter_complete: starting _load_until_found saved_index=%s filter_values=%s", saved_index, self._filter_values)

            def _load_until_found():
                try:
                    if saved_index is not None and 0 <= saved_index < self._filter_total:
                        puzzle = self.db.get_puzzle_by_offset(self._filter_values, saved_index)
                        if puzzle and puzzle.puzzle_id == pending_last_puzzle_id:
                            loaded = len(self.filtered_puzzles)
                            if saved_index >= loaded:
                                # Догружаем диапазон [loaded, saved_index], чтобы
                                # filtered_puzzles оставался непрерывным префиксом
                                # результата фильтрации. Иначе задача с номером
                                # saved_index + 1 оказывается на позиции loaded,
                                # и нумерация задач сбивается.
                                batch = self.db.filter_puzzles(
                                    **self._filter_values,
                                    limit=saved_index - loaded + 1,
                                    offset=loaded,
                                    return_total=False,
                                )
                                self.filtered_puzzles.extend(batch)
                                self._filter_offset = len(self.filtered_puzzles)
                            self.root.after(0, lambda: self._on_pending_found(saved_index))
                            return
                    self.root.after(0, lambda: self._on_pending_not_found(saved_index))
                except Exception:
                    logger.exception("_load_until_found failed")
                    self.root.after(0, lambda: self._on_pending_not_found(saved_index))

            threading.Thread(target=_load_until_found, daemon=True).start()
            return

        self._restoring_session = False
        if puzzles:
            self._show_puzzle(0)
            self.status_label.config(text=t("status_loaded", count=len(puzzles), total=count))
            self._update_stats()
        self._save_session()

    def _on_pending_found(self, index: int) -> None:
        logger.info("_on_pending_found: index=%d", index)
        self._restoring_session = False
        self._show_puzzle(index)
        self.status_label.config(
            text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total)
        )
        self._update_stats()
        self._save_session()

    def _on_pending_not_found(self, saved_index: Optional[int]) -> None:
        logger.info("_on_pending_not_found: saved_index=%s", saved_index)
        self._restoring_session = False
        if self.filtered_puzzles and saved_index is not None:
            idx = min(saved_index, len(self.filtered_puzzles) - 1)
            self._show_puzzle(idx)
        self.status_label.config(
            text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total)
        )
        self._update_stats()
        self._save_session()

    def _load_more_puzzles(self) -> None:
        if not self._filter_values:
            return
        if getattr(self, "_load_more_thread", None) and self._load_more_thread.is_alive():
            return

        self._start_status_dots(t("status_loading"))
        self.root.update_idletasks()

        def run():
            try:
                new_puzzles = self.db.filter_puzzles(
                    **self._filter_values,
                    limit=FILTER_PAGE_SIZE,
                    offset=self._filter_offset,
                )
            except Exception as exc:
                logger.exception("Load more puzzles failed: %s", exc)
                # Без except'а статус навсегда остался бы «Загрузка...»
                # exc нужно захватить значением: после except-блока имя удаляется.
                self.root.after(0, lambda exc=exc: self._on_more_loaded(None, error=exc))
                return
            self.root.after(0, lambda: self._on_more_loaded(new_puzzles))

        self._load_more_thread = threading.Thread(target=run, daemon=True)
        self._load_more_thread.start()

    def _on_more_loaded(self, new_puzzles, error=None) -> None:
        self._stop_status_dots()
        if error is not None:
            self.status_label.config(text=f"Error: {error}")
            return
        if not new_puzzles:
            self.status_label.config(text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total))
            self._update_stats()
            return
        self.filtered_puzzles.extend(new_puzzles)
        self._filter_offset += len(new_puzzles)
        self.status_label.config(
            text=t("status_loaded", count=len(self.filtered_puzzles), total=self._filter_total)
        )
        self._update_stats()
        if self.current_index is None:
            self.current_index = 0
            self._show_puzzle(0)

    def _update_stats(self) -> None:
        """Пересчитывает статистику фильтра в фоне и обновляет панель.

        Агрегирующий запрос по 6.1M задач занимал до ~3 с в главном потоке и
        морозил UI на каждое применение фильтра. Теперь считаем в воркере,
        результат применяем поллером в главном потоке (Tk из воркера небезопасен:
        роняет процесс при закрытии окна во время расчёта); повторные запросы,
        пришедшие во время расчёта, выполняются один раз после него.
        """
        if getattr(self, "_stats_thread", None) and self._stats_thread.is_alive():
            self._stats_pending = True
            return
        self._stats_pending = False
        self._stats_result = None
        self._stats_done = False
        filter_values = dict(getattr(self, "_filter_values", {}) or {})

        def run():
            if getattr(self, "_shutting_down", False):
                return
            try:
                stats = self.db.get_stats(filter_values)
            except Exception:
                logger.exception("get_stats failed")
                stats = None
            self._stats_result = stats
            self._stats_done = True

        self._stats_thread = threading.Thread(target=run, daemon=True)
        self._stats_thread.start()
        self._poll_stats()

    def _poll_stats(self) -> None:
        if getattr(self, "_stats_done", False):
            self._stats_done = False
            stats = self._stats_result
            self._stats_result = None
            self._apply_stats(stats)
            if getattr(self, "_stats_pending", False):
                self._update_stats()
            return
        thread = getattr(self, "_stats_thread", None)
        if thread is not None and thread.is_alive():
            self.root.after(50, self._poll_stats)

    def _apply_stats(self, stats) -> None:
        if stats is None:
            return
        moves_items = list(sorted(stats["by_moves"].items()))

        if len(moves_items) <= 2:
            moves_stats = ", ".join(f"{moves}: {cnt}" for moves, cnt in moves_items)
            moves_text = f"{t('stats_by_moves', moves=moves_stats)}"
        else:
            mid = (len(moves_items) + 1) // 2
            first = ", ".join(f"{moves}: {cnt}" for moves, cnt in moves_items[:mid])
            second = ", ".join(f"{moves}: {cnt}" for moves, cnt in moves_items[mid:])
            moves_text = f"{t('stats_by_moves', moves=first)}\n{second}"

        white = stats["white"]
        black = stats["black"]
        if self._filter_values.get("color"):
            white, black = black, white

        text = (
            f"{t('stats_white', white=white)}\n"
            f"{t('stats_black', black=black)}\n"
            f"{moves_text}"
        )
        self.stats_label.config(text=text)

    def _reset_filters_and_save(self) -> None:
        self._reset_filters()
        self._save_session()

    def _reset_filters(self) -> None:
        """
        Сбрасывает все фильтры в начальное состояние.

        Возвращает:
        - все скейлы/спинбоксы к значениям по умолчанию
        - комбобоксы к пустой строке
        - снимает выделение в списках тем
        - очищает выбранные задачи и статистику
        """
        for key, widget in self.filter_widgets.items():
            if isinstance(widget, tk.IntVar):
                default_value, var, label = self._scale_defaults[key]
                var.set(default_value)
                if key == "moves_exact":
                    label.config(text=t("scale_equals", value=default_value))
            elif isinstance(widget, tk.BooleanVar) and key.endswith("_enabled"):
                widget.set(False)
                scale_key = key.replace("_enabled", "")
                scale_widget = self.filter_widgets.get(f"{scale_key}_scale")
                toggle_widget = self.filter_widgets.get(f"{scale_key}_toggle")
                if scale_widget is not None:
                    scale_widget.configure(state=tk.DISABLED)
                if toggle_widget is not None:
                    toggle_widget.configure(text=t("toggle_filter_on"))
            elif isinstance(widget, ttk.Combobox):
                widget.set("")
        self.themes_listbox.selection_clear(0, tk.END)
        self.exclude_themes_listbox.selection_clear(0, tk.END)
        self._reset_themes_listbox_to_all()
        self.filtered_puzzles = []
        self.selected_puzzles = []
        for widget in self.selected_inner.winfo_children():
            widget.destroy()
        self.current_index = None
        self._filter_values = {}
        self._filter_total = 0
        self._filter_offset = 0
        self._solution_step = 0
        self._clear_display()
        self.count_label.config(text=t("found_label", count=0))
        self.stats_label.config(text="")
        self.status_label.config(text=t("status_reset"))
        self._update_selected_title()
