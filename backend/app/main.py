"""Application factory. Run with: uvicorn app.main:create_app --factory (one worker)."""

import asyncio
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from .api import backups, boot, pages, profile, security, test_support
from .boot.manager import BootManager
from .boot.mounts import is_mount_point
from .config import Settings, load_settings
from .errors import install_error_handlers
from .scheduler.backups import BackupScheduler
from .services.test_support import WriteLoop


def create_app(settings: Settings | None = None,
               is_mount: Callable[[Path], bool] = is_mount_point,
               start_scheduler: bool = True) -> FastAPI:
    settings = settings or load_settings()
    manager = BootManager(settings, is_mount)
    write_loop = WriteLoop()
    scheduler = BackupScheduler(manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # The checks run in a thread so /health answers "starting" while they work.
        threading.Thread(target=manager.run_checks, name="boot-checks", daemon=True).start()
        task = asyncio.create_task(scheduler.run()) if start_scheduler else None
        yield
        if task is not None:
            await scheduler.stop()
            await task  # a backup already running finishes first
        write_loop.stop()
        manager.shutdown()

    app = FastAPI(title="Enderchest", docs_url=None, redoc_url=None, openapi_url=None,
                  lifespan=lifespan)
    app.state.manager = manager
    app.state.write_loop = write_loop
    install_error_handlers(app)
    app.add_middleware(security.SecurityMiddleware, app_port=settings.port)

    app.include_router(boot.health_router)
    app.include_router(boot.router)
    app.include_router(backups.router)
    app.include_router(profile.router)
    if settings.env == "test":
        app.include_router(test_support.router)
    app.include_router(pages.router)  # last: its catch-all must never shadow an API route
    return app
