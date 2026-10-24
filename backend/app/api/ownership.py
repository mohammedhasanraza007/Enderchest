"""The ownership check and savings (API 2.14, PAGES P-13 and P-14)."""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile

from ..boot.manager import BootManager
from ..idempotency import IdempotencyStore
from ..schemas.savings import (
    CheckResult,
    SavingCreate,
    SavingCreated,
    SavingRemoved,
    SavingsPage,
)
from ..services import ownership as ownership_service
from ..services import savings as savings_service
from .deps import current_user_id, get_db, require_ok
from .items import get_idempotency
from .photos import read_upload

router = APIRouter(prefix="/api/v1")


@router.post("/ownership/check")
def check(image: UploadFile | None = File(default=None), text: str | None = Form(default=None),
          manager: BootManager = Depends(require_ok),
          conn: sqlite3.Connection = Depends(get_db),
          user_id: int = Depends(current_user_id)) -> CheckResult:
    """Read-only: proposes candidates and writes nothing (spec gate 4)."""
    data = read_upload(image) if image is not None else None
    return CheckResult(**ownership_service.check(conn, manager.settings, user_id, data, text))


@router.post("/savings", status_code=201)
def add_saving(body: SavingCreate, conn: sqlite3.Connection = Depends(get_db),
               user_id: int = Depends(current_user_id),
               store: IdempotencyStore = Depends(get_idempotency),
               idempotency_key: str | None = Header(default=None)) -> SavingCreated:
    fields = body.model_dump()
    return store.run("POST /savings", idempotency_key,
                     lambda: SavingCreated(**savings_service.add(conn, user_id, fields)))


@router.get("/savings")
def list_savings(period: Literal["month", "all"] = "month",
                 limit: int = Query(default=50, ge=1, le=savings_service.PAGE_MAX),
                 cursor: str | None = None, conn: sqlite3.Connection = Depends(get_db),
                 user_id: int = Depends(current_user_id)) -> SavingsPage:
    return SavingsPage(**savings_service.listing(conn, user_id, period, limit, cursor))


@router.delete("/savings/{saving_id}")
def remove_saving(saving_id: int, conn: sqlite3.Connection = Depends(get_db),
                  user_id: int = Depends(current_user_id)) -> SavingRemoved:
    return SavingRemoved(**savings_service.remove(conn, user_id, saving_id))
