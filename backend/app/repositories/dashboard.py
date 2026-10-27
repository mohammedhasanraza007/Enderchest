"""SQL for the dashboard (DATA_MODEL 3.3, 3.4): the active items and the counted tasks, with the
columns the rings need. The service classifies them, so a count and its breakdown list come from
the same rows (F-020)."""

import sqlite3


def active_items(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """Active items not in Trash (3.3), each with whether it has a live photo."""
    return conn.execute(
        "SELECT i.id, i.public_id, i.name, i.location_id, i.expiry_mode, i.expiry_date, "
        "i.label_printed_at, i.no_label_needed, i.primary_photo_id, "
        "EXISTS (SELECT 1 FROM photos p WHERE p.user_id = i.user_id AND p.item_id = i.id "
        "        AND p.deleted_at IS NULL) AS has_photo "
        "FROM items i WHERE i.user_id = ? AND i.state = 'active' AND i.deleted_at IS NULL "
        "ORDER BY i.name COLLATE NOCASE, i.id", (user_id,)).fetchall()


def counted_tasks(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """Enabled live tasks whose item, if any, is active and not in Trash (D-112): the same set the
    reconcile raises reminders for."""
    return conn.execute(
        "SELECT t.id, t.title, t.kind, t.next_due, i.public_id AS item_public_id "
        "FROM tasks t LEFT JOIN items i ON i.id = t.item_id AND i.user_id = t.user_id "
        "WHERE t.user_id = ? AND t.deleted_at IS NULL AND t.enabled = 1 "
        "AND (t.item_id IS NULL OR (i.state = 'active' AND i.deleted_at IS NULL)) "
        "ORDER BY t.next_due, t.title COLLATE NOCASE, t.id", (user_id,)).fetchall()


STREAK_KINDS = ("item_used", "item_expired_marked", "item_discarded", "task_done",
                "inspection_done", "notification_resolved")


def acted_days(conn: sqlite3.Connection, user_id: int) -> list[str]:
    """Local dates of the actions that count for the streak and were not undone (D-127)."""
    marks = ", ".join("?" for _ in STREAK_KINDS)
    rows = conn.execute(
        f"SELECT DISTINCT e.local_date FROM events e WHERE e.user_id = ? AND e.kind IN ({marks}) "
        "AND NOT EXISTS (SELECT 1 FROM events u WHERE u.user_id = e.user_id "
        "AND json_extract(u.payload, '$.undo_of') = e.id)",
        (user_id, *STREAK_KINDS)).fetchall()
    return [row[0] for row in rows]


def reminder_spans(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """When each reminder row was created and resolved (UTC stamps), for the streak's due days."""
    return conn.execute(
        "SELECT created_at, resolved_at FROM notifications WHERE user_id = ?",
        (user_id,)).fetchall()
