"""Phase 0 verification: adversarial in-process checks, run inside the tools image.

Uses only temporary folders. Nothing here touches any volume or the backup folder.
"""
import os
import random
import re
import shutil
import sqlite3
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.backup import catalog
from app.backup.restore import _SAFE_NAME, RestoreError, restore_backup
from app.backup.retention import plan_deletions
from app.boot.manager import BootManager
from app.config import load_settings
from app.db import migrate
from app.db.connection import connect
from app.scheduler.triggers import Facts, due

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + detail if detail else ""))
    if not ok:
        FAILS.append(name)


# ---------------------------------------------------------------- V3 migration atomicity
tmp = Path(tempfile.mkdtemp())
mig = tmp / "mig"
mig.mkdir()
first = next(Path(migrate.MIGRATIONS_DIR).glob("0001_*.sql"))
shutil.copy(first, mig / first.name)
(mig / "0002_bad.sql").write_text(
    "CREATE TABLE half_done (x INTEGER);\n"
    "INSERT INTO half_done VALUES (1);\n"
    "CREATE TABLE half_done (x INTEGER);\n"  # fails: already exists
)
conn = connect(tmp / "t.sqlite3")
try:
    migrate.migrate(conn, mig)
    check("V3 failing migration raises MigrationError", False, "no error raised")
except migrate.MigrationError as exc:
    check("V3 failing migration raises MigrationError", True, str(exc)[:70])
tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
check("V3 nothing from the failed migration remains", "half_done" not in tables)
check("V3 schema_version still 1", migrate.current_version(conn) == 1)
check("V3 no transaction left open", not conn.in_transaction)
conn.close()

# a migration that holds a trigger body must stay whole
(mig / "0002_bad.sql").unlink()
(mig / "0002_trigger.sql").write_text(
    "CREATE TABLE t1 (a INTEGER);\nCREATE TABLE t2 (a INTEGER);\n"
    "CREATE TRIGGER t1_ai AFTER INSERT ON t1 BEGIN\n  INSERT INTO t2 VALUES (new.a);\n"
    "  INSERT INTO t2 VALUES (new.a);\nEND;\n"
)
conn = connect(tmp / "t.sqlite3")
check("V3 trigger migration applies", migrate.migrate(conn, mig) == [2])
conn.execute("INSERT INTO t1 VALUES (7)")
check("V3 trigger body kept whole (2 rows)", conn.execute("SELECT COUNT(*) FROM t2").fetchone()[0] == 2)
conn.close()

# ---------------------------------------------------------------- V9 retention, independent re-derivation
def reference_keep(entries, now, tz):
    """My own reading of DATA_SAFETY 7: newest 12 auto; newest auto per local day for 14 days;
    newest auto per ISO week for 8 weeks; newest 10 pre-migration; never manual/safety/newest."""
    autos = sorted([e for e in entries if e.kind == "auto"], key=lambda e: (e.at, e.name),
                   reverse=True)
    keep = {e.name for e in autos[:12]}
    today = now.astimezone(tz).date()
    for back in range(14):
        day = today - timedelta(days=back)
        for e in autos:
            if e.at.astimezone(tz).date() == day:
                keep.add(e.name)
                break
    this_week = today.isocalendar()
    monday = today - timedelta(days=today.weekday())
    for back in range(8):
        start = monday - timedelta(weeks=back)
        days = {start + timedelta(days=i) for i in range(7)}
        for e in autos:
            if e.at.astimezone(tz).date() in days:
                keep.add(e.name)
                break
    pre = sorted([e for e in entries if e.kind == "pre-migration"], key=lambda e: (e.at, e.name),
                 reverse=True)
    keep |= {e.name for e in pre[:10]}
    newest = max(entries, key=lambda e: (e.at, e.name)) if entries else None
    delete = {e.name for e in entries if e.kind in ("auto", "pre-migration") and e.name not in keep}
    if newest:
        delete.discard(newest.name)
    return delete


def mk(kind, at):
    stamp = at.strftime("%Y%m%dT%H%M%SZ")
    return catalog.BackupEntry(catalog.make_name(kind, stamp, from_version=1, to_version=2)
                               if kind == "pre-migration" else f"{kind}-{stamp}", kind, at, 100)


random.seed(20261021)
mismatch = 0
protected_violation = 0
for trial in range(400):
    tz = ZoneInfo(random.choice(["UTC", "Asia/Kolkata", "America/New_York", "Pacific/Auckland",
                                 "Europe/London"]))
    now = datetime(2026, 10, 21, 16, 0, tzinfo=UTC) + timedelta(minutes=random.randint(0, 3000))
    entries = []
    for _ in range(random.randint(0, 90)):
        at = now - timedelta(minutes=random.randint(0, 60 * 24 * 130))
        entries.append(mk(random.choice(["auto"] * 6 + ["manual", "safety", "pre-migration"]), at))
    entries = list({e.name: e for e in entries}.values())
    got = {e.name for e in plan_deletions(entries, now, tz)}
    want = reference_keep(entries, now, tz)
    if got != want:
        mismatch += 1
    if any(n.startswith(("manual-", "safety-")) for n in got):
        protected_violation += 1
check("V9 retention equals an independent reading over 400 random sets", mismatch == 0,
      f"{mismatch} sets differ")
check("V9 manual and safety backups never planned for deletion", protected_violation == 0)

# ---------------------------------------------------------------- V9 triggers
UTC_TZ = ZoneInfo("UTC")
IST = ZoneInfo("Asia/Kolkata")
t0 = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
check("V9 startup, no backup yet", due(Facts(t0, None, None, True, UTC_TZ)) == "startup")
check("V9 startup skipped when last backup is 1 h old",
      due(Facts(t0, t0 - timedelta(hours=1), None, True, UTC_TZ)) is None)
check("V9 changed after 2 h + quiet",
      due(Facts(t0, t0 - timedelta(hours=2), t0 - timedelta(hours=1), False, UTC_TZ)) == "changed")
check("V9 not changed when the db is older than the backup",
      due(Facts(t0, t0 - timedelta(hours=2), t0 - timedelta(hours=3), False, UTC_TZ)) is None)
check("V9 not changed inside the 1 h minimum",
      due(Facts(t0, t0 - timedelta(minutes=30), t0 - timedelta(minutes=20), False, UTC_TZ)) is None)
check("V9 not changed while writes are recent (< 5 min quiet)",
      due(Facts(t0, t0 - timedelta(hours=2), t0 - timedelta(minutes=2), False, UTC_TZ)) is None)
ist_3am = datetime(2026, 10, 22, 3, 5, tzinfo=IST).astimezone(UTC)
check("V9 daily at 03:05 IST when last backup was yesterday evening",
      due(Facts(ist_3am, ist_3am - timedelta(hours=5), None, False, IST)) == "daily")
check("V9 no daily at 02:55 IST",
      due(Facts(ist_3am - timedelta(minutes=10), ist_3am - timedelta(hours=5), None, False, IST))
      is None)
# a backup that never happened and the start-up check already ran: does it still retry soon?
no_retry = due(Facts(t0, None, t0 - timedelta(hours=1), False, UTC_TZ))
check("V9 no backup ever + start-up check already spent: retried before 03:00?",
      no_retry is not None, f"due() returned {no_retry!r} at 12:00 UTC (daily rule fired at 12:00 "
      "only because 03:00 passed)")

# ---------------------------------------------------------------- V6 first-run rule
def boot_case(label, *, photos=False, backup_file=False, sidecar=False, backups_mounted=True,
              expect_state, expect_reason=None, expect_db=None):
    root = Path(tempfile.mkdtemp())
    data, backups = root / "data", root / "backups"
    data.mkdir()
    backups.mkdir()
    if photos:
        (data / "photos").mkdir()
        (data / "photos" / "a.jpg").write_bytes(b"x")
    if backup_file:
        (backups / "auto-20260101T000000Z.sqlite3").write_bytes(b"not a real db but a listed file")
    if sidecar:
        (data / "db").mkdir()
        (data / "db" / "enderchest.sqlite3-wal").write_bytes(b"")
    s = load_settings({"ENDERCHEST_ENV": "test", "ENDERCHEST_DATA_DIR": str(data),
                       "ENDERCHEST_BACKUPS_MOUNT": str(backups)})
    manager = BootManager(s, is_mount=lambda p: True if p == s.data_dir else backups_mounted)
    manager.run_checks()
    st = manager.state
    ok = st.status.value == expect_state and (expect_reason is None or st.reason == expect_reason)
    if expect_db is not None:
        ok = ok and s.db_path.exists() == expect_db
    check(f"V6 {label}", ok, f"state={st.status.value}/{st.reason} db_created={s.db_path.exists()}")
    manager.shutdown()


boot_case("empty data + empty backups -> new database", expect_state="ok", expect_db=True)
boot_case("no db, photos present -> recovery", photos=True, expect_state="recovery",
          expect_reason="database_missing", expect_db=False)
boot_case("no db, a backup present -> recovery", backup_file=True, expect_state="recovery",
          expect_reason="database_missing", expect_db=False)
boot_case("no db, stray -wal present -> recovery", sidecar=True, expect_state="recovery",
          expect_db=False)
boot_case("no db, backup folder NOT visible but holds a backup -> must not create empty db",
          backup_file=True, backups_mounted=False, expect_state="recovery", expect_db=False)

# ---------------------------------------------------------------- V4 restore names (function level)
check("V4 regex accepts a trailing newline (pattern uses $, not \\Z)",
      _SAFE_NAME.match("manual-20260101T000000Z\n") is None,
      "match() returned a match for a name ending in newline")
root = Path(tempfile.mkdtemp())
(root / "data").mkdir()
(root / "backups").mkdir()
s = load_settings({"ENDERCHEST_ENV": "test", "ENDERCHEST_DATA_DIR": str(root / "data"),
                   "ENDERCHEST_BACKUPS_MOUNT": str(root / "backups")})
for bad in ["../etc/passwd", "/etc/passwd", "manual-../../x", "", "x" * 300, "nokind-1",
            "auto-20260101T000000Z.partial", "auto-20260101T000000Z\n", "AUTO-20260101T000000Z"]:
    try:
        restore_backup(s, bad)
        check(f"V4 restore refuses {bad[:30]!r}", False, "no error")
    except RestoreError as exc:
        check(f"V4 restore refuses {bad[:30]!r}", True, str(exc)[:50])
    except Exception as exc:  # anything other than RestoreError is a leak of an internal error
        check(f"V4 restore refuses {bad[:30]!r} with RestoreError", False, type(exc).__name__)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "ALL CHECKS PASSED")
