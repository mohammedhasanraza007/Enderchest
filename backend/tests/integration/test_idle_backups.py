"""A backup's own log row must not count as "the database changed" (Phase 0 verification, F-4).

DATA_SAFETY 7: an automatic backup follows a change. Every backup writes a `backup_log` row after
it starts; if that write counted as a change, an idle database would be backed up every hour.
"""

import time
from datetime import UTC, datetime, timedelta

import pytest

from app import clock
from app.backup import engine
from app.scheduler.backups import BackupScheduler
from tests.conftest import Stack

pytestmark = pytest.mark.integration


def _zone_where_it_is_ten_in_the_morning() -> str:
    """A fixed-offset zone, so the daily 03:00 rule cannot fire whatever time the test runs."""
    offset = ((10 - datetime.now(UTC).hour + 11) % 24) - 11  # hours east of UTC, -11 to 12
    if offset == 0:
        return "Etc/GMT"
    return f"Etc/GMT{'-' if offset > 0 else '+'}{abs(offset)}"  # the sign is inverted in tzdata


@pytest.fixture
def real_clock():
    yield
    clock.reset()


def test_an_idle_database_is_not_backed_up_again_but_a_real_write_is(stack: Stack, real_clock):
    conn = stack.manager.db()
    zone = _zone_where_it_is_ten_in_the_morning()
    conn.execute("UPDATE users SET timezone = ? WHERE id = 1", (zone,))
    started = datetime.now(UTC)
    engine.create_backup(stack.settings, "manual", log_conn=conn)

    clock.set_now(started + timedelta(minutes=90))  # old enough for the "changed" rule
    scheduler = BackupScheduler(stack.manager)
    assert scheduler.tick() is None  # nothing changed except the backup's own log row

    assert engine.changed_since_own_write(stack.settings) is None
    time.sleep(0.05)  # file times have a coarse tick; make the real write clearly later
    conn.execute("INSERT OR REPLACE INTO scheduler_state VALUES ('a-real-change', '1')")
    assert engine.changed_since_own_write(stack.settings) is not None
    assert scheduler.tick() == "changed"

    assert scheduler.tick() is None  # and that backup's own log row is ignored in turn
