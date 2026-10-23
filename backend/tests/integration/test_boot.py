"""The boot sequence of DATA_SAFETY 4, 5 and 11 against real temporary folders."""

import sqlite3
from pathlib import Path

import pytest

from app.boot.manager import Status
from app.config import Settings
from app.db.migrate import supported_version
from tests.conftest import Stack, make_database, put_marker_row, state_keys

pytestmark = pytest.mark.integration


def health(stack: Stack) -> dict:
    return stack.client.get("/health").json()


def test_a_brand_new_volume_gets_a_database_with_marker_and_one_user(settings: Settings):
    with Stack(settings) as stack:
        assert health(stack)["status"] == "ok"
        conn = sqlite3.connect(settings.db_path)
        meta = dict(conn.execute("SELECT key, value FROM meta"))
        users = conn.execute("SELECT id, name FROM users").fetchall()
        conn.close()
    assert meta["env_marker"] == "test"
    assert meta["schema_version"] == str(supported_version())  # every migration applied
    assert {"created_at", "instance_id"} <= meta.keys()
    assert users == [(1, None)]


def test_a_second_start_keeps_the_data_and_does_not_recreate(settings: Settings):
    with Stack(settings) as first:
        first.manager.db().execute("INSERT INTO scheduler_state VALUES ('mine', '1')")
        instance = first.manager.db().execute(
            "SELECT value FROM meta WHERE key='instance_id'").fetchone()[0]
    with Stack(settings) as second:
        assert health(second)["status"] == "ok"
        assert second.manager.db().execute(
            "SELECT value FROM meta WHERE key='instance_id'").fetchone()[0] == instance
    assert "mine" in state_keys(settings)


def test_no_data_volume_locks_and_creates_nothing(settings: Settings):
    def only_backups_is_a_mount(path: Path) -> bool:
        return path == settings.backups_dir

    with Stack(settings, is_mount=only_backups_is_a_mount) as stack:
        body = health(stack)
        assert (body["status"], body["reason"]) == ("locked", "no_data_volume")
        assert stack.client.get("/api/v1/backups").status_code == 503
        assert stack.client.get("/api/v1/backups").json()["error"]["code"] == "locked"
    assert list(settings.data_dir.iterdir()) == []  # no db folder, no lock file, nothing


def test_a_missing_backup_folder_is_a_warning_not_a_failure(settings: Settings):
    with Stack(settings, is_mount=lambda p: p == settings.data_dir) as stack:
        assert health(stack)["status"] == "ok"
        boot = stack.client.get("/api/v1/boot").json()
        assert boot["backups_mounted"] is False
        assert boot["warnings"]
        assert stack.client.get("/api/v1/backups").json()["status"] == "unavailable"
        refused = stack.post("/api/v1/backups")
        assert (refused.status_code, refused.json()["error"]["code"]) == (503, "backup_unavailable")


def test_a_second_instance_is_locked_out(settings: Settings):
    with Stack(settings):
        with Stack(settings) as other:
            body = health(other)
            assert (body["status"], body["reason"]) == ("locked", "second_instance")


@pytest.mark.parametrize("stored, running", [("live", "test"), ("test", "live")])
def test_marker_mismatch_refuses_in_both_directions_and_writes_nothing(
        settings: Settings, stored: str, running: str):
    make_database(Settings(env=stored, port=settings.port, data_dir=settings.data_dir,
                           backups_dir=settings.backups_dir, backup_dir_hint="x"))
    before = settings.db_path.read_bytes()
    other = Settings(env=running, port=settings.port, data_dir=settings.data_dir,
                     backups_dir=settings.backups_dir, backup_dir_hint="x")
    with Stack(other) as stack:
        body = health(stack)
        assert (body["status"], body["reason"]) == ("locked", "env_mismatch")
        assert stack.client.get("/api/v1/backups").status_code == 503
    assert settings.db_path.read_bytes() == before


def test_a_newer_database_is_left_untouched(settings: Settings):
    make_database(settings)
    conn = sqlite3.connect(settings.db_path)
    conn.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    conn.commit()
    conn.close()
    before = settings.db_path.read_bytes()
    with Stack(settings) as stack:
        body = health(stack)
        found = (body["status"], body["reason"], body["schema_found"])
        assert found == ("locked", "newer_data", 99)
    assert settings.db_path.read_bytes() == before


def test_a_corrupt_database_goes_to_recovery_and_is_not_touched(settings: Settings):
    settings.db_path.parent.mkdir(parents=True)
    junk = b"definitely not sqlite" * 500
    settings.db_path.write_bytes(junk)
    with Stack(settings) as stack:
        body = health(stack)
        assert (body["status"], body["reason"]) == ("recovery", "corrupt")
    assert settings.db_path.read_bytes() == junk


def test_missing_database_with_photos_is_recovery_not_a_silent_new_database(settings: Settings):
    settings.photos_dir.mkdir(parents=True)
    (settings.photos_dir / "a.jpg").write_bytes(b"photo")
    with Stack(settings) as stack:
        assert health(stack)["reason"] == "database_missing"
    assert not settings.db_path.exists()


def test_missing_database_with_a_backup_is_recovery(settings: Settings):
    (settings.backups_dir / "auto-20261021T093000Z.sqlite3").write_bytes(b"x")
    with Stack(settings) as stack:
        body = stack.client.get("/api/v1/boot").json()
        assert (body["state"], body["reason"]) == ("recovery", "database_missing")
        assert [b["name"] for b in body["backups"]] == ["auto-20261021T093000Z"]
    assert not settings.db_path.exists()


def _assert_recovery_with_nothing_created(stack: Stack, settings: Settings) -> None:
    body = stack.client.get("/api/v1/boot").json()
    assert (body["state"], body["reason"]) == ("recovery", "database_missing")
    assert body["backups_mounted"] is False
    assert "backup folder" in body["message"]  # tells the owner what to fix, not just "restore"
    assert not settings.db_path.exists()


def test_a_backup_in_a_folder_that_is_not_a_mount_still_blocks_a_new_database(
        settings: Settings):
    # F-2 of the Phase 0 verification: the folder holds a backup but the container cannot treat
    # it as a mount. "Not connected" must never read as "no backups" (DATA_SAFETY 5).
    (settings.backups_dir / "auto-20261021T093000Z.sqlite3").write_bytes(b"x")
    with Stack(settings, is_mount=lambda p: p == settings.data_dir) as stack:
        _assert_recovery_with_nothing_created(stack, settings)


def test_a_backup_in_a_read_only_mount_still_blocks_a_new_database(
        settings: Settings, monkeypatch: pytest.MonkeyPatch):
    (settings.backups_dir / "auto-20261021T093000Z.sqlite3").write_bytes(b"x")
    monkeypatch.setattr("app.boot.manager.is_writable", lambda p: p != settings.backups_dir)
    with Stack(settings) as stack:  # both folders are mounts; only /backups is not writable
        _assert_recovery_with_nothing_created(stack, settings)


def test_a_stale_wal_without_a_database_is_recovery(settings: Settings):
    settings.db_path.parent.mkdir(parents=True)
    settings.db_path.with_name(settings.db_path.name + "-wal").write_bytes(b"stale")
    with Stack(settings) as stack:
        assert health(stack)["status"] == "recovery"


def test_start_empty_keeps_a_safety_copy_and_moves_the_old_file_aside(settings: Settings):
    settings.db_path.parent.mkdir(parents=True)
    junk = b"broken" * 300
    settings.db_path.write_bytes(junk)
    with Stack(settings) as stack:
        assert health(stack)["status"] == "recovery"
        refused = stack.post("/api/v1/boot/start-empty", {"confirm": "yes"})
        assert refused.status_code == 422
        done = stack.post("/api/v1/boot/start-empty", {"confirm": "START EMPTY"})
        assert done.json() == {"state": "ok"}
    safety = [p for p in settings.backups_dir.iterdir() if p.name.startswith("safety-")]
    assert len(safety) == 1 and safety[0].read_bytes() == junk
    aside = [p for p in settings.db_path.parent.iterdir() if "before-start-empty" in p.name]
    assert len(aside) == 1 and aside[0].read_bytes() == junk


def test_stale_partial_files_are_removed_at_startup(settings: Settings):
    settings.staging_dir.mkdir(parents=True)
    (settings.staging_dir / "x.sqlite3.partial").write_bytes(b"half")
    (settings.backups_dir / "auto-20261021T093000Z.sqlite3.partial").write_bytes(b"half")
    # a database with a real backup, so the partials are not what decides the first-run rule
    with Stack(settings) as stack:
        assert health(stack)["status"] == "ok"
    assert not list(settings.staging_dir.glob("*.partial"))
    assert not list(settings.backups_dir.glob("*.partial"))


def test_health_answers_200_in_every_state(settings: Settings):
    with Stack(settings, is_mount=lambda p: False) as stack:
        response = stack.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "locked"


def v1_database(settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a database at version 1 from a migrations folder holding only the real 0001.

    Returns that folder, still in use, so a test can add its own version 2 beside 0001.
    """
    from app.db import migrate

    folder = tmp_path / "migrations"
    folder.mkdir()
    (folder / "0001_foundation.sql").write_text(
        (migrate.MIGRATIONS_DIR / "0001_foundation.sql").read_text())
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", folder)
    make_database(settings)
    return folder


def test_a_pending_migration_makes_a_verified_backup_then_migrates(
        settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Build a realistic database at version 1 with a row in it.
    folder = v1_database(settings, tmp_path, monkeypatch)
    put_marker_row(settings, "kept-through-migration")

    # Add a version 2 migration (in the temporary folder beside the real 0001).
    (folder / "0002_add_note.sql").write_text(
        "CREATE TABLE note (id INTEGER PRIMARY KEY, body TEXT NOT NULL);")

    with Stack(settings) as stack:
        assert health(stack)["status"] == "ok"
        version = stack.manager.db().execute(
            "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        assert version == "2"
        log = stack.manager.db().execute(
            "SELECT kind, name, ok, verified FROM backup_log").fetchall()
    assert "kept-through-migration" in state_keys(settings)
    backups = [p.name for p in settings.backups_dir.iterdir()]
    assert any(n.startswith("pre-migration-v1-to-v2-") and n.endswith(".sqlite3") for n in backups)
    assert [(r[0], r[2], r[3]) for r in log] == [("pre-migration", 1, 1)]


def test_a_failing_migration_leaves_the_data_and_reports_the_backup(
        settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    folder = v1_database(settings, tmp_path, monkeypatch)
    put_marker_row(settings, "kept")
    (folder / "0002_bad.sql").write_text(
        "CREATE TABLE half (x INTEGER);\nINSERT INTO missing_table VALUES (1);")

    with Stack(settings) as stack:
        body = stack.client.get("/api/v1/boot").json()
        assert (body["state"], body["reason"]) == ("failed", "migration_failed")
        assert "pre-migration-v1-to-v2-" in body["message"]
    conn = sqlite3.connect(settings.db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    version = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
    conn.close()
    assert "half" not in tables and version == "1"
    assert "kept" in state_keys(settings)


def test_migration_without_a_backup_folder_is_refused_and_changes_nothing(
        settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    folder = v1_database(settings, tmp_path, monkeypatch)
    (folder / "0002_add_note.sql").write_text("CREATE TABLE note (id INTEGER PRIMARY KEY);")

    with Stack(settings, is_mount=lambda p: p == settings.data_dir) as stack:
        body = health(stack)
        assert (body["status"], body["reason"]) == ("failed", "backup_folder_unavailable")
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "1"
    conn.close()


def test_status_enum_is_what_the_contract_lists():
    assert {s.value for s in Status} == {"starting", "ok", "recovery", "locked", "failed"}


def test_the_real_inventory_migration_upgrades_a_named_v1_database(
        settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Phase 2: a Phase 1 database (owner named, a setting stored) gains the inventory tables."""
    from app.db import migrate

    real = migrate.MIGRATIONS_DIR
    folder = v1_database(settings, tmp_path, monkeypatch)
    conn = sqlite3.connect(settings.db_path)
    conn.execute("UPDATE users SET name = 'Mohammed', timezone = 'Asia/Kolkata' WHERE id = 1")
    conn.execute("INSERT INTO settings VALUES (1, 'lead_days', '5', '2026-10-01T00:00:00Z')")
    conn.commit()
    conn.close()
    (folder / "0002_inventory.sql").write_text((real / "0002_inventory.sql").read_text())

    with Stack(settings) as stack:
        assert health(stack)["status"] == "ok"
        profile = stack.client.get("/api/v1/profile").json()
        assert (profile["name"], profile["first_run_complete"]) == ("Mohammed", True)
        assert stack.client.get("/api/v1/settings").json()["lead_days"] == 5
        assert stack.client.get("/api/v1/items").json() == {"items": [], "next_cursor": None,
                                                            "total": 0}
    conn = sqlite3.connect(settings.db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"categories", "locations", "items", "photos", "drafts", "events"} <= tables
    assert conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "2"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()
    assert any(p.name.startswith("pre-migration-v1-to-v2-") for p in settings.backups_dir.iterdir())
