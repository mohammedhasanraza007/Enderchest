"""Backup status and listing for the API (DATA_SAFETY 7, Surfacing)."""

import sqlite3
from datetime import UTC, datetime, timedelta

from ..backup import catalog
from ..config import Settings

STALE_AFTER = timedelta(days=7)
FAILING_AFTER = 2  # consecutive failures


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def listing(settings: Settings, conn: sqlite3.Connection | None, mounted: bool) -> list[dict]:
    """Backups on disk; item counts come from backup_log when the database is open."""
    if not mounted:
        return []
    counts: dict[str, int | None] = {}
    if conn is not None:
        for row in conn.execute("SELECT name, item_count FROM backup_log WHERE ok = 1"):
            counts[row["name"]] = row["item_count"]
    return [
        {"name": e.name, "kind": e.kind, "at": _iso(e.at), "bytes": e.bytes,
         "item_count": counts.get(e.name), "ok": True}
        for e in catalog.list_backups(settings.backups_dir)
    ]


def last_good(conn: sqlite3.Connection, settings: Settings, mounted: bool) -> dict | None:
    row = conn.execute(
        "SELECT name, finished_at, bytes FROM backup_log "
        "WHERE ok = 1 AND verified = 1 AND kind != 'restore' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is not None:
        return {"name": row["name"], "at": row["finished_at"], "bytes": row["bytes"]}
    # A restored database has no log row for the backup it came from: the log lives inside
    # the backup, which was taken before its own row was written. The folder still has it,
    # and a finished (non-.partial) file there was verified when it was made.
    entries = catalog.list_backups(settings.backups_dir) if mounted else []
    if entries:
        newest = entries[0]
        return {"name": newest.name, "at": _iso(newest.at), "bytes": newest.bytes}
    return None


def status(conn: sqlite3.Connection, settings: Settings, mounted: bool,
           now: datetime | None = None) -> str:
    if not mounted:
        return "unavailable"
    recent = conn.execute(
        "SELECT ok FROM backup_log WHERE kind != 'restore' ORDER BY id DESC LIMIT ?",
        (FAILING_AFTER,),
    ).fetchall()
    if len(recent) == FAILING_AFTER and all(r["ok"] == 0 for r in recent):
        return "failing"
    good = last_good(conn, settings, mounted)
    if good is None:
        # A brand-new install has nothing to be stale about until a backup is due.
        return "ok"
    finished = datetime.strptime(good["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return "stale" if (now or datetime.now(UTC)) - finished > STALE_AFTER else "ok"
