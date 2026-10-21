"""Forward-only numbered SQL migrations (DATA_SAFETY 6, ARCHITECTURE 6).

Each file runs in one transaction together with the `schema_version` update, so a
failed migration leaves the database exactly as it was.
"""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .connection import write_transaction

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


class MigrationError(Exception):
    """A migration failed and was rolled back."""


@dataclass(frozen=True)
class Migration:
    version: int
    path: Path


def available(directory: Path | None = None) -> list[Migration]:
    found = []
    # Resolved at call time so tests can point the runner at a temporary folder.
    for path in sorted((directory or MIGRATIONS_DIR).glob("*.sql")):
        match = _NAME.match(path.name)
        if not match:
            raise MigrationError(f"migration file name is not NNNN_name.sql: {path.name}")
        found.append(Migration(int(match.group(1)), path))
    for expected, migration in enumerate(found, start=1):
        if migration.version != expected:
            raise MigrationError(
                f"migration numbers must run 1..N without gaps; saw {migration.version}")
    return found


def supported_version(directory: Path | None = None) -> int:
    return len(available(directory))


def current_version(conn: sqlite3.Connection) -> int:
    has_meta = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    if not has_meta:
        return 0
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    return int(row["value"]) if row else 0


def split_statements(sql: str) -> list[str]:
    """Split a script into statements; `complete_statement` keeps trigger bodies whole."""
    statements, buffer = [], ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                statements.append(buffer.strip())
            buffer = ""
    if buffer.strip() and not _only_comments(buffer):
        statements.append(buffer.strip())
    return [s for s in statements if not _only_comments(s)]


def _only_comments(text: str) -> bool:
    return all(not line.strip() or line.strip().startswith("--") for line in text.splitlines())


def pending(conn: sqlite3.Connection, directory: Path | None = None) -> list[Migration]:
    version = current_version(conn)
    return [m for m in available(directory) if m.version > version]


def apply(conn: sqlite3.Connection, migration: Migration) -> None:
    statements = split_statements(migration.path.read_text(encoding="utf-8"))
    try:
        with write_transaction(conn):
            for statement in statements:
                conn.execute(statement)
            conn.execute(
                "INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(migration.version),),
            )
    except sqlite3.Error as exc:
        raise MigrationError(f"migration {migration.path.name} failed: {exc}") from exc


def migrate(conn: sqlite3.Connection, directory: Path | None = None) -> list[int]:
    """Apply every pending migration in order; return the versions applied."""
    applied = []
    for migration in pending(conn, directory):
        apply(conn, migration)
        applied.append(migration.version)
    return applied
