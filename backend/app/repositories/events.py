"""SQL for `events`, the append-only history (DATA_MODEL 2.11). Writes run in the caller's
transaction, so an event commits together with the change it describes.
"""

import json
import sqlite3


def add(conn: sqlite3.Connection, user_id: int, *, kind: str, item_id: int | None,
        payload: dict, at: str, local_date: str, task_id: int | None = None) -> int:
    cursor = conn.execute(
        "INSERT INTO events (user_id, item_id, task_id, kind, payload, at, local_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, item_id, task_id, kind, json.dumps(payload, separators=(",", ":")), at,
         local_date),
    )
    return int(cursor.lastrowid)


def get(conn: sqlite3.Connection, user_id: int, event_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, item_id, task_id, kind, payload, at, local_date FROM events "
        "WHERE user_id = ? AND id = ?", (user_id, event_id)).fetchone()


def later_exists(conn: sqlite3.Connection, user_id: int, event_id: int, *,
                 item_id: int | None = None, task_id: int | None = None) -> bool:
    """True when the item (or task) has a newer event: undo then refuses (it would overwrite)."""
    column, value = ("item_id", item_id) if item_id is not None else ("task_id", task_id)
    return conn.execute(
        f"SELECT 1 FROM events WHERE user_id = ? AND {column} = ? AND id > ? LIMIT 1",
        (user_id, value, event_id)).fetchone() is not None


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
