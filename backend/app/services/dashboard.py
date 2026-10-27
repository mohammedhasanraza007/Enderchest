"""The dashboard (API 2.13, PAGES P-12, DATA_MODEL 3.3 to 3.6): every number in one place.

The rings, the score and the breakdown sheet classify the same rows with the same rules, so a
ring's count always equals the length of its breakdown list (F-020).
"""

import sqlite3
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .. import clock
from ..derived import (
    RINGS,
    dashboard_subtitle,
    due_days,
    greeting_part,
    health_score,
    is_documented,
    is_fresh,
    ring_value,
    road,
    short_date,
    streak_days,
)
from ..errors import AppError
from ..repositories import dashboard as dashboard_repo
from ..repositories import notifications as notifications_repo
from ..repositories import users as users_repo
from . import notifications as notifications_service
from . import profile as profile_service
from . import savings as savings_service
from .catalog import location_paths

ATTENTION_ROWS = 3
BREAKDOWN_MAX = 200
DASHBOARD_ROAD_DAYS = 14
FRESH_RECONCILE = timedelta(seconds=60)


def _plural_days(days: int) -> str:
    return "1 day" if days == 1 else f"{days} days"


def _item_entry(row: sqlite3.Row, note: str) -> dict:
    return {"kind": "item", "name": row["name"], "public_id": row["public_id"], "task_id": None,
            "note": note}


def _task_entry(row: sqlite3.Row, note: str) -> dict:
    return {"kind": "task", "name": row["title"], "public_id": row["item_public_id"],
            "task_id": row["id"], "note": note}


# Each rule answers (counts?, the short reason shown in the breakdown sheet).

def _documented(row: sqlite3.Row) -> tuple[bool, str]:
    has_photo, printed = bool(row["has_photo"]), row["label_printed_at"] is not None
    if is_documented(has_photo, printed, bool(row["no_label_needed"])):
        return True, "photo and label" if printed else "photo, no label needed"
    missing = [] if has_photo else ["no photo"]
    if not (printed or row["no_label_needed"]):
        missing.append("label not printed")
    return False, ", ".join(missing)


def _located(row: sqlite3.Row, paths: dict[int, list[str]]) -> tuple[bool, str]:
    if row["location_id"] is None:
        return False, "no location"
    return True, " › ".join(paths.get(row["location_id"], []))


def _fresh(row: sqlite3.Row, today: date) -> tuple[bool, str]:
    mode, expiry = row["expiry_mode"], row["expiry_date"]
    if is_fresh(mode, expiry, today):
        if mode == "none":
            return True, "no expiry"
        on = date.fromisoformat(expiry)
        return True, "expires today" if on == today else f"expires {short_date(on, today)}"
    if mode == "date":
        return False, f"expired {short_date(date.fromisoformat(expiry), today)}"
    return False, "date not set"


def _on_time(row: sqlite3.Row, today: date) -> tuple[bool, str]:
    due = date.fromisoformat(row["next_due"])
    if due >= today:
        return True, "due today" if due == today else f"due {short_date(due, today)}"
    return False, f"{_plural_days((today - due).days)} overdue"


class _Counted:
    """The active items and counted tasks of one request, classified once per ring."""

    def __init__(self, conn: sqlite3.Connection, user_id: int, today: date) -> None:
        self.items = dashboard_repo.active_items(conn, user_id)
        self.tasks = dashboard_repo.counted_tasks(conn, user_id)
        self.today = today
        self._paths = location_paths(conn, user_id)

    def ring(self, name: str) -> list[tuple[bool, dict]]:
        if name == "on_time":
            return [(passes, _task_entry(row, note)) for row in self.tasks
                    for passes, note in [_on_time(row, self.today)]]
        rule = {"documented": _documented,
                "located": lambda row: _located(row, self._paths),
                "fresh": lambda row: _fresh(row, self.today)}[name]
        return [(passes, _item_entry(row, note)) for row in self.items
                for passes, note in [rule(row)]]

    def road(self, days: int) -> dict:
        expiries = [{"date": row["expiry_date"], "label": row["name"],
                     "public_id": row["public_id"]}
                    for row in self.items if row["expiry_mode"] == "date"]
        jobs = [{"date": row["next_due"], "label": row["title"], "task_id": row["id"],
                 "public_id": row["item_public_id"]} for row in self.tasks]
        return road(self.today, days, expiries, jobs)


def _value(classified: list[tuple[bool, dict]]) -> dict:
    return ring_value(sum(passes for passes, _ in classified), len(classified))


def _greeting(conn: sqlite3.Connection, user_id: int) -> dict:
    user = users_repo.get(conn, user_id)
    zone = ZoneInfo(user["timezone"] if user else "UTC")
    return {"part": greeting_part(clock.now().astimezone(zone).hour),
            "name": (user["name"] if user else None) or ""}


def _streak(conn: sqlite3.Connection, user_id: int, today: date) -> int:
    """DATA_MODEL 3.7 with D-127's facts: actions not undone; days a reminder was open."""
    user = users_repo.get(conn, user_id)
    zone = ZoneInfo(user["timezone"] if user else "UTC")

    def local(stamp: str | None) -> date | None:
        if stamp is None:
            return None
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(zone).date()

    spans = [(local(row["created_at"]), local(row["resolved_at"]))
             for row in dashboard_repo.reminder_spans(conn, user_id)]
    due = due_days([(created, resolved) for created, resolved in spans if created], today)
    acted = {date.fromisoformat(day) for day in dashboard_repo.acted_days(conn, user_id)}
    return streak_days(today, acted, due.__contains__)


def dashboard(conn: sqlite3.Connection, user_id: int) -> dict:
    """GET /dashboard: one request for the whole home screen (P-12)."""
    notifications_service.refresh(conn, user_id, FRESH_RECONCILE)
    today = profile_service.local_today(conn, user_id)
    counted = _Counted(conn, user_id, today)
    rings = {name: _value(counted.ring(name)) for name in RINGS}
    item_count = len(counted.items)
    rows = notifications_repo.listing(conn, user_id, "open", ATTENTION_ROWS, 0)
    total, _unread = notifications_repo.counts(conn, user_id)
    return {
        "today": today.isoformat(), "greeting": _greeting(conn, user_id),
        "subtitle": dashboard_subtitle(item_count, total), "item_count": item_count,
        "score": health_score(rings) if item_count else None, "rings": rings,
        "attention": {"rows": [notifications_service.view(row, today) for row in rows],
                      "total": total},
        "road": counted.road(DASHBOARD_ROAD_DAYS),
        "savings": savings_service.for_dashboard(conn, user_id, today),
        "streak": {"days": _streak(conn, user_id, today)},
    }


def ring_breakdown(conn: sqlite3.Connection, user_id: int, ring: str) -> dict:
    """GET /dashboard/rings/{ring}: what counts and what does not (D-112)."""
    if ring not in RINGS:
        raise AppError("not_found", 404, "There is no such ring.")
    counted = _Counted(conn, user_id, profile_service.local_today(conn, user_id))
    classified = counted.ring(ring)
    return {"ring": ring, **_value(classified),
            "qualifying": [entry for passes, entry in classified if passes][:BREAKDOWN_MAX],
            "failing": [entry for passes, entry in classified if not passes][:BREAKDOWN_MAX]}


def road_for(conn: sqlite3.Connection, user_id: int, days: int) -> dict:
    """GET /dashboard/road?days=: the same road with the Tasks page's longer window (D-113)."""
    return _Counted(conn, user_id, profile_service.local_today(conn, user_id)).road(days)
