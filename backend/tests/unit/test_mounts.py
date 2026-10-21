from pathlib import Path

from app.boot.mounts import is_mount_point, mount_points

# Real mountinfo lines: field 5 is the mount point, with spaces written as \040.
SAMPLE = """\
36 35 98:0 /mnt1 /mnt2 rw,noatime master:1 - ext3 /dev/root rw,errors=continue
710 700 0:62 / /data rw,relatime - ext4 /dev/sdc rw
711 700 0:63 / /backups rw,relatime - 9p drvfs rw
712 700 0:64 / /with\\040space rw - tmpfs tmpfs rw
"""


def test_mount_points_reads_field_five_and_decodes_escapes():
    assert mount_points(SAMPLE) == {"/mnt2", "/data", "/backups", "/with space"}


def test_a_mounted_folder_is_recognised(tmp_path: Path):
    info = tmp_path / "mountinfo"
    info.write_text(SAMPLE)
    folder = tmp_path / "x"
    folder.mkdir()
    info.write_text(f"1 0 0:1 / {folder.resolve()} rw - ext4 /dev/x rw\n")
    assert is_mount_point(folder, mountinfo=info)


def test_a_plain_folder_in_the_container_layer_is_not_a_mount(tmp_path: Path):
    info = tmp_path / "mountinfo"
    info.write_text(SAMPLE)
    folder = tmp_path / "data"
    folder.mkdir()
    assert not is_mount_point(folder, mountinfo=info)


def test_unreadable_mountinfo_falls_back_to_ismount(tmp_path: Path):
    # A plain folder is not a mount point, so the fallback says no (and never raises).
    assert not is_mount_point(tmp_path, mountinfo=tmp_path / "missing")
