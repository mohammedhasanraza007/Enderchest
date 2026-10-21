"""The restore procedure of DATA_SAFETY 12: step order, and the stale WAL never survives."""

import os
import sqlite3
from pathlib import Path

import pytest

from app.backup import restore
from app.backup.engine import create_backup
from app.backup.restore import RestoreError, restore_backup
from app.config import Settings
from app.db.connection import connect
from tests.conftest import make_database, put_marker_row, state_keys


def build_backup_of(settings: Settings, tmp_path: Path, marker_key: str) -> str:
    """Make a real backup file from a separate database holding one distinctive row."""
    other = Settings(env=settings.env, port=settings.port, data_dir=tmp_path / "other-data",
                     backups_dir=settings.backups_dir, backup_dir_hint="x")
    other.data_dir.mkdir()
    make_database(other)
    put_marker_row(other, marker_key)
    conn = connect(other.db_path)
    try:
        return create_backup(other, "manual", log_conn=conn).name
    finally:
        conn.close()


def test_restore_moves_the_old_database_and_its_wal_aside_before_the_new_file_goes_in(
        settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    make_database(settings)
    put_marker_row(settings, "only-in-old-database")
    # Keep a connection open with auto-checkpoint off, so the old database really has a -wal.
    old = connect(settings.db_path)
    old.execute("PRAGMA wal_autocheckpoint=0")
    old.execute("INSERT INTO scheduler_state (key, value) VALUES ('in-the-wal', '1')")
    wal = settings.db_path.with_name(settings.db_path.name + "-wal")
    assert wal.exists() and wal.stat().st_size > 0

    name = build_backup_of(settings, tmp_path, "only-in-backup")

    events: list[str] = []
    real_move, real_replace, real_safety = restore.move_aside, os.replace, restore.create_backup

    def spy_move(path, label, stamp):
        events.append(f"aside:{path.name}")
        return real_move(path, label, stamp)

    def spy_replace(src, dst):
        if Path(dst) == settings.db_path:
            events.append("put-new-database")
        return real_replace(src, dst)

    def spy_safety(*args, **kwargs):
        events.append("safety-backup")
        return real_safety(*args, **kwargs)

    monkeypatch.setattr(restore, "move_aside", spy_move)
    monkeypatch.setattr(restore.os, "replace", spy_replace)
    monkeypatch.setattr(restore, "create_backup", spy_safety)

    result = restore_backup(settings, name)
    old.close()

    assert events == ["safety-backup", "aside:enderchest.sqlite3", "aside:enderchest.sqlite3-wal",
                      "aside:enderchest.sqlite3-shm", "put-new-database"]
    assert result.safety_backup is not None
    assert (settings.backups_dir / f"{result.safety_backup}.sqlite3").exists()

    # The old files are kept under new names, never deleted.
    aside = sorted(p.name for p in settings.db_path.parent.iterdir() if "before-restore" in p.name)
    assert len(aside) == 3
    assert any(n.startswith("enderchest.sqlite3-wal.before-restore") for n in aside)

    # The restored database is the backup's, and no stale WAL sits beside it.
    keys = state_keys(settings)
    assert "only-in-backup" in keys
    assert "only-in-old-database" not in keys and "in-the-wal" not in keys
    leftovers = {p.name for p in settings.db_path.parent.iterdir()
                 if p.name.startswith("enderchest.sqlite3") and "before-restore" not in p.name}
    assert leftovers <= {"enderchest.sqlite3", "enderchest.sqlite3-wal", "enderchest.sqlite3-shm"}


def test_the_safety_backup_holds_what_was_there_before(settings: Settings, tmp_path: Path):
    make_database(settings)
    put_marker_row(settings, "only-in-old-database")
    name = build_backup_of(settings, tmp_path, "only-in-backup")
    result = restore_backup(settings, name)

    safety = settings.backups_dir / f"{result.safety_backup}.sqlite3"
    check = sqlite3.connect(safety)
    keys = {r[0] for r in check.execute("SELECT key FROM scheduler_state")}
    check.close()
    assert "only-in-old-database" in keys


def test_restore_without_any_current_database_makes_no_safety_backup(settings: Settings,
                                                                     tmp_path: Path):
    name = build_backup_of(settings, tmp_path, "only-in-backup")
    result = restore_backup(settings, name)
    assert result.safety_backup is None
    assert "only-in-backup" in state_keys(settings)


def test_a_corrupt_current_database_gets_a_raw_safety_copy(settings: Settings, tmp_path: Path):
    settings.db_path.parent.mkdir(parents=True)
    settings.db_path.write_bytes(b"not a database" * 200)
    name = build_backup_of(settings, tmp_path, "only-in-backup")
    result = restore_backup(settings, name)
    raw = settings.backups_dir / f"{result.safety_backup}.sqlite3"
    assert raw.read_bytes() == b"not a database" * 200


@pytest.mark.parametrize("bad", ["../etc/passwd", "auto-1/../../x", "", "random-name"])
def test_unsafe_or_unknown_names_are_refused_before_anything_changes(settings: Settings, bad):
    make_database(settings)
    before = settings.db_path.read_bytes()
    with pytest.raises(RestoreError):
        restore_backup(settings, bad)
    assert settings.db_path.read_bytes() == before


def test_a_name_ending_in_a_newline_is_not_a_backup_name(settings: Settings):
    # F-3 of the Phase 0 verification: `$` matches before a trailing newline, so the name
    # check must use fullmatch. The refusal has to come from the name check itself.
    make_database(settings)
    with pytest.raises(RestoreError, match="not a backup name"):
        restore_backup(settings, "auto-20261021T093000Z\n")


def test_a_backup_from_another_environment_is_refused(settings: Settings, tmp_path: Path):
    live = Settings(env="live", port=8470, data_dir=tmp_path / "live-data",
                    backups_dir=settings.backups_dir, backup_dir_hint="x")
    live.data_dir.mkdir()
    make_database(live)
    conn = connect(live.db_path)
    name = create_backup(live, "manual", log_conn=conn).name
    conn.close()
    make_database(settings)
    before = settings.db_path.read_bytes()
    with pytest.raises(RestoreError, match="environment"):
        restore_backup(settings, name)
    assert settings.db_path.read_bytes() == before


def test_a_backup_from_a_newer_version_is_refused(settings: Settings, tmp_path: Path):
    name = build_backup_of(settings, tmp_path, "x")
    conn = sqlite3.connect(settings.backups_dir / f"{name}.sqlite3")
    conn.execute("UPDATE meta SET value = '999' WHERE key = 'schema_version'")
    conn.commit()
    conn.close()
    with pytest.raises(RestoreError, match="newer"):
        restore_backup(settings, name)
