# Phase 0 — Foundation and data safety

**Read list (in this order):** `CLAUDE.md` sections 0, 3, 4, 5 · this file · `DATA_SAFETY.md` (all of it; it is the contract) · `ARCHITECTURE.md` 1–6, 8–10 · `API.md` 1, 2.1, 2.3, 2.17 · `DATA_MODEL.md` 1, 2.1–2.3, 2.14, 2.15.
**Do not read:** `DESIGN.md`, `PAGES.md`, `PROJECT_PLAN.md`. The three visuals are still opened at every session start (`CLAUDE.md` section 0; D-070, amended 2026-10-21). No screen is built in this phase.
**Owner supplies:** nothing. **Milestone:** A.

## Goal
A Dockerised backend that cannot lose data, can prove it, and tells the owner plainly when something is wrong. No product features yet.

## Task order (do not reorder)
1. **Prove the guard.** Before any other command, try each of these through Claude Code's Bash tool and, if present, its PowerShell tool. **Every one must be refused by the permission system.** Record each result. If any runs, fix `.claude/settings.json` immediately and retry.
   `docker compose -f compose.yaml down -v --help` · `docker compose down --help` · `docker-compose down --help` · `docker volume rm --help` · `docker volume prune --help` · `docker system prune --help` · `echo enderchest_data` · `powershell -Command "docker volume rm --help"`.
2. **Skeleton:** repo layout of `ARCHITECTURE.md` 2; `Dockerfile` with the three targets; `compose.yaml` and `compose.test.yaml` as specified in `ARCHITECTURE.md` 3; `.env.example`.
3. **Boot state machine and `/health`, `/api/v1/boot`** (`DATA_SAFETY.md` 4, 11). The process never exits on a failed check.
4. **Database layer:** connection factory with the pragmas, migration runner, migration 0001, creation of the single user row and the `meta` rows (including `env_marker`) **only** under the first-run rule (`DATA_SAFETY.md` 5).
5. **Backup engine** (`DATA_SAFETY.md` 7): staging, verification, atomic copy, photo mirror, triggers, retention, `backup_log`; **restore** (`DATA_SAFETY.md` 12) as a function used by the CLI (`python -m app.backup.cli list|restore|backup`) and by `POST /api/v1/boot/restore`.
6. **Security middleware** (`ARCHITECTURE.md` 9).
7. **Scripts:** `build.bat`, `run.bat`, `stop.bat`, `backup.bat`, `restore.bat`, `test.bat`, `dev.bat` exactly as `DATA_SAFETY.md` 9 and `ARCHITECTURE.md` 4 say.
8. **Test stack and test-only endpoints** (`API.md` 2.17), guarded by the environment marker.
9. **Boot pages** (plain HTML, `PAGES.md` is not needed: states and wording are in `DATA_SAFETY.md` 11 and this list) and a **foundation status page** served at `/` when the state is `ok`, showing only real values: app version, schema version, environment, last good backup time and size, backup folder status. It is replaced by the app in Phase 1 and shows nothing invented.
10. **Tests:** unit tests (retention algorithm, mount check, marker check, restore step order including WAL move-aside, backup naming, `.partial` handling), integration tests (migration from a hand-built previous-version file, backup then restore round trip, middleware rejections), and the 14 probes as scripts under `backend/tests/probes/` driven by `test.bat`.

## Deliverables
Endpoints: the Phase 0 rows of `API.md` 2.1, 2.3, 2.17. Tables: migration 0001. Files: everything above.

## Gate (all must PASS with real evidence)
1. Deny-rule proof (task 1) recorded.
2. Probes 1 to 14 of `DATA_SAFETY.md` 10 all PASS on the owner's laptop.
3. Unit and integration tests above pass inside `test.bat`.
4. Build is reproducible: `build.bat` three times, no error.
5. Verification pass (`PROCESS.md` 4).

## Owner acceptance (3 minutes)
Run `build.bat`, `run.bat`; the browser shows the foundation status page with sensible values. Run `backup.bat`; a new `.sqlite3` file appears in `%USERPROFILE%\Enderchest-Backups`. Run `stop.bat`, then `run.bat`; the status page returns. Tell Claude "accepted" or what looked wrong.
