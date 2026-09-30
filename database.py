"""
Модуль для работы с базой данных SQLite.
Поддерживает пакетный импорт CSV и эффективную фильтрацию.
"""

import sqlite3
import csv
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from constants import (
    DB_FILENAME, DEFAULT_CSV_PATH, CSV_COLUMNS,
    SQL_CREATE_PUZZLES, SQL_CREATE_THEMES, SQL_INDEXES,
    IMPORT_BATCH_SIZE, IMPORT_PROGRESS_INTERVAL, FILTER_DEFAULT_LIMIT,
)


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

    # ------------------------------------------------------------------
    # Схема
    # ------------------------------------------------------------------
    def _create_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(SQL_CREATE_PUZZLES)
        cursor.executescript(SQL_CREATE_THEMES)
        self.conn.commit()

    def create_indexes(self) -> None:
        cursor = self.conn.cursor()
        for sql in SQL_INDEXES:
            cursor.execute(sql)
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
    def import_csv(self, progress_callback: Optional[Callable[[int], None]] = None) -> None:
        """
        Импортирует CSV в SQLite с оптимизацией для больших файлов.

        Использует:
        - DROP/CREATE вместо DELETE для очистки таблиц
        - Умеренные PRAGMA для стабильности
        - Пакеты по 20 000 строк с периодическим коммитом
        - Один проход по CSV
        - Создание индексов после вставки
        """
        cursor = self.conn.cursor()

        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA cache_size = -64000")
        cursor.execute("PRAGMA locking_mode = NORMAL")

        cursor.execute("DROP TABLE IF EXISTS puzzle_themes")
        cursor.execute("DROP TABLE IF EXISTS puzzles")
        self._create_schema()

        batch_size = IMPORT_BATCH_SIZE
        batch: List[tuple] = []
        theme_batch: List[tuple] = []
        total_inserted = 0
        i = 0

        try:
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

                    color = fen.split()[1] if len(fen.split()) > 1 else "w"

                    batch.append((
                        puzzle_id, fen, moves, rating, rating_deviation,
                        popularity, nb_plays, themes, game_url,
                        opening_tags, daily_date, color,
                    ))

                    for theme in themes.split():
                        theme_batch.append((puzzle_id, theme))

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
        self.create_indexes()

        if progress_callback:
            progress_callback(i)

    # ------------------------------------------------------------------
    # Справочники
    # ------------------------------------------------------------------
    def get_all_themes(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT Theme FROM puzzle_themes ORDER BY Theme")
        return [r[0] for r in cursor.fetchall()]

    def get_all_openings(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT DISTINCT OpeningTags FROM puzzles "
            "WHERE OpeningTags IS NOT NULL AND OpeningTags != '' "
            "ORDER BY OpeningTags"
        )
        return [r[0] for r in cursor.fetchall()]

    def get_stats(self, filters: Optional[dict] = None) -> dict:
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
                conditions.append(
                    "(LENGTH(puzzles.Moves) - LENGTH(REPLACE(puzzles.Moves, ' ', '')) + 1) / 2 = ?"
                )
                params.append(filters["moves_exact"])
            if filters.get("themes"):
                theme_sql, theme_params = self._build_theme_condition(filters["themes"])
                if theme_sql:
                    conditions.append(theme_sql)
                    params.extend(theme_params)

        where = " AND ".join(conditions)

        cursor.execute(
            f"""
            SELECT
                SUM(CASE WHEN puzzles.Color = 'w' THEN 1 ELSE 0 END) AS white_count,
                SUM(CASE WHEN puzzles.Color = 'b' THEN 1 ELSE 0 END) AS black_count,
                (LENGTH(puzzles.Moves) - LENGTH(REPLACE(puzzles.Moves, ' ', '')) + 1) / 2 AS moves_count,
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

        return stats

    # ------------------------------------------------------------------
    # Фильтрация
    # ------------------------------------------------------------------
    def _build_theme_condition(self, themes: List[str]):
        if not themes:
            return "", []
        if len(themes) == 1:
            return (
                "EXISTS (SELECT 1 FROM puzzle_themes pt WHERE pt.PuzzleId = puzzles.PuzzleId AND pt.Theme = ?)",
                [themes[0]],
            )
        placeholders = ",".join(["?"] * len(themes))
        return (
            f"PuzzleId IN (SELECT PuzzleId FROM puzzle_themes WHERE Theme IN ({placeholders}) GROUP BY PuzzleId HAVING COUNT(DISTINCT Theme) = ?)",
            list(themes) + [len(themes)],
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
    ) -> tuple[str, List[Any]]:
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
            conditions.append(
                "(LENGTH(Moves) - LENGTH(REPLACE(Moves, ' ', '')) + 1) / 2 = ?"
            )
            params.append(moves_exact)

        where_clause = " AND ".join(conditions)

        if themes:
            theme_sql, theme_params = self._build_theme_condition(themes)
            where_clause += f" AND {theme_sql}"
            params.extend(theme_params)

        return where_clause, params

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
        limit: int = FILTER_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> List[Puzzle]:
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
        )

        sql = f"SELECT * FROM puzzles WHERE {where_clause} ORDER BY Rating DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [self._row_to_puzzle(row) for row in rows]

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
        )

        sql = f"SELECT COUNT(*) FROM puzzles WHERE {where_clause}"

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()[0]

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

    def close(self) -> None:
        self.conn.close()

    def ensure_imported(self, progress_callback=None) -> None:
        if not self.is_imported():
            self.import_csv(progress_callback)
