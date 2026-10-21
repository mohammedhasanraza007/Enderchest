"""Is a folder a real mount point? (DATA_SAFETY 4, step 1)

A named volume or bind mount shows up in /proc/self/mountinfo. A plain folder in the
container layer does not, and writing the database there would lose it on rebuild.
"""

import os
from pathlib import Path

MOUNTINFO = Path("/proc/self/mountinfo")


def _decode(field: str) -> str:
    """mountinfo escapes space, tab, newline and backslash as octal (\\040 ...)."""
    out, i = [], 0
    while i < len(field):
        if field[i] == "\\" and field[i + 1 : i + 4].isdigit():
            out.append(chr(int(field[i + 1 : i + 4], 8)))
            i += 4
        else:
            out.append(field[i])
            i += 1
    return "".join(out)


def mount_points(mountinfo_text: str) -> set[str]:
    points = set()
    for line in mountinfo_text.splitlines():
        fields = line.split()
        if len(fields) > 4:
            points.add(_decode(fields[4]))
    return points


def is_mount_point(path: Path, mountinfo: Path = MOUNTINFO) -> bool:
    try:
        target = str(path.resolve())
        return target in mount_points(mountinfo.read_text(encoding="utf-8"))
    except OSError:
        return os.path.ismount(path)


def is_writable(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK | os.X_OK)
