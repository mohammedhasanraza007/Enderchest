"""Derived values (DATA_MODEL 3), computed in one place and unit-tested.

Every comparison with an expiry date uses the owner's local `today`, never UTC (3.1).
"""

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
