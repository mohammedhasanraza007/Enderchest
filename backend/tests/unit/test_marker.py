import sqlite3
from pathlib import Path

from app.boot.marker import matches, read_marker


def make_db(path: Path, marker: str | None) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    if marker is not None:
        conn.execute("INSERT INTO meta VALUES ('env_marker', ?)", (marker,))
    conn.commit()
    conn.close()


def test_reads_the_stored_marker(tmp_path: Path):
    make_db(tmp_path / "a.sqlite3", "test")
    assert read_marker(tmp_path / "a.sqlite3") == "test"


def test_missing_marker_row_reads_as_none(tmp_path: Path):
    make_db(tmp_path / "a.sqlite3", None)
    assert read_marker(tmp_path / "a.sqlite3") is None


def test_a_file_that_is_not_a_database_reads_as_none(tmp_path: Path):
    (tmp_path / "junk.sqlite3").write_bytes(b"this is not sqlite" * 100)
    assert read_marker(tmp_path / "junk.sqlite3") is None


def test_reading_never_writes_to_the_file(tmp_path: Path):
    path = tmp_path / "a.sqlite3"
    make_db(path, "live")
    before = path.read_bytes()
    read_marker(path)
    assert path.read_bytes() == before


def test_a_different_marker_does_not_match_but_a_missing_one_is_left_to_quick_check():
    assert matches("live", "live")
    assert not matches("test", "live")
    assert not matches("live", "test")
    assert matches(None, "live")
