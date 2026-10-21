# Phase 0 — Verification (fresh session): INCOMPLETE, two defects found

- Date: 2026-10-21 (same day as the build).
- Verifier: Sonnet 5.5 in a fresh chat. **The builder was also Sonnet 5.5**, so builder and verifier are the same model; this review is deliberately sceptical and reads the evidence rather than trusting it.
- Input: `phase0.zip` unzipped into a new empty folder; branch `phase-0`, commit `d6b71fa`, clean tree before anything ran. The same 142 tracked files were later compared by SHA-256 against the `phase-1` worktree: identical.
- Spec used: `docs/specs/phase-0-foundation.md`. `handoff.md` and the evidence log were read only to find the open items.
- Live stack rule: nothing here ran tests, probes or resets against the live stack (`CLAUDE.md` 3). Live-stack facts were read only (`docker ps`, `docker inspect`, `docker logs`, a folder listing).
- **Why incomplete:** the owner interrupted the review and said "start phase 1 now". Probes V1 to V3, V6, V9, V11 to V13 were run (some in part); V4, V5, V7, V8, V10 are partly or not verified, as listed. Under `PROCESS.md` 4 any major or blocker is a FAIL, and NOT VERIFIED never counts as PASS.

## Verdict: FAIL on the evidence so far (2 defects), verification NOT complete

Phase 0 is **not closed**. The owner chose to start Phase 1 with this open (decision D-082). The two defects below should be fixed and re-verified; until then handoff keeps `Verification: pending for phase 0`.

| # | Severity | Defect | Status |
|---|---|---|---|
| F-1 | major | `backup.bat` never makes a backup: its helper `scripts/post-backup.ps1` is refused by the security middleware with 422 "Requests must be JSON." | **confirmed** by running it on the test stack |
| F-2 | blocker by the contract's own words (`DATA_SAFETY.md` header), unlikely in practice | The first-run rule creates a new empty database when the backup folder is not visible to the container (not a mount, or not writable) even if it holds backups. `DATA_SAFETY.md` 5 allows a new database only when "the backup folder holds no backup". | **confirmed** in-process (boot manager on temporary folders); not reproduced end to end in a container |
| F-3 | minor | `restore.py` name pattern uses `$`, so a name ending in a newline passes the pattern (it then fails with "not found", the message echoing the newline). Use `fullmatch`. | confirmed in-process, harmless today |

## Probe list (written before anything was run; committed first as `62c6666` in the verify folder)

| # | Probe | Result |
|---|---|---|
| V1 | Reproducibility: `build.bat` ×3, `test.bat lint`, `unit`, `integration` | **PASS.** Exit 0 three times (`raw/phase-0-verification/build-1..3.txt`); lint clean; 65 unit and 45 integration tests passed, the counts the builder claimed. The image id differs from the owner's earlier build (`9fa6d8136a29` to `9a6be2586985`) for the same source; the live container keeps running its old image until it is next recreated. |
| V2 | Deny rules: the 8 commands of spec task 1 through Bash and PowerShell, plus look-alikes | **PASS.** 16 of 16 refused, plus `docker volume  rm --help` (two spaces) and `docker compose DOWN -V --help` refused. `.claude/settings.json` hash identical in the main checkout and the zip. Not covered by any rule (not tested): deleting files in the host backup folder with `Remove-Item` or `del`, or `docker exec … rm` inside a running container. Minor, note only. |
| V3 | Migration atomicity | **PASS** (in a throwaway container, temporary folders): a migration whose third statement fails leaves no table, no row, `schema_version` unchanged, no open transaction; a trigger body stays whole. |
| V4 | Restore safety | **PARTIAL.** Nine bad names (`../`, absolute path, empty, 300 characters, no kind, `.partial`, uppercase kind, trailing newline) were all refused with `RestoreError`; F-3 recorded. NOT VERIFIED: the HTTP path with a wrong confirmation, restore while state is `ok`, double submit. The builder's probes 8 and 11 (restore once, WAL moved aside) PASS in my re-run. |
| V5 | Backup integrity and the `backup.bat` path | **FAIL (F-1).** Probe 14 PASS in my re-run. `scripts/post-backup.ps1 -Port 8471` printed "No backup was made. Requests must be JSON." and exited 1; the test log shows `POST /api/v1/backups … 422`. The `manual-` file in the test folder came from probe 14's `curl`, not the script. Probes use `curl`, never the script, so none could catch it. |
| V6 | First-run rule | **FAIL (F-2).** 4 of 5 cases PASS: empty gives a new database; photos present, a backup present, or a stray `-wal` present each give `recovery` and create nothing. The fifth (backup folder not visible, but holding a backup) gave state `ok` and a new empty database. |
| V7 | Process never exits on a failed check | **PASS** by probes 7, 10, 13 in my re-run (`locked/no_data_volume`, `locked/newer_data` with the file hash unchanged, `locked/env_mismatch` both ways). |
| V8 | Hardening beyond probe 12 | **PARTIAL.** Probe 12 PASS in my re-run (6 checks). By reading `api/security.py`: look-alike hosts, `Origin: null`, preflight (no safety header) and `text/plain` are refused. NOT VERIFIED by running: those extras, multipart on a non-upload path, an oversized body. Notes for later: there is no body-size cap yet, and the middleware skips non-HTTP scopes, so a future WebSocket route would bypass the Host and Origin checks. |
| V9 | Retention and triggers | **PASS with one suspicion open.** `plan_deletions` equals my own independent reading over 400 random backup sets in 5 time zones; manual and safety backups were never planned for deletion; the trigger rules (startup, daily at 03:00 local, changed) behave as written. **Suspicion, NOT VERIFIED:** `create_backup` writes its `backup_log` row after the backup started, which touches the database WAL, so `db_changed_at > newest backup start` may stay true forever and make the "changed" rule take an automatic backup every hour on an idle database (retention keeps the folder small). Also, after a failed attempt `tick()` retries every 30 s while no good backup exists. Both are hypotheses from reading; a test-clock probe would settle them. |
| V10 | Reality audit | **PARTIAL.** Search of `backend/app` for mock, fake, dummy, lorem, stub, TODO, FIXME, sample, demo: only the HTML `placeholder` attribute of two input boxes. The status page shows values read from `/health` and `/api/v1/backups` only. No `innerHTML` in the static pages. Test routes are included only when `ENDERCHEST_ENV=test` (read); NOT VERIFIED by a GET on the live app. Dead-control crawler: not applicable before Phase 1. Minor: the status page reloads itself in a tight loop if `/health` is `ok` but `/api/v1/backups` keeps answering an error. |
| V11 | Scripts against `DATA_SAFETY.md` 9 | **PASS.** No down-with-volumes, volume removal or prune in any script, compose file or probe; the only deletions are probe temp files, the copy made by probe 4, and the test-only wipe. All 7 `.bat` files are CRLF, no tracked text file contains a CR, `.gitattributes` as specified. Minor: when `restore.bat` fails after `docker compose stop`, it does not tell the owner the app is still stopped (start it with `run.bat`). |
| V12 | Scope and dependencies | **PASS.** Runtime lock: fastapi, uvicorn, tzdata and their pins (the allow-list); dev: pytest, ruff, httpx (httpx is on the list); `opentelemetry-api` arrives as a FastAPI dependency. No frontend or later-phase code. NOT RUN: `scripts/check_docs.py`. Minor: pytest warns that Starlette's test client with `httpx` is deprecated in favour of `httpx2`. |
| V13 | Open items from the handoff | **Closed, with one loose end.** (a) `backup.bat`: broken, see F-1; the live container's log holds no `POST /api/v1/backups` line at all (the log shows the first start at 16:06:06Z, the start-up backup at 16:06:36Z, a restart at 16:08:06Z, and nothing in between), so what the owner saw on the live stack is not explained by F-1 alone and is **unconfirmed**; the live folder still holds only `auto-20261021T160636Z.sqlite3`. (b) Container `great_gagarin`: created 16:05:09Z by a plain `docker run` of the app image (random name, no mounts, no `ENDERCHEST_*` variables, no published port, no restart policy); its state is `locked / no_data_volume`, so it can touch no data. Probably Docker Desktop's Run button (hypothesis). Harmless; the owner may delete it in Docker Desktop. Probe 4's "same project containers" line lists it because the image carries the compose labels. |

## What was not run, and why
- The `-Live` variants of probes 4 and 9, `run.bat` three times, `restore.bat`, and `backup.bat` on the live stack: they write to the owner's live volume and backup folder (`CLAUDE.md` 3). They stay with the owner, after F-1 is fixed for `backup.bat`.
- The hourly-backup suspicion (V9), the restore HTTP cases (V4), the hardening extras (V8), a GET on the live app (V10), cold-start time against the 20 s budget, SIGTERM shutdown time, `scripts/check_docs.py`.

## Evidence
`docs/logs/raw/phase-0-verification/`: `build-1..3.txt`, `test-lint.txt`, `test-unit.txt`, `test-integration.txt`, `probes-all.txt` and `probes-rerun-2026-10-21.txt` (14 of 14 PASS), `verify0_inproc.py` (the in-process checks that produced V3, V4, V6 and V9 above; run with `docker run --rm -i -w /app enderchest-tools:latest python -`).

## Proposed fixes (smallest change each; need the owner's go)
1. F-1: send `-ContentType 'application/json' -Body '{}'` from `scripts/post-backup.ps1`, and add probe 15 that runs the real script against the test stack and expects a new `manual-` file (probes 1 to 14 would never have caught it).
2. F-2: decide the first-run listing from `backups_dir` whenever it is a directory, not only when it is a writable mount; keep the red banner for "not a mount". Add an integration test for the fifth case above.
3. F-3: `fullmatch` instead of `match` on the restore name.
4. Run the V9 test-clock probe and the other NOT VERIFIED items, then rewrite this file's verdict.

---

## Fix pass (2026-10-21, same chat, after the owner's "go, fix Phase 0 first")

Each fix was written test-first: the new test or probe was seen to FAIL on the old code for the stated reason, then PASS after the change. One commit per fix.

| # | Result | Commit | Evidence of the before and after |
|---|---|---|---|
| F-1 | **fixed** | `535493f` | probe 15 (the real `scripts/post-backup.ps1` on the test stack): FAIL "Requests must be JSON." before, PASS after with a real 44 KB `manual-` file (`raw/phase-1/probe15-before-fix.txt`, `probe15-after-fix.txt`) |
| F-2 | **fixed** | `b30cc45` | two integration tests (folder not a mount; folder mounted read-only) fail before, pass after (`f2-integration-before-fix.txt`, `f2-integration-after-fix.txt`). End to end in a real container with a read-only backup folder holding a backup: `/health` says `recovery / database_missing`, `/data/db` is empty (`f2-e2e-container.txt`) |
| F-3 | **fixed** | `67128b3` | one unit test fails before, passes after (`f3-unit-before-fix.txt`, `f3-unit-after-fix.txt`) |
| F-4 (new) | **found by probe 16, then fixed** | `586ae93` | Hourly backups of an idle database, **confirmed**: with the test clock 90 minutes ahead and no data change, the scheduler took `auto-20261021T165430Z` (reason `changed`, 45056 bytes, the same size as the baseline) within one tick (`probe16-before-fix.txt`). Cause: a backup's own `backup_log` row, written after the backup starts, counted as "the database changed". Fix: the engine remembers the modification time its own log write left; only a later modification counts (`changed_since_own_write`). Integration test and probe 16 fail before, pass after (`probe16-after-fix.txt`: 0 automatic backups on the idle database, the control backup after a real write still fires). Trade-off recorded in D-083: a user write made while a backup runs is not seen until the next change or the daily backup, and one extra backup may follow an app restart. |

**Regression after the fixes** (image rebuilt from the final code): `test.bat all` clean: lint, 66 unit, 48 integration tests (`raw/phase-1/fixes-test-all.txt`); probes 1 to 16 all PASS on the test stack (`raw/phase-1/probes-all-after-fixes.txt`). The live stack was not touched.

**Still NOT VERIFIED:** the restore HTTP cases (wrong confirmation, state `ok`, double submit), the hardening extras (look-alike hosts, `Origin: null`, preflight, multipart, oversized body), a GET on the live app, `scripts/check_docs.py`, cold start against the 20 s budget, SIGTERM shutdown time. Hypothesis not tested: after repeated failures `tick()` retries every 30 s while no good backup exists. **Owner-only, after this fix pass:** run `backup.bat` once and look for a `manual-` file in `%USERPROFILE%\Enderchest-Backups`; the `-Live` probes 4 and 9; `restore.bat`. Note that `run.bat` after this chat recreates the live container on the new image.

**Verdict after the fix pass:** the four defects are fixed and the regression is green, but the verification is **not complete** (items above) and the owner has not repeated the live checks, so this file does **not** record a PASS. Phase 0 stays `Verification: pending for phase 0` in `handoff.md` (D-082). It can close with a short fresh-session pass over the NOT VERIFIED items plus the owner's live checks.
