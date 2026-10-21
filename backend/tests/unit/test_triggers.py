from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.scheduler.triggers import Facts, due

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)  # 15:30 IST, after 03:00


def facts(**overrides) -> Facts:
    base = dict(now=NOW, newest_backup_at=NOW - timedelta(minutes=30), db_changed_at=None,
                startup_pending=False, tz=IST)
    base.update(overrides)
    return Facts(**base)


def test_startup_backup_when_the_newest_is_over_six_hours_old():
    assert due(facts(startup_pending=True, newest_backup_at=NOW - timedelta(hours=7))) == "startup"


def test_no_startup_backup_when_the_newest_is_recent():
    # also past 03:00 with a backup today, so nothing else fires either
    assert due(facts(startup_pending=True, newest_backup_at=NOW - timedelta(hours=5))) is None


def test_startup_backup_when_none_exists():
    assert due(facts(startup_pending=True, newest_backup_at=None)) == "startup"


def test_startup_rule_runs_only_once():
    assert due(facts(startup_pending=False, newest_backup_at=NOW - timedelta(hours=7),
                     db_changed_at=None)) is None


def test_after_changes_needs_change_age_and_quiet():
    last = NOW - timedelta(hours=2)
    changed = NOW - timedelta(minutes=10)
    assert due(facts(newest_backup_at=last, db_changed_at=changed)) == "changed"


def test_after_changes_waits_for_five_quiet_minutes():
    last = NOW - timedelta(hours=2)
    assert due(facts(newest_backup_at=last, db_changed_at=NOW - timedelta(minutes=2))) is None


def test_after_changes_waits_until_the_last_backup_is_an_hour_old():
    last = NOW - timedelta(minutes=40)
    assert due(facts(newest_backup_at=last, db_changed_at=NOW - timedelta(minutes=10))) is None


def test_no_backup_when_nothing_changed_since_the_last_one():
    last = NOW - timedelta(hours=2)
    assert due(facts(newest_backup_at=last, db_changed_at=last - timedelta(minutes=5))) is None


def test_daily_backup_after_three_am_local_when_none_yet_today():
    yesterday_evening = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)  # 20:30 IST yesterday
    assert due(facts(newest_backup_at=yesterday_evening)) == "daily"


def test_daily_backup_not_before_three_am_local():
    two_am_ist = datetime(2026, 10, 20, 20, 30, tzinfo=UTC)  # 02:00 IST on the 21st
    yesterday = two_am_ist - timedelta(hours=8)
    assert due(facts(now=two_am_ist, newest_backup_at=yesterday)) is None


def test_daily_backup_not_repeated_once_one_ran_after_three_am():
    after_three = datetime(2026, 10, 20, 22, 0, tzinfo=UTC)  # 03:30 IST on the 21st
    assert due(facts(newest_backup_at=after_three)) is None
