"""Drafts, the add flow (API 2.8). `POST /drafts` takes 1 to 20 images, one draft each."""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, File, Header, Response, UploadFile

from ..boot.manager import BootManager
from ..idempotency import IdempotencyStore
from ..schemas.drafts import (
    Draft,
    DraftBatch,
    DraftList,
    DraftPatch,
    ExtractQueued,
    ExtractRequest,
)
from ..schemas.items import ItemDetail
from ..services import drafts as drafts_service
from ..services import gemini as gemini_service
from ..services import reading as reading_service
from .deps import current_user_id, get_db, require_ok
from .items import get_idempotency
from .photos import read_upload

router = APIRouter(prefix="/api/v1")
# A draft shows only the fields filled in so far, not every field as null.
SET_ONLY = {"response_model_exclude_unset": True}


@router.post("/drafts", status_code=201, **SET_ONLY)
def create_drafts(images: list[UploadFile] = File(..., alias="images[]"),
                  manager: BootManager = Depends(require_ok),
                  conn: sqlite3.Connection = Depends(get_db),
                  user_id: int = Depends(current_user_id)) -> DraftBatch:
    uploads = [read_upload(image) for image in images[:drafts_service.MAX_BATCH + 1]]
    drafts = drafts_service.create_drafts(conn, manager.settings, user_id, uploads)
    for draft in drafts:  # each new draft is read at once (D-100)
        reading_service.queue_local(conn, manager, user_id, draft["id"])
    return DraftBatch(drafts=[Draft(**drafts_service.get_draft(conn, user_id, draft["id"]))
                              for draft in drafts])


@router.get("/drafts", **SET_ONLY)
def list_drafts(status: Literal["open", "committed", "discarded"] = "open",
                conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> DraftList:
    return DraftList(items=[Draft(**d) for d in drafts_service.list_drafts(conn, user_id, status)])


@router.get("/drafts/{draft_id}", **SET_ONLY)
def get_draft(draft_id: str, conn: sqlite3.Connection = Depends(get_db),
              user_id: int = Depends(current_user_id)) -> Draft:
    return Draft(**drafts_service.get_draft(conn, user_id, draft_id))


@router.patch("/drafts/{draft_id}", **SET_ONLY)
def change_draft(draft_id: str, body: DraftPatch, conn: sqlite3.Connection = Depends(get_db),
                 user_id: int = Depends(current_user_id)) -> Draft:
    fields = body.fields.model_dump(exclude_unset=True)
    return Draft(**drafts_service.change_draft(conn, user_id, draft_id, fields))


@router.post("/drafts/{draft_id}/photos", **SET_ONLY)
def add_draft_photo(draft_id: str, image: UploadFile = File(...),
                    manager: BootManager = Depends(require_ok),
                    conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> Draft:
    return Draft(**drafts_service.add_draft_photo(conn, manager.settings, user_id, draft_id,
                                                  read_upload(image)))


@router.post("/drafts/{draft_id}/commit", status_code=201)
def commit_draft(draft_id: str, conn: sqlite3.Connection = Depends(get_db),
                 user_id: int = Depends(current_user_id),
                 store: IdempotencyStore = Depends(get_idempotency),
                 idempotency_key: str | None = Header(default=None)) -> ItemDetail:
    return store.run(f"POST /drafts/{draft_id}/commit", idempotency_key,
                     lambda: ItemDetail(**drafts_service.commit(conn, user_id, draft_id)))


@router.delete("/drafts/{draft_id}", status_code=204)
def discard_draft(draft_id: str, conn: sqlite3.Connection = Depends(get_db),
                  user_id: int = Depends(current_user_id)) -> Response:
    drafts_service.discard(conn, user_id, draft_id)
    return Response(status_code=204)


@router.post("/drafts/{draft_id}/extract", status_code=202, response_model_exclude_none=True)
def extract(draft_id: str, body: ExtractRequest, manager: BootManager = Depends(require_ok),
            conn: sqlite3.Connection = Depends(get_db),
            user_id: int = Depends(current_user_id)) -> ExtractQueued:
    """Re-read (`local`) or Improve with Gemini (`gemini`); the client polls the draft."""
    drafts_service.require_open(conn, user_id, draft_id)
    if body.engine == "local":
        reading_service.queue_local(conn, manager, user_id, draft_id)
        return ExtractQueued(ocr_status="pending")
    gemini_service.queue(conn, manager, user_id, draft_id)
    return ExtractQueued(gemini_status="pending")
