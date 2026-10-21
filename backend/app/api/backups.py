"""GET /backups and POST /backups (API.md 2.3)."""

import sqlite3

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..backup.engine import BackupError, create_backup
from ..boot.manager import BootManager
from ..errors import AppError
from ..services import backups as backup_service
from .deps import get_db, require_ok

router = APIRouter(prefix="/api/v1/backups")


@router.get("")
def list_backups(manager: BootManager = Depends(require_ok),
                 conn: sqlite3.Connection = Depends(get_db)) -> dict:
    mounted = manager.backups_mounted
    return {
        "status": backup_service.status(conn, mounted),
        "last_good": backup_service.last_good(conn),
        "warnings": manager.warnings(),
        "items": backup_service.listing(manager.settings, conn, mounted),
    }


@router.post("")
def make_backup(manager: BootManager = Depends(require_ok),
                conn: sqlite3.Connection = Depends(get_db)) -> JSONResponse:
    if not manager.backups_mounted:
        raise AppError("backup_unavailable", 503,
                       "The backup folder is not connected, so no backup was made.")
    try:
        result = create_backup(manager.settings, "manual", log_conn=conn)
    except BackupError as exc:
        raise AppError("internal_error", 500, f"The backup could not be made. {exc}") from exc
    return JSONResponse(
        {"name": result.name, "bytes": result.bytes, "verified": result.verified,
         "folder_hint": result.folder_hint},
        status_code=201,
    )
