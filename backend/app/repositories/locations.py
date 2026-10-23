"""SQL for `locations`, a tree of places (DATA_MODEL 2.5).

Writes run in the caller's transaction.
"""

import sqlite3


def list_all(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """Every live location with its own item count (items directly in it, Trash left out)."""
    return conn.execute(
        "SELECT l.id, l.name, l.parent_id, "
        "(SELECT COUNT(*) FROM items i WHERE i.location_id = l.id AND i.deleted_at IS NULL) "
        "AS item_count FROM locations l WHERE l.user_id = ? AND l.deleted_at IS NULL "
        "ORDER BY l.name COLLATE NOCASE",
        (user_id,),
    ).fetchall()


def name_taken(conn: sqlite3.Connection, user_id: int, name: str, parent_id: int | None,
               except_id: int | None = None) -> bool:
    row = conn.execute(
        "SELECT 1 FROM locations WHERE user_id = ? AND deleted_at IS NULL "
        "AND COALESCE(parent_id, 0) = COALESCE(?, 0) AND name = ? COLLATE NOCASE "
        "AND id IS NOT ?",
        (user_id, parent_id, name, except_id),
    ).fetchone()
    return row is not None


def insert(conn: sqlite3.Connection, user_id: int, *, name: str, parent_id: int | None,
           now: str) -> int:
    cursor = conn.execute(
        "INSERT INTO locations (user_id, name, parent_id, created_at) VALUES (?, ?, ?, ?)",
        (user_id, name, parent_id, now),
    )
    return int(cursor.lastrowid)


def update(conn: sqlite3.Connection, user_id: int, location_id: int, *, name: str,
           parent_id: int | None) -> None:
    conn.execute("UPDATE locations SET name = ?, parent_id = ? WHERE user_id = ? AND id = ?",
                 (name, parent_id, user_id, location_id))


def soft_delete(conn: sqlite3.Connection, user_id: int, location_id: int, now: str) -> None:
    conn.execute("UPDATE locations SET deleted_at = ? WHERE user_id = ? AND id = ?",
                 (now, user_id, location_id))


def descendant_ids(conn: sqlite3.Connection, user_id: int, location_id: int) -> list[int]:
    """The location itself and every live location below it."""
    rows = conn.execute(
        "WITH RECURSIVE sub(id) AS (SELECT ? UNION "
        "SELECT l.id FROM locations l JOIN sub ON l.parent_id = sub.id "
        "WHERE l.user_id = ? AND l.deleted_at IS NULL) SELECT id FROM sub",
        (location_id, user_id),
    ).fetchall()
    return [row["id"] for row in rows]
