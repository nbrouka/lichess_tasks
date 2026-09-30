#!/usr/bin/env python3
"""Regenerate test DOCX files from puzzles.db."""

import os
import sqlite3
from pathlib import Path

from database import PuzzleDatabase, Puzzle
from ui_selection import PuzzleSelectionMixin
from docx_exporter import PuzzleDocxExporter


class Regenerator(PuzzleSelectionMixin):
    def __init__(self, db_path: str):
        self.db = PuzzleDatabase(db_path=db_path, csv_path="")
        self.selected_puzzles = []

    def load_puzzles(self, limit: int):
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes, GameUrl, OpeningTags, DailyDate, Color FROM puzzles LIMIT ?",
            (limit,),
        )
        puzzles = []
        for row in cursor.fetchall():
            puzzles.append(Puzzle(
                puzzle_id=row[0],
                fen=row[1],
                moves=row[2],
                rating=row[3],
                rating_deviation=row[4],
                popularity=row[5],
                nb_plays=row[6],
                themes=row[7].split() if row[7] else [],
                game_url=row[8],
                opening_tags=row[9].split(",") if row[9] else [],
                daily_date=row[10],
                color=row[11],
            ))
        return puzzles

    def export(self, puzzles, topic: str, path: str):
        self.selected_puzzles = puzzles
        self._create_sheets_docx(path, topic)


def main():
    base = Path(__file__).parent
    db_path = str(base / "puzzles.db")
    out_base = base

    reg = Regenerator(db_path)

    sets = [
        (12, "Test 12 puzzles", out_base / "Test 12 puzzles.docx"),
        (25, "Test 25 puzzles", out_base / "Test 25 puzzles.docx"),
        (12, "Test Topic", out_base / "Test Topic.docx"),
    ]

    for count, topic, path in sets:
        print(f"Generating {path} ({count} puzzles)...")
        puzzles = reg.load_puzzles(count)
        reg.export(puzzles, topic, str(path))
        print(f"Saved {path}")

    # Also regenerate named files referenced in repo root
    extra = [
        (12, "Test 12 puzzles", out_base / "test_12_puzzles_fit_one_page.docx"),
        (25, "Test 25 puzzles", out_base / "test_25_puzzles_create_three_pages.docx"),
    ]
    for count, topic, path in extra:
        print(f"Generating {path} ({count} puzzles)...")
        puzzles = reg.load_puzzles(count)
        reg.export(puzzles, topic, str(path))
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
