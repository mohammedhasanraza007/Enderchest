"""Creation of a brand-new database (DATA_SAFETY 5).

Callers must have decided that a new database is allowed (first-run rule, the
owner's typed "START EMPTY", or the test reset). The file is built under a
temporary name and renamed, so a crash never leaves a half-made database.
"""

import os
import uuid
from datetime import UTC, datetime

from ..config import Settings
from ..fsutil import fsync_dir
from . import migrate
from .connection import connect, write_transaction

DEFAULT_TIMEZONE = "UTC"  # replaced by the owner's zone when first run completes (Phase 1)


def create_database(settings: Settings) -> None:
    final = settings.db_path
    building = final.with_name(final.name + ".creating")
    for leftover in (building, building.with_name(building.name + "-wal"),
                     building.with_name(building.name + "-shm")):
        leftover.unlink(missing_ok=True)

    conn = connect(building)
    try:
        migrate.migrate(conn)
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with write_transaction(conn):
            conn.execute(
                "INSERT INTO users (id, name, timezone, created_at, updated_at) "
                "VALUES (1, NULL, ?, ?, ?)",
                (DEFAULT_TIMEZONE, now, now),
            )
            for key, value in (
                ("created_at", now),
                ("env_marker", settings.env),
                ("instance_id", str(uuid.uuid4())),
            ):
                conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (key, value))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()

    os.replace(building, final)
    fsync_dir(final.parent)
