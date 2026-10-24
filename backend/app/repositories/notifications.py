"""SQL for `notifications` (DATA_MODEL 2.12). The reconcile owns inserts; writes run in the
caller's transaction.
"""

import sqlite3

_SELECT = (
    "SELECT n.id, n.kind, n.item_id, n.task_id, n.due_date, n.dedupe_key, n.status, "
    "n.snoozed_until, n.read_at, n.os_notified_at, n.created_at, n.resolved_at, n.resolution, "
    "i.public_id AS item_public_id, i.name AS item_name, "
    "i.primary_photo_id AS item_primary_photo_id, t.title AS task_title, t.kind AS task_kind, "
    "(SELECT s.result FROM inspections s WHERE s.user_id = n.user_id AND s.item_id = n.item_id "
    " ORDER BY s.id DESC LIMIT 1) AS latest_result "
    "FROM notifications n "
    "LEFT JOIN items i ON i.id = n.item_id AND i.user_id = n.user_id "
    "LEFT JOIN tasks t ON t.id = n.task_id AND t.user_id = n.user_id"
)
_STATUSES = {"open": ("open",), "snoozed": ("snoozed",), "resolved": ("resolved",),
             "all": ("open", "snoozed", "resolved")}


def get(conn: sqlite3.Connection, user_id: int, notification_id: int) -> sqlite3.Row | None:
    return conn.execute(f"{_SELECT} WHERE n.user_id = ? AND n.id = ?",
                        (user_id, notification_id)).fetchone()


def listing(conn: sqlite3.Connection, user_id: int, status: str, limit: int,
            offset: int) -> list[sqlite3.Row]:
    """Open and snoozed rows soonest first; resolved rows newest resolution first."""
    statuses = _STATUSES[status]
    order = ("n.resolved_at DESC, n.id DESC" if status == "resolved"
             else "n.due_date, n.kind, n.id")
    marks = ",".join("?" * len(statuses))
    return conn.execute(
        f"{_SELECT} WHERE n.user_id = ? AND n.status IN ({marks}) ORDER BY {order} "
        "LIMIT ? OFFSET ?", (user_id, *statuses, limit, offset)).fetchall()


def unresolved(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """Every open or snoozed row: what the reconcile compares with the desired set."""
    return conn.execute(
        "SELECT id, dedupe_key, status, snoozed_until FROM notifications WHERE user_id = ? "
        "AND status IN ('open', 'snoozed')", (user_id,)).fetchall()


def by_keys(conn: sqlite3.Connection, user_id: int, keys: list[str]) -> list[sqlite3.Row]:
    rows: list[sqlite3.Row] = []
    for start in range(0, len(keys), 500):  # stay far below SQLite's bound-parameter limit
        chunk = keys[start:start + 500]
        rows += conn.execute(
            "SELECT id, dedupe_key, status, resolution FROM notifications WHERE user_id = ? "
            f"AND dedupe_key IN ({','.join('?' * len(chunk))})", (user_id, *chunk)).fetchall()
    return rows


def insert(conn: sqlite3.Connection, user_id: int, *, kind: str, item_id: int | None,
           task_id: int | None, due_date: str, dedupe_key: str, now: str) -> None:
    conn.execute(
        "INSERT INTO notifications (user_id, kind, item_id, task_id, due_date, dedupe_key, "
        "status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'open', ?) "
        "ON CONFLICT(dedupe_key) DO NOTHING",
        (user_id, kind, item_id, task_id, due_date, dedupe_key, now))


def reopen(conn: sqlite3.Connection, user_id: int, ids: list[int]) -> None:
    """Back to open; `os_notified_at` stays, so a row never makes a second browser alert."""
    for notification_id in ids:
        conn.execute(
            "UPDATE notifications SET status = 'open', snoozed_until = NULL, resolution = NULL, "
            "resolved_at = NULL WHERE user_id = ? AND id = ?", (user_id, notification_id))


def resolve(conn: sqlite3.Connection, user_id: int, ids: list[int], resolution: str,
            now: str) -> None:
    for notification_id in ids:
        conn.execute(
            "UPDATE notifications SET status = 'resolved', snoozed_until = NULL, "
            "resolution = ?, resolved_at = ? WHERE user_id = ? AND id = ? "
            "AND status != 'resolved'", (resolution, now, user_id, notification_id))


def unresolved_for(conn: sqlite3.Connection, user_id: int, *, item_id: int | None = None,
                   task_id: int | None = None) -> list[int]:
    """Open or snoozed rows of one item or one task."""
    column, value = ("item_id", item_id) if item_id is not None else ("task_id", task_id)
    rows = conn.execute(
        f"SELECT id FROM notifications WHERE user_id = ? AND {column} = ? "
        "AND status IN ('open', 'snoozed')", (user_id, value)).fetchall()
    return [row["id"] for row in rows]


def snooze(conn: sqlite3.Connection, user_id: int, notification_id: int, until: str) -> None:
    conn.execute("UPDATE notifications SET status = 'snoozed', snoozed_until = ? "
                 "WHERE user_id = ? AND id = ?", (until, user_id, notification_id))


def mark_read(conn: sqlite3.Connection, user_id: int, notification_id: int, now: str) -> None:
    conn.execute("UPDATE notifications SET read_at = ? WHERE user_id = ? AND id = ? "
                 "AND read_at IS NULL", (now, user_id, notification_id))


def mark_all_read(conn: sqlite3.Connection, user_id: int, now: str) -> int:
    cursor = conn.execute("UPDATE notifications SET read_at = ? WHERE user_id = ? "
                          "AND status = 'open' AND read_at IS NULL", (now, user_id))
    return cursor.rowcount


def claim_shown(conn: sqlite3.Connection, user_id: int, notification_id: int, now: str) -> bool:
    """Record the browser alert; True only for the first caller (D-107)."""
    cursor = conn.execute("UPDATE notifications SET os_notified_at = ? WHERE user_id = ? "
                          "AND id = ? AND os_notified_at IS NULL", (now, user_id, notification_id))
    return cursor.rowcount == 1


def counts(conn: sqlite3.Connection, user_id: int) -> tuple[int, int]:
    row = conn.execute(
        "SELECT COUNT(*) AS open, COALESCE(SUM(read_at IS NULL), 0) AS unread "
        "FROM notifications WHERE user_id = ? AND status = 'open'", (user_id,)).fetchone()
    return int(row["open"]), int(row["unread"])


def unshown(conn: sqlite3.Connection, user_id: int, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        f"{_SELECT} WHERE n.user_id = ? AND n.status = 'open' AND n.os_notified_at IS NULL "
        "ORDER BY n.due_date, n.kind, n.id LIMIT ?", (user_id, limit)).fetchall()


def delete_for(conn: sqlite3.Connection, user_id: int, *, item_id: int | None = None,
               task_ids: list[int] | None = None) -> None:
    """Permanent delete only: the rows of a purged item and of its tasks."""
    if item_id is not None:
        conn.execute("DELETE FROM notifications WHERE user_id = ? AND item_id = ?",
                     (user_id, item_id))
    for task_id in task_ids or []:
        conn.execute("DELETE FROM notifications WHERE user_id = ? AND task_id = ?",
                     (user_id, task_id))
