"""The environment marker: `meta.env_marker` must equal ENDERCHEST_ENV (D-054)."""

import sqlite3
from pathlib import Path


def read_marker(db_path: Path) -> str | None:
    """Return the stored marker, or None if the file has none or cannot be read."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
    except sqlite3.Error:
        return None
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'env_marker'").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def matches(marker: str | None, environment: str) -> bool:
    """A readable marker must equal the environment; an unreadable one is left to quick_check."""
    return marker is None or marker == environment
