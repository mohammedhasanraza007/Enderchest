"""Application factory. Run with: uvicorn app.main:create_app --factory (one worker)."""

import asyncio
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from .api import (
    backups,
    boot,
    catalog,
    coach,
    dashboard,
    drafts,
    gemini,
    items,
    labels,
    lifecycle,
    notifications,
    ownership,
    pages,
    photos,
    profile,
    security,
    test_support,
)
from .boot.manager import BootManager
from .boot.mounts import is_mount_point
from .config import Settings, load_settings
from .errors import install_error_handlers
from .idempotency import IdempotencyStore
from .scheduler.backups import BackupScheduler
from .scheduler.embeddings import Embedder
from .scheduler.reconcile import Reconciler
from .services.test_support import WriteLoop


def create_app(settings: Settings | None = None,
               is_mount: Callable[[Path], bool] = is_mount_point,
               start_scheduler: bool = True) -> FastAPI:
    settings = settings or load_settings()
    manager = BootManager(settings, is_mount)
    write_loop = WriteLoop()
    scheduler = BackupScheduler(manager)
    reconciler = Reconciler(manager)
    embedder = Embedder(manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # The checks run in a thread so /health answers "starting" while they work.
        threading.Thread(target=manager.run_checks, name="boot-checks", daemon=True).start()
        tasks = ([asyncio.create_task(scheduler.run()), asyncio.create_task(reconciler.run()),
                  asyncio.create_task(embedder.run())]
                 if start_scheduler else [])
        yield
        if tasks:
            await scheduler.stop()
            await reconciler.stop()
            await embedder.stop()
            await asyncio.gather(*tasks)  # a backup already running finishes first
        write_loop.stop()
        manager.shutdown()

    app = FastAPI(title="Enderchest", docs_url=None, redoc_url=None, openapi_url=None,
                  lifespan=lifespan)
    app.state.manager = manager
    app.state.reconciler = reconciler
    app.state.embedder = embedder
    app.state.write_loop = write_loop
    app.state.idempotency = IdempotencyStore()
    install_error_handlers(app)
    app.add_middleware(security.SecurityMiddleware, app_port=settings.port)

    app.include_router(boot.health_router)
    app.include_router(boot.router)
    app.include_router(backups.router)
    app.include_router(profile.router)
    app.include_router(catalog.router)
    app.include_router(labels.router)
    app.include_router(items.router)
    app.include_router(photos.router)
    app.include_router(drafts.router)
    app.include_router(gemini.router)
    app.include_router(lifecycle.router)
    app.include_router(notifications.router)
    app.include_router(dashboard.router)
    app.include_router(ownership.router)
    app.include_router(coach.router)
    if settings.env == "test":
        app.include_router(test_support.router)
    app.include_router(pages.router)  # last: its catch-all must never shadow an API route
    return app
