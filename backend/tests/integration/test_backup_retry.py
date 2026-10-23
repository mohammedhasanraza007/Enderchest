"""A failing automatic backup is retried after a pause, not on every tick (failure kind F-025).

With no good backup since 03:00 local the daily rule stays due, so before this pause a backup
folder that refused every copy (disk full, folder gone read-only) got a full backup attempt and a
failed `backup_log` row every 30 s, all day.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app import clock
from app.backup.engine import BackupError
from app.scheduler import backups as scheduler_module
from app.scheduler.backups import RETRY_AFTER_FAILURE, BackupScheduler
from tests.conftest import Stack
from tests.integration.test_idle_backups import _zone_where_it_is_ten_in_the_morning

pytestmark = pytest.mark.integration


def test_the_pause_is_fifteen_minutes():
    assert RETRY_AFTER_FAILURE == timedelta(minutes=15)  # D-090


@pytest.fixture
def real_clock():
    yield
    clock.reset()


def test_a_failing_backup_waits_before_the_next_attempt(stack: Stack, real_clock, monkeypatch):
    conn = stack.manager.db()
    conn.execute("UPDATE users SET timezone = ? WHERE id = 1",
                 (_zone_where_it_is_ten_in_the_morning(),))
    attempts: list[str] = []

    def refuse(settings, kind, **_):
        attempts.append(kind)
        raise BackupError("the backup folder refused the copy")

    monkeypatch.setattr(scheduler_module, "create_backup", refuse)
    clock.set_now(datetime.now(UTC))
    scheduler = BackupScheduler(stack.manager)

    assert scheduler.tick() == "startup"  # the first attempt fails
    for _ in range(5):  # 2.5 minutes of ticks: still due ("daily"), but no new attempt
        clock.advance(30)
        assert scheduler.tick() is None
    assert attempts == ["auto"]

    clock.advance(RETRY_AFTER_FAILURE.total_seconds())
    assert scheduler.tick() == "daily"  # the pause is over: one more attempt
    assert attempts == ["auto", "auto"]


def test_a_success_clears_the_pause(stack: Stack, real_clock, monkeypatch):
    conn = stack.manager.db()
    conn.execute("UPDATE users SET timezone = ? WHERE id = 1",
                 (_zone_where_it_is_ten_in_the_morning(),))
    real_create = scheduler_module.create_backup
    fail_next = [True]

    def flaky(settings, kind, **kwargs):
        if fail_next[0]:
            fail_next[0] = False
            raise BackupError("one bad moment")
        return real_create(settings, kind, **kwargs)

    monkeypatch.setattr(scheduler_module, "create_backup", flaky)
    clock.set_now(datetime.now(UTC))
    scheduler = BackupScheduler(stack.manager)
    assert scheduler.tick() == "startup"  # fails
    clock.advance(RETRY_AFTER_FAILURE.total_seconds())
    assert scheduler.tick() == "daily"  # succeeds
    assert scheduler.tick() is None  # a good backup exists now; nothing is due
