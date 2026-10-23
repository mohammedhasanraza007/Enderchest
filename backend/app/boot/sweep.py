"""The start-up photo sweep (DATA_SAFETY 4, D-096).

An upload writes its file first and its row second, so a crash in between leaves a photo file
that no row names. The sweep counts such files so the owner is told; it never deletes one.
"""

import sqlite3
from pathlib import Path


def orphan_photos(conn: sqlite3.Connection, photos_dir: Path) -> list[str]:
    """Photo files that no `photos` row names (hidden photos still count as named)."""
    if not photos_dir.is_dir():
        return []
    has_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='photos'").fetchone()
    named = {row[0] for row in conn.execute("SELECT path FROM photos")} if has_table else set()
    return sorted(p.name for p in photos_dir.iterdir() if p.is_file() and p.name not in named)
