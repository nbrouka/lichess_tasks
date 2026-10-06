#!/usr/bin/env python3
"""CLI script for importing lichess_db_puzzle.csv into local SQLite database."""

import sys
from pathlib import Path

from database import PuzzleDatabase
from constants import DEFAULT_CSV_PATH, DB_FILENAME


def main() -> int:
    csv_path = DEFAULT_CSV_PATH
    db_path = DB_FILENAME

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        db_path = sys.argv[2]

    if not Path(csv_path).exists():
        print(f"Error: CSV file not found: {csv_path}")
        print("Usage: python import_csv.py [csv_path] [db_path]")
        return 1

    print(f"Importing from: {csv_path}")
    print(f"Database: {db_path}")
    print()

    db = PuzzleDatabase(db_path=db_path, csv_path=csv_path)

    if db.is_imported():
        print("Database already imported. Reimporting...")
        db.import_csv()
    else:
        db.import_csv()

    local_total = db.count_filtered()
    print(f"\nLocal puzzles in DB: {local_total}")

    report = db.verify_import(csv_path)
    if report["matches"]:
        print(f"CSV rows: {report['csv_total']}")
        print("All tasks imported successfully.")
    else:
        print(f"CSV rows: {report['csv_total']}")
        print(f"Difference: {report['mismatches']}")
        print("Warning: import verification failed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
