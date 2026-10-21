"""Helpers behind the test-only endpoints (API.md 2.17). Used on the test stack only."""

import shutil
import sqlite3
import threading
import time

from ..boot.manager import BootManager
from ..config import Settings
from ..db.connection import connect, write_transaction
from ..db.create import create_database

COUNTER_KEY = "test_write_loop:counter"
SEQ_PREFIX = "test_write_loop:seq:"


class WriteLoop:
    """A background loop of paired writes, so a kill mid-write can be checked afterwards.

    Each round adds one `seq` row and bumps `counter` in ONE transaction. After a crash the
    rows must still be 1..N with the counter equal to N: no half-written record.
    """

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: Settings, seconds: int) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(settings, seconds), name="write-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)

    def _run(self, settings: Settings, seconds: int) -> None:
        conn = connect(settings.db_path)
        deadline = time.monotonic() + seconds
        try:
            while time.monotonic() < deadline and not self._stop.is_set():
                with write_transaction(conn):
                    row = conn.execute("SELECT value FROM scheduler_state WHERE key = ?",
                                       (COUNTER_KEY,)).fetchone()
                    number = (int(row["value"]) if row else 0) + 1
                    conn.execute("INSERT INTO scheduler_state (key, value) VALUES (?, ?)",
                                 (f"{SEQ_PREFIX}{number:09d}", "1"))
                    conn.execute(
                        "INSERT INTO scheduler_state (key, value) VALUES (?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (COUNTER_KEY, str(number)))
                time.sleep(0.005)
        except sqlite3.Error:
            pass  # the database was closed or deleted under the loop; that is expected in probes
        finally:
            conn.close()


def write_loop_report(conn: sqlite3.Connection, running: bool) -> dict:
    rows = [r["key"] for r in conn.execute(
        "SELECT key FROM scheduler_state WHERE key LIKE ? ORDER BY key", (SEQ_PREFIX + "%",))]
    counter_row = conn.execute("SELECT value FROM scheduler_state WHERE key = ?",
                               (COUNTER_KEY,)).fetchone()
    counter = int(counter_row["value"]) if counter_row else 0
    contiguous = rows == [f"{SEQ_PREFIX}{n:09d}" for n in range(1, len(rows) + 1)]
    return {
        "running": running,
        "rows": len(rows),
        "counter": counter,
        "consistent": contiguous and counter == len(rows),
        "quick_check": conn.execute("PRAGMA quick_check").fetchone()[0],
    }


def _wipe_contents(folder) -> None:
    """Delete what is inside a folder but keep the folder (its mount stays in place)."""
    if not folder.is_dir():
        return
    for child in folder.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def delete_database_files(settings: Settings) -> None:
    assert settings.env == "test", "test-only helper"
    for suffix in ("", "-wal", "-shm"):
        settings.db_path.with_name(settings.db_path.name + suffix).unlink(missing_ok=True)


def reset_test_data(settings: Settings, manager: BootManager, loop: WriteLoop) -> None:
    """Wipe the TEST database, photos, thumbnails, staging and test backups, then start fresh."""
    assert settings.env == "test", "test-only helper"
    with manager.exclusive():
        loop.stop()
        manager.release_connections()
        delete_database_files(settings)
        for folder in (settings.photos_dir, settings.thumbs_dir, settings.staging_dir):
            _wipe_contents(folder)
        if manager.backups_mounted:
            _wipe_contents(settings.backups_dir)
        create_database(settings)
        manager.run_checks()
