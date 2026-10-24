"""POST /events/{id}/undo (API 2.10, PAGES 2, D-092): one entry point for every reversible kind.

Undo works for 60 seconds, once; a second click changes nothing. Each kind's own service puts the
old values back from `payload.before` and records an event with `undo_of`.
"""

import sqlite3
from datetime import UTC, datetime, timedelta

from .. import clock
from ..errors import AppError
from ..repositories import events as events_repo
from . import items as items_service
from . import lifecycle as lifecycle_service
from . import savings as savings_service
from . import tasks as tasks_service

UNDO_WINDOW = timedelta(seconds=60)
_TASK_KINDS = {"task_done", "task_skipped", "task_deleted"}
UNDOABLE = {"item_deleted"} | lifecycle_service.UNDOABLE | _TASK_KINDS | savings_service.UNDOABLE


def undo(conn: sqlite3.Connection, user_id: int, event_id: int) -> None:
    event = events_repo.get(conn, user_id, event_id)
    if event is None or event["kind"] not in UNDOABLE:
        raise AppError("not_found", 404, "There is nothing to undo.")
    at = datetime.strptime(event["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    if clock.now() - at > UNDO_WINDOW:
        hint = " Restore the item from Trash." if event["kind"] == "item_deleted" else ""
        raise AppError("undo_expired", 409, f"It is too late to undo.{hint}")
    if events_repo.undone(conn, user_id, event_id):
        return  # a second Undo click changes nothing
    if event["kind"] == "item_deleted":
        items_service.undo_delete(conn, user_id, event)
    elif event["kind"] in lifecycle_service.UNDOABLE:
        lifecycle_service.undo(conn, user_id, event)
    elif event["kind"] in savings_service.UNDOABLE:
        savings_service.undo(conn, user_id, event)
    else:
        tasks_service.undo_task_event(conn, user_id, event)
