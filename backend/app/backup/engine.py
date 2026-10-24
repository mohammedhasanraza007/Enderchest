"""Building and verifying backups (DATA_SAFETY 7). Every kind uses the same flow."""

import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..config import Settings
from ..db.connection import write_transaction
from ..fsutil import copy_atomic, fsync_dir, fsync_path, remove_partials, sha256_of, utc_stamp
from ..logs import log_event
from . import catalog

# One backup at a time (DATA_SAFETY 7 step 1). The single-instance flock already
# guarantees one process; this guards the threads inside it.
_backup_slot = threading.Lock()

# DATA_SAFETY 7 takes an automatic backup "after changes", judged by the database's newest
# modification time. Every backup writes its own backup_log row once it has started, which
# would count as a change and make that rule fire every hour on an idle database. The time left
# by that write is kept here (one database per process); only a later modification counts.
# A user write made while a backup runs (before its log row) is therefore not seen; the next
# change or the daily backup picks it up.
_own_write_mtime: dict[Path, float] = {}


def _db_mtime(settings: Settings) -> float | None:
    files = (settings.db_path, settings.db_path.with_name(settings.db_path.name + "-wal"))
    times = [p.stat().st_mtime for p in files if p.exists()]
    return max(times) if times else None


def _note_own_write(settings: Settings, log_conn: sqlite3.Connection | None) -> None:
    if log_conn is not None:  # record_log wrote nothing without a connection
        _own_write_mtime[settings.db_path] = _db_mtime(settings) or 0.0


def note_app_write(settings: Settings) -> None:
    """A write the app made by itself on a database with no unseen change (the reconcile on its
    timer adding the day's reminders, D-108): like a backup's log row, it is not a change."""
    _own_write_mtime[settings.db_path] = _db_mtime(settings) or 0.0


def changed_since_own_write(settings: Settings) -> datetime | None:
    """When the database was last modified by anything other than a backup's own log row."""
    newest = _db_mtime(settings)
    if newest is None or newest <= _own_write_mtime.get(settings.db_path, 0.0):
        return None
    return datetime.fromtimestamp(newest, UTC)


class BackupError(Exception):
    """A backup could not be built or did not verify; nothing partial is kept."""


@dataclass(frozen=True)
class Verification:
    ok: bool
    error: str | None
    schema_version: int | None
    item_count: int | None
    env_marker: str | None


@dataclass
class BackupResult:
    name: str
    bytes: int
    item_count: int | None
    verified: bool
    folder_hint: str
    photos_copied: int = 0
    photo_warnings: list[str] = field(default_factory=list)


def verify_database(path: Path) -> Verification:
    """Open a database file read-only and check it. Never call this on a `/backups` path."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5.0)
    except sqlite3.Error as exc:
        return Verification(False, f"cannot open: {exc}", None, None, None)
    try:
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            return Verification(False, "quick_check failed", None, None, None)
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            return Verification(False, "foreign_key_check failed", None, None, None)
        version = _meta(conn, "schema_version")
        marker = _meta(conn, "env_marker")
        has_items = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='items'"
        ).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] if has_items else None
        return Verification(True, None, int(version) if version else None, count, marker)
    except sqlite3.Error as exc:
        return Verification(False, f"unreadable: {exc}", None, None, None)
    finally:
        conn.close()


def _meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def record_log(conn: sqlite3.Connection | None, *, kind: str, name: str, started_at: datetime,
               ok: bool, error: str | None, size: int, item_count: int | None,
               verified: bool) -> None:
    if conn is None:
        return
    finished = datetime.now(UTC)
    with write_transaction(conn):
        conn.execute(
            "INSERT INTO backup_log (kind, name, started_at, finished_at, ok, error, bytes, "
            "item_count, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kind, name, _iso(started_at), _iso(finished), int(ok), error, size, item_count,
             int(verified)),
        )


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_backup(settings: Settings, kind: str, *, log_conn: sqlite3.Connection | None = None,
                  from_version: int | None = None, to_version: int | None = None) -> BackupResult:
    """Build, verify and copy out one backup; raise BackupError and keep nothing on failure."""
    with _backup_slot:
        started = datetime.now(UTC)
        name = _free_name(settings, kind, from_version, to_version)
        staged_partial = settings.staging_dir / f"{name}.sqlite3.partial"
        staged = settings.staging_dir / f"{name}.sqlite3"
        out_partial = settings.backups_dir / f"{name}.sqlite3.partial"
        try:
            settings.staging_dir.mkdir(parents=True, exist_ok=True)
            _snapshot(settings.db_path, staged_partial)
            check = verify_database(staged_partial)
            if not check.ok:
                raise BackupError(f"the backup did not verify: {check.error}")
            staged_partial.rename(staged)
            copy_atomic(staged, settings.backups_dir / f"{name}.sqlite3")
            final = settings.backups_dir / f"{name}.sqlite3"
            if sha256_of(final) != sha256_of(staged):
                final.unlink(missing_ok=True)
                raise BackupError("the copy in the backup folder does not match the staged file")
            size = final.stat().st_size
            staged.unlink(missing_ok=True)
        except (OSError, sqlite3.Error, BackupError) as exc:
            for leftover in (staged_partial, staged, out_partial):
                leftover.unlink(missing_ok=True)
            message = str(exc) if isinstance(exc, BackupError) else f"{type(exc).__name__}: {exc}"
            log_event("error", "backup_failed", kind=kind, name=name, reason=message)
            record_log(log_conn, kind=kind, name=name, started_at=started, ok=False, error=message,
                       size=0, item_count=None, verified=False)
            _note_own_write(settings, log_conn)
            if isinstance(exc, BackupError):
                raise
            raise BackupError(message) from exc

        copied, warnings = mirror_photos(settings)
        record_log(log_conn, kind=kind, name=name, started_at=started, ok=True, error=None,
                   size=size, item_count=check.item_count, verified=True)
        _note_own_write(settings, log_conn)
        log_event("info", "backup_done", kind=kind, name=name, bytes=size)
        return BackupResult(name, size, check.item_count, True, settings.backup_dir_hint,
                            copied, warnings)


def _free_name(settings: Settings, kind: str, from_version: int | None,
               to_version: int | None) -> str:
    """A name not already used; if the second is taken, use the next second."""
    while True:
        name = catalog.make_name(kind, utc_stamp(), from_version=from_version,
                                 to_version=to_version)
        if not (settings.backups_dir / f"{name}.sqlite3").exists():
            return name
        time.sleep(1.0)


def _snapshot(db_path: Path, destination: Path) -> None:
    """Online backup of the live database onto the volume (never onto `/backups`)."""
    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
        target.execute("PRAGMA journal_mode=DELETE")
    finally:
        target.close()
        source.close()
    fsync_path(destination)


def mirror_photos(settings: Settings) -> tuple[int, list[str]]:
    """Copy photos missing from `/backups/photos`; report size mismatches, never overwrite."""
    copied, warnings = 0, []
    if not settings.photos_dir.is_dir():
        return copied, warnings
    settings.backup_photos_dir.mkdir(parents=True, exist_ok=True)
    remove_partials(settings.backup_photos_dir)
    for photo in sorted(settings.photos_dir.iterdir()):
        if not photo.is_file():
            continue
        target = settings.backup_photos_dir / photo.name
        if target.exists():
            if target.stat().st_size != photo.stat().st_size:
                warnings.append(f"{photo.name}: backup copy differs in size, left untouched")
            continue
        copy_atomic(photo, target)
        copied += 1
    fsync_dir(settings.backup_photos_dir)
    return copied, warnings
