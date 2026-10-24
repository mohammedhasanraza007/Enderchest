"""Confirmed savings (Phase 6; DATA_MODEL 2.13; API 2.14; P-14).

A saving is written only when the owner taps "I didn't buy it" and confirms a price they typed
(CLAUDE.md 6): there are no estimates. Amounts are integer paise. "This month" is the month of
today in the owner's time zone. Removing is a soft delete with Undo (60 s, `services.undo`).
"""

import json
import sqlite3
from datetime import date

from .. import clock
from ..db.connection import write_transaction
from ..errors import AppError
from ..repositories import events as events_repo
from ..repositories import items as items_repo
from ..repositories import savings as savings_repo
from . import profile as profile_service
from .items import decode_cursor, encode_cursor, problem

UNDOABLE = {"saving_added", "saving_removed"}
PAGE_MAX = 200


def _month_start(today: date) -> str:
    return today.replace(day=1).isoformat()


def add(conn: sqlite3.Connection, user_id: int, body: dict) -> dict:
    """POST /savings: `item_public_id` (an item the owner has) or `item_name`, and the price."""
    item_id, name = None, body.get("item_name")
    if body.get("item_public_id"):
        row = items_repo.get(conn, user_id, body["item_public_id"])
        if row is None or row["deleted_at"] is not None:
            raise AppError("not_found", 404, "That item is not in your inventory.",
                           {"field": "item_public_id"})
        item_id, name = row["id"], row["name"]
    if not name:
        raise problem("item_name", "Enter the item name.")
    today = profile_service.local_today(conn, user_id)
    now = clock.stamp()
    with write_transaction(conn):
        saving_id = savings_repo.insert(conn, user_id, {
            "item_id": item_id, "item_name": name, "price_paise": body["price_paise"],
            "confirmed_at": now, "local_date": today.isoformat(), "note": body.get("note", "")})
        event_id = _event(conn, user_id, "saving_added", saving_id, now, today)
    return {"id": saving_id, "event_id": event_id}


def remove(conn: sqlite3.Connection, user_id: int, saving_id: int) -> dict:
    """DELETE /savings/{id}: hidden from totals and the list; Undo brings it back."""
    row = savings_repo.get(conn, user_id, saving_id)
    if row is None or row["deleted_at"] is not None:
        raise AppError("not_found", 404, "That saving is not in the list.")
    today = profile_service.local_today(conn, user_id)
    now = clock.stamp()
    with write_transaction(conn):
        savings_repo.set_deleted(conn, user_id, saving_id, now)
        event_id = _event(conn, user_id, "saving_removed", saving_id, now, today)
    return {"event_id": event_id}


def _event(conn: sqlite3.Connection, user_id: int, kind: str, saving_id: int, now: str,
           today: date, extra: dict | None = None) -> int:
    # No item_id: a saving is not a change to the item, so it stays out of the item's history.
    return events_repo.add(conn, user_id, kind=kind, item_id=None,
                           payload={"saving_id": saving_id, **(extra or {})}, at=now,
                           local_date=today.isoformat())


def undo(conn: sqlite3.Connection, user_id: int, event: sqlite3.Row) -> None:
    """Undo an add (the saving is removed) or a remove (it comes back)."""
    saving_id = json.loads(event["payload"])["saving_id"]
    deleted_at = clock.stamp() if event["kind"] == "saving_added" else None
    with write_transaction(conn):
        savings_repo.set_deleted(conn, user_id, saving_id, deleted_at)
        _event(conn, user_id, "saving_undone", saving_id, clock.stamp(),
               profile_service.local_today(conn, user_id), {"undo_of": event["id"]})


def listing(conn: sqlite3.Connection, user_id: int, period: str, limit: int,
            cursor: str | None) -> dict:
    """GET /savings: both totals always; the list for this month or all time."""
    since = _month_start(profile_service.local_today(conn, user_id))
    offset = decode_cursor(cursor)
    rows = savings_repo.listing(conn, user_id, since if period == "month" else None, limit + 1,
                                offset)
    more = len(rows) > limit
    return {"total_paise": savings_repo.total(conn, user_id),
            "month_paise": savings_repo.total(conn, user_id, since),
            "items": [dict(row) for row in rows[:limit]],
            "next_cursor": encode_cursor(offset + limit) if more else None}


def for_dashboard(conn: sqlite3.Connection, user_id: int, today: date) -> dict | None:
    """The dashboard pill's data (D-116): `null` until a saving exists."""
    latest = savings_repo.latest_date(conn, user_id)
    if latest is None:
        return None
    return {"month_paise": savings_repo.total(conn, user_id, _month_start(today)),
            "pill_date": latest}
