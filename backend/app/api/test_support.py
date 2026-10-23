"""Test-only endpoints (API.md 2.17).

They exist only when ENDERCHEST_ENV=test, and every call also checks that the database
itself says meta.env_marker='test'; otherwise they answer 404.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .. import clock
from ..boot.manager import BootManager
from ..errors import AppError
from ..services import test_support
from .deps import require_ok


def require_test_marker(manager: BootManager = Depends(require_ok)) -> BootManager:
    marker = manager.db().execute("SELECT value FROM meta WHERE key = 'env_marker'").fetchone()
    if manager.settings.env != "test" or marker is None or marker["value"] != "test":
        raise AppError("not_found", 404, "That does not exist.")
    return manager


router = APIRouter(prefix="/api/v1/test", dependencies=[Depends(require_test_marker)])


def _loop(request: Request) -> test_support.WriteLoop:
    return request.app.state.write_loop


@router.post("/reset")
def reset(request: Request, manager: BootManager = Depends(require_test_marker)) -> dict:
    test_support.reset_test_data(manager.settings, manager, _loop(request))
    return {"state": manager.state.status.value}


@router.post("/delete-db")
def delete_db(request: Request, manager: BootManager = Depends(require_test_marker)) -> dict:
    """Probe 8: delete only the test database file, then re-run the boot checks."""
    with manager.exclusive():
        _loop(request).stop()
        manager.release_connections()
        test_support.delete_database_files(manager.settings)
        manager.run_checks()
    return {"state": manager.state.status.value, "reason": manager.state.reason}


class WriteLoopBody(BaseModel):
    seconds: int = Field(ge=1, le=600)


@router.post("/write-loop")
def start_write_loop(body: WriteLoopBody, request: Request,
                     manager: BootManager = Depends(require_test_marker)) -> dict:
    _loop(request).start(manager.settings, body.seconds)
    return {"running": True, "seconds": body.seconds}


@router.get("/write-loop")
def write_loop_status(request: Request,
                      manager: BootManager = Depends(require_test_marker)) -> dict:
    return test_support.write_loop_report(manager.db(), _loop(request).running)


def _clock_view(manager: BootManager) -> dict:
    tz = manager.db().execute("SELECT timezone FROM users WHERE id = 1").fetchone()["timezone"]
    return {"now": clock.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "local_date": clock.local_date(tz).isoformat()}


class ClockBody(BaseModel):
    now: datetime | None = None
    advance_seconds: float | None = None
    local_date: date | None = None


@router.get("/clock")
def get_clock(manager: BootManager = Depends(require_test_marker)) -> dict:
    return _clock_view(manager)


@router.post("/clock")
def set_clock(body: ClockBody, manager: BootManager = Depends(require_test_marker)) -> dict:
    tz = manager.db().execute("SELECT timezone FROM users WHERE id = 1").fetchone()["timezone"]
    if body.now is not None:
        clock.set_now(body.now)
    if body.local_date is not None:
        clock.set_local_date(body.local_date, tz)
    if body.advance_seconds is not None:
        clock.advance(body.advance_seconds)
    return _clock_view(manager)


@router.post("/fixtures/{name}")
def load_fixture(name: str, manager: BootManager = Depends(require_test_marker)) -> dict:
    try:
        return test_support.load_fixture(manager.db(), name)
    except KeyError:
        raise AppError("not_found", 404, "There is no fixture with that name.") from None
