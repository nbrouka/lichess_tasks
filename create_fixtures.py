#!/usr/bin/env python3
"""Создаёт фикстуры для тестов из реальной БД puzzles.db.

Генерирует:
- tests/fixtures/puzzles_fixture.csv — CSV с репрезентативной выборкой задач
- tests/fixtures/puzzles_fixture.db — SQLite БД с теми же задачами,
  стандартными темами и пользовательскими темами из реальной БД

Фикстура содержит репрезентативную выборку реальных задач:
- все 9 тем категории «Фазы» (нужны для test_category_filter_updates_listbox)
- частые мотивы (fork, pin, mate и т.д.)
- несколько высокорейтинговых задач для разнообразия
- пользовательские темы и связи из реальной БД

При выполнении тестов реальная БД (puzzles.db, ~4 ГБ) НЕ используется —
тесты работают только с копией этой фикстуры во временной директории.

Использование:
    python create_fixtures.py
"""

import csv
import sqlite3
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
REAL_DB = PROJECT_DIR / "puzzles.db"
FIXTURE_DIR = PROJECT_DIR / "tests" / "fixtures"
FIXTURE_CSV = FIXTURE_DIR / "puzzles_fixture.csv"
FIXTURE_DB = FIXTURE_DIR / "puzzles_fixture.db"

CSV_HEADER = [
    "PuzzleId", "FEN", "Moves", "Rating", "RatingDeviation",
    "Popularity", "NbPlays", "Themes", "GameUrl", "OpeningTags", "DailyDate",
]

# Все 9 тем категории «Фазы» — обязательны, иначе тест
# test_category_filter_updates_listbox не увидит 9 тем в списке.
PHASES_THEMES = [
    "opening", "middlegame", "endgame",
    "rookEndgame", "bishopEndgame", "pawnEndgame",
    "knightEndgame", "queenEndgame", "queenRookEndgame",
]

# Частые мотивы для разнообразия выборки.
MOTIF_THEMES = [
    "fork", "pin", "mate", "mateIn1", "mateIn2",
    "sacrifice", "hangingPiece", "discoveredAttack", "doubleCheck", "skewer",
]

PER_THEME = 2
EXTRA_COUNT = 10


def pick_puzzles(conn: sqlite3.Connection) -> list:
    """Выбирает репрезентативную выборку задач из реальной БД."""
    selected: dict = {}  # PuzzleId -> row (дедупликация)

    def add_theme(theme: str, limit: int) -> None:
        rows = conn.execute(
            """
            SELECT p.PuzzleId, p.FEN, p.Moves, p.Rating, p.RatingDeviation,
                   p.Popularity, p.NbPlays, p.Themes, p.GameUrl,
                   p.OpeningTags, p.DailyDate
            FROM puzzles p
            JOIN puzzle_themes pt ON p.PuzzleId = pt.PuzzleId
            WHERE pt.Theme = ?
            ORDER BY p.Rating DESC
            LIMIT ?
            """,
            (theme, limit),
        ).fetchall()
        for row in rows:
            selected[row[0]] = row

    for theme in PHASES_THEMES + MOTIF_THEMES:
        add_theme(theme, PER_THEME)

    # Дополнительно: высокорейтинговые задачи для разнообразия.
    rows = conn.execute(
        """
        SELECT PuzzleId, FEN, Moves, Rating, RatingDeviation,
               Popularity, NbPlays, Themes, GameUrl, OpeningTags, DailyDate
        FROM puzzles
        ORDER BY Rating DESC
        LIMIT ?
        """,
        (EXTRA_COUNT,),
    ).fetchall()
    for row in rows:
        selected[row[0]] = row

    return list(selected.values())


def write_fixture_csv(rows: list) -> None:
    with open(FIXTURE_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow(["" if v is None else v for v in row])


def build_fixture_db(rows: list) -> None:
    """Строит SQLite-фикстуру с теми же задачами и пользовательскими темами."""
    from database import PuzzleDatabase

    if FIXTURE_DB.exists():
        FIXTURE_DB.unlink()

    db = PuzzleDatabase(db_path=str(FIXTURE_DB), csv_path=str(FIXTURE_CSV))
    cursor = db.conn.cursor()

    puzzle_rows = []
    theme_rows = []
    for row in rows:
        puzzle_id, fen = row[0], row[1]
        # В CSV цвет хода = сторона, которая только что сходила.
        color = fen.split()[1] if len(fen.split()) > 1 else "w"
        puzzle_rows.append((*row, color))
        # Rating/Popularity денормализованы в puzzle_themes для быстрого
        # theme-only пути выборки (covering-индекс).
        for theme in (row[7] or "").split():
            theme_rows.append((puzzle_id, theme, row[3], row[5]))

    cursor.executemany(
        "INSERT OR REPLACE INTO puzzles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        puzzle_rows,
    )
    cursor.executemany(
        "INSERT OR IGNORE INTO puzzle_themes VALUES (?,?,?,?)",
        theme_rows,
    )
    db.conn.commit()

    # Пользовательские темы и связи — копируем из реальной БД,
    # оставляем только связи с задачами из фикстуры.
    fixture_ids = {row[0] for row in rows}
    real = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    try:
        for (name,) in real.execute("SELECT name FROM user_themes ORDER BY id"):
            db.get_or_create_user_theme(name)
        links = real.execute(
            "SELECT pt.puzzle_id, ut.name FROM puzzle_user_themes pt "
            "JOIN user_themes ut ON ut.id = pt.theme_id"
        ).fetchall()
        for puzzle_id, theme_name in links:
            if puzzle_id in fixture_ids:
                theme_id = db.get_or_create_user_theme(theme_name)
                db.link_puzzles_to_user_theme(theme_id, [puzzle_id])
    finally:
        real.close()

    db.create_indexes()
    db.close()


def main() -> int:
    if not REAL_DB.exists():
        print(f"Ошибка: реальная БД не найдена: {REAL_DB}", file=sys.stderr)
        print("Скачайте puzzles.db или выполните импорт CSV.", file=sys.stderr)
        return 1

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    try:
        rows = pick_puzzles(conn)
    finally:
        conn.close()

    write_fixture_csv(rows)
    build_fixture_db(rows)

    print(f"CSV-фикстура создана: {FIXTURE_CSV}")
    print(f"DB-фикстура создана: {FIXTURE_DB}")
    print(f"Задач: {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
