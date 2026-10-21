"""Restore one backup over the live database (DATA_SAFETY 12).

One implementation for two entry points: `python -m app.backup.cli restore` and
`POST /api/v1/boot/restore`. The caller holds the single-instance lock and has no open
connection to the database. Nothing is ever deleted: the old files are moved aside.
"""

import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..config import Settings
from ..db.connection import connect
from ..db.migrate import supported_version
from ..fsutil import copy_atomic, fsync_dir, fsync_path, move_aside, utc_stamp
from ..logs import log_event
from . import catalog
from .engine import BackupError, create_backup, mirror_photos, record_log, verify_database

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class RestoreError(Exception):
    """The restore was refused or failed before the live database was touched."""


@dataclass
class RestoreResult:
    restored: str
    items: int | None
    photos_missing: int
    safety_backup: str | None
    notes: list[str] = field(default_factory=list)


def _sidecars(db: Path) -> list[Path]:
    return [db.with_name(db.name + "-wal"), db.with_name(db.name + "-shm")]


def restore_backup(settings: Settings, name: str) -> RestoreResult:
    if not _SAFE_NAME.match(name) or catalog.kind_of(name) is None:
        raise RestoreError("that is not a backup name")
    source = settings.backups_dir / f"{name}.sqlite3"
    if not source.is_file():
        raise RestoreError(f"backup {name} was not found in the backup folder")

    # 1. Verify on the volume (never open SQLite on /backups).
    # The CLI can run on a brand-new volume where the boot sequence never created these.
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = settings.staging_dir / "restore-candidate.sqlite3"
    copy_atomic(source, candidate)
    try:
        check = verify_database(candidate)
        if not check.ok:
            raise RestoreError(f"backup {name} did not verify: {check.error}")
        if check.schema_version is None or check.schema_version > supported_version():
            raise RestoreError(f"backup {name} is from a newer version of Enderchest")
        if check.env_marker != settings.env:
            raise RestoreError(f"backup {name} belongs to the '{check.env_marker}' "
                               f"environment, not '{settings.env}'")

        # 2. Safety backup of whatever is on disk now.
        safety = _safety_backup(settings)

        # 3. Stage next to the live file so the final rename is atomic.
        tmp = settings.db_path.with_name(settings.db_path.name + ".restore-tmp")
        shutil.copyfile(candidate, tmp)
        fsync_path(tmp)

        # 4. Move aside, never delete: the old file AND its -wal and -shm together.
        stamp = utc_stamp()
        move_aside(settings.db_path, "before-restore", stamp)
        for sidecar in _sidecars(settings.db_path):
            move_aside(sidecar, "before-restore", stamp)

        # 5. Put the restored file in place.
        os.replace(tmp, settings.db_path)
        fsync_dir(settings.db_path.parent)
    finally:
        candidate.unlink(missing_ok=True)

    # 6. Photos missing here come back from the backup folder; existing files stay.
    restored_photos = _restore_photos(settings)

    # 7. Open it and look.
    after = verify_database(settings.db_path)
    if not after.ok:
        raise RestoreError(f"the restored database failed its check: {after.error}")

    # 8. Record it.
    conn = connect(settings.db_path)
    try:
        record_log(conn, kind="restore", name=name, started_at=datetime.now(UTC), ok=True,
                   error=None, size=settings.db_path.stat().st_size, item_count=after.item_count,
                   verified=True)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()

    log_event("info", "restore_done", name=name, safety=safety, photos_copied=restored_photos)
    return RestoreResult(name, after.item_count, 0, safety)


def _safety_backup(settings: Settings) -> str | None:
    if not settings.db_path.exists():
        return None
    if verify_database(settings.db_path).ok:
        try:
            return create_backup(settings, "safety").name
        except BackupError as exc:
            raise RestoreError(f"the safety backup failed, nothing was changed: {exc}") from exc
    # The database does not open: keep a raw copy of the file and its -wal.
    name = catalog.make_name("safety", utc_stamp())
    copy_atomic(settings.db_path, settings.backups_dir / f"{name}.sqlite3")
    wal = settings.db_path.with_name(settings.db_path.name + "-wal")
    if wal.exists():
        copy_atomic(wal, settings.backups_dir / f"{name}.sqlite3-wal")
    return name


def _restore_photos(settings: Settings) -> int:
    source = settings.backup_photos_dir
    if not source.is_dir():
        return 0
    settings.photos_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for photo in sorted(source.iterdir()):
        target = settings.photos_dir / photo.name
        if photo.is_file() and not photo.name.endswith(".partial") and not target.exists():
            copy_atomic(photo, target)
            copied += 1
    return copied


def start_empty_safety(settings: Settings) -> str | None:
    """Before "start empty": keep a safety copy of whatever is on disk, move the rest aside."""
    name = _safety_backup(settings)
    stamp = utc_stamp()
    move_aside(settings.db_path, "before-start-empty", stamp)
    for sidecar in _sidecars(settings.db_path):
        move_aside(sidecar, "before-start-empty", stamp)
    mirror_photos(settings)
    return name
