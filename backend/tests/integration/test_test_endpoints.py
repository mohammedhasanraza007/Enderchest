"""Test-only endpoints (API.md 2.17): present on the test stack only, guarded by the marker."""

import time

import pytest

from app.config import Settings
from tests.conftest import Stack, make_database, state_keys

pytestmark = pytest.mark.integration


def test_they_do_not_exist_when_the_environment_is_live(settings: Settings):
    live = Settings(env="live", port=settings.port, data_dir=settings.data_dir,
                    backups_dir=settings.backups_dir, backup_dir_hint="x")
    with Stack(live) as stack:
        for path in ("/api/v1/test/clock", "/api/v1/test/write-loop"):
            assert stack.client.get(path).status_code == 404
        assert stack.post("/api/v1/test/reset").status_code == 404
    # and the live data was not touched by those attempts
    assert settings.db_path.exists()


def test_the_marker_is_checked_as_well_as_the_environment(settings: Settings):
    """A test-environment app must never act on a database that says it is live."""
    live = Settings(env="live", port=settings.port, data_dir=settings.data_dir,
                    backups_dir=settings.backups_dir, backup_dir_hint="x")
    make_database(live)
    with Stack(settings) as stack:  # env=test on a live-marked database: locked, so 503
        assert stack.client.get("/health").json()["reason"] == "env_mismatch"
        assert stack.post("/api/v1/test/reset").status_code == 503
    assert settings.db_path.exists()


def test_reset_wipes_the_test_data_and_starts_fresh(stack: Stack):
    stack.manager.db().execute("INSERT INTO scheduler_state VALUES ('junk', '1')")
    (stack.settings.photos_dir / "p.jpg").write_bytes(b"x")
    stack.post("/api/v1/backups")
    assert stack.post("/api/v1/test/reset").json() == {"state": "ok"}
    assert "junk" not in state_keys(stack.settings)
    assert not list(stack.settings.photos_dir.iterdir())
    assert not list(stack.settings.backups_dir.iterdir())
    assert stack.client.get("/health").json()["status"] == "ok"


def test_the_clock_can_be_set_and_advanced(stack: Stack):
    from app import clock

    try:
        got = stack.post("/api/v1/test/clock", {"now": "2026-12-31T20:00:00Z"}).json()
        assert got["now"].startswith("2026-12-31T20:00:0")
        assert got["local_date"] == "2026-12-31"  # the default user zone is UTC
        later = stack.post("/api/v1/test/clock", {"advance_seconds": 6 * 3600}).json()
        assert later["local_date"] == "2027-01-01"
        pinned = stack.post("/api/v1/test/clock", {"local_date": "2026-02-03"}).json()
        assert pinned["local_date"] == "2026-02-03"
        assert stack.client.get("/api/v1/test/clock").json()["local_date"] == "2026-02-03"
    finally:
        clock.reset()


def test_write_loop_keeps_every_record_whole(stack: Stack):
    assert stack.post("/api/v1/test/write-loop", {"seconds": 1}).json()["running"] is True
    time.sleep(1.5)
    report = stack.client.get("/api/v1/test/write-loop").json()
    assert report["running"] is False
    assert report["rows"] > 10 and report["consistent"] is True
    assert report["quick_check"] == "ok"


def test_write_loop_rejects_silly_durations(stack: Stack):
    assert stack.post("/api/v1/test/write-loop", {"seconds": 0}).status_code == 422
    assert stack.post("/api/v1/test/write-loop", {"seconds": 100000}).status_code == 422


def test_delete_db_leads_to_recovery_when_a_backup_exists(stack: Stack):
    stack.manager.db().execute("INSERT INTO scheduler_state VALUES ('precious', '1')")
    name = stack.post("/api/v1/backups").json()["name"]
    result = stack.post("/api/v1/test/delete-db").json()
    assert result == {"state": "recovery", "reason": "database_missing"}
    restored = stack.post("/api/v1/boot/restore", {"name": name, "confirm": "RESTORE"})
    assert restored.status_code == 200
    assert "precious" in state_keys(stack.settings)
