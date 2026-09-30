#!/usr/bin/env python3
"""Archive docx_export.log and remove old archives older than retention days."""

import os
import shutil
import time
from pathlib import Path

LOG_NAME = "docx_export.log"
RETENTION_DAYS = 10
ARCHIVE_EXT = ".gz"


def _now() -> int:
    return int(time.time())


def rotate() -> None:
    log_path = Path(LOG_NAME)
    if not log_path.exists():
        return
    try:
        stat = log_path.stat()
        if stat.st_size == 0:
            return
    except OSError:
        return

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_name = f"{log_path.stem}-{timestamp}{log_path.suffix}"
    archive_path = log_path.with_name(archive_name)
    try:
        shutil.move(str(log_path), str(archive_path))
    except OSError:
        return

    try:
        gz_path = archive_path.with_suffix(log_path.suffix + ARCHIVE_EXT)
        with open(archive_path, "rb") as f_in, __import__("gzip").open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        archive_path.unlink(missing_ok=True)
    except Exception:
        return


def prune() -> None:
    now = _now()
    max_age = RETENTION_DAYS * 86400
    base = Path(".")
    for path in base.glob(f"{Path(LOG_NAME).stem}-*{ARCHIVE_EXT}"):
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age > max_age:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def main() -> None:
    rotate()
    prune()


if __name__ == "__main__":
    main()
