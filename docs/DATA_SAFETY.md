# DATA_SAFETY.md — The Data Persistence Contract

> **Read when:** any Docker, database, script, backup, restore, migration, boot or test-isolation work (Phase 0, and any later phase that changes schema, scripts or storage). Violating this file is a **blocker**. **Do not read when:** building screens or styling.
> **Sections:** 1 Causes closed · 2 Layout · 3 Compose and host · 4 Startup sequence · 5 First-run rule · 6 Migrations · 7 Backups · 8 Test isolation · 9 Scripts · 10 Gate probes · 11 Boot states · 12 Restore procedure · 13 Docker facts and guards.

**Goal:** the owner's items, photos and settings survive every re-run, rebuild, restart, crash, folder move and app update. "Re-running the app" must never reset it.

Honest scope note: this contract is preventive. It closes every known way a Docker-on-Windows SQLite app loses data and makes each one testable. v4 corrected several flaws found in v3 (stale-WAL restore, SQLite written onto a Windows bind mount, crash-loop on refusal, a bypassable guard); see `docs/PLAN_REVIEW.md`.

---

## 1. How data gets lost (the causes this contract closes)

| # | Cause | Closed by |
|---|---|---|
| 1 | Database written inside the container image layer (no mount); rebuild wipes it | 2, 4 (mount check) |
| 2 | `docker compose down -v`, `docker volume rm`, `docker volume prune --all`, `docker system prune -a --volumes` | 3 external volume, 13 guards, scripts never call them |
| 3 | Compose names a volume after the **folder name**; moving the folder creates a new empty volume | Pinned project name and pinned external volume name (3) |
| 4 | App creates a fresh DB whenever it does not see one and the owner starts over without noticing | 5 first-run rule, 11 boot states |
| 5 | Startup code that runs `create_all`, drops tables or re-seeds | 6 migrations only |
| 6 | A migration fails halfway | Pre-migration backup + transactional migration (6) |
| 7 | Tests or scripts run against the live volume | 8 test isolation and the environment marker |
| 8 | Docker Desktop reset or "Clean / Purge data", disk clean-up, reinstall | 7 host backups outside Docker |
| 9 | Crash or kill during a write | WAL, `synchronous=FULL`, transactions, atomic file writes (4, 7) |
| 10 | Newer database opened by an older app build | Downgrade refusal (4, 11) |
| 11 | Restoring a database file while a stale `-wal`/`-shm` from the old database remains, corrupting the restored one | 12 restore procedure |
| 12 | Refusal to start combined with `restart: unless-stopped` becoming an endless crash loop that hides the message | 11: the app never exits on a boot failure; it serves a boot page |
| 13 | A web page the owner visits writes to or deletes from the local API | `ARCHITECTURE.md` 9 hardening, probe 12 |
| 14 | Backup written half-way and later mistaken for a good one | 7 staging, verification, atomic rename |

---

## 2. Layout

Inside the container, everything persistent is under **`/data`** (the only writable persistent path):

| Path | Content | In backups? |
|---|---|---|
| `/data/db/enderchest.sqlite3` | The database (WAL mode) | Yes (online backup API) |
| `/data/photos/` | Original photos (immutable files, UUID names) | Yes (copy missing files) |
| `/data/thumbs/` | Thumbnails (re-creatable) | No |
| `/data/secrets/gemini.key` | Gemini API key, mode 0600 | **Never** |
| `/data/backup-staging/` | In-progress backups before they are verified and copied out | No |
| `/data/lock` | Single-instance lock (`flock`) | No |

`/backups` is a second mount (host folder, 3). Nothing else is persistent. The image holds code and OCR models only. The database also stores `meta.env_marker` (`live` or `test`), written once at creation (8).

The Gemini key is **not** stored in the database. The API never returns it; it reports only "key set" or "not set". After restoring onto a brand-new volume the owner re-enters the key.

---

## 3. Compose and host layout

- Compose sets `name: enderchest` (fixed project name; the folder name must not matter).
- The data volume is **external** and explicitly named: `volumes: enderchest_data: { external: true, name: enderchest_data }`. `build.bat` creates it once (`docker volume inspect enderchest_data`, then `docker volume create enderchest_data` only if missing). If the volume does not exist, `docker compose up` fails loudly instead of creating an empty one.
- Mounts: `enderchest_data:/data` and `${ENDERCHEST_BACKUP_DIR}:/backups`.
- **Default host backup folder: `%USERPROFILE%\Enderchest-Backups`** (D-053), created by `build.bat` if missing and written into `.env` with forward slashes. It is deliberately **not** under `Documents`: Windows often redirects Documents into OneDrive, which can lock files mid-write and breaks the plain path. The owner may point it at a OneDrive or other folder on purpose by editing `.env`.
- Port: `127.0.0.1:${ENDERCHEST_PORT:-8470}:8470`. Inside, the server binds `0.0.0.0:8470`.
- Why a named volume for the live database and not a Windows folder: SQLite locking and WAL are unreliable on Windows bind mounts under WSL2, and slow. **The same reasoning forbids opening any SQLite database on `/backups`**: backups are built on the volume and copied out as finished plain files (7).
- Single uvicorn worker. Container runs as a non-root user that owns `/data`; probe 11 proves it can also write to `/backups`.

---

## 4. Startup sequence (exactly this order; the process never exits because of a failed check, see 11)

1. **Mount checks.** `/data` must be a mount point (read `/proc/self/mountinfo`; fall back to `os.path.ismount`). If not: state `locked / no_data_volume`. Never create `/data/db` in the container layer. `/backups` not being a mount is **not** fatal: the app runs, shows a red banner, and refuses migrations and permanent deletes (nothing could be backed up).
2. **Single-instance lock** (`flock` on `/data/lock`). Held by another process: state `locked / second_instance`.
3. **Environment marker.** Read `meta.env_marker` (if a database exists). It must equal `ENDERCHEST_ENV`. A mismatch (a test container on the live volume, or the reverse): state `locked / env_mismatch`; nothing is written.
4. **Open the database** (`journal_mode=WAL`, `synchronous=FULL`, `busy_timeout=5000`, foreign keys on) and run `PRAGMA quick_check`. Failure: do not touch the file; state `recovery` (5).
5. **Read `schema_version`.** Newer than the app supports: state `locked / newer_data`; never "fix" it.
6. **Pending migrations?** Make a verified pre-migration backup (7), then migrate in one transaction. Failure: roll back; state `failed` with the backup name.
7. **Backup check** (7) and **start the scheduler** (reconcile once), then state `ok`.

Atomic writes: files are written to a temp name in the same folder, flushed, then renamed. A photo upload writes the file first, then the row in one transaction; a crash between them leaves at most an orphan file that a start-up sweep **reports** and never deletes.

---

## 5. First-run rule (never silently start empty)

A brand-new empty database is created **only** when all are true: `/data` is a mount, no database file exists, no photos exist, **and the backup folder holds no backup**. Anything else is state `recovery`:

- Database missing but photos or backups exist, or `quick_check` failed → the boot page "We found existing backups" (P-16 in `PAGES.md`) with **Restore this backup**. **Start empty anyway** needs typed confirmation and first takes a safety backup of whatever is on disk.
- The app never auto-restores and never auto-wipes.

---

## 6. Migrations and seeding

- Versioned, forward-only numbered `.sql` files, each in one transaction, each with a test that migrates a realistic previous-version database (`DATA_MODEL.md` 4).
- No `create_all`, no drop-and-recreate, no schema edits by hand.
- No demo or seed data in the real database, ever. Starter categories are created by the owner's tick at first run, not seeded. Demo data for screenshots lives in the test volume only (`POST /api/v1/test/fixtures/{name}`).
- `meta` holds `schema_version`, `created_at`, `env_marker`, `instance_id`.

---

## 7. Backups

**Building one (every kind uses this flow; no step is skipped):**
1. Take the single-instance lock-protected backup slot (one backup at a time).
2. `sqlite3.Connection.backup()` from the live database into `/data/backup-staging/<name>.sqlite3.partial` (on the volume, never on `/backups`).
3. Open the partial file; run `PRAGMA quick_check` and `PRAGMA foreign_key_check`; read the item count. Failure: delete the partial, record the failure in `backup_log`, warn in the UI.
4. Rename to `<name>.sqlite3` in staging; copy it to `/backups/<name>.sqlite3.partial`; `fsync`; compare SHA-256 with the staged file; rename to `/backups/<name>.sqlite3`; delete the staged file. A `.partial` file is never listed, restored or counted as a backup, and stale ones are removed at start-up.
5. Photos: copy files missing from `/backups/photos/` (each written as `.partial`, then renamed). Photos never change after upload, so this is incremental. A file whose size differs from its backup copy is reported, never silently overwritten.
6. Write the `backup_log` row.

**Names:** `auto-<UTC timestamp>`, `manual-…`, `pre-migration-v<from>-to-v<to>-…`, `safety-…`.

**When (D-052):** at start-up if the newest good backup is over 6 hours old; **after changes**: when the database changed since the last backup (compare the newest modification time of the database and its WAL with the last backup's start time), the last backup is at least 1 hour old, and nothing was written for 5 minutes; once a day around 03:00 local time if running; before any migration; on demand (`backup.bat`, Settings → Back up now, and the pre-delete offer in Trash).

**Retention (automatic backups only):** keep the newest 12; plus the newest of each local day for the last 14 days; plus the newest of each ISO week for the last 8 weeks; delete other `auto-*`. Keep the last 10 `pre-migration-*`. Never auto-delete `manual-*`, `safety-*`, or the newest good backup of any kind.

**Surfacing:** Settings → Backup shows the last good backup and the list. Status `stale` after 7 days without a good backup, `failing` after two consecutive failures, `unavailable` when `/backups` is not mounted. A non-`ok` status adds a banner under the nav capsule on every page.

Excluded from backups: the Gemini key and thumbnails (re-creatable).

---

## 8. Test isolation

- Tests, seed scripts and probes use the **test stack**: `ENDERCHEST_ENV=test`, project `enderchest-test`, volume `enderchest_test_data`, backup folder `./.test-backups`, port 8471.
- **The environment marker is the real guard** (D-054): the database records `env_marker` when created, and the app refuses to start if it does not equal `ENDERCHEST_ENV`. Test-only endpoints (`API.md` 2.17) exist only when both are `test`. Names of volumes are a second, weaker line of defence.
- The test database is reset with `POST /api/v1/test/reset`, not by deleting the volume (the deny rules block `docker volume rm`, and that is intended).
- The "container removed and rebuilt" probes use `docker rm -f` and `docker compose up -d --build`. They never use `down -v`.

---

## 9. Scripts

| Script | Must do | Must never do |
|---|---|---|
| `build.bat` | Check Docker installed and running; create the external volume only if missing; create the backup folder and `.env` if missing; build the image; stop on the first error with a plain message | `down -v`, volume removal, prune, touching data |
| `run.bat` | Confirm image and volume exist; check the port is free (clear message if not); `docker compose up -d --wait --wait-timeout 120`; read `/health`; open the browser when the server answers; print a plain-language warning when the state is not `ok`; print how to stop | Recreate or delete volumes |
| `stop.bat` | `docker compose stop` | `down -v` |
| `backup.bat` | `POST /api/v1/backups` with the safety header; print name, size, folder | |
| `restore.bat` | Section 12 | Restore without typed confirmation |
| `test.bat`, `dev.bat` | `ARCHITECTURE.md` 4 | Run against the live stack |

All scripts are safe to run repeatedly, check the exit code of every command, and are CRLF.

---

## 10. Gate probes for Phase 0 (all must PASS on the owner's laptop, with real evidence)

1. Write an item (a photo too once Phase 2 exists); `docker compose stop`; `docker compose up -d`; data present. *(Before Phase 2 the probe writes through the test-only write loop.)*
2. Remove the container (`docker rm -f`); start again; data present.
3. Rebuild with `--no-cache`; start; data present.
4. **Folder move:** copy the whole project folder to a differently named sibling (never rename the folder Claude is working in); run `build.bat` and `run.bat` from the copy; data present (proves pinned project and volume names). Delete the copy afterwards.
5. `docker compose rm -sf` (never `down`); `docker compose up -d`; data present.
6. `docker kill` during `POST /api/v1/test/write-loop`; restart; `quick_check` passes; no half-written record.
7. **Volume detached:** `docker run --rm -p 127.0.0.1:8472:8470 <image>` (no volume); the app answers with state `locked / no_data_volume` and creates nothing.
8. Delete the database file in the **test** volume (`POST /api/v1/test/delete-db`) with a backup present: recovery page appears, restore works, data matches.
9. Run `build.bat` three times in a row, then `run.bat` three times: no error, no data change.
10. Set `meta.schema_version` to a higher number in a test database copy and start the app on it: state `locked / newer_data`, data untouched.
11. **Backup round trip as the non-root user:** create a backup; it appears in the host folder (`%USERPROFILE%\Enderchest-Backups` equivalent for test), is verified, restores into a fresh test volume, and photos match by SHA-256.
12. **Localhost hardening:** requests with a wrong `Host`, no `X-Enderchest` header, a foreign `Origin`, or a `text/plain` body are refused with `forbidden_host`/`validation_error`; no CORS headers appear on any response.
13. **Marker mismatch:** start the live stack config against a test-marked database and the reverse: both refuse (`env_mismatch`).
14. **Interrupted backup:** `docker kill` mid-backup; restart; no `.partial` file is listed as a backup; the next backup succeeds.

The Phase Verification Gate (`docs/PROCESS.md`) re-runs the relevant probes in every later phase that changes schema, scripts or storage.

---

## 11. Boot states (the process never exits on a failed check)

| State | Condition | Served | `/health` status | `run.bat` |
|---|---|---|---|---|
| `starting` | checks running or migrating | boot page "Starting…" | `starting` | waits |
| `ok` | all checks passed | full API and app | `ok` | opens browser |
| `locked` / `no_data_volume` | `/data` not a mount | boot page only; API answers `locked` | `locked` | opens browser, prints warning |
| `locked` / `second_instance` | lock held | boot page | `locked` | same |
| `locked` / `env_mismatch` | marker differs from environment | boot page | `locked` | same |
| `locked` / `newer_data` | schema newer than app | boot page | `locked` | same |
| `recovery` | database missing or corrupt, or backups found on a fresh volume | recovery page, restore API | `recovery` | opens browser |
| `failed` | migration failed and rolled back | boot page with backup name | `failed` | opens browser |
`ok` with `warnings` (for example `/backups` not mounted) is not a separate state; the warning appears as a banner. `/health` answers 200 whenever the process runs, so the container is "healthy" and Docker does not restart it; a human reads the page.

## 12. Restore procedure (one implementation, two entry points)

Entry points: `restore.bat` (app stopped, one-off container running `python -m app.backup.cli restore <name>`) and the recovery page (`POST /api/v1/boot/restore`, app in `recovery` state with no open database connection). `restore.bat` lists with `… cli list`, asks for the number, asks the owner to type `RESTORE`, runs `docker compose stop`, runs the restore in a one-off container (`docker compose run --rm --no-deps -T app …`), then `docker compose up -d --wait`.

Steps (all inside one function, under the lock):
1. Verify the chosen backup: opens, `quick_check`, `schema_version` not newer than supported (an older one is allowed and migrated afterwards with a pre-migration backup).
2. **Safety backup** of the current state to `/backups/safety-<UTC>` (the database if it opens; otherwise a raw copy of the file and its `-wal`).
3. Copy the chosen backup to `/data/db/enderchest.sqlite3.restore-tmp`; `fsync`.
4. **Move aside, never delete:** rename the current `enderchest.sqlite3` to `enderchest.sqlite3.before-restore-<UTC>` **and move its `-wal` and `-shm` files aside with it**. Leaving an old WAL beside a new database file can corrupt it.
5. Rename `.restore-tmp` to `enderchest.sqlite3`.
6. Copy photos missing from `/data/photos` out of `/backups/photos` (never overwrite).
7. Open the database; `quick_check`; count items; list referenced photos missing from both places (reported to the owner, not fatal).
8. Write a `backup_log` row of kind `restore`. Start normally.

## 13. Docker facts and guards (verified Oct 2026)

- On current Docker, `docker volume prune` and `docker system prune --volumes` remove only **anonymous** volumes by default; named volumes need `--all`. A named volume is also kept while any container, even a stopped one, references it. `docker compose rm -sf` removes the container, so the volume is then "unused" and exposed to `--all` prunes. The real catastrophes are `--all` prunes, `docker volume rm`, and Docker Desktop's **Reset / Clean / Purge data**. Host backups (7) are the defence against all of them.
- Claude Code's Bash deny rules are **glob** patterns; `Bash(docker compose down:*)` is only a prefix match and misses `docker compose -f x.yml down -v`. v4 uses patterns with a wildcard between words, adds substring nets for `volume rm`, `volume prune`, `system prune`, `down -v`, and any command naming `enderchest_data`, and mirrors every rule for the **PowerShell** tool because Claude can fall back to it when Bash is denied.
- Rules are still best effort. The first task of Phase 0 proves them with harmless forms (`docker compose -f x.yml down -v --help`) before anything else runs; a form that is not blocked is fixed in `.claude/settings.json` immediately.
- If a legitimate need ever includes the live volume's name, the owner runs that command personally.
