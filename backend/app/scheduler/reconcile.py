"""The in-process reconcile loop (DATA_MODEL 3.8, ARCHITECTURE 6 Scheduler).

It reconciles at start, then whenever the local date changes or 15 minutes have passed; the
check runs every 30 seconds, so a date change (or a moved test clock) is seen within a tick.
"""

import asyncio
import sqlite3

from ..boot.manager import BootManager, Status, WrongState
from ..logs import log_event
from ..services import notifications as notifications_service

TICK_SECONDS = 30
# Until the start-up reconcile has run (the boot checks may still be working), look every second.
STARTUP_TICK_SECONDS = 1
USER_ID = 1  # the one user of this laptop app (DATA_MODEL 1)


class Reconciler:
    def __init__(self, manager: BootManager) -> None:
        self._manager = manager
        self._startup_pending = True
        self._stop = asyncio.Event()

    async def run(self) -> None:
        while not self._stop.is_set():
            await asyncio.to_thread(self.tick)
            wait = STARTUP_TICK_SECONDS if self._startup_pending else TICK_SECONDS
            try:
                await asyncio.wait_for(self._stop.wait(), wait)
            except TimeoutError:
                pass

    async def stop(self) -> None:
        self._stop.set()

    def tick(self) -> bool:
        """One check. Returns True when a reconcile ran (for tests)."""
        if self._manager.state.status is not Status.OK:
            self._startup_pending = True  # after a restore or a recovery, start over
            return False
        try:
            conn = self._manager.db()
            if self._startup_pending or notifications_service.is_stale(conn, USER_ID):
                notifications_service.reconcile(conn, USER_ID)
                self._startup_pending = False
                return True
        except WrongState:
            return False
        except sqlite3.Error as exc:
            log_event("warning", "reconcile_failed", error=type(exc).__name__)
        return False
