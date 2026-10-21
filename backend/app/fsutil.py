"""Small file helpers: atomic copy, checksum, fsync, move aside (never delete)."""

import hashlib
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_path(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_dir(path: Path) -> None:
    """Flush a directory entry; some bind mounts refuse it, which is not an error."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def copy_atomic(source: Path, destination: Path) -> None:
    """Copy to `<destination>.partial`, fsync, then rename into place."""
    partial = destination.with_name(destination.name + ".partial")
    shutil.copyfile(source, partial)
    fsync_path(partial)
    os.replace(partial, destination)
    fsync_dir(destination.parent)


def move_aside(path: Path, label: str, stamp: str) -> Path | None:
    """Rename `path` to `<name>.<label>-<stamp>`; return the new path or None if absent."""
    if not path.exists():
        return None
    target = path.with_name(f"{path.name}.{label}-{stamp}")
    os.replace(path, target)
    return target


def remove_partials(directory: Path) -> list[str]:
    """Delete stale `.partial` files (never a finished backup); return their names."""
    removed = []
    if not directory.is_dir():
        return removed
    for path in directory.iterdir():
        if path.is_file() and path.name.endswith(".partial"):
            path.unlink()
            removed.append(path.name)
    return removed
