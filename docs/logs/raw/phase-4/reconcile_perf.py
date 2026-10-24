"""Time the reconcile on the items-1000 fixture (test settings, temporary folders)."""
import statistics
import tempfile
import time
from pathlib import Path

from app.config import Settings
from app.services import notifications, test_support
from tests.conftest import SHELL_HTML, Stack, CLOSED_GEMINI_URL

root = Path(tempfile.mkdtemp())
for name in ("data", "backups", "frontend"):
    (root / name).mkdir()
(root / "frontend" / "index.html").write_text(SHELL_HTML)
settings = Settings(env="test", port=8470, data_dir=root / "data", backups_dir=root / "backups",
                    backup_dir_hint="x", frontend_dir=root / "frontend", gemini_url=CLOSED_GEMINI_URL)
with Stack(settings) as stack:
    conn = stack.manager.db()
    test_support.load_fixture(conn, "items-1000")
    for n in range(40):  # tasks due, to have task rows too
        conn.execute("INSERT INTO tasks (user_id, title, kind, next_due, created_at, updated_at) "
                     "VALUES (1, ?, 'chore', '2026-01-01', 'x', 'x')", (f"t{n}",))
    first = time.perf_counter(); changed = notifications.reconcile(conn, 1); first = time.perf_counter() - first
    runs = []
    for _ in range(20):
        t = time.perf_counter(); notifications.reconcile(conn, 1); runs.append(time.perf_counter() - t)
    count = time.perf_counter(); stack.client.get("/api/v1/notifications/count"); count = time.perf_counter() - count
    print(f"first reconcile {first*1000:.1f} ms {changed}; again median {statistics.median(runs)*1000:.1f} ms max {max(runs)*1000:.1f} ms; GET count {count*1000:.1f} ms")
