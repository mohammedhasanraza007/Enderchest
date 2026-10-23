"""The in-process backup loop (ARCHITECTURE 6, Scheduler). No cron, no Celery."""

import asyncio
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .. import clock
from ..backup import catalog
from ..backup.engine import BackupError, changed_since_own_write, create_backup
from ..backup.retention import plan_deletions
from ..boot.manager import BootManager, Status, WrongState
from ..logs import log_event
from .triggers import Facts, due

TICK_SECONDS = 30
# A failed automatic backup stays due (nothing good was made), so without a pause a folder that
# refuses every copy would get a full attempt every tick (F-025, D-090).
RETRY_AFTER_FAILURE = timedelta(minutes=15)


class BackupScheduler:
    def __init__(self, manager: BootManager) -> None:
        self._manager = manager
        self._startup_pending = True
        self._retry_at: datetime | None = None
        self._stop = asyncio.Event()

    async def run(self) -> None:
        while not self._stop.is_set():
            await asyncio.to_thread(self.tick)
            try:
                await asyncio.wait_for(self._stop.wait(), TICK_SECONDS)
            except TimeoutError:
                pass

    async def stop(self) -> None:
        """Ask the loop to end; a backup already running finishes first (it is in a thread)."""
        self._stop.set()

    def tick(self) -> str | None:
        """One check. Returns the reason a backup was attempted, for tests and logs."""
        manager = self._manager
        if manager.state.status is not Status.OK or not manager.backups_mounted:
            return None
        try:
            conn = manager.db()
            facts = self._facts(conn)
            reason = due(facts)
            self._startup_pending = False
            if reason is None or (self._retry_at is not None and clock.now() < self._retry_at):
                return None
            log_event("info", "backup_due", reason=reason)
            try:
                create_backup(manager.settings, "auto", log_conn=conn)
            except BackupError:
                self._retry_at = clock.now() + RETRY_AFTER_FAILURE
                return reason  # already logged and recorded in backup_log
            self._retry_at = None
            self._apply_retention(conn)
            return reason
        except WrongState:
            return None

    def _facts(self, conn) -> Facts:
        settings = self._manager.settings
        row = conn.execute(
            "SELECT started_at FROM backup_log WHERE ok = 1 AND kind != 'restore' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        newest = (datetime.strptime(row["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
                  if row else None)
        changed = changed_since_own_write(settings)
        tz_name = conn.execute("SELECT timezone FROM users WHERE id = 1").fetchone()["timezone"]
        return Facts(now=clock.now(), newest_backup_at=newest, db_changed_at=changed,
                     startup_pending=self._startup_pending, tz=ZoneInfo(tz_name))

    def _apply_retention(self, conn) -> None:
        settings = self._manager.settings
        tz_name = conn.execute("SELECT timezone FROM users WHERE id = 1").fetchone()["timezone"]
        entries = catalog.list_backups(settings.backups_dir)
        for entry in plan_deletions(entries, clock.now(), ZoneInfo(tz_name)):
            (settings.backups_dir / f"{entry.name}.sqlite3").unlink(missing_ok=True)
            log_event("info", "backup_retired", name=entry.name, kind=entry.kind)
