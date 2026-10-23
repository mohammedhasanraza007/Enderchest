"""SQL for `events`, the append-only history (DATA_MODEL 2.11). Writes run in the caller's
transaction, so an event commits together with the change it describes.
"""

import json
import sqlite3


def add(conn: sqlite3.Connection, user_id: int, *, kind: str, item_id: int | None,
        payload: dict, at: str, local_date: str) -> int:
    cursor = conn.execute(
        "INSERT INTO events (user_id, item_id, kind, payload, at, local_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, item_id, kind, json.dumps(payload, separators=(",", ":")), at, local_date),
    )
    return int(cursor.lastrowid)


def get(conn: sqlite3.Connection, user_id: int, event_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, item_id, kind, payload, at, local_date FROM events WHERE user_id = ? "
        "AND id = ?", (user_id, event_id)).fetchone()


def for_item(conn: sqlite3.Connection, user_id: int, item_id: int, limit: int,
             offset: int) -> list[sqlite3.Row]:
    """Newest first."""
    return conn.execute(
        "SELECT id, kind, payload, at, local_date FROM events WHERE user_id = ? AND item_id = ? "
        "ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, item_id, limit, offset)).fetchall()


def undone(conn: sqlite3.Connection, user_id: int, event_id: int) -> bool:
    """True when a later event records that this one was undone."""
    return conn.execute(
        "SELECT 1 FROM events WHERE user_id = ? AND json_extract(payload, '$.undo_of') = ?",
        (user_id, event_id)).fetchone() is not None
