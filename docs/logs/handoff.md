# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase1.1.zip` (a checkpoint inside Phase 1, made because the chat ran out of room). Unzip into a NEW empty folder (the folder inside is `Enderchest/`, with `.git`), branch `phase-1`. Never unzip over an existing repo or worktree (D-067; `MISTAKES_TO_AVOID.md` N).
- Last closed phase: none. Phase 0 is built and fixed but NOT closed (`Verification: pending for phase 0`, D-082). Phase 1 is BUILT and its automated checks pass; it is NOT closed (`Verification: pending for phase 1`).
- Resume check: `git log --oneline -3` shows `phase1: checkpoint` (or later `phase1:` commits). Phase 0 fixes F-1 to F-4 are the `phase0-fix:` commits.
- DO NOT restart Phase 1 and do not rebuild what exists. Read `docs/CODE_MAP.md` (backend and frontend are described there) and extend through it.
- Time-box bug fixing: a bug found while verifying is fixed once, simply, with a test; if it needs a second attempt, log it in the evidence log and move on.

## Next steps, in this order
1. Read the final test and probe results in the evidence log (last "Phase 1 checkpoint" lines). If a probe failed, that is the first job.
2. Short fresh-session verification of Phase 1 (`PROCESS.md` 4, spec `docs/specs/phase-1-shell.md`) into `docs/reviews/phase-1-verification.md`. Gates 2 to 7 already have real evidence (`docs/logs/raw/phase-1/`); read it, re-run `test.bat e2e` once, probe the riskiest 5 to 8 things (first run on a real empty live database, theme flash on a slow load, a failing `PUT /profile`, the name menu by keyboard, dev.bat). Gate 1 needs the owner's approval of the screenshots.
3. Finish the Phase 0 verification: items listed NOT VERIFIED in `docs/reviews/phase-0-verification.md` (restore HTTP cases, hardening extras, `check_docs.py`, cold start and SIGTERM timing). Then rewrite that file's verdict.
4. After both pass (or PASS WITH NOTES the owner accepts): Phase 2, `docs/specs/phase-2-inventory.md`. Phase 2 must add the stored first-run step marker (D-084).

## Current state (facts)
- Built in Phase 1: `GET`/`PUT /profile`, `GET`/`PATCH /settings`; typed responses; `build_date` in `/health`; `folder_hint` in `GET /backups`; the server serves the built app with the stored theme written in (no flash); the restyled boot page; the frontend (tokens, primitives, nav capsule and name menu, backup banner, first run, Settings: Profile, Appearance, Backup, About, not found); `test.bat lint|unit|integration|probes|e2e|types|format`; probes 15 to 17; Vite in `dev.bat`.
- Results at the checkpoint: ruff, tsc, eslint, prettier clean; 68 pytest unit, 44 vitest, 90 integration; browser suite 34 on the normal test app and 3 on an app with no `/backups` (all pass); contrast 222 text samples per theme pass and match DESIGN 4.3 and 4.5; capsule within 1 px of the reference frame; the final probe run is in the evidence log.
- The LIVE stack: container `enderchest-app-1` still runs the OLD (Phase 0) image until the owner runs `run.bat`; the live database is empty (no name), so the first `run.bat` shows the welcome screen. The owner's data volume is untouched.
- Decisions D-082 to D-088 are this chat's. API.md is amended (D-085).

## Owner runs next
- `run.bat` (rebuilds the live container on the Phase 1 image), complete the welcome screen, switch the three themes, press Back up now and look for the `manual-` file in `%USERPROFILE%\Enderchest-Backups`, then look at `docs/logs/raw/phase-1/shots/*.png` and say "approved" or what looks wrong (gate 1).
- Later, after `build.bat`: the `-Live` probes 4 and 9 and `restore.bat` (Phase 0 owner checks, still open).
- Optional: delete container `great_gagarin` in Docker Desktop (a stray, no mounts).

## Known issues to carry
- `dev.bat` (Vite) was written but NOT run (port 8471 is shared with the test app; stop it first with `docker compose -f compose.test.yaml stop app`). NOT VERIFIED.
- Boot pages use system fonts (D-088). Dev reloads the whole page (D-086). The Settings page leaves the right half empty until later sections exist.
- `photos_missing` and backup `item_count` stay placeholders until Phase 2. `tests/fixtures/expiry_cases.csv` has CRLF (Phase 3 TODO).
- Docker Desktop stopped once during the browser run (cause unknown, maybe memory); it was restarted by the owner and the live app came back by itself.

## How to work on this laptop
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`; the owner starts it. Claude's guard denies any command containing the live volume's name, volume removal, prune or `down -v`. Use full paths; the shell folder resets between calls.
- `.\test.bat <what>` from cmd or PowerShell; never use `2>&1` on a native exe in PowerShell for a pass/fail check, redirect inside `cmd /c`. Commit messages with double quotes go through `git commit -F <file>`.
- The Windows zip route is proven (`docs/PROCESS.md` 7, `tar -a -c -f ... -T zip-list.txt`).
