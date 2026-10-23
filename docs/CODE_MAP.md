# CODE_MAP.md — What the code is, and how to extend it

State after Phase 1 (backend about 2,700 lines; frontend: tokens, primitives, nav capsule, first run, Settings). This file describes what exists; the specs say what to build. **Extend through these interfaces; never create a parallel version of a module.** Update this file in every phase that adds or changes a module. If code and this file disagree, the code wins: fix this file.

> **Read when:** before writing or changing any backend code, frontend code, scripts or tests. **Do not read when:** only reading specs.

## 1. Backend layout (all under `backend/app/`)
| Module | Holds | Key names |
|---|---|---|
| `main.py` | App factory; lifespan (boot checks in a thread, scheduler task, shutdown) | `create_app(settings, is_mount, start_scheduler)`; run as `uvicorn app.main:create_app --factory`. `pages.router` is included **last**: its catch-all must never shadow an API route |
| `config.py` | Environment into one frozen object | `Settings` (paths: `db_path`, `photos_dir`, `thumbs_dir`, `secrets_dir`, `staging_dir`, `lock_path`, `backup_photos_dir`, `frontend_dir`; also `gemini_model_default`, `build_date`), `load_settings()`, `APP_VERSION`, `INTERNAL_PORT` |
| `boot/` | Startup state machine (DATA_SAFETY 4, 5, 11) | `BootManager` (`manager.py`), `Status`, `mounts.py` (`is_mount_point`), `lock.py` (`InstanceLock`, flock), `marker.py` (`read_marker`) |
| `db/` | SQLite access, migrations, creation | `connection.connect`, `write_transaction`, `ThreadConnections`; `migrate.migrate/pending/supported_version`; `create.create_database`; `migrations/NNNN_name.sql` (only `0001_foundation.sql` so far: `meta`, `users`, `settings`, `scheduler_state`, `backup_log`) |
| `backup/` | Backups and restore | `engine.create_backup`, `verify_database`, `mirror_photos`, `record_log`, `changed_since_own_write` (the scheduler's "database changed" test; a backup's own log row does not count); `catalog.list_backups`, `make_name`; `retention.plan_deletions`; `restore.restore_backup`, `start_empty_safety`; `cli.py` |
| `scheduler/` | In-process loop | `backups.BackupScheduler` (30 s tick, asyncio + thread), `triggers.due(Facts)` pure rules |
| `api/` | Routers and middleware | `security.SecurityMiddleware`/`check_request`, `deps.py` (`get_manager`, `require_ok`, `get_db`, `current_user_id`), `boot.py` (`/health`, `/boot`), `backups.py`, `profile.py` (`/profile`, `/settings`), `pages.py` (app shell, built files, boot page), `test_support.py` |
| `schemas/` | Pydantic request and response models; they are also the source of the generated frontend types | `profile.py` (`Profile`, `ProfileUpdate`, `SettingsView`, `SettingsPatch`; strict, name 1 to 40 characters), `backups.py` (`BackupsView`, `BackupMade`, `Health`) |
| `repositories/` | SQL only; **every function takes `user_id`** | `users.py` (`get`, `update_profile`), `settings.py` (`all_values`, `upsert_many`) |
| `services/` | Business rules between routes and repositories | `profile.py` (`get_profile`, `save_profile`, `get_settings`, `change_settings`, `SETTING_DEFAULTS`), `backups.py` (status, listing, last good), `test_support.py` (write loop, reset) |
| `errors.py` | One error shape | `AppError(code, status, message, details)`, `install_error_handlers` |
| `clock.py` | The only "now" for app logic; test endpoints can move it | `now()`, `local_date(tz)`, `set_now`, `advance`, `reset` |
| `fsutil.py`, `logs.py` | Atomic copy, fsync, move aside, checksums; JSON log lines | `copy_atomic`, `move_aside`, `remove_partials`, `log_event` |
| `static/boot/` | The plain HTML boot page (P-16); it works without the database | `boot.html` |

## 2. How the backend pieces behave (the facts a new phase needs)
- **Boot:** `BootManager.run_checks()` runs in a thread at start-up and never exits the process. States: `starting`, `ok`, `recovery`, `locked`, `failed` plus a `reason` (`no_data_volume`, `data_not_writable`, `second_instance`, `env_mismatch`, `newer_data`, `corrupt`, `database_missing`, `backup_folder_unavailable`, `pre_migration_backup_failed`, `migration_failed`). `manager.state`, `manager.db()` (this thread's connection; only valid in `ok`), `manager.backups_mounted`, `manager.exclusive()` (operation lock), `manager.release_connections()`.
- **Routes:** use `Depends(require_ok)` or `Depends(get_db)` so a non-`ok` state answers `locked` (503). Routes are plain `def` (thread pool). Give each route a **return type or response model** (the frontend types are generated from them). Add a router in `api/`, then `app.include_router(...)` in `main.py` **above** `pages.router`. Layers: route → service → repository → `write_transaction`; a route never touches SQL.
- **Pages:** state `ok`: every app path gets `frontend-dist/index.html` with `data-theme-pref` written from the stored theme (no flash); any other state: `boot.html`. Built files (`/assets/*`, `/tokens.css`, `/favicon.ico`, `/enderchest-logo.svg`) are served in every state. A missing file is a 404 in the one error shape; an unknown method or `/api/...` path is 404, never 405 or the shell.
- **Database:** connections are autocommit (`isolation_level=None`); every write is `with write_transaction(conn):` (`BEGIN IMMEDIATE`). Pragmas: WAL, `synchronous=FULL`, `foreign_keys=ON`, `busy_timeout=5000`. Never call `create_all`; never edit a released migration.
- **New migration:** add `backend/app/db/migrations/000N_name.sql` (numbers contiguous, one transaction, no seed data). Boot makes a verified `pre-migration-vA-to-vB-…` backup first, then migrates; `schema_supported` follows the file count automatically. Write a test that builds a v(N-1) database and migrates it (`backend/tests/integration/test_boot.py` shows the pattern with `monkeypatch.setattr(migrate, "MIGRATIONS_DIR", folder)`).
- **Profile and settings:** `first_run_complete` is `users.name IS NOT NULL` (D-084). Settings are JSON text per `(user_id, key)`; defaults are filled when a key was never written; unknown stored keys are ignored; a patch is applied whole or not at all. Phase 2 adds a stored first-run step marker (D-084).
- **Backups:** `create_backup(settings, kind, log_conn=conn)` builds on the volume, verifies, copies to `/backups` atomically, mirrors `photos/`, writes `backup_log`. A backup is never opened on `/backups`. Listing is from file names; `item_count` is `null` until an `items` table exists (then `verify_database` counts it).
- **Restore:** `restore_backup(settings, name)` (CLI and `POST /boot/restore`): verify on the volume, safety backup, move the old db **and its -wal and -shm** aside, rename the new one in, copy missing photos. Refuses a newer schema or a different `env_marker`.
- **Security middleware:** Host must be localhost/127.0.0.1/[::1] on the app port or 8470; writes need `X-Enderchest: 1`; `Origin` must equal the app's own; bodies must be `application/json` (multipart only for paths in `security.MULTIPART_PATHS`, empty until Phase 2: add the upload path there). No CORS headers anywhere.
- **Errors:** raise `AppError("not_found", 404, "…")`; codes are in API.md 1. Unexpected exceptions become `internal_error` with the traceback only in the log.
- **Test stack only:** `api/test_support.py` routes exist only when `ENDERCHEST_ENV=test` and `meta.env_marker='test'`. `reset` works only in state `ok`. Never point a test at the live stack.
- **Environment variables:** `ENDERCHEST_ENV` (`live`/`test`), `ENDERCHEST_PORT` (published port), `ENDERCHEST_DATA_DIR` (default `/data`), `ENDERCHEST_BACKUPS_MOUNT` (default `/backups`), `ENDERCHEST_BACKUP_DIR` (host folder, display only), `ENDERCHEST_FRONTEND_DIR` (default `/app/frontend-dist`), `ENDERCHEST_GEMINI_MODEL`, `ENDERCHEST_BUILD_DATE` (set by `build.bat`), compose-only: `ENDERCHEST_TEST_PORT`, `ENDERCHEST_TEST_VOLUME`, `ENDERCHEST_TEST_BACKUP_DIR`, `BUILD_DATE`.

## 3. Frontend layout (all under `frontend/`)
React 19 + TypeScript strict + Vite 8, plain CSS with one tokens file. Node exists only inside containers.
| Path | Holds |
|---|---|
| `index.html` | Shell with the tokens `<link>`, favicons, and the tiny inline script that sets `data-theme` before first paint (the server writes `data-theme-pref`) |
| `src/tokens/tokens.css` | **Every colour, radius, spacing, duration and font stack**, both themes (`:root[data-theme="dark"]` default and `light`), reduced-motion durations. Served unhashed as `/tokens.css`; the boot page links the same file |
| `src/styles/base.css` | Reset, page background glow, focus ring, `.page`, `.stack`, `theme-fade` |
| `src/api/` | `client.ts` (the only `fetch`: safety header on writes, `ApiError`, locked → reload to the boot page), `endpoints.ts` (one function per endpoint, types from the schema), `queries.ts` (TanStack Query hooks and keys), `schema.d.ts` and `../openapi.json` (**generated**, `test.bat types`) |
| `src/lib/` | Pure helpers with vitest tests: `format.ts` (dates in the owner's zone, sizes, day part), `theme.ts`, `backupText.ts` (all backup wording), `timezones.ts` |
| `src/hooks/` | `useThemeSync`, `useChooseTheme`, `usePageTitle`, `useSingleFlight` (blocks a double click before React redraws) |
| `src/primitives/` | `Button`/`LinkButton`, `Input`/`Select`, `Toggle`, `Chip`, `StatusChip`, `GlassCard`/`InnerPanel`, `Dialog`/`Sheet` (native `<dialog>`), `Toast` (+ `useToast`), `Skeleton`, `BrandMark` (the supplied logo as an `<img>`), `LiveBadge` (built, unused until the camera page); styles in `primitives.css` |
| `src/patterns/` | `NavCapsule`, `NameMenu`, `BackupBanner`/`BannerView`, `AppShell`, `ErrorBoundary`, `ErrorState`; styles in `patterns.css` |
| `src/screens/` | `Welcome` (P-01), `Settings` (P-02) with `settings/` sections (Profile, Appearance, Backup, About), `NotFound` (P-17); styles in `screens.css` |
| `src/routes.tsx`, `App.tsx`, `main.tsx` | Routes and `FirstRunGate`; providers; entry |
| `gallery.html`, `src/gallery/` | **Test-only** component gallery (sample values live only here); built by `vite.gallery.config.ts` into `dist-e2e`, never into the app |
| `vite.config.ts`, `vite.shared.ts` | Build; the shared plugin copies `tokens.css`, favicons and the logo from `assets/logo` to the build root |
| `playwright.config.ts` | Browser tests; `tests/e2e/*.spec.ts` at the repository root |

**How to extend**
- **A new screen:** add `src/screens/X.tsx`, a `<Route>` in `routes.tsx` inside `AppShell`, and a nav item **only when the page works** (`NavCapsule`, PAGES.md 1). Read data through hooks in `api/queries.ts`; every list needs loading (Skeleton), empty and error (`ErrorState`) states.
- **A new endpoint:** write the route with a response model, run `test.bat types`, commit the regenerated `openapi.json` and `schema.d.ts` (`test.bat unit` fails if they are stale), add the function to `endpoints.ts`.
- **A new Settings section:** a file in `screens/settings/` using `GlassCard`, added to `Settings.tsx`. A section appears only when its feature exists.
- **A new primitive:** component in `primitives/`, styles in `primitives.css` using tokens only, a markup test in `primitives.test.tsx`, an entry in the gallery (so the contrast and render specs cover it).
- **Colour, radius, duration:** only from `tokens.css`. Text on glass uses `--text` or `--text-muted-glass`; a status colour on text only inside `StatusChip`. The logo is never styled. Light theme: everything a pill, tall boxes use the soft capsule radius.
- **A control that cannot act** is disabled with a visible reason (`disabledReason`); a control that cannot work is not on screen.

## 4. Docker, scripts, tests
- `Dockerfile` targets `frontend-deps` (node_modules from the lock file), `frontend-build` (the Vite bundle), `runtime` (copies `backend/app` and `frontend-dist`; `ARG BUILD_DATE` is the last layer), `tools` (Python + Node + dev dependencies; `PYTHONPATH=/app`; `/frontend`, `scripts/export_openapi.py`) and `e2e` (the pinned official Playwright image). `compose.yaml` (live: project `enderchest`, external volume `enderchest_data`, port 8470) and `compose.test.yaml` (project `enderchest-test`, volume `enderchest_test_data`, `./.test-backups`, port 8471; profiles `tools`, `dev`, `e2e`, `e2e-nobackups`; services `app-nobackups`, `e2e`, `e2e-nobackups` share the app's network so the Host check passes, D-087).
- Dependencies: `backend/pyproject.toml` lists the Python ones, `requirements.lock` / `requirements-dev.lock` pin them; `frontend/package.json` pins the JavaScript ones exactly and `package-lock.json` is committed (regenerate with `npm install --package-lock-only` in a `node:22` container; record versions in the evidence log). Only allow-listed packages (D-086).
- Scripts: `build.bat run.bat stop.bat backup.bat restore.bat test.bat dev.bat` (CRLF); helpers `scripts/health.ps1`, `scripts/post-backup.ps1`, `scripts/export_openapi.py`. From cmd run `.\test.bat`.
- `test.bat lint` (ruff, tsc, eslint, prettier), `unit` (pytest, vitest, generated-types check), `integration`, `probes`, `e2e` (rebuilds the app image, then Playwright on the test stack twice: normal app and the app with no `/backups`), `types` (rewrite the generated API files), `format` (prettier --write), `all`.
- Tests: `backend/tests/unit` (pure), `integration` (real folders; fixture `stack` in `backend/tests/conftest.py` starts the app on temporary folders, `Stack(settings, is_mount=…)` simulates mounts; the `settings` fixture gives a throwaway frontend folder), `probes/` (PowerShell, Docker, test stack; `run-probes.ps1 -Only "6,12"`; probes 1 to 14 are the DATA_SAFETY gate, 15 runs the real `scripts/post-backup.ps1`, 16 moves the test clock, 17 checks the first-run name survives a stop and start, 18 checks `dev.bat`'s Vite sees a Windows edit (Vite polls, `vite.config.ts`); never call `backup.bat` from a probe, it reads `.env` and talks to the live port), `frontend/src/**/*.test.ts(x)` (vitest, node environment), `tests/e2e/*.spec.ts` (contrast, dead controls, first run, theme, backups, nobackups, primitives, shell reference; helpers in `helpers.ts`). Probe 10 and 11 make a new throwaway test volume each run; do not delete volumes (the guard blocks it).

## 5. Known gaps carried forward
- `photos_missing` (restore) and `item_count` (backups) are placeholders until Phase 2's tables exist.
- First-run step marker (P-01 step 2, "resume at step 2") arrives with Phase 2 (D-084).
- The Gemini model default is empty until Phase 3 picks one (`ENDERCHEST_GEMINI_MODEL`); no Gemini section is on screen before then.
- Probes 4 and 9 have `-Live` variants that were not run by Claude. `backup.bat` itself has not been seen to work on the live stack: its helper script was broken until the Phase 0 fix pass (F-1, `docs/reviews/phase-0-verification.md`), so the owner repeats it once.
- A user write made while a backup is running (before the backup's own log row) is not seen by the "changed" rule; the next change or the daily backup covers it (`engine.changed_since_own_write`, D-083). After an app restart one extra backup may follow once the last one is over an hour old.
- The first-run rule looks at the backup folder even when it is not a writable mount; the recovery page then lists no backups (it only lists a connected folder) and tells the owner to fix the folder (D-083).
- Dev reloads the whole page, not a hot swap: `@vitejs/plugin-react` is not on the allow-list (D-086).
