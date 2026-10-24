"""SQL for `inspections`, the QM-flavoured record (DATA_MODEL 2.10). Writes run in the caller's
transaction.
"""

import sqlite3

_COLUMNS = "id, item_id, task_id, performed_at, local_date, result, note, photo_id"


def insert(conn: sqlite3.Connection, user_id: int, *, item_id: int, task_id: int | None,
           performed_at: str, local_date: str, result: str, note: str,
           photo_id: str | None) -> int:
    cursor = conn.execute(
        "INSERT INTO inspections (user_id, item_id, task_id, performed_at, local_date, result, "
        "note, photo_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, item_id, task_id, performed_at, local_date, result, note, photo_id))
    return int(cursor.lastrowid)


def get(conn: sqlite3.Connection, user_id: int, inspection_id: int) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM inspections WHERE user_id = ? AND id = ?",
                        (user_id, inspection_id)).fetchone()


def for_item(conn: sqlite3.Connection, user_id: int, item_id: int) -> list[sqlite3.Row]:
    """Newest first."""
    return conn.execute(
        f"SELECT {_COLUMNS} FROM inspections WHERE user_id = ? AND item_id = ? ORDER BY id DESC",
        (user_id, item_id)).fetchall()


def open_findings(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """Active items (not in Trash) whose latest inspection was worn or defective (D-104)."""
    return conn.execute(
        f"SELECT {', '.join('s.' + c.strip() for c in _COLUMNS.split(','))} "
        "FROM inspections s JOIN items i ON i.id = s.item_id AND i.user_id = s.user_id "
        "WHERE s.user_id = ? AND i.state = 'active' AND i.deleted_at IS NULL "
        "AND s.result IN ('worn', 'defective') "
        "AND s.id = (SELECT MAX(id) FROM inspections WHERE user_id = s.user_id "
        "AND item_id = s.item_id)", (user_id,)).fetchall()


def delete_for_item(conn: sqlite3.Connection, user_id: int, item_id: int) -> None:
    """Permanent delete only."""
    conn.execute("DELETE FROM inspections WHERE user_id = ? AND item_id = ?", (user_id, item_id))
