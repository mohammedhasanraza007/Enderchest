"""SQL for `drafts`, the add flow's server-stored drafts (DATA_MODEL 2.8, D-049).

A draft is not an item: no count, ring or search ever reads this table. Writes run in the
caller's transaction.
"""

import sqlite3

_COLUMNS = ("id, status, fields, ocr_status, ocr_result, gemini_status, gemini_result, "
            "created_at, updated_at, committed_item_id")


def insert(conn: sqlite3.Connection, user_id: int, draft_id: str, now: str) -> None:
    conn.execute("INSERT INTO drafts (id, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                 (draft_id, user_id, now, now))


def get(conn: sqlite3.Connection, user_id: int, draft_id: str) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM drafts WHERE user_id = ? AND id = ?",
                        (user_id, draft_id)).fetchone()


def list_by_status(conn: sqlite3.Connection, user_id: int, status: str) -> list[sqlite3.Row]:
    return conn.execute(
        f"SELECT {_COLUMNS} FROM drafts WHERE user_id = ? AND status = ? "
        "ORDER BY created_at, rowid", (user_id, status)).fetchall()


def set_fields(conn: sqlite3.Connection, user_id: int, draft_id: str, fields_json: str,
               now: str) -> None:
    conn.execute("UPDATE drafts SET fields = ?, updated_at = ? WHERE user_id = ? AND id = ?",
                 (fields_json, now, user_id, draft_id))


_READING_COLUMNS = {"ocr": ("ocr_status", "ocr_result"),
                    "gemini": ("gemini_status", "gemini_result")}


def set_reading(conn: sqlite3.Connection, user_id: int, draft_id: str, kind: str, status: str,
                result_json: str | None, now: str) -> None:
    """A reading's state; `result_json` None keeps the last result (shown while re-reading)."""
    status_column, result_column = _READING_COLUMNS[kind]
    conn.execute(
        f"UPDATE drafts SET {status_column} = ?, {result_column} = COALESCE(?, {result_column}), "
        "updated_at = ? WHERE user_id = ? AND id = ?",
        (status, result_json, now, user_id, draft_id))


def set_status(conn: sqlite3.Connection, user_id: int, draft_id: str, status: str, now: str,
               committed_item_id: int | None = None) -> None:
    conn.execute(
        "UPDATE drafts SET status = ?, committed_item_id = ?, updated_at = ? "
        "WHERE user_id = ? AND id = ?",
        (status, committed_item_id, now, user_id, draft_id))
