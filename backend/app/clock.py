"""The one place that answers "what time is it" for app logic (ARCHITECTURE 6).

Only the test endpoints can move the clock, and they exist only on the test stack.
File timestamps and backup names use the real clock, never this one.
"""

import threading
import time
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

_lock = threading.Lock()
_fake_base: datetime | None = None
_real_base: float = 0.0


def now() -> datetime:
    with _lock:
        if _fake_base is None:
            return datetime.now(UTC)
        return _fake_base + timedelta(seconds=time.monotonic() - _real_base)


def local_date(tz_name: str) -> date:
    return now().astimezone(ZoneInfo(tz_name)).date()


def set_now(moment: datetime) -> None:
    global _fake_base, _real_base
    with _lock:
        _fake_base = moment.astimezone(UTC)
        _real_base = time.monotonic()


def advance(seconds: float) -> None:
    current = now()
    set_now(current + timedelta(seconds=seconds))


def set_local_date(day: date, tz_name: str) -> None:
    """Set the clock to noon on the given date in the given zone."""
    noon = datetime(day.year, day.month, day.day, 12, 0, tzinfo=ZoneInfo(tz_name))
    set_now(noon)


def reset() -> None:
    global _fake_base
    with _lock:
        _fake_base = None
