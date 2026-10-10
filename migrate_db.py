#!/usr/bin/env python3
"""
Миграция существующей базы Lichess Puzzle Viewer под новые индексы и схему.

Применяется, если база уже импортирована из CSV до добавления:
- generated столбца moves_count
- индексов idx_puzzle_user_themes_puzzle_theme
- индексов idx_puzzle_themes_puzzle_theme
"""

import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

DB_FILENAME = "puzzles.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute("PRAGMA table_xinfo(" + table + ")")
    return any(row[1] == column for row in cursor.fetchall())


def has_index(cursor: sqlite3.Cursor, name: str) -> bool:
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name=?", (name,))
    return cursor.fetchone()[0] > 0


def migrate(db_path: str) -> None:
    if not os.path.exists(db_path):
        logger.error("DB not found: %s", db_path)
        sys.exit(1)

    logger.info("Connect to %s", db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # moves_count column
        if not has_column(cursor, "puzzles", "moves_count"):
            logger.info("Add moves_count column to puzzles")
            cursor.execute(
                "ALTER TABLE puzzles ADD COLUMN moves_count INTEGER"
            )
            logger.info("Populate moves_count from Moves")
            cursor.execute(
                "UPDATE puzzles SET moves_count = (LENGTH(Moves) - LENGTH(REPLACE(Moves, ' ', '')) + 1) / 2"
            )
            conn.commit()
            logger.info("moves_count populated")
        else:
            logger.info("moves_count already exists")

        # sheets_created column
        if not has_column(cursor, "user_themes", "sheets_created"):
            logger.info("Add sheets_created column to user_themes")
            cursor.execute(
                "ALTER TABLE user_themes ADD COLUMN sheets_created INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            logger.info("sheets_created added")
        else:
            logger.info("sheets_created already exists")

        # Denormalized Rating/Popularity in puzzle_themes + covering index
        # for the theme-only listing fast path.
        added_rating = not has_column(cursor, "puzzle_themes", "Rating")
        if added_rating:
            logger.info("Add Rating column to puzzle_themes")
            cursor.execute("ALTER TABLE puzzle_themes ADD COLUMN Rating INTEGER")
            conn.commit()
        added_popularity = not has_column(cursor, "puzzle_themes", "Popularity")
        if added_popularity:
            logger.info("Add Popularity column to puzzle_themes")
            cursor.execute("ALTER TABLE puzzle_themes ADD COLUMN Popularity INTEGER")
            conn.commit()
        if not (added_rating or added_popularity):
            logger.info("puzzle_themes Rating/Popularity already exist")

        # Backfill once after adding the columns (single pass over puzzle_themes).
        if added_rating or added_popularity:
            logger.info("Backfill puzzle_themes Rating/Popularity from puzzles")
            try:
                cursor.execute(
                    "UPDATE puzzle_themes SET Rating = p.Rating, Popularity = p.Popularity "
                    "FROM puzzles p WHERE p.PuzzleId = puzzle_themes.PuzzleId"
                )
            except sqlite3.OperationalError:
                # UPDATE ... FROM требует SQLite 3.33+; фоллбэк для старых версий.
                cursor.execute(
                    "UPDATE puzzle_themes SET "
                    "Rating = (SELECT p.Rating FROM puzzles p WHERE p.PuzzleId = puzzle_themes.PuzzleId), "
                    "Popularity = (SELECT p.Popularity FROM puzzles p WHERE p.PuzzleId = puzzle_themes.PuzzleId)"
                )
            conn.commit()
            logger.info("Backfill done")

        # Indexes
        indexes = [
            ("idx_puzzle_user_themes_puzzle_theme", "CREATE INDEX IF NOT EXISTS idx_puzzle_user_themes_puzzle_theme ON puzzle_user_themes(puzzle_id, theme_id)"),
            ("idx_puzzle_themes_puzzle_theme", "CREATE INDEX IF NOT EXISTS idx_puzzle_themes_puzzle_theme ON puzzle_themes(PuzzleId, Theme)"),
            ("idx_puzzle_user_themes_theme_puzzle", "CREATE INDEX IF NOT EXISTS idx_puzzle_user_themes_theme_puzzle ON puzzle_user_themes(theme_id, puzzle_id)"),
            ("idx_rating_popularity", "CREATE INDEX IF NOT EXISTS idx_rating_popularity ON puzzles(Rating, Popularity DESC)"),
            ("idx_color_rating_popularity", "CREATE INDEX IF NOT EXISTS idx_color_rating_popularity ON puzzles(Color, Rating, Popularity DESC)"),
            ("idx_puzzle_themes_theme_rating", "CREATE INDEX IF NOT EXISTS idx_puzzle_themes_theme_rating ON puzzle_themes(Theme, Rating, Popularity DESC, PuzzleId)"),
        ]

        # Устаревший индекс под ORDER BY Rating DESC — сортировка теперь ASC.
        if has_index(cursor, "idx_puzzles_color_rating"):
            logger.info("Drop obsolete index idx_puzzles_color_rating")
            cursor.execute("DROP INDEX idx_puzzles_color_rating")
            conn.commit()
        else:
            logger.info("Obsolete index idx_puzzles_color_rating already absent")

        for name, sql in indexes:
            if not has_index(cursor, name):
                logger.info("Create index %s", name)
                cursor.execute(sql)
                conn.commit()
            else:
                logger.info("Index %s already exists", name)

        # WAL and stats
        logger.info("Check WAL mode")
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        logger.info("Current journal_mode=%s", mode)

        logger.info("Run ANALYZE")
        cursor.execute("ANALYZE")
        conn.commit()

        # Summary
        cursor.execute("SELECT COUNT(*) FROM puzzles")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM puzzle_themes")
        themes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM puzzle_user_themes")
        user_links = cursor.fetchone()[0]

        logger.info("Done. puzzles=%s, puzzle_themes=%s, puzzle_user_themes=%s", total, themes, user_links)
    finally:
        conn.close()


if __name__ == "__main__":
    base = Path(__file__).parent
    db_path = str(base / DB_FILENAME)
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    migrate(db_path)
