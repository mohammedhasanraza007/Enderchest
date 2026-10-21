"""The home page: the boot page unless the state is `ok`, then the foundation status page."""

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..boot.manager import BootManager, Status
from .deps import get_manager

router = APIRouter()
STATIC = Path(__file__).parent.parent / "static" / "boot"


@router.get("/", include_in_schema=False)
def home(manager: BootManager = Depends(get_manager)) -> FileResponse:
    page = "status.html" if manager.state.status is Status.OK else "boot.html"
    # no-store: the same URL shows different pages as the state changes
    return FileResponse(STATIC / page, headers={"Cache-Control": "no-store"})
