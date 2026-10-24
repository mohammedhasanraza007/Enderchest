"""SQL for `savings` (DATA_MODEL 2.13). Writes run in the caller's transaction.

A removed saving keeps its row with `deleted_at` (soft delete), so Undo can bring it back.
"""

import sqlite3

_VIEW = ("SELECT s.id, s.item_name, i.public_id AS item_public_id, s.price_paise, s.local_date, "
         "s.note FROM savings s LEFT JOIN items i ON i.id = s.item_id AND i.deleted_at IS NULL ")


def insert(conn: sqlite3.Connection, user_id: int, values: dict) -> int:
    cursor = conn.execute(
        "INSERT INTO savings (user_id, item_id, item_name, price_paise, confirmed_at, local_date, "
        "note) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, values["item_id"], values["item_name"], values["price_paise"],
         values["confirmed_at"], values["local_date"], values["note"]))
    return int(cursor.lastrowid)


def get(conn: sqlite3.Connection, user_id: int, saving_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT id, deleted_at FROM savings WHERE user_id = ? AND id = ?",
                        (user_id, saving_id)).fetchone()


def set_deleted(conn: sqlite3.Connection, user_id: int, saving_id: int,
                deleted_at: str | None) -> None:
    conn.execute("UPDATE savings SET deleted_at = ? WHERE user_id = ? AND id = ?",
                 (deleted_at, user_id, saving_id))


def listing(conn: sqlite3.Connection, user_id: int, since: str | None, limit: int,
            offset: int) -> list[sqlite3.Row]:
    """Live savings newest first; `since` (a local date) limits them to this month."""
    where, params = "WHERE s.user_id = ? AND s.deleted_at IS NULL", [user_id]
    if since:
        where += " AND s.local_date >= ?"
        params.append(since)
    return conn.execute(f"{_VIEW}{where} ORDER BY s.local_date DESC, s.id DESC LIMIT ? OFFSET ?",
                        (*params, limit, offset)).fetchall()


def total(conn: sqlite3.Connection, user_id: int, since: str | None = None) -> int:
    sql = ("SELECT COALESCE(SUM(price_paise), 0) FROM savings "
           "WHERE user_id = ? AND deleted_at IS NULL")
    params: list = [user_id]
    if since:
        sql += " AND local_date >= ?"
        params.append(since)
    return int(conn.execute(sql, params).fetchone()[0])


def latest_date(conn: sqlite3.Connection, user_id: int) -> str | None:
    return conn.execute("SELECT MAX(local_date) FROM savings WHERE user_id = ? "
                        "AND deleted_at IS NULL", (user_id,)).fetchone()[0]
