from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.backup.catalog import BackupEntry
from app.backup.retention import plan_deletions

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def entry(kind: str, when: datetime) -> BackupEntry:
    return BackupEntry(f"{kind}-{when.strftime('%Y%m%dT%H%M%SZ')}", kind, when, 1000)


def names(entries: list[BackupEntry]) -> set[str]:
    return {e.name for e in entries}


def test_keeps_the_newest_twelve_autos_and_deletes_dense_old_ones():
    # 40 autos, one every 30 minutes, ending an hour ago: all on the same two days.
    autos = [entry("auto", NOW - timedelta(hours=1, minutes=30 * i)) for i in range(40)]
    deleted = names(plan_deletions(autos, NOW, IST))
    newest_twelve = names(sorted(autos, key=lambda e: e.at, reverse=True)[:12])
    assert not deleted & newest_twelve
    assert deleted  # the dense middle of the same day is thinned out
    # the newest of each local day survives, so no day that had a backup is left empty
    survivors = [e for e in autos if e.name not in deleted]
    assert len({e.at.astimezone(IST).date() for e in survivors}) == len(
        {e.at.astimezone(IST).date() for e in autos})


def test_daily_and_weekly_keepers_for_a_long_history():
    # one auto backup per day for 120 days
    autos = [entry("auto", NOW - timedelta(days=d)) for d in range(120)]
    kept = [e for e in autos if e.name not in names(plan_deletions(autos, NOW, IST))]
    ages = [(NOW - e.at).days for e in kept]
    assert all(age in ages for age in range(0, 14))  # every day in the last 14 days
    assert max(ages) == 45  # the weekly window is this ISO week plus the 7 before it
    older = sorted(age for age in ages if age > 13)
    assert older == [17, 24, 31, 38, 45]  # exactly the newest backup of each older week


def test_manual_and_safety_backups_are_never_deleted():
    old = NOW - timedelta(days=400)
    entries = [entry("manual", old), entry("safety", old), entry("auto", NOW)]
    assert plan_deletions(entries, NOW, IST) == []


def test_pre_migration_keeps_the_newest_ten():
    pre = [entry("pre-migration", NOW - timedelta(days=i)) for i in range(13)]
    deleted = names(plan_deletions(pre, NOW, IST))
    assert deleted == names(sorted(pre, key=lambda e: e.at, reverse=True)[10:])


def test_day_boundaries_use_the_local_zone_not_utc():
    # 20:00 UTC on the 20th is 01:30 IST on the 21st: it belongs to the 21st locally, a day
    # that already has a newer keeper. Bucketed by UTC date it would wrongly be kept.
    late = entry("auto", datetime(2026, 10, 20, 20, 0, tzinfo=UTC))
    early = entry("auto", datetime(2026, 10, 21, 1, 0, tzinfo=UTC))
    filler = [entry("auto", NOW - timedelta(minutes=5 * i)) for i in range(13)]
    result = names(plan_deletions([late, early, *filler], NOW, IST))
    assert result == {late.name, early.name, filler[12].name}
