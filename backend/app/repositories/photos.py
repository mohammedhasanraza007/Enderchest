"""SQL for `photos` (DATA_MODEL 2.7). A photo row belongs to an item or to a draft.

Files never change; hiding a photo sets `deleted_at` only. Writes run in the caller's transaction.
"""

import sqlite3

_COLUMNS = "id, item_id, draft_id, path, thumb_path, width, height, bytes, sha256, mime, created_at"


def insert(conn: sqlite3.Connection, user_id: int, photo: dict) -> None:
    conn.execute(
        "INSERT INTO photos (id, user_id, item_id, draft_id, path, thumb_path, width, height, "
        "bytes, sha256, mime, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (photo["id"], user_id, photo.get("item_id"), photo.get("draft_id"), photo["path"],
         photo["thumb_path"], photo["width"], photo["height"], photo["bytes"], photo["sha256"],
         photo["mime"], photo["created_at"]),
    )


def get(conn: sqlite3.Connection, user_id: int, photo_id: str) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS}, deleted_at FROM photos WHERE user_id = ? AND id = ?",
                        (user_id, photo_id)).fetchone()


def live_for_item(conn: sqlite3.Connection, user_id: int, item_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        f"SELECT {_COLUMNS} FROM photos WHERE user_id = ? AND item_id = ? AND deleted_at IS NULL "
        "ORDER BY created_at, rowid", (user_id, item_id)).fetchall()


def live_for_draft(conn: sqlite3.Connection, user_id: int, draft_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        f"SELECT {_COLUMNS} FROM photos WHERE user_id = ? AND draft_id = ? "
        "AND deleted_at IS NULL ORDER BY created_at, rowid", (user_id, draft_id)).fetchall()


def hide(conn: sqlite3.Connection, user_id: int, photo_id: str, now: str) -> None:
    conn.execute("UPDATE photos SET deleted_at = ? WHERE user_id = ? AND id = ?",
                 (now, user_id, photo_id))


def move_to_item(conn: sqlite3.Connection, user_id: int, draft_id: str, item_id: int) -> None:
    """On commit a draft's photos become the item's (DATA_MODEL 2.7)."""
    conn.execute("UPDATE photos SET item_id = ?, draft_id = NULL WHERE user_id = ? "
                 "AND draft_id = ?", (item_id, user_id, draft_id))


def referenced_paths(conn: sqlite3.Connection) -> list[str]:
    """Every stored photo path, hidden ones too, for the restore report of missing files."""
    return [row["path"] for row in conn.execute("SELECT path FROM photos")]
