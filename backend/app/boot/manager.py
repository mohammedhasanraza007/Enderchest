"""The boot state machine (DATA_SAFETY 4, 5, 11).

The process never exits because a check failed: it records a state and serves a boot
page, so `restart: unless-stopped` can never hide the reason in a crash loop.
"""

import os
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ..backup import catalog
from ..backup.engine import BackupError, create_backup
from ..backup.restore import RestoreError, RestoreResult, restore_backup, start_empty_safety
from ..config import Settings
from ..db import migrate
from ..db.connection import ThreadConnections, connect
from ..db.create import create_database
from ..fsutil import remove_partials
from ..logs import log_event
from . import marker
from .lock import InstanceLock
from .mounts import is_mount_point, is_writable


class Status(StrEnum):
    STARTING = "starting"
    OK = "ok"
    RECOVERY = "recovery"
    LOCKED = "locked"
    FAILED = "failed"


@dataclass(frozen=True)
class BootState:
    status: Status
    reason: str | None = None
    schema_found: int | None = None
    detail: str | None = None  # one plain sentence for the boot page


class WrongState(Exception):
    """The requested action is not allowed in the current boot state."""


class BootManager:
    def __init__(self, settings: Settings,
                 is_mount: Callable[[Path], bool] = is_mount_point) -> None:
        self.settings = settings
        self._is_mount = is_mount
        self._lock = InstanceLock(settings.lock_path)
        self._op_lock = threading.RLock()
        self._state = BootState(Status.STARTING)
        self._connections: ThreadConnections | None = None
        self.data_mounted = False
        self.backups_mounted = False

    # ----- reading the state -------------------------------------------------------------

    @property
    def state(self) -> BootState:
        return self._state

    def _set(self, status: Status, reason: str | None = None, *, schema_found: int | None = None,
             detail: str | None = None) -> None:
        self._state = BootState(status, reason, schema_found, detail)
        log_event("info", "boot_state", state=status.value, reason=reason)

    def db(self) -> sqlite3.Connection:
        """This thread's connection; only valid in state `ok`."""
        connections = self._connections
        if self._state.status is not Status.OK or connections is None:
            raise WrongState("the database is not open")
        return connections.get()

    def warnings(self) -> list[str]:
        found = []
        if self.data_mounted and not self.backups_mounted:
            found.append("The backup folder is not connected. Nothing is being backed up.")
        return found

    # ----- the startup sequence ----------------------------------------------------------

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        """Hold the operation lock: boot checks, restore and test resets never overlap."""
        with self._op_lock:
            yield

    def run_checks(self) -> None:
        with self._op_lock:
            self.release_connections()
            self._set(Status.STARTING)
            try:
                self._sequence()
            except Exception as exc:  # a check must never take the process down
                log_event("error", "boot_unexpected", error=type(exc).__name__)
                self._set(Status.FAILED, "unexpected_error",
                          detail="Enderchest hit an unexpected problem while starting. "
                                 "Your data was not changed.")

    def _sequence(self) -> None:
        s = self.settings
        # 1. Mount checks.
        self.data_mounted = self._is_mount(s.data_dir)
        self.backups_mounted = self._is_mount(s.backups_dir) and is_writable(s.backups_dir)
        if not self.data_mounted:
            self._set(Status.LOCKED, "no_data_volume",
                      detail="The data volume is not connected, so nothing was created or changed.")
            return
        if not is_writable(s.data_dir):
            self._set(Status.LOCKED, "data_not_writable",
                      detail="The data volume is connected but this app may not write to it.")
            return
        # 2. Single-instance lock.
        if not self._lock.acquire():
            self._set(Status.LOCKED, "second_instance",
                      detail="Another Enderchest is already using this data.")
            return

        self._prepare_folders()

        if s.db_path.exists():
            if not self._check_existing_database():
                return
        elif not self._first_run():
            return

        # 7. Open for business. The scheduler reads this state and starts its own work.
        self._connections = ThreadConnections(s.db_path)
        self._set(Status.OK, schema_found=migrate.supported_version())

    def _prepare_folders(self) -> None:
        s = self.settings
        for folder in (s.db_path.parent, s.photos_dir, s.thumbs_dir, s.secrets_dir, s.staging_dir):
            folder.mkdir(parents=True, exist_ok=True)
        os.chmod(s.secrets_dir, 0o700)
        remove_partials(s.staging_dir)
        if self.backups_mounted:
            remove_partials(s.backups_dir)
            remove_partials(s.backup_photos_dir)

    def _check_existing_database(self) -> bool:
        """Steps 3 to 6. Returns True when the database is ready; False after setting a state."""
        s = self.settings
        stored = marker.read_marker(s.db_path)
        if not marker.matches(stored, s.env):
            self._set(Status.LOCKED, "env_mismatch",
                      detail=f"This data belongs to the '{stored}' environment, "
                             f"but this app runs as '{s.env}'. Nothing was written.")
            return False
        conn: sqlite3.Connection | None = None
        try:
            conn = connect(s.db_path)  # raises on a file that is not a database
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("quick_check failed")
            version = migrate.current_version(conn)
            if version == 0:
                raise sqlite3.DatabaseError("no schema version")
        except sqlite3.Error:
            if conn is not None:
                conn.close()
            self._set(Status.RECOVERY, "corrupt",
                      detail="The database file did not pass its integrity check. "
                             "Nothing was changed.")
            return False
        try:
            supported = migrate.supported_version()
            if version > supported:
                self._set(Status.LOCKED, "newer_data", schema_found=version,
                          detail="This data was written by a newer version of Enderchest. "
                                 "It was left untouched.")
                return False
            if migrate.pending(conn):
                return self._migrate_with_backup(conn, version, supported)
            return True
        finally:
            conn.close()

    def _migrate_with_backup(self, conn: sqlite3.Connection, version: int, target: int) -> bool:
        if not self.backups_mounted:
            self._set(Status.FAILED, "backup_folder_unavailable", schema_found=version,
                      detail="An update needs a verified backup first, but the backup folder "
                             "is not connected. Nothing was changed.")
            return False
        try:
            backup = create_backup(self.settings, "pre-migration", log_conn=conn,
                                   from_version=version, to_version=target)
        except BackupError as exc:
            self._set(Status.FAILED, "pre_migration_backup_failed", schema_found=version,
                      detail=f"The backup before updating failed, so nothing was changed. {exc}")
            return False
        try:
            migrate.migrate(conn)
        except migrate.MigrationError as exc:
            self._set(Status.FAILED, "migration_failed", schema_found=version,
                      detail=f"The update failed and was rolled back. Your data is as it was; "
                             f"the backup is {backup.name}. {exc}")
            return False
        return True

    def _first_run(self) -> bool:
        """DATA_SAFETY 5: a new empty database only when nothing else exists anywhere."""
        s = self.settings
        sidecars = [s.db_path.with_name(s.db_path.name + suffix) for suffix in ("-wal", "-shm")]
        has_photos = s.photos_dir.is_dir() and any(p.is_file() for p in s.photos_dir.iterdir())
        # Look at the folder even when it is not a writable mount: "not connected" must never
        # read as "no backups", or a lost volume would silently start empty (DATA_SAFETY 5).
        has_backups = bool(catalog.list_backups(s.backups_dir))
        if has_photos or has_backups or any(p.exists() for p in sidecars):
            detail = ("The database is missing but photos or backups were found. "
                      "Choose a backup to restore.")
            if not self.backups_mounted:
                detail = ("The database is missing but photos or backups were found, and the "
                          "backup folder is not connected or not writable. Nothing was created. "
                          "Fix the backup folder, then start Enderchest again.")
            self._set(Status.RECOVERY, "database_missing", detail=detail)
            return False
        create_database(s)
        log_event("info", "database_created", env=s.env)
        return True

    # ----- the recovery page's two actions ------------------------------------------------

    def restore(self, name: str) -> RestoreResult:
        with self._op_lock:
            self._require(Status.RECOVERY)
            if not self.backups_mounted:
                raise RestoreError("the backup folder is not connected")
            self.release_connections()
            result = restore_backup(self.settings, name)
            self.run_checks()
            return result

    def start_empty(self) -> None:
        with self._op_lock:
            self._require(Status.RECOVERY)
            if not self.backups_mounted:
                raise RestoreError("the backup folder is not connected, so no safety copy "
                                   "can be made")
            self.release_connections()
            start_empty_safety(self.settings)
            create_database(self.settings)
            self.run_checks()

    def _require(self, status: Status) -> None:
        if self._state.status is not status:
            raise WrongState(f"not allowed while the state is {self._state.status.value}")

    # ----- ending -------------------------------------------------------------------------

    def release_connections(self) -> None:
        connections, self._connections = self._connections, None
        if connections is not None:
            connections.close_all()

    def shutdown(self) -> None:
        """SIGTERM path: checkpoint the WAL, close connections, drop the lock."""
        with self._op_lock:
            if self._state.status is Status.OK and self.settings.db_path.exists():
                try:
                    conn = connect(self.settings.db_path)
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    conn.close()
                except sqlite3.Error as exc:
                    log_event("error", "shutdown_checkpoint_failed", error=type(exc).__name__)
            self.release_connections()
            self._lock.release()
