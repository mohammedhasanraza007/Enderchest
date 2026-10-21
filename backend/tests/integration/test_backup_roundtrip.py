"""Backup then restore through the real API, including the recovery page's path."""

import hashlib
import sqlite3

import pytest

from app.config import Settings
from tests.conftest import Stack, state_keys

pytestmark = pytest.mark.integration


def write(stack: Stack, key: str) -> None:
    stack.manager.db().execute("INSERT OR REPLACE INTO scheduler_state VALUES (?, '1')", (key,))


def test_post_backups_makes_a_verified_file_and_logs_it(stack: Stack):
    write(stack, "before-backup")
    response = stack.post("/api/v1/backups")
    assert response.status_code == 201
    body = response.json()
    assert body["verified"] is True and body["bytes"] > 0
    path = stack.settings.backups_dir / f"{body['name']}.sqlite3"
    assert path.exists() and path.stat().st_size == body["bytes"]
    assert not list(stack.settings.backups_dir.glob("*.partial"))
    assert not list(stack.settings.staging_dir.glob("*"))  # staged copy is cleaned up

    listing = stack.client.get("/api/v1/backups").json()
    assert listing["status"] == "ok"
    assert listing["last_good"]["name"] == body["name"]
    assert [i["name"] for i in listing["items"]] == [body["name"]]
    assert listing["items"][0]["kind"] == "manual"


def test_the_backup_file_is_a_complete_copy_with_the_data(stack: Stack):
    write(stack, "in-the-backup")
    name = stack.post("/api/v1/backups").json()["name"]
    conn = sqlite3.connect(stack.settings.backups_dir / f"{name}.sqlite3")
    assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    assert conn.execute("SELECT 1 FROM scheduler_state WHERE key='in-the-backup'").fetchone()
    conn.close()


def test_photos_are_mirrored_incrementally_and_never_overwritten(stack: Stack):
    photos = stack.settings.photos_dir
    (photos / "a.jpg").write_bytes(b"first photo")
    stack.post("/api/v1/backups")
    mirror = stack.settings.backup_photos_dir
    assert (mirror / "a.jpg").read_bytes() == b"first photo"

    (photos / "b.jpg").write_bytes(b"second photo")
    (photos / "a.jpg").write_bytes(b"changed on disk!")  # photos are immutable; this is an anomaly
    stack.post("/api/v1/backups")
    assert (mirror / "b.jpg").read_bytes() == b"second photo"
    assert (mirror / "a.jpg").read_bytes() == b"first photo"  # reported, not overwritten


def test_delete_database_then_restore_from_the_recovery_state(settings: Settings):
    photo = b"a precious photo"
    with Stack(settings) as stack:
        write(stack, "item-1")
        write(stack, "item-2")
        (settings.photos_dir / "p.jpg").write_bytes(photo)
        name = stack.post("/api/v1/backups").json()["name"]

    # The database vanishes (Docker reset, deleted volume contents ...); photos are gone too.
    for suffix in ("", "-wal", "-shm"):
        settings.db_path.with_name(settings.db_path.name + suffix).unlink(missing_ok=True)
    (settings.photos_dir / "p.jpg").unlink()

    with Stack(settings) as stack:
        boot = stack.client.get("/api/v1/boot").json()
        assert (boot["state"], boot["reason"]) == ("recovery", "database_missing")
        assert boot["backups"][0]["name"] == name
        assert stack.client.get("/api/v1/backups").status_code == 503  # API is locked

        wrong = stack.post("/api/v1/boot/restore", {"name": name, "confirm": "restore"})
        assert wrong.status_code == 422  # confirmation must be typed exactly

        done = stack.post("/api/v1/boot/restore", {"name": name, "confirm": "RESTORE"})
        assert done.status_code == 200 and done.json()["restored"] == name
        assert stack.client.get("/health").json()["status"] == "ok"
        assert {"item-1", "item-2"} <= state_keys(settings)
    assert (settings.photos_dir / "p.jpg").read_bytes() == photo
    assert (hashlib.sha256((settings.photos_dir / "p.jpg").read_bytes()).hexdigest()
            == hashlib.sha256(photo).hexdigest())


def test_restore_is_only_allowed_in_the_recovery_state(stack: Stack):
    name = stack.post("/api/v1/backups").json()["name"]
    refused = stack.post("/api/v1/boot/restore", {"name": name, "confirm": "RESTORE"})
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "conflict")
    refused = stack.post("/api/v1/boot/start-empty", {"confirm": "START EMPTY"})
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "conflict")


def test_restoring_a_name_that_does_not_exist_changes_nothing(settings: Settings):
    (settings.backups_dir / "auto-20261021T093000Z.sqlite3").write_bytes(b"x")
    with Stack(settings) as stack:
        assert stack.client.get("/health").json()["status"] == "recovery"
        missing = stack.post("/api/v1/boot/restore",
                             {"name": "auto-20260101T000000Z", "confirm": "RESTORE"})
        assert (missing.status_code, missing.json()["error"]["code"]) == (409, "conflict")
        assert stack.client.get("/health").json()["status"] == "recovery"


def test_status_becomes_failing_after_two_failed_backups(stack: Stack):
    for _ in range(2):
        stack.manager.db().execute(
            "INSERT INTO backup_log (kind, name, started_at, finished_at, ok, error, bytes, "
            "item_count, verified) VALUES ('auto', 'x', '2026-10-21T00:00:00Z', "
            "'2026-10-21T00:00:01Z', 0, 'boom', 0, NULL, 0)")
    assert stack.client.get("/api/v1/backups").json()["status"] == "failing"


def test_status_becomes_stale_after_seven_days(stack: Stack):
    stack.manager.db().execute(
        "INSERT INTO backup_log (kind, name, started_at, finished_at, ok, error, bytes, "
        "item_count, verified) VALUES ('auto', 'old', '2020-01-01T00:00:00Z', "
        "'2020-01-01T00:00:01Z', 1, NULL, 10, NULL, 1)")
    assert stack.client.get("/api/v1/backups").json()["status"] == "stale"
