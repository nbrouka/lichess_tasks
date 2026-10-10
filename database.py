"""
Модуль для работы с базой данных SQLite.
Поддерживает пакетный импорт CSV и эффективную фильтрацию.
"""

import logging
import sqlite3
import csv
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Union
from hashlib import md5

from constants import (
    DB_FILENAME, DEFAULT_CSV_PATH, SQL_CREATE_PUZZLES,
    SQL_CREATE_THEMES, SQL_CREATE_USER_THEMES, SQL_CREATE_USER_PUZZLE_THEMES,
    SQL_INDEXES, IMPORT_BATCH_SIZE,
    IMPORT_PROGRESS_INTERVAL, FILTER_DEFAULT_LIMIT,
)

logger = logging.getLogger(__name__)


class Puzzle:
    """Объектная модель задачи."""
    def __init__(
        self,
        puzzle_id: str,
        fen: str,
        moves: str,
        rating: Optional[int],
        rating_deviation: Optional[int],
        popularity: Optional[int],
        nb_plays: Optional[int],
        themes: List[str],
        game_url: str,
        opening_tags: List[str],
        daily_date: Optional[str],
        color: str,
    ) -> None:
        self.puzzle_id = puzzle_id
        self.fen = fen
        self.moves = moves
        self.rating = rating
        self.rating_deviation = rating_deviation
        self.popularity = popularity
        self.nb_plays = nb_plays
        self.themes = themes
        self.game_url = game_url
        self.opening_tags = opening_tags
        self.daily_date = daily_date
        self.color = color

    @property
    def first_move(self) -> Optional[str]:
        if self.moves:
            return self.moves.split()[0]
        return None

    @property
    def solution(self) -> str:
        parts = self.moves.split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    @property
    def moves_count(self) -> int:
        if not self.moves:
            return 0
        return len(self.moves.split())

    @property
    def solution_moves_count(self) -> int:
        if not self.moves:
            return 0
        parts = self.moves.split()
        return max(len(parts) - 1, 0)

    def __repr__(self) -> str:
        return f"<Puzzle {self.puzzle_id} rating={self.rating} themes={self.themes}>"


class PuzzleDatabase:
    """Обёртка над SQLite для задач Lichess."""

    def __init__(self, db_path: str = DB_FILENAME, csv_path: str = DEFAULT_CSV_PATH):
        self.db_path = db_path
        self.csv_path = csv_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        self._filter_cache: Dict[str, tuple[float, Any]] = {}
        self._stats_cache: Dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 60.0
        self._filter_cache: Dict[str, tuple[float, Any]] = {}
        self._theme_counts_cache: Optional[dict] = None

    # ------------------------------------------------------------------
    # Схема
    # ------------------------------------------------------------------
    def _create_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(SQL_CREATE_PUZZLES)
        cursor.executescript(SQL_CREATE_THEMES)
        cursor.execute(SQL_CREATE_USER_THEMES)
        cursor.execute(SQL_CREATE_USER_PUZZLE_THEMES)
        self._ensure_sheets_created_column()
        self.conn.commit()

    def _ensure_sheets_created_column(self) -> None:
        """Добавляет столбец sheets_created в БД, созданные до его появления."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(user_themes)")
        if any(row[1] == "sheets_created" for row in cursor.fetchall()):
            return
        cursor.execute(
            "ALTER TABLE user_themes ADD COLUMN sheets_created INTEGER NOT NULL DEFAULT 0"
        )

    def create_indexes(self, progress_callback: Optional[Callable[[int], None]] = None) -> None:
        cursor = self.conn.cursor()
        for idx, sql in enumerate(SQL_INDEXES, start=1):
            cursor.execute(sql)
            if progress_callback:
                progress_callback(idx)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Статус импорта
    # ------------------------------------------------------------------
    def is_imported(self) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM puzzles")
        return cursor.fetchone()[0] > 0

    def get_puzzle_count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM puzzles")
        return cursor.fetchone()[0]

    # ------------------------------------------------------------------
    # Импорт CSV
    # ------------------------------------------------------------------
    def import_csv(self, progress_callback: Optional[Callable[[int], None]] = None, status_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Импортирует CSV в SQLite с оптимизацией для больших файлов.

        Использует:
        - DROP/CREATE вместо DELETE для очистки таблиц
        - Умеренные PRAGMA для стабильности
        - Пакеты по 20 000 строк с периодическим коммитом
        - Один проход по CSV
        - Создание индексов после вставки
        """
        logger.info("Import started csv=%s db=%s", self.csv_path, self.db_path)
        cursor = self.conn.cursor()

        # WAL-режим позволяет читать таблицу во время записи, что важно для UI.
        # NORMAL синхронизация безопасна для desktop и значительно быстрее FULL.
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA cache_size = -64000")
        cursor.execute("PRAGMA locking_mode = NORMAL")

        # Полная пересборка схемы быстрее и надёжнее, чем DELETE FROM.
        cursor.execute("DROP TABLE IF EXISTS puzzle_themes")
        cursor.execute("DROP TABLE IF EXISTS puzzles")
        self._create_schema()
        logger.info("Schema created")

        batch_size = IMPORT_BATCH_SIZE
        batch: List[tuple] = []
        theme_batch: List[tuple] = []
        total_inserted = 0
        i = 0

        try:
            # Один проход по CSV. Большие файлы не хранятся целиком в памяти.
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)

                for i, row in enumerate(reader, start=1):
                    puzzle_id, fen, moves = row[0], row[1], row[2]
                    rating = int(row[3]) if row[3] else None
                    rating_deviation = int(row[4]) if row[4] else None
                    popularity = int(row[5]) if row[5] else None
                    nb_plays = int(row[6]) if row[6] else None
                    themes = row[7] if len(row) > 7 else ""
                    game_url = row[8] if len(row) > 8 else ""
                    opening_tags = row[9] if len(row) > 9 else ""
                    daily_date = row[10] if len(row) > 10 and row[10] else None

                    # В CSV цвет хода = сторона, которая только что сходила.
                    color = fen.split()[1] if len(fen.split()) > 1 else "w"

                    batch.append((
                        puzzle_id, fen, moves, rating, rating_deviation,
                        popularity, nb_plays, themes, game_url,
                        opening_tags, daily_date, color,
                    ))

                    # Темы хранятся в отдельной таблице для быстрого фильтра по теме.
                    for theme in themes.split():
                        theme_batch.append((puzzle_id, theme))

                    # Пакетная вставка уменьшает количество транзакций и ускоряет импорт.
                    if len(batch) >= batch_size:
                        cursor.executemany(
                            "INSERT OR REPLACE INTO puzzles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            batch,
                        )
                        cursor.executemany(
                            "INSERT OR IGNORE INTO puzzle_themes VALUES (?,?)",
                            theme_batch,
                        )
                        self.conn.commit()
                        total_inserted += len(batch)
                        batch.clear()
                        theme_batch.clear()

                    if progress_callback and i % IMPORT_PROGRESS_INTERVAL == 0:
                        progress_callback(i)

        except Exception as exc:
            raise RuntimeError(f"Failed to import CSV: {exc}") from exc

        # Вставляем остаток после последнего полного пакета.
        if batch:
            cursor.executemany(
                "INSERT OR REPLACE INTO puzzles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                batch,
            )
            cursor.executemany(
                "INSERT OR IGNORE INTO puzzle_themes VALUES (?,?)",
                theme_batch,
            )
            total_inserted += len(batch)

        self.conn.commit()

        # Индексы создаём после вставки: это быстрее, чем поддерживать их во время импорта.
        if status_callback:
            status_callback(f"Creating indexes (0/{len(SQL_INDEXES)})")
        self.create_indexes(progress_callback=lambda idx: status_callback(f"Creating indexes ({idx}/{len(SQL_INDEXES)})") if status_callback else None)
        self._invalidate_cache()
        logger.info("Indexes created count=%d", len(SQL_INDEXES))

        if progress_callback:
            progress_callback(i)

        logger.info("Import finished total_inserted=%d", total_inserted)

    # ------------------------------------------------------------------
    # Справочники
    # ------------------------------------------------------------------
    def get_all_themes(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT Theme FROM puzzle_themes ORDER BY Theme")
        return [r[0] for r in cursor.fetchall()]

    def get_theme_counts(self) -> dict:
        if self._theme_counts_cache is not None:
            return self._theme_counts_cache
        cursor = self.conn.cursor()
        cursor.execute("SELECT Theme, COUNT(*) FROM puzzle_themes GROUP BY Theme")
        result = {row[0]: row[1] for row in cursor.fetchall()}
        self._theme_counts_cache = result
        return result

    def get_all_openings(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT DISTINCT OpeningTags FROM puzzles "
            "WHERE OpeningTags IS NOT NULL AND OpeningTags != '' "
            "ORDER BY OpeningTags"
        )
        return [r[0] for r in cursor.fetchall()]

    def get_user_themes(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM user_themes ORDER BY name")
        return [r[0] for r in cursor.fetchall()]

    def mark_theme_sheets_created(self, name: str) -> None:
        """Отмечает, что по теме создавались листы (PDF/DOCX)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE user_themes SET sheets_created = 1 WHERE name = ?",
            (name,),
        )
        self.conn.commit()

    def get_themes_with_sheets_created(self) -> List[str]:
        """Возвращает темы, по которым уже создавались листы."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name FROM user_themes WHERE sheets_created = 1 ORDER BY name"
        )
        return [r[0] for r in cursor.fetchall()]

    def get_user_theme_puzzle_count(self, name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM puzzle_user_themes
            WHERE theme_id = (SELECT id FROM user_themes WHERE name = ?)
            """,
            (name,),
        )
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_stats(self, filters: Optional[dict] = None) -> dict:
        """
        Возвращает статистику по текущим фильтрам.

        Статистика кэшируется, чтобы не выполнять один и тот же запрос
        несколько раз при обновлении UI.
        """
        cache_key = self._build_cache_key(**(filters or {}))
        cached = self._get_cached(cache_key, "stats")
        if cached is not None:
            return cached

        cursor = self.conn.cursor()
        stats = {
            "white": 0,
            "black": 0,
            "by_moves": {},
        }

        conditions = ["1=1"]
        params: List[Any] = []

        if filters:
            if filters.get("color"):
                conditions.append("puzzles.Color = ?")
                params.append(filters["color"])
            if filters.get("moves_exact") is not None:
                moves_expr = "puzzles.moves_count" if self._has_moves_count_column() else "(LENGTH(puzzles.Moves) - LENGTH(REPLACE(puzzles.Moves, ' ', '')) + 1) / 2"
                conditions.append(f"{moves_expr} = ?")
                params.append(filters["moves_exact"])
            if filters.get("themes"):
                theme_sql, theme_params = self._build_theme_condition(filters["themes"])
                if theme_sql:
                    conditions.append(theme_sql)
                    params.extend(theme_params)
            if filters.get("user_themes"):
                unique_user_themes = [name for name in filters["user_themes"] if name]
                if unique_user_themes:
                    placeholders = ",".join(["?"] * len(unique_user_themes))
                    conditions.append(
                        f"PuzzleId IN ("
                        f"SELECT puzzle_id FROM puzzle_user_themes "
                        f"WHERE theme_id IN (SELECT id FROM user_themes WHERE name IN ({placeholders}))"
                        f")"
                    )
                    params.extend(unique_user_themes)
            if filters.get("exclude_user_themes"):
                unique_exclude = [name for name in filters["exclude_user_themes"] if name]
                if unique_exclude:
                    placeholders = ",".join(["?"] * len(unique_exclude))
                    conditions.append(
                        f"PuzzleId NOT IN ("
                        f"SELECT puzzle_id FROM puzzle_user_themes "
                        f"WHERE theme_id IN (SELECT id FROM user_themes WHERE name IN ({placeholders}))"
                        f")"
                    )
                    params.extend(unique_exclude)

        where = " AND ".join(conditions)

        # Группируем по количеству полуходов, чтобы получить статистику по длине решения.
        moves_expr = "puzzles.moves_count" if self._has_moves_count_column() else "(LENGTH(puzzles.Moves) - LENGTH(REPLACE(puzzles.Moves, ' ', '')) + 1) / 2"
        cursor.execute(
            f"""
            SELECT
                SUM(CASE WHEN puzzles.Color = 'w' THEN 1 ELSE 0 END) AS white_count,
                SUM(CASE WHEN puzzles.Color = 'b' THEN 1 ELSE 0 END) AS black_count,
                {moves_expr} AS moves_count,
                COUNT(*) AS cnt
            FROM puzzles
            WHERE {where}
            GROUP BY moves_count
            """,
            params,
        )
        rows = cursor.fetchall()

        for row in rows:
            stats["white"] += row["white_count"] or 0
            stats["black"] += row["black_count"] or 0
            moves_count = row["moves_count"] or 0
            stats["by_moves"][moves_count] = stats["by_moves"].get(moves_count, 0) + (row["cnt"] or 0)

        self._set_cached(cache_key, "stats", stats)
        return stats

    # ------------------------------------------------------------------
    # Фильтрация
    # ------------------------------------------------------------------
    def _build_theme_condition(self, themes: List[str]):
        """
        Строит SQL-условие для фильтрации по нескольким темам.

        При нескольких темах задача должна содержать ХОТЯ БЫ ОДНУ из указанных тем.
        Это реализуется через простой IN-подзапрос.
        """
        if not themes:
            return "", []
        placeholders = ",".join(["?"] * len(themes))
        return (
            f"PuzzleId IN (SELECT PuzzleId FROM puzzle_themes WHERE Theme IN ({placeholders}))",
            list(themes),
        )

    def _build_filter_conditions(
        self,
        puzzle_id_contains: str = "",
        rating_min: Optional[int] = None,
        rating_max: Optional[int] = None,
        popularity_min: Optional[int] = None,
        popularity_max: Optional[int] = None,
        nb_plays_min: Optional[int] = None,
        nb_plays_max: Optional[int] = None,
        color: Optional[str] = None,
        opening_contains: str = "",
        daily_date_from: Optional[str] = None,
        daily_date_to: Optional[str] = None,
        moves_exact: Optional[int] = None,
        themes: Optional[List[str]] = None,
        user_themes: Optional[List[str]] = None,
        exclude_user_themes: Optional[List[str]] = None,
    ) -> tuple[str, List[Any]]:
        """
        Строит WHERE-условие и параметры для фильтрации задач.

        Возвращает кортеж (where_clause, params), который можно подставить
        в SQL-запрос вида SELECT * FROM puzzles WHERE <where_clause>.
        """
        conditions = ["1=1"]
        params: List[Any] = []

        if puzzle_id_contains:
            conditions.append("PuzzleId LIKE ?")
            params.append(f"%{puzzle_id_contains}%")
        if rating_min is not None:
            conditions.append("Rating >= ?")
            params.append(rating_min)
        if rating_max is not None:
            conditions.append("Rating <= ?")
            params.append(rating_max)
        if popularity_min is not None:
            conditions.append("Popularity >= ?")
            params.append(popularity_min)
        if popularity_max is not None:
            conditions.append("Popularity <= ?")
            params.append(popularity_max)
        if nb_plays_min is not None:
            conditions.append("NbPlays >= ?")
            params.append(nb_plays_min)
        if nb_plays_max is not None:
            conditions.append("NbPlays <= ?")
            params.append(nb_plays_max)
        if color:
            conditions.append("Color = ?")
            params.append(color)
        if opening_contains:
            conditions.append("OpeningTags LIKE ?")
            params.append(f"%{opening_contains}%")
        if daily_date_from:
            conditions.append("DailyDate >= ?")
            params.append(daily_date_from)
        if daily_date_to:
            conditions.append("DailyDate <= ?")
            params.append(daily_date_to)
        if moves_exact is not None:
            # При наличии материализованного moves_count используем его,
            # иначе считаем количество полуходов из строки Moves.
            if self._has_moves_count_column():
                conditions.append("moves_count = ?")
            else:
                conditions.append(
                    "(LENGTH(Moves) - LENGTH(REPLACE(Moves, ' ', '')) + 1) / 2 = ?"
                )
            params.append(moves_exact)

        where_clause = " AND ".join(conditions)

        # Фильтр по нескольким стандартным темам: задача должна содержать ВСЕ выбранные темы.
        if themes:
            unique_themes = list(dict.fromkeys(themes))
            theme_sql, theme_params = self._build_theme_condition(unique_themes)
            where_clause += f" AND {theme_sql}"
            params.extend(theme_params)

        # Фильтр по пользовательским темам: задача должна принадлежать хотя бы одной из выбранных.
        if user_themes:
            unique_user_themes = [name for name in user_themes if name]
            if unique_user_themes:
                placeholders = ",".join(["?"] * len(unique_user_themes))
                where_clause += (
                    f" AND PuzzleId IN ("
                    f"SELECT puzzle_id FROM puzzle_user_themes "
                    f"WHERE theme_id IN (SELECT id FROM user_themes WHERE name IN ({placeholders}))"
                    f")"
                )
                params.extend(unique_user_themes)

        # Исключение по пользовательским темам: задача НЕ должна принадлежать ни одной из выбранных.
        if exclude_user_themes:
            unique_exclude = [name for name in exclude_user_themes if name]
            if unique_exclude:
                placeholders = ",".join(["?"] * len(unique_exclude))
                where_clause += (
                    f" AND PuzzleId NOT IN ("
                    f"SELECT puzzle_id FROM puzzle_user_themes "
                    f"WHERE theme_id IN (SELECT id FROM user_themes WHERE name IN ({placeholders}))"
                    f")"
                )
                params.extend(unique_exclude)

        return where_clause, params

    def _has_moves_count_column(self) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_xinfo(puzzles)")
        return any(row[1] == "moves_count" for row in cursor.fetchall())

    def get_puzzle_by_offset(self, filters: dict, offset: int) -> Optional["Puzzle"]:
        """Fast path: fetch exactly one puzzle by offset without total count."""
        where_clause, params = self._build_filter_conditions(**filters)
        sql = f"SELECT * FROM puzzles WHERE {where_clause} ORDER BY Rating DESC LIMIT 1 OFFSET ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, params + [offset])
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_puzzle(row)

    def get_puzzle_by_id(self, puzzle_id: str) -> Optional["Puzzle"]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM puzzles WHERE PuzzleId = ?", (puzzle_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_puzzle(row)

    def _build_cache_key(self, **kwargs) -> str:
        parts = []
        for key in sorted(kwargs):
            value = kwargs[key]
            if isinstance(value, list):
                value = tuple(sorted(value))
            parts.append(f"{key}={value}")
        return md5("|".join(parts).encode()).hexdigest()

    def _get_cached(self, cache_key: str, sub_key: str):
        entry = self._filter_cache.get(f"{cache_key}:{sub_key}")
        if entry:
            ts, value = entry
            if time.time() - ts < self._cache_ttl:
                return value
            self._filter_cache.pop(f"{cache_key}:{sub_key}", None)
        return None

    def _set_cached(self, cache_key: str, sub_key: str, value: Any) -> None:
        self._filter_cache[f"{cache_key}:{sub_key}"] = (time.time(), value)

    def _invalidate_cache(self) -> None:
        self._filter_cache.clear()
        self._stats_cache.clear()
        self._theme_counts_cache = None

    def filter_puzzles(
        self,
        puzzle_id_contains: str = "",
        rating_min: Optional[int] = None,
        rating_max: Optional[int] = None,
        popularity_min: Optional[int] = None,
        popularity_max: Optional[int] = None,
        nb_plays_min: Optional[int] = None,
        nb_plays_max: Optional[int] = None,
        themes: Optional[List[str]] = None,
        opening_contains: str = "",
        color: Optional[str] = None,
        daily_date_from: Optional[str] = None,
        daily_date_to: Optional[str] = None,
        moves_exact: Optional[int] = None,
        user_themes: Optional[List[str]] = None,
        exclude_user_themes: Optional[List[str]] = None,
        limit: int = FILTER_DEFAULT_LIMIT,
        offset: int = 0,
        return_total: bool = False,
    ) -> Union[List[Puzzle], tuple[List[Puzzle], int]]:
        """
        Фильтрует задачи по заданным критериям с кэшированием.

        При return_total=True возвращает кортеж (puzzles, total_count),
        где total_count - общее количество задач, удовлетворяющих фильтру.
        Это позволяет реализовать пагинацию без двух отдельных запросов.
        """
        cache_key = self._build_cache_key(
            puzzle_id_contains=puzzle_id_contains,
            rating_min=rating_min,
            rating_max=rating_max,
            popularity_min=popularity_min,
            popularity_max=popularity_max,
            nb_plays_min=nb_plays_min,
            nb_plays_max=nb_plays_max,
            themes=themes,
            opening_contains=opening_contains,
            color=color,
            daily_date_from=daily_date_from,
            daily_date_to=daily_date_to,
            moves_exact=moves_exact,
            user_themes=user_themes,
            exclude_user_themes=exclude_user_themes,
        )
        cached = self._get_cached(cache_key, f"filter:{offset}:{limit}")
        if cached is not None:
            puzzles, total = cached
            return (puzzles, total) if return_total else puzzles

        where_clause, params = self._build_filter_conditions(
            puzzle_id_contains=puzzle_id_contains,
            rating_min=rating_min,
            rating_max=rating_max,
            popularity_min=popularity_min,
            popularity_max=popularity_max,
            nb_plays_min=nb_plays_min,
            nb_plays_max=nb_plays_max,
            color=color,
            opening_contains=opening_contains,
            daily_date_from=daily_date_from,
            daily_date_to=daily_date_to,
            moves_exact=moves_exact,
            themes=themes,
            user_themes=user_themes,
            exclude_user_themes=exclude_user_themes,
        )

        # При return_total=True сначала получаем общее количество задач
        # отдельным COUNT(*), а потом сами задачи. Это значительно быстрее,
        # чем использовать оконную функцию COUNT(*) OVER() на больших объёмах.
        if return_total:
            count_sql = f"SELECT COUNT(*) FROM puzzles WHERE {where_clause}"
            cursor = self.conn.cursor()
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
        else:
            total = 0

        sql = f"SELECT * FROM puzzles WHERE {where_clause} ORDER BY Rating DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        puzzles = [self._row_to_puzzle(row) for row in rows]
        self._set_cached(cache_key, f"filter:{offset}:{limit}", (puzzles, total))
        return (puzzles, total) if return_total else puzzles

    def count_filtered(
        self,
        puzzle_id_contains: str = "",
        rating_min: Optional[int] = None,
        rating_max: Optional[int] = None,
        popularity_min: Optional[int] = None,
        popularity_max: Optional[int] = None,
        nb_plays_min: Optional[int] = None,
        nb_plays_max: Optional[int] = None,
        themes: Optional[List[str]] = None,
        opening_contains: str = "",
        color: Optional[str] = None,
        daily_date_from: Optional[str] = None,
        daily_date_to: Optional[str] = None,
        moves_exact: Optional[int] = None,
        user_themes: Optional[List[str]] = None,
        exclude_user_themes: Optional[List[str]] = None,
    ) -> int:
        where_clause, params = self._build_filter_conditions(
            puzzle_id_contains=puzzle_id_contains,
            rating_min=rating_min,
            rating_max=rating_max,
            popularity_min=popularity_min,
            popularity_max=popularity_max,
            nb_plays_min=nb_plays_min,
            nb_plays_max=nb_plays_max,
            color=color,
            opening_contains=opening_contains,
            daily_date_from=daily_date_from,
            daily_date_to=daily_date_to,
            moves_exact=moves_exact,
            themes=themes,
            user_themes=user_themes,
            exclude_user_themes=exclude_user_themes,
        )

        # Optimization: если единственный значимый фильтр — темы, считаем
        # напрямую из puzzle_themes, без джойна к puzzles. Это ускоряет
        # первый выбор темы на порядок.
        theme_only = (
            themes
            and not puzzle_id_contains
            and not rating_min
            and not rating_max
            and not popularity_min
            and not popularity_max
            and not nb_plays_min
            and not nb_plays_max
            and not color
            and not opening_contains
            and not daily_date_from
            and not daily_date_to
            and moves_exact is None
            and not user_themes
            and not exclude_user_themes
        )
        if theme_only:
            unique_themes = list(dict.fromkeys(themes))
            placeholders = ",".join(["?"] * len(unique_themes))
            cursor = self.conn.cursor()
            cursor.execute(
                f"SELECT COUNT(DISTINCT PuzzleId) FROM puzzle_themes WHERE Theme IN ({placeholders})",
                list(unique_themes),
            )
            return cursor.fetchone()[0]

        sql = f"SELECT COUNT(*) FROM puzzles WHERE {where_clause}"

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()[0]

    # ------------------------------------------------------------------
    # Пользовательские темы
    # ------------------------------------------------------------------
    def get_or_create_user_theme(self, name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM user_themes WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO user_themes (name) VALUES (?)", (name,))
        self.conn.commit()
        return cursor.lastrowid

    def link_puzzles_to_user_theme(self, theme_id: int, puzzle_ids: List[str]) -> None:
        if not puzzle_ids:
            return
        cursor = self.conn.cursor()
        data = [(pid, theme_id) for pid in puzzle_ids]
        cursor.executemany(
            "INSERT OR IGNORE INTO puzzle_user_themes (puzzle_id, theme_id) VALUES (?, ?)",
            data,
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Вспомогательное
    # ------------------------------------------------------------------
    def _row_to_puzzle(self, row: sqlite3.Row) -> Puzzle:
        return Puzzle(
            puzzle_id=row["PuzzleId"],
            fen=row["FEN"],
            moves=row["Moves"],
            rating=row["Rating"],
            rating_deviation=row["RatingDeviation"],
            popularity=row["Popularity"],
            nb_plays=row["NbPlays"],
            themes=row["Themes"].split() if row["Themes"] else [],
            game_url=row["GameUrl"],
            opening_tags=row["OpeningTags"].split(",") if row["OpeningTags"] else [],
            daily_date=row["DailyDate"],
            color=row["Color"],
        )

    def delete_user_themes(self, names: List[str]) -> int:
        cursor = self.conn.cursor()
        placeholders = ",".join(["?"] * len(names))
        cursor.execute(
            f"DELETE FROM puzzle_user_themes WHERE theme_id IN (SELECT id FROM user_themes WHERE name IN ({placeholders}))",
            names,
        )
        cursor.execute(
            f"DELETE FROM user_themes WHERE name IN ({placeholders})",
            names,
        )
        self.conn.commit()
        self._invalidate_cache()
        return cursor.rowcount

    def verify_import(self, csv_path: Optional[str] = None) -> dict:
        """
        Проверяет, что импорт CSV завершился успешно.

        Сравнивает количество задач в локальной БД с количеством строк в CSV.
        Возвращает отчет с результатами проверки.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM puzzles")
        local_total = cursor.fetchone()[0]

        cursor.execute("SELECT Theme, COUNT(*) FROM puzzle_themes GROUP BY Theme")
        local_theme_counts = {row[0]: row[1] for row in cursor.fetchall()}

        csv_total = None
        if csv_path and Path(csv_path).exists():
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    csv_total = sum(1 for _ in f) - 1
            except Exception:
                csv_total = None

        return {
            "local_total": local_total,
            "csv_total": csv_total,
            "theme_counts": local_theme_counts,
            "matches": local_total if csv_total is None else (local_total == csv_total),
            "mismatches": 0 if csv_total is None else abs(local_total - csv_total),
        }

    def ensure_imported(self, progress_callback=None) -> None:
        if not self.is_imported():
            self.import_csv(progress_callback)

    def close(self) -> None:
        self.conn.close()
