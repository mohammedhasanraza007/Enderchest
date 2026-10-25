"""The camera coach's server tier (API 2.15, Phase 7)."""

import sqlite3

from fastapi import APIRouter, Depends, File, UploadFile

from ..boot.manager import BootManager
from ..schemas.coach import FrameResult
from ..services import coach as coach_service
from ..services import profile
from .deps import current_user_id, get_db, require_ok

router = APIRouter(prefix="/api/v1")


@router.post("/capture/frame", response_model_exclude_none=True)
def read_frame(image: UploadFile = File(...), manager: BootManager = Depends(require_ok),
               conn: sqlite3.Connection = Depends(get_db),
               user_id: int = Depends(current_user_id)) -> FrameResult:
    """Read-only: the frame is read in memory and kept nowhere (D-121)."""
    data = image.file.read(coach_service.FRAME_MAX_BYTES + 1)
    today = profile.local_today(conn, user_id)
    return FrameResult(**coach_service.frame(manager.settings.ocr_threads, data, today))
