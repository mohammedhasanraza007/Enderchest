"""GET /backups and POST /backups (API.md 2.3)."""

import sqlite3

from fastapi import APIRouter, Depends

from ..backup.engine import BackupError, create_backup
from ..boot.manager import BootManager
from ..errors import AppError
from ..schemas.backups import BackupMade, BackupsView
from ..services import backups as backup_service
from .deps import get_db, require_ok

router = APIRouter(prefix="/api/v1/backups")


@router.get("")
def list_backups(manager: BootManager = Depends(require_ok),
                 conn: sqlite3.Connection = Depends(get_db)) -> BackupsView:
    mounted = manager.backups_mounted
    return BackupsView(
        status=backup_service.status(conn, manager.settings, mounted),
        last_good=backup_service.last_good(conn, manager.settings, mounted),
        warnings=manager.warnings(),
        items=backup_service.listing(manager.settings, conn, mounted),
        folder_hint=manager.settings.backup_dir_hint,
    )


@router.post("", status_code=201)
def make_backup(manager: BootManager = Depends(require_ok),
                conn: sqlite3.Connection = Depends(get_db)) -> BackupMade:
    if not manager.backups_mounted:
        raise AppError("backup_unavailable", 503,
                       "The backup folder is not connected, so no backup was made.")
    try:
        result = create_backup(manager.settings, "manual", log_conn=conn)
    except BackupError as exc:
        raise AppError("internal_error", 500, f"The backup could not be made. {exc}") from exc
    return BackupMade(name=result.name, bytes=result.bytes, verified=result.verified,
                      folder_hint=result.folder_hint)
