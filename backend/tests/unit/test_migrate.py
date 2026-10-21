import sqlite3
from pathlib import Path

import pytest

from app.db import migrate
from app.db.connection import connect


def test_the_shipped_migrations_are_numbered_without_gaps():
    found = migrate.available()
    assert [m.version for m in found] == list(range(1, len(found) + 1))
    assert migrate.supported_version() == len(found)


def test_split_statements_keeps_trigger_bodies_whole():
    sql = """
    -- a comment
    CREATE TABLE a (x INTEGER);
    CREATE TRIGGER t AFTER INSERT ON a BEGIN
        UPDATE a SET x = x + 1;
        DELETE FROM a WHERE x > 100;
    END;
    INSERT INTO a VALUES (1);
    """
    statements = migrate.split_statements(sql)
    assert len(statements) == 3
    assert statements[1].startswith("CREATE TRIGGER") and statements[1].endswith("END;")


def test_a_gap_in_the_numbering_is_refused(tmp_path: Path):
    (tmp_path / "0001_a.sql").write_text("CREATE TABLE a (x);")
    (tmp_path / "0003_c.sql").write_text("CREATE TABLE c (x);")
    with pytest.raises(migrate.MigrationError, match="gaps"):
        migrate.available(tmp_path)


def test_a_badly_named_file_is_refused(tmp_path: Path):
    (tmp_path / "add_stuff.sql").write_text("CREATE TABLE a (x);")
    with pytest.raises(migrate.MigrationError):
        migrate.available(tmp_path)


def test_a_failing_migration_rolls_back_completely(tmp_path: Path):
    folder = tmp_path / "m"
    folder.mkdir()
    (folder / "0001_ok.sql").write_text(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
    (folder / "0002_bad.sql").write_text(
        "CREATE TABLE half_made (x INTEGER);\nINSERT INTO no_such_table VALUES (1);")
    conn = connect(tmp_path / "db.sqlite3")
    with pytest.raises(migrate.MigrationError, match="0002_bad"):
        migrate.migrate(conn, folder)
    assert migrate.current_version(conn) == 1  # 0001 stayed, 0002 left no trace
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "half_made" not in tables
    conn.close()


def test_current_version_of_an_empty_database_is_zero(tmp_path: Path):
    conn = sqlite3.connect(tmp_path / "e.sqlite3")
    conn.row_factory = sqlite3.Row
    assert migrate.current_version(conn) == 0
    conn.close()
