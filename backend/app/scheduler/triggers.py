"""When an automatic backup is due (D-052, DATA_SAFETY 7, "When").

Pure functions: the caller supplies the times, so each rule is unit-tested without waiting.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

STARTUP_MAX_AGE = timedelta(hours=6)
CHANGE_MIN_BACKUP_AGE = timedelta(hours=1)
CHANGE_QUIET_FOR = timedelta(minutes=5)
DAILY_AT = time(3, 0)


@dataclass(frozen=True)
class Facts:
    now: datetime  # UTC, from the app clock
    newest_backup_at: datetime | None  # when the newest good backup was started
    db_changed_at: datetime | None  # newest modification time of the database and its WAL
    startup_pending: bool  # the one start-up check has not run yet
    tz: ZoneInfo  # the owner's zone, for the daily 03:00 rule


def due(facts: Facts) -> str | None:
    """Return why a backup is due (`startup`, `daily`, `changed`) or None."""
    last = facts.newest_backup_at
    if facts.startup_pending and (last is None or facts.now - last > STARTUP_MAX_AGE):
        return "startup"

    local_now = facts.now.astimezone(facts.tz)
    today_3am = datetime.combine(local_now.date(), DAILY_AT, tzinfo=facts.tz)
    if local_now >= today_3am and (last is None or last < today_3am):
        return "daily"

    if facts.db_changed_at is not None and last is not None:
        changed_since = facts.db_changed_at > last
        old_enough = facts.now - last >= CHANGE_MIN_BACKUP_AGE
        quiet = facts.now - facts.db_changed_at >= CHANGE_QUIET_FOR
        if changed_since and old_enough and quiet:
            return "changed"
    return None
