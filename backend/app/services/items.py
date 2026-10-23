"""Items: create, read, edit, delete, restore, permanent delete, history, undo, lookup and labels
(API 2.5, 2.7; DATA_MODEL 2.6, 2.11, 3.2; D-092).

Every change writes its event in the same transaction. Items are addressed by `public_id`.
"""

import base64
import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from .. import clock, ids
from ..config import Settings
from ..db.connection import write_transaction
from ..derived import expiry_view
from ..errors import AppError
from ..logs import log_event
from ..repositories import categories as categories_repo
from ..repositories import events as events_repo
from ..repositories import items as items_repo
from ..repositories import locations as locations_repo
from ..repositories import photos as photos_repo
from . import catalog
from . import profile as profile_service

UNDO_WINDOW = timedelta(seconds=60)
UNDOABLE = {"item_deleted"}
_ID_ATTEMPTS = 20


def _not_found() -> AppError:
    return AppError("not_found", 404, "That item does not exist.")


def problem(field: str, message: str) -> AppError:
    return AppError("validation_error", 422, "Some values are not valid.",
                    {"problems": [{"field": field, "problem": message}]})


# ---- reading ----------------------------------------------------------------------------------

class _Context:
    """What turning rows into views needs: today, lead days and the location paths."""

    def __init__(self, conn: sqlite3.Connection, user_id: int) -> None:
        self.today = profile_service.local_today(conn, user_id)
        self.lead_days = profile_service.lead_days(conn, user_id)
        self.paths = catalog.location_paths(conn, user_id)


def _summary(row: sqlite3.Row, ctx: _Context) -> dict:
    return {
        "public_id": row["public_id"], "name": row["name"],
        "category_name": row["category_name"],
        "location_path": ctx.paths.get(row["location_id"], []) if row["location_id"] else [],
        "quantity": row["quantity"], "state": row["state"],
        "expiry": expiry_view(row["expiry_mode"], row["expiry_date"], ctx.today, ctx.lead_days),
        "primary_photo_id": row["primary_photo_id"],
        "has_photo": row["primary_photo_id"] is not None, "deleted_at": row["deleted_at"],
    }


def _detail(conn: sqlite3.Connection, user_id: int, row: sqlite3.Row) -> dict:
    ctx = _Context(conn, user_id)
    location = None
    if row["location_id"] is not None and row["location_id"] in ctx.paths:
        location = {"id": row["location_id"], "name": ctx.paths[row["location_id"]][-1]}
    photos = photos_repo.live_for_item(conn, user_id, row["id"])
    return {
        **_summary(row, ctx),
        "category": ({"id": row["category_id"], "name": row["category_name"]}
                     if row["category_id"] is not None else None),
        "location": location,
        "price_paise": row["price_paise"], "notes": row["notes"],
        "attributes": json.loads(row["attributes"]),
        "label": {"printed_at": row["label_printed_at"],
                  "no_label_needed": bool(row["no_label_needed"])},
        "photos": [{"id": p["id"], "is_primary": p["id"] == row["primary_photo_id"],
                    "width": p["width"], "height": p["height"]} for p in photos],
        "maintenance": None,
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def item_row(conn: sqlite3.Connection, user_id: int, public_id: str) -> sqlite3.Row:
    """The item's row (Trash included), or `not_found`."""
    row = items_repo.get(conn, user_id, public_id) if ids.is_public_id(public_id) else None
    if row is None:
        raise _not_found()
    return row


def get_item(conn: sqlite3.Connection, user_id: int, public_id: str) -> dict:
    return _detail(conn, user_id, item_row(conn, user_id, public_id))


def detail_by_id(conn: sqlite3.Connection, user_id: int, item_id: int) -> dict:
    row = items_repo.get_by_id(conn, user_id, item_id)
    if row is None:
        raise _not_found()
    return _detail(conn, user_id, row)


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        text = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        kind, _, number = text.partition(":")
        if kind == "o" and number.isdigit():
            return int(number)
    except (ValueError, UnicodeDecodeError):
        pass
    raise problem("cursor", "That page marker is not valid. Reload the list.")


def list_items(conn: sqlite3.Connection, user_id: int, *, q: str | None,
               category_id: int | None, location_id: int | None, state: str, expiry: str,
               has_photo: bool | None, sort: str, deleted: str, limit: int,
               cursor: str | None) -> dict:
    """GET /items. The cursor is an opaque page marker (an offset), so Back restores a list."""
    offset = decode_cursor(cursor)
    ctx = _Context(conn, user_id)
    location_ids = None
    if location_id is not None:
        location_ids = tuple(locations_repo.descendant_ids(conn, user_id, location_id))
    query = items_repo.ItemQuery(
        words=tuple((q or "").split())[:8], category_id=category_id, location_ids=location_ids,
        state=state, expiry=expiry, has_photo=has_photo, deleted=deleted,
        today=ctx.today.isoformat(),
        soon_until=(ctx.today + timedelta(days=ctx.lead_days)).isoformat(), sort=sort)
    rows = items_repo.search(conn, user_id, query, limit + 1, offset)
    page = rows[:limit]
    return {"items": [_summary(row, ctx) for row in page],
            "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None,
            "total": items_repo.count(conn, user_id, query)}


def item_events(conn: sqlite3.Connection, user_id: int, public_id: str, limit: int,
                cursor: str | None) -> dict:
    row = item_row(conn, user_id, public_id)
    offset = decode_cursor(cursor)
    rows = events_repo.for_item(conn, user_id, row["id"], limit + 1, offset)
    return {"items": [{"kind": e["kind"], "payload": json.loads(e["payload"]), "at": e["at"],
                       "local_date": e["local_date"]} for e in rows[:limit]],
            "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None}


def lookup(conn: sqlite3.Connection, user_id: int, code: str) -> dict:
    """A scanned or typed code to its item (API 2.7). Items in Trash are found too."""
    public_id = ids.normalise(code)
    row = items_repo.get(conn, user_id, public_id) if public_id else None
    if row is None:
        raise AppError("not_found", 404, "No item with that ID.")
    return _summary(row, _Context(conn, user_id))


# ---- writing ----------------------------------------------------------------------------------

def _event(conn: sqlite3.Connection, user_id: int, kind: str, item_id: int | None,
           payload: dict, now: str) -> int:
    local = profile_service.local_today(conn, user_id).isoformat()
    return events_repo.add(conn, user_id, kind=kind, item_id=item_id, payload=payload, at=now,
                           local_date=local)


def resolve_expiry(mode: str | None, date: str | None, *, current_mode: str = "unknown",
                   current_date: str | None = None, mode_sent: bool, date_sent: bool
                   ) -> tuple[str, str | None]:
    """The stored pair (mode, date) after a create or an edit; the CHECK of DATA_MODEL 2.6."""
    if mode_sent and mode is not None:
        new_mode = mode
    elif date_sent and date is not None:
        new_mode = "date"
    else:
        new_mode = current_mode
    if new_mode != "date":
        if date_sent and date is not None:
            raise problem("expiry_date", "A date needs \"Has date\". Choose it, or clear the date.")
        return new_mode, None
    new_date = date if date_sent else current_date
    if new_date is None:
        raise problem("expiry_date", "Enter the expiry date, or choose \"No expiry\" or "
                                     "\"Not sure\".")
    return new_mode, new_date


def _check_refs(conn: sqlite3.Connection, user_id: int, values: dict) -> None:
    if values.get("category_id") is not None and categories_repo.get(
            conn, user_id, values["category_id"]) is None:
        raise problem("category_id", "That category no longer exists. Choose another.")
    if values.get("location_id") is not None and values["location_id"] not in (
            catalog.location_paths(conn, user_id)):
        raise problem("location_id", "That location no longer exists. Choose another.")


def _new_public_id(conn: sqlite3.Connection) -> str:
    for _ in range(_ID_ATTEMPTS):
        candidate = ids.new_public_id()
        if not items_repo.public_id_used(conn, candidate):
            return candidate
    raise RuntimeError("could not find an unused public id")  # 32^8 ids: never in practice


def insert_item(conn: sqlite3.Connection, user_id: int, fields: dict, now: str) -> int:
    """Create an item inside the caller's transaction; `fields` as in POST /items."""
    mode, date = resolve_expiry(fields.get("expiry_mode"), fields.get("expiry_date"),
                                mode_sent="expiry_mode" in fields,
                                date_sent="expiry_date" in fields)
    values = {key: fields[key] for key in items_repo.EDITABLE
              if key in fields and fields[key] is not None}
    values.update(expiry_mode=mode, expiry_date=date)
    values["attributes"] = json.dumps(fields.get("attributes") or {}, ensure_ascii=False)
    for flag in ("no_label_needed",):
        if flag in values:
            values[flag] = int(values[flag])
    _check_refs(conn, user_id, values)
    item_id = items_repo.insert(conn, user_id, _new_public_id(conn), values, now)
    _event(conn, user_id, "item_created", item_id, {"name": values["name"]}, now)
    return item_id


def create_item(conn: sqlite3.Connection, user_id: int, fields: dict) -> dict:
    with write_transaction(conn):
        item_id = insert_item(conn, user_id, fields, clock.stamp())
    return detail_by_id(conn, user_id, item_id)


def change_item(conn: sqlite3.Connection, user_id: int, public_id: str, changes: dict) -> dict:
    """PATCH: `changes` holds only the keys the request sent (null clears a nullable field)."""
    now = clock.stamp()
    with write_transaction(conn):
        row = item_row(conn, user_id, public_id)
        mode, date = resolve_expiry(
            changes.get("expiry_mode"), changes.get("expiry_date"),
            current_mode=row["expiry_mode"], current_date=row["expiry_date"],
            mode_sent="expiry_mode" in changes, date_sent="expiry_date" in changes)
        values = {key: changes[key] for key in items_repo.EDITABLE if key in changes}
        values.update(expiry_mode=mode, expiry_date=date)
        if "attributes" in values:
            values["attributes"] = json.dumps(values["attributes"], ensure_ascii=False)
        if "no_label_needed" in values:
            values["no_label_needed"] = int(values["no_label_needed"])
        _check_refs(conn, user_id, values)
        before = {key: row[key] for key, value in values.items() if row[key] != value}
        if before:
            items_repo.update(conn, user_id, row["id"], values, now)
            _event(conn, user_id, "item_updated", row["id"],
                   {"before": {k: _plain(k, v) for k, v in before.items()}}, now)
    return get_item(conn, user_id, public_id)


def _plain(key: str, value: object) -> object:
    return json.loads(value) if key == "attributes" and isinstance(value, str) else value


def delete_item(conn: sqlite3.Connection, user_id: int, public_id: str) -> int:
    """Soft delete; the returned event id is what Undo sends back (D-092)."""
    now = clock.stamp()
    with write_transaction(conn):
        row = item_row(conn, user_id, public_id)
        if row["deleted_at"] is not None:
            raise AppError("conflict", 409, "That item is already in Trash.",
                           {"reason": "already_deleted"})
        items_repo.set_deleted(conn, user_id, row["id"], now, now)
        return _event(conn, user_id, "item_deleted", row["id"], {"before": {"deleted_at": None}},
                      now)


def restore_item(conn: sqlite3.Connection, user_id: int, public_id: str,
                 undo_of: int | None = None) -> dict:
    now = clock.stamp()
    with write_transaction(conn):
        row = item_row(conn, user_id, public_id)
        if row["deleted_at"] is not None:
            items_repo.set_deleted(conn, user_id, row["id"], None, now)
            payload = {"undo_of": undo_of} if undo_of is not None else {}
            _event(conn, user_id, "item_restored", row["id"], payload, now)
    return get_item(conn, user_id, public_id)


def undo(conn: sqlite3.Connection, user_id: int, event_id: int) -> None:
    """POST /events/{id}/undo (D-092): only `item_deleted`, within 60 seconds."""
    event = events_repo.get(conn, user_id, event_id)
    if event is None or event["kind"] not in UNDOABLE:
        raise AppError("not_found", 404, "There is nothing to undo.")
    at = datetime.strptime(event["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    if clock.now() - at > UNDO_WINDOW:
        raise AppError("undo_expired", 409, "It is too late to undo. Restore the item from Trash.")
    row = items_repo.get_by_id(conn, user_id, event["item_id"])
    if row is None:
        raise _not_found()
    if row["deleted_at"] is None or events_repo.undone(conn, user_id, event_id):
        return  # already back: a second Undo click changes nothing
    restore_item(conn, user_id, row["public_id"], undo_of=event_id)


def purge_item(conn: sqlite3.Connection, settings: Settings, user_id: int, public_id: str,
               has_recent_backup: Callable[[], bool]) -> None:
    """Permanent delete: only from Trash, only with a good backup under 24 hours old.

    The item's photo files go too, after the commit (D-096): the backup holds them, and a file
    no row names would otherwise be reported by the start-up sweep for ever.
    """
    now = clock.stamp()
    with write_transaction(conn):
        row = item_row(conn, user_id, public_id)
        if row["deleted_at"] is None:
            raise AppError("not_deleted", 409, "Move the item to Trash first.")
        if not has_recent_backup():
            raise AppError("backup_required", 409, "Make a backup first: permanent delete needs "
                           "a good backup from the last 24 hours.")
        _event(conn, user_id, "item_purged", row["id"],
               {"name": row["name"], "public_id": row["public_id"]}, now)
        files = items_repo.purge(conn, user_id, row["id"])
    for photo, thumb in files:
        (settings.photos_dir / photo).unlink(missing_ok=True)
        (settings.thumbs_dir / thumb).unlink(missing_ok=True)
    if files:
        log_event("info", "item_purged_photos", count=len(files))


def mark_labels_printed(conn: sqlite3.Connection, user_id: int, public_ids: list[str]) -> int:
    """Set "label printed" for each live item named; only after the owner confirms (D-045)."""
    now = clock.stamp()
    updated = 0
    with write_transaction(conn):
        for public_id in dict.fromkeys(public_ids):
            row = items_repo.get(conn, user_id, public_id) if ids.is_public_id(public_id) else None
            if row is None or row["deleted_at"] is not None:
                continue
            items_repo.mark_label_printed(conn, user_id, row["id"], now)
            _event(conn, user_id, "label_printed", row["id"], {}, now)
            updated += 1
    return updated
