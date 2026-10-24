"""Item lifecycle: use, mark expired, discard, reactivate, and their undo (API 2.10, D-105).

An item leaves `active` only by the owner's action; when it does, its open reminders resolve with
that action's resolution in the same transaction. Each change stores `payload.before` for undo.
"""

import json
import sqlite3

from .. import clock
from ..db.connection import write_transaction
from ..errors import AppError
from ..repositories import events as events_repo
from ..repositories import items as items_repo
from . import items as items_service
from . import notifications as notifications_service
from . import profile as profile_service

# Event kind and the resolution of the item's reminders, per action.
_LEAVING = {"used": ("item_used", "used"), "expired": ("item_expired_marked", "expired_marked"),
            "discarded": ("item_discarded", "discarded")}
UNDOABLE = {"item_used", "item_expired_marked", "item_discarded"}


def _active_row(conn: sqlite3.Connection, user_id: int, public_id: str) -> sqlite3.Row:
    row = items_service.item_row(conn, user_id, public_id)
    if row["deleted_at"] is not None:
        raise AppError("conflict", 409, "That item is in Trash. Restore it first.",
                       {"reason": "in_trash"})
    if row["state"] != "active":
        raise AppError("conflict", 409, f"That item is already {row['state']}.",
                       {"reason": "not_active", "state": row["state"]})
    return row


def _change(conn: sqlite3.Connection, user_id: int, row: sqlite3.Row, *, state: str,
            quantity: int, kind: str, payload: dict, now: str) -> int:
    """Write the new state and quantity with its event; inside the caller's transaction."""
    before = {"state": row["state"], "quantity": row["quantity"],
              "state_changed_at": row["state_changed_at"]}
    changed_at = now if state != row["state"] else row["state_changed_at"]
    items_repo.set_state(conn, user_id, row["id"], state=state, quantity=quantity,
                         state_changed_at=changed_at, now=now)
    local = profile_service.local_today(conn, user_id).isoformat()
    return events_repo.add(conn, user_id, kind=kind, item_id=row["id"],
                           payload={**payload, "before": before}, at=now, local_date=local)


def use(conn: sqlite3.Connection, user_id: int, public_id: str, amount: int) -> dict:
    """Quantity minus `amount`; at 0 the item is `used` and its reminders resolve."""
    now = clock.stamp()
    with write_transaction(conn):
        row = _active_row(conn, user_id, public_id)
        if amount > row["quantity"]:
            raise items_service.problem(
                "amount", f"You have {row['quantity']}. Use at most that many.")
        left = row["quantity"] - amount
        state = "used" if left == 0 else "active"
        event_id = _change(conn, user_id, row, state=state, quantity=left, kind="item_used",
                           payload={"amount": amount}, now=now)
        if state == "used":
            notifications_service.resolve_for_item(conn, user_id, row["id"], "used", now)
    return {"item": items_service.get_item(conn, user_id, public_id), "event_id": event_id}


def leave(conn: sqlite3.Connection, user_id: int, public_id: str, state: str) -> dict:
    """Mark expired or discard: the item leaves `active` with its quantity kept."""
    kind, resolution = _LEAVING[state]
    now = clock.stamp()
    with write_transaction(conn):
        row = _active_row(conn, user_id, public_id)
        event_id = _change(conn, user_id, row, state=state, quantity=row["quantity"], kind=kind,
                           payload={}, now=now)
        notifications_service.resolve_for_item(conn, user_id, row["id"], resolution, now)
    return {"item": items_service.get_item(conn, user_id, public_id), "event_id": event_id}


def reactivate(conn: sqlite3.Connection, user_id: int, public_id: str,
               quantity: int | None) -> dict:
    """Back to `active`; the quantity is the one sent, else the kept one, else 1."""
    now = clock.stamp()
    with write_transaction(conn):
        row = items_service.item_row(conn, user_id, public_id)
        if row["deleted_at"] is not None:
            raise AppError("conflict", 409, "That item is in Trash. Restore it first.",
                           {"reason": "in_trash"})
        if row["state"] == "active":
            raise AppError("conflict", 409, "That item is already active.",
                           {"reason": "already_active"})
        new_quantity = quantity or row["quantity"] or 1
        _change(conn, user_id, row, state="active", quantity=new_quantity,
                kind="item_reactivated", payload={}, now=now)
    return items_service.get_item(conn, user_id, public_id)


def undo(conn: sqlite3.Connection, user_id: int, event: sqlite3.Row) -> None:
    """Undo use, mark expired or discard: the old state and quantity come back. The reconcile
    that follows reopens the reminders those actions resolved (D-104)."""
    now = clock.stamp()
    with write_transaction(conn):
        row = items_repo.get_by_id(conn, user_id, event["item_id"])
        if row is None:
            raise AppError("not_found", 404, "That item does not exist.")
        if events_repo.later_exists(conn, user_id, event["id"], item_id=row["id"]):
            raise AppError("conflict", 409, "The item changed since. Undo is not possible.",
                           {"reason": "changed"})
        before = json.loads(event["payload"])["before"]
        items_repo.set_state(conn, user_id, row["id"], state=before["state"],
                             quantity=before["quantity"],
                             state_changed_at=before["state_changed_at"], now=now)
        local = profile_service.local_today(conn, user_id).isoformat()
        events_repo.add(conn, user_id, kind="item_updated", item_id=row["id"],
                        payload={"undo_of": event["id"],
                                 "before": {"state": row["state"], "quantity": row["quantity"]}},
                        at=now, local_date=local)
