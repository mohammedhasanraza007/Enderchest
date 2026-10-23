"""Items, their history and undo (API 2.5; undo from 2.10 is built early for delete, D-092)."""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from .. import clock
from ..boot.manager import BootManager
from ..idempotency import IdempotencyStore
from ..schemas.items import (
    DeletedItem,
    EventPage,
    ItemCreate,
    ItemDetail,
    ItemPage,
    ItemPatch,
    PermanentDelete,
    UndoDone,
)
from ..services import backups as backup_service
from ..services import items as items_service
from .deps import current_user_id, get_db, require_ok

router = APIRouter(prefix="/api/v1")


def get_idempotency(request: Request) -> IdempotencyStore:
    return request.app.state.idempotency


@router.get("/items")
def list_items(
    q: str | None = Query(default=None, max_length=200),
    category_id: int | None = None,
    location_id: int | None = None,
    state: Literal["active", "used", "expired", "discarded", "all"] = "active",
    expiry: Literal["soon", "today", "past", "none", "unknown", "any"] = "any",
    has_photo: bool | None = None,
    sort: Literal["created_desc", "name_asc", "expiry_asc"] = "created_desc",
    deleted: Literal["exclude", "only"] = "exclude",
    limit: int = Query(default=100, ge=1, le=200),
    cursor: str | None = Query(default=None, max_length=100),
    conn: sqlite3.Connection = Depends(get_db),
    user_id: int = Depends(current_user_id),
) -> ItemPage:
    page = items_service.list_items(
        conn, user_id, q=q, category_id=category_id, location_id=location_id, state=state,
        expiry=expiry, has_photo=has_photo, sort=sort, deleted=deleted, limit=limit,
        cursor=cursor)
    return ItemPage(**page)


@router.post("/items", status_code=201)
def create_item(body: ItemCreate, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id),
                store: IdempotencyStore = Depends(get_idempotency),
                idempotency_key: str | None = Header(default=None)) -> ItemDetail:
    fields = body.model_dump(exclude_unset=True)
    return store.run("POST /items", idempotency_key,
                     lambda: ItemDetail(**items_service.create_item(conn, user_id, fields)))


@router.get("/items/{public_id}")
def get_item(public_id: str, conn: sqlite3.Connection = Depends(get_db),
             user_id: int = Depends(current_user_id)) -> ItemDetail:
    return ItemDetail(**items_service.get_item(conn, user_id, public_id))


@router.patch("/items/{public_id}")
def change_item(public_id: str, body: ItemPatch, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> ItemDetail:
    changes = body.model_dump(exclude_unset=True)
    return ItemDetail(**items_service.change_item(conn, user_id, public_id, changes))


@router.delete("/items/{public_id}")
def delete_item(public_id: str, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> DeletedItem:
    return DeletedItem(event_id=items_service.delete_item(conn, user_id, public_id))


@router.post("/items/{public_id}/restore")
def restore_item(public_id: str, conn: sqlite3.Connection = Depends(get_db),
                 user_id: int = Depends(current_user_id)) -> ItemDetail:
    return ItemDetail(**items_service.restore_item(conn, user_id, public_id))


@router.delete("/items/{public_id}/permanent", status_code=204)
def purge_item(public_id: str, body: PermanentDelete,
               manager: BootManager = Depends(require_ok),
               conn: sqlite3.Connection = Depends(get_db),
               user_id: int = Depends(current_user_id)) -> Response:
    items_service.purge_item(
        conn, manager.settings, user_id, public_id,
        lambda: backup_service.has_recent_good(conn, manager.backups_mounted, clock.now()))
    return Response(status_code=204)


@router.get("/items/{public_id}/events")
def item_events(public_id: str, limit: int = Query(default=50, ge=1, le=200),
                cursor: str | None = Query(default=None, max_length=100),
                conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> EventPage:
    return EventPage(**items_service.item_events(conn, user_id, public_id, limit, cursor))


@router.post("/events/{event_id}/undo")
def undo(event_id: int, conn: sqlite3.Connection = Depends(get_db),
         user_id: int = Depends(current_user_id)) -> UndoDone:
    items_service.undo(conn, user_id, event_id)
    return UndoDone(ok=True)
