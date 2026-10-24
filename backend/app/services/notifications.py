"""Notifications: the reconcile (DATA_MODEL 3.8, D-104), the rows' views and actions (PAGES P-11,
D-106), snooze, read and the browser-alert claim (API 2.12, D-107).

The scheduler reconciles; nothing "fires" a notification. Reconcile computes the rows that should
be open from current data and makes the table match, so restarts, downtime and double runs create
no duplicates and lose nothing.
"""

import sqlite3
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from .. import clock
from ..db.connection import write_transaction
from ..derived import dedupe_key, notification_word, snooze_until, urgency
from ..errors import AppError
from ..logs import log_event
from ..repositories import events as events_repo
from ..repositories import inspections as inspections_repo
from ..repositories import notifications as notifications_repo
from ..repositories import tasks as tasks_repo
from . import profile as profile_service

RECONCILE_EVERY = timedelta(minutes=15)
UNSHOWN_MAX = 5


class Desired(NamedTuple):
    kind: str
    item_id: int | None
    task_id: int | None
    due_date: str


def desired_rows(items: list[tuple[int, str]], tasks: list[tuple[int, str, int | None, str]],
                 findings: list[tuple[int, str]], today: date,
                 lead_days: int) -> dict[str, Desired]:
    """The rows that should be open or snoozed, by dedupe key (DATA_MODEL 3.8 steps 1, 2; D-104).

    `items`: (id, expiry_date) of active items with a date; `tasks`: (id, kind, item_id,
    next_due) of enabled tasks due by today whose item is active; `findings`: (item_id,
    local_date) of active items whose latest inspection was worn or defective.
    """
    rows: dict[str, Desired] = {}

    def add(kind: str, item_id: int | None, task_id: int | None, due: str) -> None:
        rows[dedupe_key(kind, item_id, task_id, date.fromisoformat(due))] = Desired(
            kind, item_id, task_id, due)

    for item_id, expiry in items:
        days_left = (date.fromisoformat(expiry) - today).days
        if days_left < 0:
            add("expired", item_id, None, expiry)
        elif days_left <= lead_days:
            add("expiry_soon", item_id, None, expiry)
    for task_id, kind, item_id, next_due in tasks:
        add("inspection_due" if kind == "maintenance" else "task_due", item_id, task_id, next_due)
    for item_id, local_date in findings:
        add("inspection_finding", item_id, None, local_date)
    return rows


def _gather(conn: sqlite3.Connection, user_id: int, today: date,
            lead_days: int) -> dict[str, Desired]:
    until = (today + timedelta(days=lead_days)).isoformat()
    items = conn.execute(
        "SELECT id, expiry_date FROM items WHERE user_id = ? AND state = 'active' "
        "AND deleted_at IS NULL AND expiry_mode = 'date' AND expiry_date <= ?",
        (user_id, until)).fetchall()
    tasks = tasks_repo.due_by(conn, user_id, today.isoformat())
    findings = inspections_repo.open_findings(conn, user_id)
    return desired_rows([(r["id"], r["expiry_date"]) for r in items],
                        [(t["id"], t["kind"], t["item_id"], t["next_due"]) for t in tasks],
                        [(f["item_id"], f["local_date"]) for f in findings], today, lead_days)


def reconcile(conn: sqlite3.Connection, user_id: int) -> dict:
    """Make the table match the desired set; idempotent. Returns what changed (for tests, logs)."""
    now = clock.stamp()
    changed = {"inserted": 0, "reopened": 0, "woken": 0, "superseded": 0}
    with write_transaction(conn):
        # Read inside the write transaction: two reconciles at once run one after the other.
        today = profile_service.local_today(conn, user_id)
        wanted = _gather(conn, user_id, today, profile_service.lead_days(conn, user_id))
        known = {row["dedupe_key"]: row for row in notifications_repo.by_keys(
            conn, user_id, list(wanted))}
        reopen = []
        for key, row in wanted.items():
            existing = known.get(key)
            if existing is None:
                notifications_repo.insert(conn, user_id, kind=row.kind, item_id=row.item_id,
                                          task_id=row.task_id, due_date=row.due_date,
                                          dedupe_key=key, now=now)
                changed["inserted"] += 1
            elif existing["status"] == "resolved" and existing["resolution"] != "dismissed":
                reopen.append(existing["id"])
        notifications_repo.reopen(conn, user_id, reopen)
        changed["reopened"] = len(reopen)
        stale, wake = [], []
        for row in notifications_repo.unresolved(conn, user_id):
            if row["dedupe_key"] not in wanted:
                stale.append(row["id"])
            elif row["status"] == "snoozed" and row["snoozed_until"] <= today.isoformat():
                wake.append(row["id"])
        notifications_repo.resolve(conn, user_id, stale, "superseded", now)
        notifications_repo.reopen(conn, user_id, wake)
        changed.update(superseded=len(stale), woken=len(wake))
        _remember(conn, now, today)
    if any(changed.values()):
        log_event("info", "reconciled", **changed)
    return changed


def _remember(conn: sqlite3.Connection, now: str, today: date) -> None:
    for key, value in (("last_reconcile_at", now), ("last_local_date", today.isoformat())):
        conn.execute("INSERT INTO scheduler_state (key, value) VALUES (?, ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))


def is_stale(conn: sqlite3.Connection, user_id: int) -> bool:
    """True when the local date moved or the last run is 15 minutes old (or never ran)."""
    state = {row["key"]: row["value"] for row in conn.execute(
        "SELECT key, value FROM scheduler_state WHERE key IN "
        "('last_reconcile_at', 'last_local_date')")}
    if state.get("last_local_date") != profile_service.local_today(conn, user_id).isoformat():
        return True
    last = state.get("last_reconcile_at")
    if last is None:
        return True
    at = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return not timedelta(0) <= clock.now() - at < RECONCILE_EVERY  # a clock moved back counts


def refresh(conn: sqlite3.Connection, user_id: int) -> None:
    """Reconcile only if stale: what reads and the loop's tick call."""
    if is_stale(conn, user_id):
        reconcile(conn, user_id)


# ---- views ------------------------------------------------------------------------------------

def _actions(kind: str, can_snooze: bool) -> list[dict]:
    """Server-supplied actions per kind (PAGES P-11). The first two show as pills; the rest go in
    the row's "More" menu. Snooze is left out where it could not move the row."""
    snooze = [{"key": "snooze", "label": "Snooze", "primary": False}] if can_snooze else []
    if kind == "expiry_soon":
        return [{"key": "use", "label": "Use it", "primary": True}, *snooze]
    if kind == "expired":
        return [{"key": "mark_expired", "label": "Mark expired", "primary": True}, *snooze,
                {"key": "use", "label": "Use it", "primary": False},
                {"key": "discard", "label": "Discard", "primary": False}]
    if kind == "inspection_due":
        return [{"key": "inspect", "label": "Inspect now", "primary": True}, *snooze,
                {"key": "skip", "label": "Skip", "primary": False},
                {"key": "discard", "label": "Discard", "primary": False}]
    if kind == "task_due":
        return [{"key": "done", "label": "Mark done", "primary": True}, *snooze,
                {"key": "skip", "label": "Skip", "primary": False}]
    return [{"key": "discard", "label": "Mark discarded", "primary": True},
            {"key": "keep", "label": "Keep using", "primary": False}]


def view(row: sqlite3.Row, today: date) -> dict:
    due = date.fromisoformat(row["due_date"])
    can_snooze = row["status"] != "resolved" and any(
        snooze_until(option, row["kind"], due, today) for option in ("tomorrow", "3days", "week"))
    return {
        "id": row["id"], "kind": row["kind"],
        "item": ({"public_id": row["item_public_id"], "name": row["item_name"],
                  "primary_photo_id": row["item_primary_photo_id"]}
                 if row["item_id"] is not None else None),
        "task": ({"id": row["task_id"], "title": row["task_title"]}
                 if row["task_id"] is not None else None),
        "due_date": row["due_date"],
        "word": notification_word(row["kind"], due, today, row["latest_result"]),
        "urgency": urgency(row["kind"], due, today), "status": row["status"],
        "snoozed_until": row["snoozed_until"], "read_at": row["read_at"],
        "resolution": row["resolution"],
        "actions": _actions(row["kind"], can_snooze) if row["status"] != "resolved" else [],
    }


def _row(conn: sqlite3.Connection, user_id: int, notification_id: int) -> sqlite3.Row:
    row = notifications_repo.get(conn, user_id, notification_id)
    if row is None:
        raise AppError("not_found", 404, "That reminder does not exist.")
    return row


def list_notifications(conn: sqlite3.Connection, user_id: int, status: str, limit: int,
                       cursor: str | None) -> dict:
    from .items import decode_cursor, encode_cursor  # one cursor format; items imports this module
    refresh(conn, user_id)
    offset = decode_cursor(cursor)
    today = profile_service.local_today(conn, user_id)
    rows = notifications_repo.listing(conn, user_id, status, limit + 1, offset)
    return {"items": [view(row, today) for row in rows[:limit]],
            "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None}


def count(conn: sqlite3.Connection, user_id: int) -> dict:
    refresh(conn, user_id)
    today = profile_service.local_today(conn, user_id)
    open_count, unread = notifications_repo.counts(conn, user_id)
    unshown = notifications_repo.unshown(conn, user_id, UNSHOWN_MAX)
    return {"open": open_count, "unread": unread, "unshown": [view(r, today) for r in unshown]}


# ---- actions on a row -------------------------------------------------------------------------

def mark_read(conn: sqlite3.Connection, user_id: int, notification_id: int) -> None:
    with write_transaction(conn):
        _row(conn, user_id, notification_id)
        notifications_repo.mark_read(conn, user_id, notification_id, clock.stamp())


def mark_all_read(conn: sqlite3.Connection, user_id: int) -> int:
    with write_transaction(conn):
        return notifications_repo.mark_all_read(conn, user_id, clock.stamp())


def claim_shown(conn: sqlite3.Connection, user_id: int, notification_id: int) -> bool:
    with write_transaction(conn):
        _row(conn, user_id, notification_id)
        return notifications_repo.claim_shown(conn, user_id, notification_id, clock.stamp())


def snooze(conn: sqlite3.Connection, user_id: int, notification_id: int, option: str) -> dict:
    with write_transaction(conn):
        row = _row(conn, user_id, notification_id)
        today = profile_service.local_today(conn, user_id)
        if row["status"] == "resolved":
            raise AppError("conflict", 409, "That reminder is already resolved.",
                           {"reason": "resolved"})
        until = snooze_until(option, row["kind"], date.fromisoformat(row["due_date"]), today)
        if until is None:
            raise AppError("conflict", 409, "This reminder cannot be snoozed: it is due today.",
                           {"reason": "cannot_snooze"})
        notifications_repo.snooze(conn, user_id, notification_id, until.isoformat())
    return view(_row(conn, user_id, notification_id), today)


def dismiss(conn: sqlite3.Connection, user_id: int, notification_id: int) -> dict:
    """Keep using: the owner closes an inspection finding (D-104). It never comes back."""
    now = clock.stamp()
    with write_transaction(conn):
        row = _row(conn, user_id, notification_id)
        if row["kind"] != "inspection_finding":
            raise AppError("conflict", 409, "Only an inspection finding can be closed this way.",
                           {"reason": "not_a_finding"})
        if row["status"] != "resolved":
            notifications_repo.resolve(conn, user_id, [notification_id], "dismissed", now)
            today = profile_service.local_today(conn, user_id)
            events_repo.add(conn, user_id, kind="notification_resolved", item_id=row["item_id"],
                            payload={"notification_id": notification_id,
                                     "resolution": "dismissed"},
                            at=now, local_date=today.isoformat())
    return view(_row(conn, user_id, notification_id), profile_service.local_today(conn, user_id))


def resolve_for_item(conn: sqlite3.Connection, user_id: int, item_id: int, resolution: str,
                     now: str) -> None:
    """Inside the caller's transaction: an item left `active` (D-105)."""
    ids = notifications_repo.unresolved_for(conn, user_id, item_id=item_id)
    notifications_repo.resolve(conn, user_id, ids, resolution, now)


def resolve_for_task(conn: sqlite3.Connection, user_id: int, task_id: int, resolution: str,
                     now: str) -> None:
    """Inside the caller's transaction: a task was done, skipped or inspected."""
    ids = notifications_repo.unresolved_for(conn, user_id, task_id=task_id)
    notifications_repo.resolve(conn, user_id, ids, resolution, now)
