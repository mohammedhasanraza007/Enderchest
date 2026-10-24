"""Gemini settings (API 2.9): key status, set or remove the key, a real test call.

Mode, model and "send photos" are ordinary settings (`PATCH /settings`). The key is write-only:
no response ever contains it.
"""

import sqlite3

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from ..boot.manager import BootManager
from ..schemas.profile import GeminiMode
from ..services import gemini as gemini_service
from .deps import current_user_id, get_db, require_ok

router = APIRouter(prefix="/api/v1")


class GeminiStatus(BaseModel):
    key_set: bool
    model: str
    mode: GeminiMode
    share_images: bool


class KeyBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    key: str


class KeySet(BaseModel):
    key_set: bool


class TestResult(BaseModel):
    ok: bool
    model: str
    latency_ms: int


@router.get("/gemini")
def get_gemini(manager: BootManager = Depends(require_ok),
               conn: sqlite3.Connection = Depends(get_db),
               user_id: int = Depends(current_user_id)) -> GeminiStatus:
    return GeminiStatus(**gemini_service.status(conn, user_id, manager.settings))


@router.put("/gemini/key")
def put_key(body: KeyBody, manager: BootManager = Depends(require_ok)) -> KeySet:
    gemini_service.save_key(manager.settings, body.key)
    return KeySet(key_set=True)


@router.delete("/gemini/key", status_code=204)
def delete_key(manager: BootManager = Depends(require_ok)) -> Response:
    gemini_service.remove_key(manager.settings)
    return Response(status_code=204)


@router.post("/gemini/test")
def test_gemini(manager: BootManager = Depends(require_ok),
                conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> TestResult:
    return TestResult(**gemini_service.test_connection(conn, user_id, manager.settings))
