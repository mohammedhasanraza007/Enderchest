"""Which automatic backups to delete (DATA_SAFETY 7, Retention).

Keep: the newest 12 `auto-*`; the newest of each local day for the last 14 days; the
newest of each ISO week for the last 8 weeks; the newest 10 `pre-migration-*`.
Never delete `manual-*`, `safety-*`, or the newest backup of any kind.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .catalog import BackupEntry

KEEP_NEWEST_AUTO = 12
KEEP_DAYS = 14
KEEP_WEEKS = 8
KEEP_PRE_MIGRATION = 10


def _iso_week(day: date) -> tuple[int, int]:
    iso = day.isocalendar()
    return (iso.year, iso.week)


def plan_deletions(entries: list[BackupEntry], now: datetime, tz: ZoneInfo) -> list[BackupEntry]:
    newest_first = sorted(entries, key=lambda e: (e.at, e.name), reverse=True)
    autos = [e for e in newest_first if e.kind == "auto"]
    keep = {e.name for e in autos[:KEEP_NEWEST_AUTO]}

    today = now.astimezone(tz).date()
    day_floor = today - timedelta(days=KEEP_DAYS - 1)
    week_floor = _iso_week(today - timedelta(weeks=KEEP_WEEKS - 1))
    seen_days: set[date] = set()
    seen_weeks: set[tuple[int, int]] = set()
    for entry in autos:  # newest first, so the first seen per day or week is its newest
        local_day = entry.at.astimezone(tz).date()
        if local_day >= day_floor and local_day not in seen_days:
            seen_days.add(local_day)
            keep.add(entry.name)
        week = _iso_week(local_day)
        if week >= week_floor and week not in seen_weeks:
            seen_weeks.add(week)
            keep.add(entry.name)

    delete = [e for e in autos if e.name not in keep]
    pre_migration = [e for e in newest_first if e.kind == "pre-migration"]
    delete += pre_migration[KEEP_PRE_MIGRATION:]

    newest_any = newest_first[0].name if newest_first else None
    return [e for e in delete if e.name != newest_any]
