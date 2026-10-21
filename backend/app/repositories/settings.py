"""SQL for the `settings` table: one row per (user_id, key), the value stored as JSON text."""

import sqlite3

from ..db.connection import write_transaction


def all_values(conn: sqlite3.Connection, user_id: int) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM settings WHERE user_id = ?", (user_id,))
    return {row["key"]: row["value"] for row in rows}


def upsert_many(conn: sqlite3.Connection, user_id: int, values: dict[str, str], now: str) -> None:
    """Write several keys in one transaction, so a patch is applied whole or not at all."""
    with write_transaction(conn):
        for key, value in values.items():
            conn.execute(
                "INSERT INTO settings (user_id, key, value, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (user_id, key, value, now),
            )
