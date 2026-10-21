"""Shared route dependencies."""

import sqlite3

from fastapi import Request

from ..boot.manager import BootManager, Status
from ..errors import AppError


def get_manager(request: Request) -> BootManager:
    return request.app.state.manager


def require_ok(request: Request) -> BootManager:
    """The API answers `locked` (503) whenever the boot state is not `ok` (API.md 1)."""
    manager = get_manager(request)
    if manager.state.status is not Status.OK:
        raise AppError("locked", 503, "Enderchest is not ready. Open the home page for details.",
                       {"state": manager.state.status.value, "reason": manager.state.reason})
    return manager


def get_db(request: Request) -> sqlite3.Connection:
    return require_ok(request).db()
