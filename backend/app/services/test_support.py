"""Helpers behind the test-only endpoints (API.md 2.17). Used on the test stack only."""

import json
import random
import shutil
import sqlite3
import threading
import time
from datetime import timedelta

from .. import clock, ids
from ..boot.manager import BootManager
from ..config import Settings
from ..db.connection import connect, write_transaction
from ..db.create import create_database
from ..repositories import items as items_repo
from . import profile as profile_service

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
    """Wipe the TEST database, photos, thumbnails, staging, test backups and the Gemini key, then
    start fresh: a reset app has never been given a key."""
    assert settings.env == "test", "test-only helper"
    with manager.exclusive():
        loop.stop()
        manager.release_connections()
        delete_database_files(settings)
        for folder in (settings.photos_dir, settings.thumbs_dir, settings.staging_dir,
                       settings.secrets_dir):
            _wipe_contents(folder)
        if manager.backups_mounted:
            _wipe_contents(settings.backups_dir)
        create_database(settings)
        manager.run_checks()


# ---- fixtures (API 2.17, D-092): realistic data for the TEST database only ---------------------

_NOUNS = ("Spanner", "Screwdriver", "Drill bit", "Battery", "Cable", "Charger", "Shampoo",
          "Toothpaste", "Rice", "Lentils", "Olive oil", "Coffee", "Tea", "Glue", "Tape",
          "Bulb", "Fuse", "Sunscreen", "Paracetamol", "Notebook")
_WORDS = ("small", "large", "spare", "blue", "red", "steel", "old", "new", "travel", "kitchen")
_CATEGORIES = (("Tools", 0, 1, 1), ("Electronics", 0, 1, 1), ("Food and drink", 1, 0, 0),
               ("Cosmetics", 1, 0, 0), ("Household", 0, 0, 1), ("Other", 0, 0, 1))
_PLACES = (("Garage", None), ("Shelf 1", "Garage"), ("Shelf 2", "Garage"),
           ("Blue box", "Shelf 2"), ("Kitchen", None), ("Pantry", "Kitchen"),
           ("Fridge", "Kitchen"), ("Bedroom", None), ("Wardrobe", "Bedroom"))


def load_fixture(conn: sqlite3.Connection, name: str, user_id: int = 1) -> dict:
    if name != "items-1000":
        raise KeyError(name)
    rng = random.Random(1000)  # the same 1,000 items every time, so tests can count them
    today = profile_service.local_today(conn, user_id)
    now = clock.stamp()
    with write_transaction(conn):
        category_ids = []
        for cat_name, expires, maintenance, label in _CATEGORIES:
            cursor = conn.execute(
                "INSERT INTO categories (user_id, name, expires_default, maintenance_default, "
                "label_default, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, cat_name, expires, maintenance, label, now))
            category_ids.append(cursor.lastrowid)
        place_ids: dict[str, int] = {}
        for place, parent in _PLACES:
            cursor = conn.execute(
                "INSERT INTO locations (user_id, name, parent_id, created_at) VALUES (?, ?, ?, ?)",
                (user_id, place, place_ids.get(parent) if parent else None, now))
            place_ids[place] = cursor.lastrowid
        for number in range(1, 1001):
            roll = rng.random()
            if roll < 0.35:
                mode, date = "date", (today + timedelta(days=rng.randint(-30, 90))).isoformat()
            elif roll < 0.65:
                mode, date = "none", None
            else:
                mode, date = "unknown", None
            values = {
                "name": f"{rng.choice(_WORDS).title()} {rng.choice(_NOUNS).lower()} {number}",
                "category_id": rng.choice(category_ids + [None]),
                "location_id": rng.choice(list(place_ids.values()) + [None]),
                "quantity": rng.randint(1, 5), "expiry_mode": mode, "expiry_date": date,
                "price_paise": rng.choice([None, rng.randint(1, 500) * 100]),
                "attributes": json.dumps({"size": rng.choice([8, 10, 12, 13])}
                                         if number % 7 == 0 else {}),
                "notes": "", "no_label_needed": int(number % 5 == 0),
            }
            stamp = f"2026-01-01T00:{number // 60 % 60:02d}:{number % 60:02d}Z"
            item_id = items_repo.insert(conn, user_id, ids.new_public_id(), values, stamp)
            state = ("used", "expired", "discarded")[number % 3] if number % 20 == 0 else "active"
            deleted = now if number % 50 == 0 else None
            conn.execute("UPDATE items SET state = ?, deleted_at = ? WHERE id = ?",
                         (state, deleted, item_id))
    return {"fixture": name, "items": 1000, "categories": len(category_ids),
            "locations": len(place_ids)}
