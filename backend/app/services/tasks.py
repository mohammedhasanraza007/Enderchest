"""Tasks, maintenance and inspections (API 2.11; DATA_MODEL 2.9, 2.10; D-102, D-106).

Every change writes its event in the same transaction. A maintenance task belongs to one item
(at most one live per item); its `enabled` flag is the item's maintenance toggle.
"""

import json
import sqlite3
from datetime import date, timedelta

from .. import clock, ids
from ..db.connection import write_transaction
from ..derived import next_due_after, task_word
from ..errors import AppError
from ..repositories import drafts as drafts_repo
from ..repositories import events as events_repo
from ..repositories import inspections as inspections_repo
from ..repositories import items as items_repo
from ..repositories import photos as photos_repo
from ..repositories import tasks as tasks_repo
from . import notifications as notifications_service
from . import profile as profile_service

DUE_SOON_DAYS = 7  # "Due soon" on the Tasks page: overdue or due within a week (D-106)
_TITLE_MAX = 120


def _not_found() -> AppError:
    return AppError("not_found", 404, "That task does not exist.")


def _problem(field: str, message: str) -> AppError:
    return AppError("validation_error", 422, "Some values are not valid.",
                    {"problems": [{"field": field, "problem": message}]})


def task_view(row: sqlite3.Row, today: date) -> dict:
    last_done = date.fromisoformat(row["last_done"]) if row["last_done"] else None
    item = None
    if row["item_id"] is not None and row["item_public_id"] is not None:
        item = {"public_id": row["item_public_id"], "name": row["item_name"]}
    return {
        "id": row["id"], "title": row["title"], "kind": row["kind"], "item": item,
        "interval_days": row["interval_days"], "schedule_mode": row["schedule_mode"],
        "next_due": row["next_due"], "last_done": row["last_done"],
        "enabled": bool(row["enabled"]), "source": row["source"], "notes": row["notes"],
        "word": task_word(date.fromisoformat(row["next_due"]), today, bool(row["enabled"]),
                          row["interval_days"], last_done),
    }


def _live_task(conn: sqlite3.Connection, user_id: int, task_id: int) -> sqlite3.Row:
    row = tasks_repo.get(conn, user_id, task_id)
    if row is None or row["deleted_at"] is not None:
        raise _not_found()
    return row


def _view_by_id(conn: sqlite3.Connection, user_id: int, task_id: int) -> dict:
    return task_view(tasks_repo.get(conn, user_id, task_id),
                     profile_service.local_today(conn, user_id))


def _event(conn: sqlite3.Connection, user_id: int, kind: str, refs: tuple[int | None, int | None],
           payload: dict, now: str) -> int:
    item_id, task_id = refs  # (item, task) the event belongs to
    return events_repo.add(conn, user_id, kind=kind, item_id=item_id, task_id=task_id,
                           payload=payload, at=now,
                           local_date=profile_service.local_today(conn, user_id).isoformat())


def _live_item(conn: sqlite3.Connection, user_id: int, public_id: str,
               field: str | None = None) -> sqlite3.Row:
    """A live item (not in Trash); `field` names the request field when it came from a body."""
    row = items_repo.get(conn, user_id, public_id) if ids.is_public_id(public_id) else None
    if row is None:
        if field:
            raise _problem(field, "That item does not exist.")
        raise AppError("not_found", 404, "That item does not exist.")
    if row["deleted_at"] is not None:
        if field:
            raise _problem(field, "That item is in Trash. Restore it first.")
        raise AppError("conflict", 409, "That item is in Trash. Restore it first.",
                       {"reason": "in_trash"})
    return row


# ---- reading ----------------------------------------------------------------------------------

def list_tasks(conn: sqlite3.Connection, user_id: int, scope: str,
               item_public_id: str | None) -> dict:
    today = profile_service.local_today(conn, user_id)
    item_id = None
    if item_public_id is not None:
        row = items_repo.get(conn, user_id, item_public_id) if ids.is_public_id(
            item_public_id) else None
        if row is None:
            return {"items": []}
        item_id = row["id"]
    due_until = (today + timedelta(days=DUE_SOON_DAYS)).isoformat()
    rows = tasks_repo.listing(conn, user_id, scope, due_until, item_id)
    return {"items": [task_view(row, today) for row in rows]}


def maintenance_view(conn: sqlite3.Connection, user_id: int, item_id: int) -> dict | None:
    row = tasks_repo.maintenance_for_item(conn, user_id, item_id)
    if row is None:
        return None
    return {"task_id": row["id"], "enabled": bool(row["enabled"]),
            "interval_days": row["interval_days"], "next_due": row["next_due"],
            "last_done": row["last_done"], "source": row["source"]}


def maintenance_suggestion(conn: sqlite3.Connection, user_id: int,
                           item_id: int) -> dict | None:
    days = drafts_repo.gemini_interval_for_item(conn, user_id, item_id)
    return {"interval_days": days} if days is not None else None


# ---- tasks ------------------------------------------------------------------------------------

def create_task(conn: sqlite3.Connection, user_id: int, body: dict) -> dict:
    now = clock.stamp()
    with write_transaction(conn):
        item_id = None
        if body.get("item_public_id") is not None:
            item_id = _live_item(conn, user_id, body["item_public_id"], "item_public_id")["id"]
        if body["kind"] == "maintenance":
            if item_id is None:
                raise _problem("item_public_id", "A maintenance task needs an item.")
            if tasks_repo.maintenance_for_item(conn, user_id, item_id) is not None:
                raise AppError("conflict", 409, "That item already has a maintenance plan. "
                               "Change it on the item's page.", {"reason": "has_maintenance"})
        values = {"item_id": item_id, "title": body["title"], "kind": body["kind"],
                  "interval_days": body.get("interval_days"),
                  "schedule_mode": body["schedule_mode"], "next_due": body["first_due"],
                  "enabled": int(body["enabled"]), "source": "user", "notes": body["notes"]}
        task_id = tasks_repo.insert(conn, user_id, values, now)
        _event(conn, user_id, "task_created", (item_id, task_id), {"title": body["title"]}, now)
    return _view_by_id(conn, user_id, task_id)


def change_task(conn: sqlite3.Connection, user_id: int, task_id: int, changes: dict) -> dict:
    now = clock.stamp()
    with write_transaction(conn):
        row = _live_task(conn, user_id, task_id)
        values = {key: changes[key] for key in ("title", "interval_days", "schedule_mode",
                                                "next_due", "notes") if key in changes}
        if "enabled" in changes:
            values["enabled"] = int(changes["enabled"])
        if "item_public_id" in changes:
            if row["kind"] == "maintenance":
                raise _problem("item_public_id", "A maintenance task stays with its item.")
            public_id = changes["item_public_id"]
            values["item_id"] = (None if public_id is None else
                                 _live_item(conn, user_id, public_id, "item_public_id")["id"])
        before = {key: row[key] for key, value in values.items() if row[key] != value}
        if before:
            values["source"] = "user"  # an edited suggestion is the owner's own (DATA_MODEL 2.9)
            tasks_repo.update(conn, user_id, task_id, values, now)
            _event(conn, user_id, "task_updated", (row["item_id"], task_id),
                   {"before": before}, now)
    return _view_by_id(conn, user_id, task_id)


def delete_task(conn: sqlite3.Connection, user_id: int, task_id: int) -> int:
    now = clock.stamp()
    with write_transaction(conn):
        row = _live_task(conn, user_id, task_id)
        tasks_repo.set_deleted(conn, user_id, task_id, now, now)
        return _event(conn, user_id, "task_deleted", (row["item_id"], task_id),
                      {"before": {"deleted_at": None}, "title": row["title"]}, now)


def _complete(conn: sqlite3.Connection, user_id: int, row: sqlite3.Row, today: date,
              *, set_last_done: bool, resolution: str, now: str) -> dict:
    """The completion rule, inside the caller's transaction; returns the fields' old values."""
    before = {"next_due": row["next_due"], "last_done": row["last_done"],
              "enabled": row["enabled"]}
    following = next_due_after(row["schedule_mode"], row["interval_days"],
                               date.fromisoformat(row["next_due"]), today)
    values: dict = {"last_done": today.isoformat()} if set_last_done else {}
    if following is None:
        values["enabled"] = 0  # a one-off is finished
    else:
        values["next_due"] = following.isoformat()
    tasks_repo.update(conn, user_id, row["id"], values, now)
    notifications_service.resolve_for_task(conn, user_id, row["id"], resolution, now)
    return before


def complete_task(conn: sqlite3.Connection, user_id: int, task_id: int, how: str) -> dict:
    """POST /tasks/{id}/done or /skip. Skip moves the schedule but records no `last_done`."""
    now = clock.stamp()
    with write_transaction(conn):
        row = _live_task(conn, user_id, task_id)
        if not row["enabled"]:
            raise AppError("conflict", 409, "This task is switched off. Switch it on first.",
                           {"reason": "disabled"})
        today = profile_service.local_today(conn, user_id)
        done = how == "done"
        before = _complete(conn, user_id, row, today, set_last_done=done,
                           resolution="done" if done else "skipped", now=now)
        event_id = _event(conn, user_id, "task_done" if done else "task_skipped",
                          (row["item_id"], task_id),
                          {"before": before, "on": today.isoformat(), "title": row["title"]}, now)
    return {"task": _view_by_id(conn, user_id, task_id), "event_id": event_id}


def undo_task_event(conn: sqlite3.Connection, user_id: int, event: sqlite3.Row) -> None:
    """Undo `task_done`, `task_skipped` or `task_deleted` (PAGES 2): put the old values back."""
    now = clock.stamp()
    with write_transaction(conn):
        row = tasks_repo.get(conn, user_id, event["task_id"])
        if row is None:
            raise _not_found()
        if events_repo.later_exists(conn, user_id, event["id"], task_id=event["task_id"]):
            raise AppError("conflict", 409, "The task changed since. Undo is not possible.",
                           {"reason": "changed"})
        before = json.loads(event["payload"])["before"]
        if event["kind"] == "task_deleted":
            if row["kind"] == "maintenance" and row["item_id"] is not None and (
                    tasks_repo.maintenance_for_item(conn, user_id, row["item_id"]) is not None):
                raise AppError("conflict", 409, "The item has a new maintenance plan.",
                               {"reason": "has_maintenance"})
            tasks_repo.set_deleted(conn, user_id, row["id"], None, now)
        else:
            tasks_repo.update(conn, user_id, row["id"], before, now)
        _event(conn, user_id, "task_updated", (row["item_id"], row["id"]),
               {"undo_of": event["id"]}, now)


# ---- maintenance and inspections -------------------------------------------------------------

def put_maintenance(conn: sqlite3.Connection, user_id: int, public_id: str, body: dict) -> dict:
    """PUT /items/{id}/maintenance: create or update the item's maintenance task."""
    now = clock.stamp()
    with write_transaction(conn):
        item = _live_item(conn, user_id, public_id)
        today = profile_service.local_today(conn, user_id)
        task = tasks_repo.maintenance_for_item(conn, user_id, item["id"])
        if task is None:
            interval = body.get("interval_days")
            first_due = body.get("first_due") or (
                today + timedelta(days=interval or 0)).isoformat()
            values = {"item_id": item["id"], "title": f"Inspect {item['name']}"[:_TITLE_MAX],
                      "kind": "maintenance", "interval_days": interval,
                      "schedule_mode": "from_completion", "next_due": first_due,
                      "enabled": int(body["enabled"]), "source": body.get("source") or "user",
                      "notes": ""}
            task_id = tasks_repo.insert(conn, user_id, values, now)
            _event(conn, user_id, "task_created", (item["id"], task_id),
                   {"title": values["title"]}, now)
        else:
            task_id = task["id"]
            values = {"enabled": int(body["enabled"])}
            if "interval_days" in body:
                values["interval_days"] = body["interval_days"]
            if body.get("first_due") is not None:
                values["next_due"] = body["first_due"]
            plan_changed = any(task[key] != values[key] for key in ("interval_days", "next_due")
                               if key in values)
            if body.get("source") is not None:
                values["source"] = body["source"]
            elif plan_changed:
                values["source"] = "user"
            before = {key: task[key] for key, value in values.items() if task[key] != value}
            if before:
                tasks_repo.update(conn, user_id, task_id, values, now)
                _event(conn, user_id, "task_updated", (item["id"], task_id),
                       {"before": before}, now)
    return _view_by_id(conn, user_id, task_id)


def inspection_view(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "performed_at": row["performed_at"],
            "local_date": row["local_date"], "result": row["result"], "note": row["note"],
            "photo_id": row["photo_id"]}


def add_inspection(conn: sqlite3.Connection, user_id: int, public_id: str, body: dict) -> dict:
    """An inspection completes the item's maintenance task (DATA_MODEL 2.10); worn and defective
    leave the item active and raise a finding through the reconcile (D-104)."""
    now = clock.stamp()
    with write_transaction(conn):
        item = _live_item(conn, user_id, public_id)
        photo_id = body.get("photo_id")
        if photo_id is not None:
            photo = photos_repo.get(conn, user_id, photo_id)
            if photo is None or photo["item_id"] != item["id"] or photo["deleted_at"]:
                raise _problem("photo_id", "That photo is not one of this item's photos.")
        today = profile_service.local_today(conn, user_id)
        task = tasks_repo.maintenance_for_item(conn, user_id, item["id"])
        before = None
        if task is not None and task["enabled"]:
            before = _complete(conn, user_id, task, today, set_last_done=True,
                               resolution="inspected", now=now)
        inspection_id = inspections_repo.insert(
            conn, user_id, item_id=item["id"], task_id=task["id"] if task else None,
            performed_at=now, local_date=today.isoformat(), result=body["result"],
            note=body.get("note", ""), photo_id=photo_id)
        payload: dict = {"result": body["result"], "inspection_id": inspection_id}
        if before is not None:
            payload["task_before"] = before
        event_id = _event(conn, user_id, "inspection_done",
                          (item["id"], task["id"] if task else None), payload, now)
        inspection = inspections_repo.get(conn, user_id, inspection_id)
    return {"inspection": inspection_view(inspection),
            "task": _view_by_id(conn, user_id, task["id"]) if task else None,
            "event_id": event_id}


def list_inspections(conn: sqlite3.Connection, user_id: int, public_id: str) -> dict:
    row = items_repo.get(conn, user_id, public_id) if ids.is_public_id(public_id) else None
    if row is None:
        raise AppError("not_found", 404, "That item does not exist.")
    return {"items": [inspection_view(r) for r in
                      inspections_repo.for_item(conn, user_id, row["id"])]}
