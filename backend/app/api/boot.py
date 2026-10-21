"""GET /health, GET /boot, POST /boot/restore, POST /boot/start-empty (API.md 2.1)."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..backup.restore import RestoreError
from ..boot.manager import BootManager, Status, WrongState
from ..db import migrate
from ..errors import AppError
from ..schemas.backups import Health
from ..services import backups as backup_service
from .deps import get_manager

health_router = APIRouter()
router = APIRouter(prefix="/api/v1/boot")


@health_router.get("/health")
def health(manager: BootManager = Depends(get_manager)) -> Health:
    """Answers 200 whenever the process runs, so Docker never restarts a locked app."""
    state = manager.state
    return Health(
        status=state.status.value,
        reason=state.reason,
        app_version=manager.settings.app_version,
        schema_found=state.schema_found,
        schema_supported=migrate.supported_version(),
        env=manager.settings.env,
        build_date=manager.settings.build_date,
    )


@router.get("")
def boot(manager: BootManager = Depends(get_manager)) -> dict:
    state = manager.state
    conn = manager.db() if state.status is Status.OK else None
    return {
        "state": state.status.value,
        "reason": state.reason,
        "message": state.detail,
        "data_mounted": manager.data_mounted,
        "backups_mounted": manager.backups_mounted,
        "schema_found": state.schema_found,
        "schema_supported": migrate.supported_version(),
        "backups": backup_service.listing(manager.settings, conn, manager.backups_mounted),
        "warnings": manager.warnings(),
    }


class RestoreBody(BaseModel):
    name: str
    confirm: Literal["RESTORE"]


class StartEmptyBody(BaseModel):
    confirm: Literal["START EMPTY"]


@router.post("/restore")
def restore(body: RestoreBody, manager: BootManager = Depends(get_manager)) -> dict:
    try:
        result = manager.restore(body.name)
    except WrongState as exc:
        raise AppError("conflict", 409, "Restore is only possible on the recovery page.",
                       {"reason": str(exc)}) from exc
    except RestoreError as exc:
        raise AppError("conflict", 409, str(exc), {"reason": "restore_refused"}) from exc
    return {"restored": result.restored, "items": result.items,
            "photos_missing": result.photos_missing}


@router.post("/start-empty")
def start_empty(_: StartEmptyBody, manager: BootManager = Depends(get_manager)) -> dict:
    try:
        manager.start_empty()
    except WrongState as exc:
        raise AppError("conflict", 409, "Starting empty is only possible on the recovery page.",
                       {"reason": str(exc)}) from exc
    except RestoreError as exc:
        raise AppError("conflict", 409, str(exc), {"reason": "start_empty_refused"}) from exc
    return {"state": manager.state.status.value}
