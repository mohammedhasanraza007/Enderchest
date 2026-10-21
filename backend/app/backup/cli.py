"""Command line for backups, run in a one-off container while the app is stopped.

    python -m app.backup.cli list
    python -m app.backup.cli restore <name>
    python -m app.backup.cli backup

`restore.bat` drives these (DATA_SAFETY 12). The restore asks for no confirmation here:
the script asks the owner to type RESTORE before it calls this.
"""

import sys

from ..boot.lock import InstanceLock
from ..boot.mounts import is_mount_point, is_writable
from ..config import load_settings
from ..db.connection import connect
from . import catalog
from .engine import BackupError, create_backup
from .restore import RestoreError, restore_backup


def main(argv: list[str]) -> int:
    settings = load_settings()
    if len(argv) < 1 or argv[0] not in ("list", "restore", "backup"):
        print("usage: python -m app.backup.cli list | restore <name> | backup", file=sys.stderr)
        return 2
    command = argv[0]

    if not is_mount_point(settings.data_dir) or not is_writable(settings.data_dir):
        print("The data volume is not connected. Nothing was changed.", file=sys.stderr)
        return 1
    if not is_mount_point(settings.backups_dir) or not is_writable(settings.backups_dir):
        print("The backup folder is not connected. Nothing was changed.", file=sys.stderr)
        return 1

    if command == "list":
        for number, entry in enumerate(catalog.list_backups(settings.backups_dir), start=1):
            # "|" separated so restore.bat can split the line with `for /f`
            print(f"{number}|{entry.name}|{entry.kind}|"
                  f"{entry.at.strftime('%Y-%m-%d %H:%M UTC')}|{entry.bytes}")
        return 0

    lock = InstanceLock(settings.lock_path)
    if not lock.acquire():
        print("Enderchest is running. Stop it first (stop.bat). Nothing was changed.",
              file=sys.stderr)
        return 1
    try:
        if command == "restore":
            if len(argv) != 2:
                print("usage: python -m app.backup.cli restore <name>", file=sys.stderr)
                return 2
            result = restore_backup(settings, argv[1])
            safety = result.safety_backup or "none (no database)"
            items = result.items if result.items is not None else "not counted yet"
            print(f"Restored {result.restored}. Items: {items}. "
                  f"Safety copy of the previous data: {safety}.")
            return 0
        conn = connect(settings.db_path)
        try:
            result = create_backup(settings, "manual", log_conn=conn)
        finally:
            conn.close()
        print(f"Backup {result.name}, {result.bytes} bytes, in {result.folder_hint}.")
        return 0
    except (RestoreError, BackupError) as exc:
        print(f"{exc} Nothing was lost.", file=sys.stderr)
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
