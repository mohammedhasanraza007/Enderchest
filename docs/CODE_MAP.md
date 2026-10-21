# CODE_MAP.md — What the code is, and how to extend it

State after Phase 0 (about 2,000 lines of backend, no frontend yet). This file describes what exists; the specs say what to build. **Extend through these interfaces; never create a parallel version of a module.** Update this file in every phase that adds or changes a module. If code and this file disagree, the code wins: fix this file.

> **Read when:** before writing or changing any backend code, scripts or tests. **Do not read when:** doing screens or styling.

## 1. Layout (all under `backend/app/`)
| Module | Holds | Key names |
|---|---|---|
| `main.py` | App factory; lifespan (boot checks in a thread, scheduler task, shutdown) | `create_app(settings, is_mount, start_scheduler)`; run as `uvicorn app.main:create_app --factory` |
| `config.py` | Environment into one frozen object | `Settings` (paths: `db_path`, `photos_dir`, `thumbs_dir`, `secrets_dir`, `staging_dir`, `lock_path`, `backup_photos_dir`), `load_settings()`, `APP_VERSION`, `INTERNAL_PORT` |
| `boot/` | Startup state machine (DATA_SAFETY 4, 5, 11) | `BootManager` (`manager.py`), `Status`, `mounts.py` (`is_mount_point`), `lock.py` (`InstanceLock`, flock), `marker.py` (`read_marker`) |
| `db/` | SQLite access, migrations, creation | `connection.connect`, `write_transaction`, `ThreadConnections`; `migrate.migrate/pending/supported_version`; `create.create_database`; `migrations/NNNN_name.sql` |
| `backup/` | Backups and restore | `engine.create_backup`, `verify_database`, `mirror_photos`, `record_log`, `changed_since_own_write` (the scheduler's "database changed" test; a backup's own log row does not count); `catalog.list_backups`, `make_name`; `retention.plan_deletions`; `restore.restore_backup`, `start_empty_safety`; `cli.py` |
| `scheduler/` | In-process loop | `backups.BackupScheduler` (30 s tick, asyncio + thread), `triggers.due(Facts)` pure rules |
| `api/` | Routers and middleware | `security.SecurityMiddleware`/`check_request`, `deps.py` (`get_manager`, `require_ok`, `get_db`), `boot.py`, `backups.py`, `pages.py`, `test_support.py` |
| `services/` | Business rules between routes and SQL | `backups.py` (status, listing, last good), `test_support.py` (write loop, reset) |
| `errors.py` | One error shape | `AppError(code, status, message, details)`, `install_error_handlers` |
| `clock.py` | The only "now" for app logic; test endpoints can move it | `now()`, `local_date(tz)`, `set_now`, `advance`, `reset` |
| `fsutil.py`, `logs.py` | Atomic copy, fsync, move aside, checksums; JSON log lines | `copy_atomic`, `move_aside`, `remove_partials`, `log_event` |
| `static/boot/` | Plain HTML boot page and foundation status page | `boot.html`, `status.html` (Phase 1 replaces the status page at `/` with the app) |

There is no `repositories/` or `schemas/` yet: Phase 0 has no user-owned tables. **Phase 1 and 2 create them** following ARCHITECTURE 2 (routes → services → repositories → db; every repository query takes `user_id`).

## 2. How the pieces behave (the facts a new phase needs)
- **Boot:** `BootManager.run_checks()` runs in a thread at start-up and never exits the process. States: `starting`, `ok`, `recovery`, `locked`, `failed` plus a `reason` (`no_data_volume`, `data_not_writable`, `second_instance`, `env_mismatch`, `newer_data`, `corrupt`, `database_missing`, `backup_folder_unavailable`, `pre_migration_backup_failed`, `migration_failed`). `manager.state`, `manager.db()` (this thread's connection; only valid in `ok`), `manager.backups_mounted`, `manager.exclusive()` (operation lock), `manager.release_connections()`.
- **Routes:** use `Depends(require_ok)` or `Depends(get_db)` so a non-`ok` state answers `locked` (503). Routes are plain `def` (thread pool). Add a router in `api/`, then `app.include_router(...)` in `main.py`.
- **Database:** connections are autocommit (`isolation_level=None`); every write is `with write_transaction(conn):` (`BEGIN IMMEDIATE`). Pragmas: WAL, `synchronous=FULL`, `foreign_keys=ON`, `busy_timeout=5000`. Never call `create_all`; never edit a released migration.
- **New migration:** add `backend/app/db/migrations/000N_name.sql` (numbers contiguous, one transaction, no seed data). Boot makes a verified `pre-migration-vA-to-vB-…` backup first, then migrates; `schema_supported` follows the file count automatically. Write a test that builds a v(N-1) database and migrates it (`tests/integration/test_boot.py` shows the pattern with `monkeypatch.setattr(migrate, "MIGRATIONS_DIR", folder)`).
- **Backups:** `create_backup(settings, kind, log_conn=conn)` builds on the volume, verifies, copies to `/backups` atomically, mirrors `photos/`, writes `backup_log`. A backup is never opened on `/backups`. Listing is from file names; `item_count` is `null` until an `items` table exists (then `verify_database` counts it).
- **Restore:** `restore_backup(settings, name)` (CLI and `POST /boot/restore`): verify on the volume, safety backup, move the old db **and its -wal and -shm** aside, rename the new one in, copy missing photos. Refuses a newer schema or a different `env_marker`.
- **Security middleware:** Host must be localhost/127.0.0.1/[::1] on the app port or 8470; writes need `X-Enderchest: 1`; `Origin` must equal the app's own; bodies must be `application/json` (multipart only for paths in `security.MULTIPART_PATHS`, empty until Phase 2: add the upload path there). No CORS headers anywhere.
- **Errors:** raise `AppError("not_found", 404, "…")`; codes are in API.md 1. Unexpected exceptions become `internal_error` with the traceback only in the log.
- **Test stack only:** `api/test_support.py` routes exist only when `ENDERCHEST_ENV=test` and `meta.env_marker='test'`. `reset` works only in state `ok`. Never point a test at the live stack.
- **Environment variables:** `ENDERCHEST_ENV` (`live`/`test`), `ENDERCHEST_PORT` (published port), `ENDERCHEST_DATA_DIR` (default `/data`), `ENDERCHEST_BACKUPS_MOUNT` (default `/backups`), `ENDERCHEST_BACKUP_DIR` (host folder, display only), compose-only: `ENDERCHEST_TEST_PORT`, `ENDERCHEST_TEST_VOLUME`, `ENDERCHEST_TEST_BACKUP_DIR`.

## 3. Docker, scripts, tests
- `Dockerfile` targets `frontend-build` (empty `dist` for now, D-073), `runtime`, `tools`. `compose.yaml` (live: project `enderchest`, external volume `enderchest_data`, port 8470) and `compose.test.yaml` (project `enderchest-test`, volume `enderchest_test_data`, `./.test-backups`, port 8471; profiles `tools` and `dev`). The runtime image copies `backend/app` and `frontend-dist` (nothing serves `frontend-dist` yet: Phase 1 adds that).
- Dependencies: `backend/pyproject.toml` lists them, `requirements.lock` / `requirements-dev.lock` pin them (regenerate in a `python:3.13-slim-bookworm` container with `pip freeze`; record versions in the evidence log). The tools image copies the code at build time, so rebuild it before each test run (`test.bat` does).
- Scripts: `build.bat run.bat stop.bat backup.bat restore.bat test.bat dev.bat` (CRLF); helpers `scripts/health.ps1`, `scripts/post-backup.ps1`. From cmd run `.\test.bat`.
- Tests: `backend/tests/unit` (pure), `integration` (real folders; fixture `stack` in `tests/conftest.py` starts the app on temporary folders, `Stack(settings, is_mount=…)` simulates mounts), `probes/` (PowerShell, Docker, test stack; `run-probes.ps1 -Only "6,12"`; probes 1 to 14 are the DATA_SAFETY gate, probe 15 runs the real `scripts/post-backup.ps1` that `backup.bat` calls, probe 16 moves the test clock and checks an idle database is not backed up again; never call `backup.bat` from a probe, it reads `.env` and talks to the live port). Probe 10 and 11 make a new throwaway test volume each run; do not delete volumes (the guard blocks it).

## 4. Known gaps carried forward
- `photos_missing` (restore) and `item_count` (backups) are placeholders until Phase 2's tables exist.
- `users.timezone` starts as `UTC` (D-077); Phase 1 sets the real zone when first run completes.
- No frontend, no `scripts/export_openapi.py`, no Node in the `tools` image, no e2e suite: Phase 1.
- Probes 4 and 9 have `-Live` variants that were not run by Claude (the owner ran build/run/backup by hand, see the evidence log). `backup.bat` itself has not been seen to work on the live stack: its helper script was broken until the Phase 0 fix pass (F-1, `docs/reviews/phase-0-verification.md`), so the owner repeats it once.
- A user write made while a backup is running (before the backup's own log row) is not seen by the "changed" rule; the next change or the daily backup covers it (`engine.changed_since_own_write`, D-083). After an app restart one extra backup may follow once the last one is over an hour old.
- The first-run rule looks at the backup folder even when it is not a writable mount; the recovery page then lists no backups (it only lists a connected folder) and tells the owner to fix the folder (D-083).
