"""Response shapes for GET /backups, POST /backups and GET /health (API.md 2.1, 2.3).

They exist so the generated frontend types describe these endpoints exactly.
"""

from typing import Literal

from pydantic import BaseModel

BackupKind = Literal["auto", "manual", "pre-migration", "safety"]
BackupStatus = Literal["ok", "stale", "failing", "unavailable"]
BootStatus = Literal["starting", "ok", "recovery", "locked", "failed"]


class BackupItem(BaseModel):
    name: str
    kind: BackupKind
    at: str
    bytes: int
    item_count: int | None
    ok: bool


class LastGoodBackup(BaseModel):
    name: str
    at: str
    bytes: int


class BackupsView(BaseModel):
    status: BackupStatus
    last_good: LastGoodBackup | None
    warnings: list[str]
    items: list[BackupItem]
    folder_hint: str  # the host folder, for the Settings page (the container sees /backups)


class BackupMade(BaseModel):
    name: str
    bytes: int
    verified: bool
    folder_hint: str


class Health(BaseModel):
    status: BootStatus
    reason: str | None
    app_version: str
    schema_found: int | None
    schema_supported: int
    env: Literal["live", "test"]
    build_date: str | None  # ENDERCHEST_BUILD_DATE, set by build.bat; None when not recorded
