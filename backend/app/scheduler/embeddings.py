"""The in-process embedding loop (Phase 6 spec, Build 1: background job and backfill).

Each tick embeds a few photos that have no vector from the current model; while there is work
it ticks again at once, otherwise every 10 seconds, so a new photo is ready within seconds and
an old library is backfilled without blocking anything (the work runs in the heavy worker).
"""

import asyncio
import sqlite3

from ..backup.engine import changed_since_own_write, note_app_write
from ..boot.manager import BootManager, Status, WrongState
from ..logs import log_event
from ..services import embeddings as embeddings_service

TICK_SECONDS = 10
USER_ID = 1  # the one user of this laptop app (DATA_MODEL 1)


class Embedder:
    def __init__(self, manager: BootManager) -> None:
        self._manager = manager
        self._stop = asyncio.Event()

    async def run(self) -> None:
        while not self._stop.is_set():
            written = await asyncio.to_thread(self.tick)
            try:
                await asyncio.wait_for(self._stop.wait(), 0 if written else TICK_SECONDS)
            except TimeoutError:
                pass

    async def stop(self) -> None:
        self._stop.set()

    def tick(self) -> int:
        """One batch. Returns how many photos were embedded (for tests)."""
        if self._manager.state.status is not Status.OK:
            return 0
        try:
            settings = self._manager.settings
            idle = changed_since_own_write(settings) is None
            written = embeddings_service.fill(self._manager.db(), settings, USER_ID)
            if idle and written:
                # Derived vectors on an unchanged database are not an owner's change (D-108).
                note_app_write(settings)
            return written
        except WrongState:
            return 0
        except sqlite3.Error as exc:
            log_event("warning", "embedding_tick_failed", error=type(exc).__name__)
            return 0
        except Exception as exc:
            # Anything else (an ONNX Runtime error, say) must not end the loop until a restart.
            log_event("error", "embedding_tick_failed", error=type(exc).__name__)
            return 0
