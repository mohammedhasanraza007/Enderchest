"""SQL for `tasks`: maintenance plans and chores (DATA_MODEL 2.9). Writes run in the caller's
transaction, so a task change commits together with its event.
"""

import sqlite3

# The columns a create or an edit may set.
EDITABLE = ("item_id", "title", "kind", "interval_days", "schedule_mode", "next_due", "last_done",
            "enabled", "source", "notes")

_SELECT = (
    "SELECT t.id, t.item_id, t.title, t.kind, t.interval_days, t.schedule_mode, t.next_due, "
    "t.last_done, t.enabled, t.source, t.notes, t.created_at, t.updated_at, t.deleted_at, "
    "i.public_id AS item_public_id, i.name AS item_name, i.state AS item_state, "
    "i.deleted_at AS item_deleted_at "
    "FROM tasks t LEFT JOIN items i ON i.id = t.item_id AND i.user_id = t.user_id"
)


def get(conn: sqlite3.Connection, user_id: int, task_id: int) -> sqlite3.Row | None:
    """A task, deleted ones too (undo needs them)."""
    return conn.execute(f"{_SELECT} WHERE t.user_id = ? AND t.id = ?",
                        (user_id, task_id)).fetchone()


def maintenance_for_item(conn: sqlite3.Connection, user_id: int,
                         item_id: int) -> sqlite3.Row | None:
    return conn.execute(
        f"{_SELECT} WHERE t.user_id = ? AND t.item_id = ? AND t.kind = 'maintenance' "
        "AND t.deleted_at IS NULL", (user_id, item_id)).fetchone()


def listing(conn: sqlite3.Connection, user_id: int, scope: str, due_until: str,
            item_id: int | None) -> list[sqlite3.Row]:
    """GET /tasks scopes (D-106): open, due (overdue or due by `due_until`), all, done."""
    where = ["t.user_id = ?", "t.deleted_at IS NULL"]
    params: list = [user_id]
    order = "t.next_due, t.id"
    if scope in ("open", "due"):
        where.append("t.enabled = 1")
    if scope == "due":
        where.append("t.next_due <= ?")
        params.append(due_until)
    if scope == "done":
        where.append("t.last_done IS NOT NULL")
        order = "t.last_done DESC, t.id DESC"
    if item_id is not None:
        where.append("t.item_id = ?")
        params.append(item_id)
    return conn.execute(f"{_SELECT} WHERE {' AND '.join(where)} ORDER BY {order}",
                        params).fetchall()


def due_by(conn: sqlite3.Connection, user_id: int, today: str) -> list[sqlite3.Row]:
    """Enabled live tasks due today or earlier whose item (if any) is active and not in Trash:
    the tasks that should have a reminder (DATA_MODEL 3.8 steps 2 and 4)."""
    return conn.execute(
        f"{_SELECT} WHERE t.user_id = ? AND t.deleted_at IS NULL AND t.enabled = 1 "
        "AND t.next_due <= ? AND (t.item_id IS NULL OR (i.state = 'active' "
        "AND i.deleted_at IS NULL))", (user_id, today)).fetchall()


def insert(conn: sqlite3.Connection, user_id: int, values: dict, now: str) -> int:
    columns = [c for c in EDITABLE if c in values]
    cursor = conn.execute(
        f"INSERT INTO tasks (user_id, {', '.join(columns)}, created_at, updated_at) "
        f"VALUES (?, {', '.join('?' * len(columns))}, ?, ?)",
        (user_id, *(values[c] for c in columns), now, now))
    return int(cursor.lastrowid)


def update(conn: sqlite3.Connection, user_id: int, task_id: int, changes: dict, now: str) -> None:
    columns = [c for c in EDITABLE if c in changes]
    if not columns:
        return
    assignments = ", ".join(f"{c} = ?" for c in columns)
    conn.execute(f"UPDATE tasks SET {assignments}, updated_at = ? WHERE user_id = ? AND id = ?",
                 (*(changes[c] for c in columns), now, user_id, task_id))


def set_deleted(conn: sqlite3.Connection, user_id: int, task_id: int, deleted_at: str | None,
                now: str) -> None:
    conn.execute("UPDATE tasks SET deleted_at = ?, updated_at = ? WHERE user_id = ? AND id = ?",
                 (deleted_at, now, user_id, task_id))


def ids_for_item(conn: sqlite3.Connection, user_id: int, item_id: int) -> list[int]:
    """Every task row of an item, deleted ones too (permanent delete removes them)."""
    rows = conn.execute("SELECT id FROM tasks WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id)).fetchall()
    return [row["id"] for row in rows]
