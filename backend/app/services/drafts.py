"""Drafts, the add flow (API 2.8, DATA_MODEL 2.8, D-049).

One draft per photo. A draft is not an item and counts nowhere until it is committed; closing
the browser loses nothing because the draft and its photos are on the server.
"""

import json
import sqlite3
import uuid

from pydantic import ValidationError

from .. import clock, images
from ..config import Settings
from ..db.connection import write_transaction
from ..errors import AppError, problems_from
from ..repositories import drafts as drafts_repo
from ..repositories import events as events_repo
from ..repositories import items as items_repo
from ..repositories import photos as photos_repo
from ..schemas.items import ItemCreate
from . import items as items_service
from . import photos as photos_service
from . import profile as profile_service
from . import reading

MAX_BATCH = 20


def _view(conn: sqlite3.Connection, user_id: int, row: sqlite3.Row) -> dict:
    photos = photos_repo.live_for_draft(conn, user_id, row["id"])
    return {"id": row["id"], "status": row["status"], "fields": json.loads(row["fields"]),
            "photos": [{"id": p["id"], "width": p["width"], "height": p["height"]}
                       for p in photos],
            **reading.view(row), "created_at": row["created_at"]}


def _row(conn: sqlite3.Connection, user_id: int, draft_id: str) -> sqlite3.Row:
    row = drafts_repo.get(conn, user_id, draft_id)
    if row is None:
        raise AppError("not_found", 404, "That draft does not exist.")
    return row


def _open(row: sqlite3.Row) -> None:
    if row["status"] != "open":
        raise AppError("conflict", 409, f"That draft is already {row['status']}.",
                       {"reason": row["status"]})


def require_open(conn: sqlite3.Connection, user_id: int, draft_id: str) -> None:
    _open(_row(conn, user_id, draft_id))


def get_draft(conn: sqlite3.Connection, user_id: int, draft_id: str) -> dict:
    return _view(conn, user_id, _row(conn, user_id, draft_id))


def list_drafts(conn: sqlite3.Connection, user_id: int, status: str) -> list[dict]:
    return [_view(conn, user_id, row) for row in drafts_repo.list_by_status(conn, user_id, status)]


def create_drafts(conn: sqlite3.Connection, settings: Settings, user_id: int,
                  uploads: list[bytes]) -> list[dict]:
    """Every image is checked before anything is written, so a bad file adds nothing at all."""
    if not 1 <= len(uploads) <= MAX_BATCH:
        raise AppError("validation_error", 422, "Some values are not valid.",
                       {"problems": [{"field": "images", "problem":
                                      f"Add 1 to {MAX_BATCH} photos at a time."}]})
    processed = []
    for number, data in enumerate(uploads, start=1):
        try:
            processed.append(photos_service.prepare(data))
        except AppError as refused:
            if len(uploads) > 1:
                refused.message = f"Photo {number}: {refused.message}"
            raise
    stored: list[images.Stored] = []
    now = clock.stamp()
    try:
        for item in processed:
            stored.append(images.store(settings, item))
        draft_ids = []
        with write_transaction(conn):
            for item, files in zip(processed, stored, strict=True):
                draft_id = str(uuid.uuid4())
                drafts_repo.insert(conn, user_id, draft_id, now)
                photos_service.store_row(conn, user_id, files, item, draft_id=draft_id, now=now)
                draft_ids.append(draft_id)
    except BaseException:
        for files in stored:
            images.discard(settings, files)
        raise
    return [get_draft(conn, user_id, draft_id) for draft_id in draft_ids]


def change_draft(conn: sqlite3.Connection, user_id: int, draft_id: str, fields: dict) -> dict:
    """Merge the sent fields into the draft (saved as the owner edits, P-07)."""
    with write_transaction(conn):
        row = _row(conn, user_id, draft_id)
        _open(row)
        merged = {**json.loads(row["fields"]), **fields}
        drafts_repo.set_fields(conn, user_id, draft_id, json.dumps(merged, ensure_ascii=False),
                               clock.stamp())
    return get_draft(conn, user_id, draft_id)


def add_draft_photo(conn: sqlite3.Connection, settings: Settings, user_id: int, draft_id: str,
                    data: bytes) -> dict:
    row = _row(conn, user_id, draft_id)
    _open(row)
    if len(photos_repo.live_for_draft(conn, user_id, draft_id)) >= photos_service.MAX_PER_ITEM:
        raise photos_service.limit_reached("A draft")
    processed = photos_service.prepare(data)
    stored = images.store(settings, processed)
    try:
        with write_transaction(conn):
            if len(photos_repo.live_for_draft(conn, user_id, draft_id)) >= (
                    photos_service.MAX_PER_ITEM):
                raise photos_service.limit_reached("A draft")
            photos_service.store_row(conn, user_id, stored, processed, draft_id=draft_id,
                                     now=clock.stamp())
    except BaseException:
        images.discard(settings, stored)
        raise
    return get_draft(conn, user_id, draft_id)


def commit(conn: sqlite3.Connection, user_id: int, draft_id: str) -> dict:
    """Turn a draft into an item: the item rules apply now, and its photos move with it."""
    row = _row(conn, user_id, draft_id)
    _open(row)
    fields = {k: v for k, v in json.loads(row["fields"]).items() if v is not None}
    confirmed = fields.pop("expiry_confirmed", True)
    fields.pop("owned", None)
    if not fields.get("name"):
        raise items_service.problem("name", "Enter a name to save the item.")
    if fields.get("expiry_mode", "date" if "expiry_date" in fields else None) == "date" \
            and confirmed is False:
        raise AppError("expiry_unconfirmed", 422, "Confirm the expiry date.",
                       {"problems": [{"field": "expiry_date", "problem": "Confirm the date."}]})
    try:
        checked = ItemCreate.model_validate(fields).model_dump(exclude_unset=True)
    except ValidationError as invalid:
        raise AppError("validation_error", 422, "Some values are not valid.",
                       {"problems": problems_from(invalid.errors())}) from None
    now = clock.stamp()
    with write_transaction(conn):
        _open(_row(conn, user_id, draft_id))  # a second commit racing this one stops here
        item_id = items_service.insert_item(conn, user_id, checked, now)
        photos = photos_repo.live_for_draft(conn, user_id, draft_id)
        photos_repo.move_to_item(conn, user_id, draft_id, item_id)
        if photos:
            items_repo.set_primary_photo(conn, user_id, item_id, photos[0]["id"], now)
        drafts_repo.set_status(conn, user_id, draft_id, "committed", now, item_id)
        events_repo.add(conn, user_id, kind="draft_committed", item_id=item_id,
                        payload={"draft_id": draft_id}, at=now,
                        local_date=profile_service.local_today(conn, user_id).isoformat())
    return items_service.detail_by_id(conn, user_id, item_id)


def discard(conn: sqlite3.Connection, user_id: int, draft_id: str) -> None:
    """Status `discarded`; the photos are left as they are (API 2.8)."""
    with write_transaction(conn):
        row = _row(conn, user_id, draft_id)
        _open(row)
        drafts_repo.set_status(conn, user_id, draft_id, "discarded", clock.stamp())
