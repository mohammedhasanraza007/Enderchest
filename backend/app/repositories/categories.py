"""SQL for `categories` (DATA_MODEL 2.4). Every query takes user_id; deleted rows never show.

Writes run inside the caller's `write_transaction`, so a service can change several tables
(reassign items, delete the category, record it) all or nothing.
"""

import sqlite3

_SELECT = (
    "SELECT c.id, c.name, c.expires_default, c.maintenance_default, c.label_default, "
    "(SELECT COUNT(*) FROM items i WHERE i.category_id = c.id AND i.deleted_at IS NULL) "
    "AS item_count FROM categories c WHERE c.user_id = ? AND c.deleted_at IS NULL"
)


def list_all(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(_SELECT + " ORDER BY c.name COLLATE NOCASE", (user_id,)).fetchall()


def get(conn: sqlite3.Connection, user_id: int, category_id: int) -> sqlite3.Row | None:
    return conn.execute(_SELECT + " AND c.id = ?", (user_id, category_id)).fetchone()


def name_taken(conn: sqlite3.Connection, user_id: int, name: str,
               except_id: int | None = None) -> bool:
    row = conn.execute(
        "SELECT 1 FROM categories WHERE user_id = ? AND deleted_at IS NULL "
        "AND name = ? COLLATE NOCASE AND id IS NOT ?",
        (user_id, name, except_id),
    ).fetchone()
    return row is not None


def insert(conn: sqlite3.Connection, user_id: int, *, name: str, expires_default: bool,
           maintenance_default: bool, label_default: bool, now: str) -> int:
    cursor = conn.execute(
        "INSERT INTO categories (user_id, name, expires_default, maintenance_default, "
        "label_default, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, int(expires_default), int(maintenance_default), int(label_default), now),
    )
    return int(cursor.lastrowid)


def update(conn: sqlite3.Connection, user_id: int, category_id: int, changes: dict) -> None:
    """`changes` holds only allowed column names (the service decides which)."""
    if not changes:
        return
    columns = ", ".join(f"{column} = ?" for column in changes)
    values = [int(v) if isinstance(v, bool) else v for v in changes.values()]
    conn.execute(f"UPDATE categories SET {columns} WHERE user_id = ? AND id = ?",
                 (*values, user_id, category_id))


def soft_delete(conn: sqlite3.Connection, user_id: int, category_id: int, now: str) -> None:
    conn.execute("UPDATE categories SET deleted_at = ? WHERE user_id = ? AND id = ?",
                 (now, user_id, category_id))
