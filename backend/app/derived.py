"""Derived values (DATA_MODEL 3), computed in one place and unit-tested.

Every comparison with an expiry date uses the owner's local `today`, never UTC (3.1).
"""

from collections.abc import Callable
from datetime import date, timedelta

SNOOZE_DAYS = {"tomorrow": 1, "3days": 3, "week": 7}


def expiry_view(mode: str, expiry_date: str | None, today: date, lead_days: int) -> dict:
    """The expiry status and its word for one item (DATA_MODEL 3.2)."""
    if mode == "none":
        return {"mode": mode, "date": None, "status": "no_expiry", "days_left": None,
                "word": "no expiry"}
    if mode != "date" or expiry_date is None:
        return {"mode": "unknown", "date": None, "status": "unknown", "days_left": None,
                "word": "date not set"}
    days_left = (date.fromisoformat(expiry_date) - today).days
    if days_left < 0:
        status, word = "expired", "expired"
    elif days_left == 0:
        status, word = "today", "expires today"
    elif days_left == 1:
        status, word = "soon", "1 day left"
    elif days_left <= lead_days:
        status, word = "soon", f"{days_left} days left"
    else:
        status, word = "ok", f"{days_left} days left"
    return {"mode": mode, "date": expiry_date, "status": status, "days_left": days_left,
            "word": word}


def _plural_days(days: int) -> str:
    return "1 day" if days == 1 else f"{days} days"


def short_date(day: date, today: date) -> str:
    """`16 Oct`, or `16 Oct 2025` when the year is not the current one (PAGES 2)."""
    text = f"{day.day} {day.strftime('%b')}"
    return text if day.year == today.year else f"{text} {day.year}"


def next_due_after(mode: str, interval_days: int | None, next_due: date,
                   done_on: date) -> date | None:
    """The completion rule (DATA_MODEL 2.9); None for a one-off task.

    `fixed` keeps the original series: the next date of it strictly after the day done, always
    at least one step on (the occurrence just done is satisfied, even when done early).
    """
    if interval_days is None:
        return None
    step = timedelta(days=interval_days)
    if mode == "from_completion":
        return done_on + step
    upcoming = next_due + step
    while upcoming <= done_on:
        upcoming += step
    return upcoming


def task_word(next_due: date, today: date, enabled: bool, interval_days: int | None,
              last_done: date | None) -> str:
    """The word on a task row (D-106)."""
    if not enabled:
        if interval_days is None and last_done is not None:
            return f"done {short_date(last_done, today)}"
        return "off"
    days = (next_due - today).days
    if days < 0:
        return f"{_plural_days(-days)} overdue"
    if days == 0:
        return "due today"
    if days == 1:
        return "due tomorrow"
    return f"due in {days} days"


def notification_word(kind: str, due_date: date, today: date,
                      finding: str | None = None) -> str:
    """The word after a row's name, as in "Oat Milk (expires today)" (DESIGN 6.9, D-106)."""
    days = (due_date - today).days
    if kind == "expiry_soon":
        return "expires today" if days <= 0 else f"{_plural_days(days)} left"
    if kind == "expired":
        return "expired"
    if kind == "inspection_finding":
        # A later "ok" inspection supersedes the row; the Resolved tab then shows no result.
        return f"inspection suggested: {finding}" if finding in ("worn", "defective") else (
            "inspection suggested")
    late = f"{_plural_days(-days)} overdue" if days < 0 else None
    if kind == "inspection_due":
        return f"inspect, {late}" if late else "inspect"
    return late or "due today"


def urgency(kind: str, due_date: date, today: date) -> str:
    """`overdue`, `today` or `upcoming`: how soon a row needs the owner (D-106)."""
    if kind == "expired" or due_date < today:
        return "overdue"
    return "today" if due_date == today else "upcoming"


def snooze_until(option: str, kind: str, due_date: date, today: date) -> date | None:
    """The date a snoozed row comes back; an expiry reminder never passes its date (D-047).

    None when the snooze would not move the row past today (nothing to snooze).
    """
    if kind == "inspection_finding":
        return None
    until = today + timedelta(days=SNOOZE_DAYS[option])
    if kind == "expiry_soon":
        until = min(until, due_date)
    return until if until > today else None


def dedupe_key(kind: str, item_id: int | None, task_id: int | None, due_date: date) -> str:
    """`kind|item_id-or-dash|task_id-or-dash|due_date` (DATA_MODEL 2.12, D-022)."""
    item = str(item_id) if item_id is not None else "-"
    task = str(task_id) if task_id is not None else "-"
    return f"{kind}|{item}|{task}|{due_date.isoformat()}"


# ---- the dashboard (DATA_MODEL 3.3 to 3.6; Phase 5) ---------------------------------------------

RINGS = ("documented", "located", "fresh", "on_time")
# Default score weights (DATA_MODEL 3.5, open question O-004).
RING_WEIGHTS = {"documented": 25, "located": 20, "fresh": 35, "on_time": 20}


def round_half_up(value: float) -> int:
    """Rounding as people expect it (82.5 → 83); Python's round() would give 82."""
    return int(value + 0.5)


def ring_value(num: int, den: int) -> dict:
    """One ring: `value = round(100 × num / den)`, or None when not applicable (den 0, D-044)."""
    return {"value": round_half_up(100 * num / den) if den else None, "num": num, "den": den}


def health_score(rings: dict[str, dict]) -> int | None:
    """The weighted average over applicable rings only (3.5); None when no ring applies."""
    applicable = [name for name in RINGS if rings[name]["value"] is not None]
    if not applicable:
        return None
    total = sum(RING_WEIGHTS[name] * rings[name]["value"] for name in applicable)
    return round_half_up(total / sum(RING_WEIGHTS[name] for name in applicable))


def is_documented(has_photo: bool, label_printed: bool, no_label_needed: bool) -> bool:
    """A live photo, and a printed label or no label needed (3.4)."""
    return has_photo and (label_printed or no_label_needed)


def is_fresh(mode: str, expiry_date: str | None, today: date) -> bool:
    """No expiry, or a date not yet past; an unknown date is not fresh (3.4)."""
    if mode == "none":
        return True
    return mode == "date" and expiry_date is not None and date.fromisoformat(expiry_date) >= today


def greeting_part(hour: int) -> str:
    """The greeting word by the owner's local hour (DESIGN 6.7, D-113)."""
    if 5 <= hour <= 11:
        return "morning"
    if 12 <= hour <= 16:
        return "afternoon"
    if 17 <= hour <= 20:
        return "evening"
    return "night"


def dashboard_subtitle(item_count: int, attention_total: int) -> str:
    """One real fact about today (DESIGN 6.7, PAGES P-12); never a slogan."""
    if attention_total == 1:
        return "1 thing needs you today"
    if attention_total > 1:
        return f"{attention_total} things need you today"
    if item_count == 0:
        return "Add items to see your overview"
    return "Everything is on track"


def road(today: date, days: int, expiries: list[dict], tasks: list[dict]) -> dict:
    """The road (3.6, D-110): one event per date in `today … today + days - 1`, and the truck.

    `expiries`: `{date, label, public_id}` of active items with a date; `tasks`: `{date, label,
    task_id, public_id}` of the tasks On time counts. Anything before today is not on the road.
    """
    end = today + timedelta(days=days - 1)
    by_date: dict[str, list[dict]] = {}
    for kind, source, key in (("task", tasks, "task_id"), ("expiry", expiries, None)):
        for entry in source:
            on = date.fromisoformat(entry["date"])
            if today <= on <= end:
                by_date.setdefault(entry["date"], []).append({
                    "kind": kind, "label": entry["label"], "public_id": entry.get("public_id"),
                    "task_id": entry.get(key) if key else None})
    events = []
    for on in sorted(by_date):
        entries = by_date[on]  # tasks first, so a mixed day is named after its task
        kinds = {entry["kind"] for entry in entries}
        events.append({"date": on, "kind": kinds.pop() if len(kinds) == 1 else "mixed",
                       "label": entries[0]["label"], "count": len(entries), "entries": entries})
    later = [event for event in events if event["date"] > today.isoformat()]
    next_task = next((e for e in later if e["kind"] in ("task", "mixed")), None)
    truck = next_task or (later[0] if later else None)
    return {"start": today.isoformat(), "end": end.isoformat(), "events": events,
            "truck_date": truck["date"] if truck else today.isoformat()}


# ---- Phase 8: the streak (DATA_MODEL 3.7, D-127) ----------------------------------------------


def due_days(rows: list[tuple[date, date | None]], today: date) -> set[date]:
    """Local days on which a reminder row was open or snoozed: from its creation day to its
    resolution day, or to today while it is unresolved."""
    days: set[date] = set()
    for created, resolved in rows:
        day, last = created, min(resolved or today, today)
        while day <= last:
            days.add(day)
            day += timedelta(days=1)
    return days


def streak_days(today: date, acted: set[date], was_due: Callable[[date], bool]) -> int:
    """Consecutive counting days ending today or yesterday. A day with nothing due is skipped;
    today not counting yet breaks nothing; the walk stops at the first day anything was done."""
    if not acted:
        return 0
    first = min(acted)
    day = today if today in acted else today - timedelta(days=1)
    days = 0
    while day >= first:
        if day in acted:
            days += 1
        elif was_due(day):
            break
        day -= timedelta(days=1)
    return days
