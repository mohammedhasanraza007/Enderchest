"""Derived values (DATA_MODEL 3), computed in one place and unit-tested.

Every comparison with an expiry date uses the owner's local `today`, never UTC (3.1).
"""

from datetime import date


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
