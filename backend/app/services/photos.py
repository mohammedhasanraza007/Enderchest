"""Item photos: add, hide, choose the primary, serve the files (API 2.6, DATA_MODEL 2.7).

A photo's files are written first and its row second (DATA_SAFETY 4); if the row cannot be
written, the files are removed again, because nothing ever pointed at them.
"""

import sqlite3
from pathlib import Path

from .. import clock, images
from ..config import Settings
from ..db.connection import write_transaction
from ..errors import AppError
from ..repositories import events as events_repo
from ..repositories import items as items_repo
from ..repositories import photos as photos_repo
from . import items as items_service
from . import profile as profile_service

MAX_PER_ITEM = 12


def prepare(data: bytes) -> images.Processed:
    """Check and re-encode one upload, or raise the API error that explains the refusal."""
    try:
        return images.process_in_executor(data)
    except images.ImageRefused as refused:
        raise AppError(refused.code, refused.status, refused.message) from None


def limit_reached(what: str) -> AppError:
    return AppError("limit_reached", 409, f"{what} can have up to {MAX_PER_ITEM} photos. "
                    "Hide one to add another.", {"limit": MAX_PER_ITEM})


def store_row(conn: sqlite3.Connection, user_id: int, stored: images.Stored,
              processed: images.Processed, *, item_id: int | None = None,
              draft_id: str | None = None, now: str) -> None:
    photos_repo.insert(conn, user_id, {
        "id": stored.id, "item_id": item_id, "draft_id": draft_id, "path": stored.path,
        "thumb_path": stored.thumb_path, "width": processed.width, "height": processed.height,
        "bytes": len(processed.jpeg), "sha256": processed.sha256, "mime": "image/jpeg",
        "created_at": now})


def add_item_photo(conn: sqlite3.Connection, settings: Settings, user_id: int, public_id: str,
                   data: bytes) -> dict:
    row = items_service.item_row(conn, user_id, public_id)
    if row["deleted_at"] is not None:
        raise AppError("conflict", 409, "Restore the item from Trash before adding photos.",
                       {"reason": "deleted"})
    if len(photos_repo.live_for_item(conn, user_id, row["id"])) >= MAX_PER_ITEM:
        raise limit_reached("An item")
    processed = prepare(data)
    stored = images.store(settings, processed)
    now = clock.stamp()
    try:
        with write_transaction(conn):
            current = items_repo.get_by_id(conn, user_id, row["id"])
            if len(photos_repo.live_for_item(conn, user_id, row["id"])) >= MAX_PER_ITEM:
                raise limit_reached("An item")
            store_row(conn, user_id, stored, processed, item_id=row["id"], now=now)
            is_primary = current["primary_photo_id"] is None
            if is_primary:
                items_repo.set_primary_photo(conn, user_id, row["id"], stored.id, now)
            events_repo.add(conn, user_id, kind="photo_added", item_id=row["id"],
                            payload={"photo_id": stored.id}, at=now,
                            local_date=profile_service.local_today(conn, user_id).isoformat())
    except BaseException:
        images.discard(settings, stored)
        raise
    return {"id": stored.id, "is_primary": is_primary, "width": processed.width,
            "height": processed.height}


def hide_photo(conn: sqlite3.Connection, user_id: int, photo_id: str) -> None:
    """Sets `deleted_at` only: the file stays on disk and in backups."""
    now = clock.stamp()
    with write_transaction(conn):
        photo = photos_repo.get(conn, user_id, photo_id)
        if photo is None or photo["deleted_at"] is not None:
            raise AppError("not_found", 404, "That photo does not exist.")
        photos_repo.hide(conn, user_id, photo_id, now)
        if photo["item_id"] is None:
            return
        item = items_repo.get_by_id(conn, user_id, photo["item_id"])
        if item is not None and item["primary_photo_id"] == photo_id:
            remaining = photos_repo.live_for_item(conn, user_id, photo["item_id"])
            items_repo.set_primary_photo(conn, user_id, photo["item_id"],
                                         remaining[0]["id"] if remaining else None, now)
        events_repo.add(conn, user_id, kind="photo_removed", item_id=photo["item_id"],
                        payload={"photo_id": photo_id}, at=now,
                        local_date=profile_service.local_today(conn, user_id).isoformat())


def set_primary(conn: sqlite3.Connection, user_id: int, public_id: str, photo_id: str) -> dict:
    with write_transaction(conn):
        row = items_service.item_row(conn, user_id, public_id)
        photo = photos_repo.get(conn, user_id, photo_id)
        if photo is None or photo["deleted_at"] is not None or photo["item_id"] != row["id"]:
            raise AppError("not_found", 404, "That photo is not one of this item's photos.")
        items_repo.set_primary_photo(conn, user_id, row["id"], photo_id, clock.stamp())
    return items_service.get_item(conn, user_id, public_id)


def file_for(conn: sqlite3.Connection, settings: Settings, user_id: int, photo_id: str,
             *, thumb: bool) -> Path:
    """The file to serve. A missing thumbnail (thumbnails are not backed up) is made again."""
    photo = photos_repo.get(conn, user_id, photo_id)
    if photo is None:
        raise AppError("not_found", 404, "That photo does not exist.")
    original = _inside(settings.photos_dir, photo["path"])
    if not thumb:
        return original
    path = _inside(settings.thumbs_dir, photo["thumb_path"], must_exist=False)
    if not path.is_file():
        images.remake_thumb(settings, original, path)
    return path


def _inside(folder: Path, relative: str, *, must_exist: bool = True) -> Path:
    path = (folder / relative).resolve()
    if path.parent != folder.resolve() or (must_exist and not path.is_file()):
        raise AppError("not_found", 404, "That photo file is missing.")
    return path
