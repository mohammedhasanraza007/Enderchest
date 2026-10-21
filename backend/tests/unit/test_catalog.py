from datetime import UTC, datetime
from pathlib import Path

from app.backup import catalog
from app.fsutil import remove_partials


def test_names_follow_the_contract():
    stamp = "20261021T093000Z"
    assert catalog.make_name("auto", stamp) == "auto-20261021T093000Z"
    assert catalog.make_name("manual", stamp) == "manual-20261021T093000Z"
    assert catalog.make_name("safety", stamp) == "safety-20261021T093000Z"
    assert (catalog.make_name("pre-migration", stamp, from_version=1, to_version=2)
            == "pre-migration-v1-to-v2-20261021T093000Z")


def test_kind_and_time_are_read_back_from_the_name():
    name = "pre-migration-v1-to-v2-20261021T093000Z"
    assert catalog.kind_of(name) == "pre-migration"
    assert catalog.parse_stamp(name) == datetime(2026, 10, 21, 9, 30, tzinfo=UTC)
    assert catalog.kind_of("something-else") is None


def test_listing_never_includes_partial_or_unknown_files(tmp_path: Path):
    (tmp_path / "auto-20261021T093000Z.sqlite3").write_bytes(b"x" * 10)
    (tmp_path / "manual-20261021T100000Z.sqlite3").write_bytes(b"x" * 20)
    (tmp_path / "auto-20261021T110000Z.sqlite3.partial").write_bytes(b"half")
    (tmp_path / "safety-20261021T120000Z.sqlite3-wal").write_bytes(b"wal")
    (tmp_path / "notes.sqlite3").write_bytes(b"not a backup name")
    (tmp_path / "photos").mkdir()
    listed = [e.name for e in catalog.list_backups(tmp_path)]
    assert listed == ["manual-20261021T100000Z", "auto-20261021T093000Z"]  # newest first


def test_remove_partials_deletes_only_partial_files(tmp_path: Path):
    keep = tmp_path / "auto-20261021T093000Z.sqlite3"
    keep.write_bytes(b"done")
    (tmp_path / "auto-20261021T110000Z.sqlite3.partial").write_bytes(b"half")
    (tmp_path / "x.jpg.partial").write_bytes(b"half")
    removed = remove_partials(tmp_path)
    assert sorted(removed) == ["auto-20261021T110000Z.sqlite3.partial", "x.jpg.partial"]
    assert keep.exists()
    assert [p.name for p in tmp_path.iterdir()] == [keep.name]
