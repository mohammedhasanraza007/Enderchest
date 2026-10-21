"""SQL for the `users` table. Every query takes user_id (DATA_MODEL 1), even with one user."""

import sqlite3

from ..db.connection import write_transaction


def get(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, timezone, theme FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def update_profile(conn: sqlite3.Connection, user_id: int, *, name: str, timezone: str,
                   theme: str | None, now: str) -> None:
    """Save name and time zone; a theme of None keeps the stored one."""
    with write_transaction(conn):
        conn.execute(
            "UPDATE users SET name = ?, timezone = ?, theme = COALESCE(?, theme), "
            "updated_at = ? WHERE id = ?",
            (name, timezone, theme, now, user_id),
        )
