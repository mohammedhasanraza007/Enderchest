"""SQL for `items` (DATA_MODEL 2.6). Every query takes user_id. Writes run in the caller's
transaction, so an item change and its event commit together.
"""

import sqlite3
from dataclasses import dataclass

_SUMMARY = (
    "SELECT i.id, i.public_id, i.name, i.category_id, c.name AS category_name, i.location_id, "
    "i.quantity, i.state, i.expiry_mode, i.expiry_date, i.primary_photo_id, i.deleted_at "
    "FROM items i LEFT JOIN categories c ON c.id = i.category_id"
)
_DETAIL = (
    "SELECT i.*, c.name AS category_name FROM items i "
    "LEFT JOIN categories c ON c.id = i.category_id"
)
_ORDER = {
    "created_desc": "i.created_at DESC, i.id DESC",
    "name_asc": "i.name COLLATE NOCASE ASC, i.id ASC",
    "expiry_asc": "(i.expiry_date IS NULL), i.expiry_date ASC, i.name COLLATE NOCASE, i.id",
}
# Columns a create or an edit may write; anything else is refused by the service first.
EDITABLE = ("name", "category_id", "location_id", "quantity", "expiry_mode", "expiry_date",
            "price_paise", "attributes", "notes", "no_label_needed")


@dataclass(frozen=True)
class ItemQuery:
    """The filters of GET /items (API 2.5), already checked and resolved by the service."""

    words: tuple[str, ...] = ()
    category_id: int | None = None
    location_ids: tuple[int, ...] | None = None  # the location and its descendants
    state: str = "active"
    expiry: str = "any"
    has_photo: bool | None = None
    deleted: str = "exclude"
    today: str = ""  # the owner's local date, for the expiry filters
    soon_until: str = ""  # today + lead_days
    sort: str = "created_desc"


def _escape_like(word: str) -> str:
    return word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _where(user_id: int, query: ItemQuery) -> tuple[str, list]:
    clauses, params = ["i.user_id = ?"], [user_id]
    clauses.append("i.deleted_at IS NULL" if query.deleted == "exclude"
                   else "i.deleted_at IS NOT NULL")
    if query.state != "all":
        clauses.append("i.state = ?")
        params.append(query.state)
    for word in query.words:
        pattern = f"%{_escape_like(word)}%"
        clauses.append("(i.name LIKE ? ESCAPE '\\' OR i.attributes LIKE ? ESCAPE '\\' "
                       "OR i.public_id LIKE ? ESCAPE '\\')")
        params += [pattern, pattern, pattern]
    if query.category_id is not None:
        clauses.append("i.category_id = ?")
        params.append(query.category_id)
    if query.location_ids is not None:
        clauses.append(f"i.location_id IN ({','.join('?' * len(query.location_ids))})")
        params += list(query.location_ids)
    if query.has_photo is not None:
        clauses.append("i.primary_photo_id IS NOT NULL" if query.has_photo
                       else "i.primary_photo_id IS NULL")
    if query.expiry == "soon":
        clauses.append("i.expiry_mode = 'date' AND i.expiry_date > ? AND i.expiry_date <= ?")
        params += [query.today, query.soon_until]
    elif query.expiry == "today":
        clauses.append("i.expiry_mode = 'date' AND i.expiry_date = ?")
        params.append(query.today)
    elif query.expiry == "past":
        clauses.append("i.expiry_mode = 'date' AND i.expiry_date < ?")
        params.append(query.today)
    elif query.expiry in ("none", "unknown"):
        clauses.append("i.expiry_mode = ?")
        params.append(query.expiry)
    return " AND ".join(clauses), params


def search(conn: sqlite3.Connection, user_id: int, query: ItemQuery, limit: int,
           offset: int) -> list[sqlite3.Row]:
    where, params = _where(user_id, query)
    return conn.execute(
        f"{_SUMMARY} WHERE {where} ORDER BY {_ORDER[query.sort]} LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()


def count(conn: sqlite3.Connection, user_id: int, query: ItemQuery) -> int:
    where, params = _where(user_id, query)
    return int(conn.execute(f"SELECT COUNT(*) FROM items i WHERE {where}", params).fetchone()[0])


def get(conn: sqlite3.Connection, user_id: int, public_id: str) -> sqlite3.Row | None:
    return conn.execute(f"{_DETAIL} WHERE i.user_id = ? AND i.public_id = ?",
                        (user_id, public_id)).fetchone()


def get_by_id(conn: sqlite3.Connection, user_id: int, item_id: int) -> sqlite3.Row | None:
    return conn.execute(f"{_DETAIL} WHERE i.user_id = ? AND i.id = ?",
                        (user_id, item_id)).fetchone()


def public_id_used(conn: sqlite3.Connection, public_id: str) -> bool:
    """True if any item has it, or a permanently deleted item had it (never reused)."""
    if conn.execute("SELECT 1 FROM items WHERE public_id = ?", (public_id,)).fetchone():
        return True
    return conn.execute(
        "SELECT 1 FROM events WHERE kind = 'item_purged' "
        "AND json_extract(payload, '$.public_id') = ?", (public_id,),
    ).fetchone() is not None


def insert(conn: sqlite3.Connection, user_id: int, public_id: str, values: dict, now: str) -> int:
    columns = [c for c in EDITABLE if c in values]
    cursor = conn.execute(
        f"INSERT INTO items (user_id, public_id, {', '.join(columns)}, created_at, updated_at, "
        f"state_changed_at) VALUES (?, ?, {', '.join('?' * len(columns))}, ?, ?, ?)",
        (user_id, public_id, *(values[c] for c in columns), now, now, now),
    )
    return int(cursor.lastrowid)


def update(conn: sqlite3.Connection, user_id: int, item_id: int, changes: dict, now: str) -> None:
    columns = [c for c in EDITABLE if c in changes]
    if not columns:
        return
    assignments = ", ".join(f"{c} = ?" for c in columns)
    conn.execute(f"UPDATE items SET {assignments}, updated_at = ? WHERE user_id = ? AND id = ?",
                 (*(changes[c] for c in columns), now, user_id, item_id))


def set_deleted(conn: sqlite3.Connection, user_id: int, item_id: int, deleted_at: str | None,
                now: str) -> None:
    conn.execute("UPDATE items SET deleted_at = ?, updated_at = ? WHERE user_id = ? AND id = ?",
                 (deleted_at, now, user_id, item_id))


def set_primary_photo(conn: sqlite3.Connection, user_id: int, item_id: int,
                      photo_id: str | None, now: str) -> None:
    conn.execute(
        "UPDATE items SET primary_photo_id = ?, updated_at = ? WHERE user_id = ? AND id = ?",
        (photo_id, now, user_id, item_id))


def mark_label_printed(conn: sqlite3.Connection, user_id: int, item_id: int, now: str) -> None:
    conn.execute(
        "UPDATE items SET label_printed_at = ?, updated_at = ? WHERE user_id = ? AND id = ?",
        (now, now, user_id, item_id))


def count_using(conn: sqlite3.Connection, user_id: int, column: str, ids: list[int]) -> int:
    """Items (Trash included) whose category_id or location_id is one of `ids`."""
    assert column in ("category_id", "location_id")
    marks = ",".join("?" * len(ids))
    return int(conn.execute(
        f"SELECT COUNT(*) FROM items WHERE user_id = ? AND {column} IN ({marks})",
        (user_id, *ids)).fetchone()[0])


def reassign(conn: sqlite3.Connection, user_id: int, column: str, from_id: int,
             to_id: int | None, now: str) -> None:
    """Move every item (Trash included) from one category or location to another, or to none."""
    assert column in ("category_id", "location_id")
    conn.execute(f"UPDATE items SET {column} = ?, updated_at = ? WHERE user_id = ? "
                 f"AND {column} = ?", (to_id, now, user_id, from_id))


def purge(conn: sqlite3.Connection, user_id: int, item_id: int) -> list[tuple[str, str]]:
    """Remove the item row and what points at it. The caller records `item_purged` first.

    Returns the (photo, thumbnail) paths of its photo rows, hidden ones too, so the caller can
    remove the files after the commit. Drafts that made the item keep their history without the
    link; the item's own events go, except `item_purged`.
    """
    rows = conn.execute("SELECT path, thumb_path FROM photos WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id)).fetchall()
    files = [(row["path"], row["thumb_path"]) for row in rows]
    conn.execute("DELETE FROM photos WHERE user_id = ? AND item_id = ?", (user_id, item_id))
    conn.execute("UPDATE drafts SET committed_item_id = NULL WHERE user_id = ? "
                 "AND committed_item_id = ?", (user_id, item_id))
    conn.execute("DELETE FROM events WHERE user_id = ? AND item_id = ? AND kind != 'item_purged'",
                 (user_id, item_id))
    conn.execute("DELETE FROM items WHERE user_id = ? AND id = ?", (user_id, item_id))
    return files
