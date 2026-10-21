"""What backups exist in the backup folder, read from file names only.

A backup database on `/backups` is never opened there (DATA_SAFETY 3); listing uses
names, sizes and times. `.partial` files are never listed (DATA_SAFETY 7).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

KINDS = ("pre-migration", "manual", "safety", "auto")
_STAMP = re.compile(r"-(\d{8}T\d{6}Z)$")


@dataclass(frozen=True)
class BackupEntry:
    name: str  # file name without ".sqlite3"
    kind: str
    at: datetime
    bytes: int


def kind_of(name: str) -> str | None:
    for kind in KINDS:
        if name.startswith(kind + "-"):
            return kind
    return None


def parse_stamp(name: str) -> datetime | None:
    match = _STAMP.search(name)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


def make_name(kind: str, stamp: str, *, from_version: int | None = None,
              to_version: int | None = None) -> str:
    if kind == "pre-migration":
        return f"pre-migration-v{from_version}-to-v{to_version}-{stamp}"
    return f"{kind}-{stamp}"


def list_backups(backups_dir: Path) -> list[BackupEntry]:
    """Finished backups, newest first. Unknown file names are ignored."""
    entries = []
    if not backups_dir.is_dir():
        return entries
    for path in backups_dir.iterdir():
        if not path.is_file() or not path.name.endswith(".sqlite3"):
            continue
        name = path.name[: -len(".sqlite3")]
        kind = kind_of(name)
        if kind is None:
            continue
        stat = path.stat()
        at = parse_stamp(name) or datetime.fromtimestamp(stat.st_mtime, UTC)
        entries.append(BackupEntry(name, kind, at, stat.st_size))
    return sorted(entries, key=lambda e: (e.at, e.name), reverse=True)
