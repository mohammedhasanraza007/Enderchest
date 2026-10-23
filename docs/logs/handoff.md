# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase1.2.zip`. The phase 1.1 session already unzipped it into `D:\Projects\Enderchest-phase-2\Enderchest` and made branch `phase-2` there (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, owner 2026-10-23):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Do not wait for "go". Each session ends by zipping, unzipping into a NEW folder, branching, writing `D:\Projects\<next>-next-prompt.txt` and starting the next session there. Owner-only gates are BLOCKED and listed below; they never stop the chain.
- Last closed phase: none formally. Phase 0: verification complete for Claude's part, **PASS**; Phase 1: verification complete for Claude's part, no blocker or major. Both close as PASS WITH NOTES once the owner's checks below are done (`Verification: pending (owner) for phase 0 and phase 1`).
- Resume check: `git log --oneline -3` shows `phase1.2: checkpoint`.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it. Time-box bugs: fix once, simply, with a test; a second failure goes to the evidence log.

## Next steps, in this order
1. **Phase 2 build**, `docs/specs/phase-2-inventory.md` (prompt: `D:\Projects\phase2-next-prompt.txt`). It must add the stored first-run step marker and P-01 step 2 (D-084), put the upload path in `security.MULTIPART_PATHS`, and give every new form a general message for a problem on a field it does not show (F-024).
2. A fresh session verifies Phase 2 (`PROCESS.md` 4, probe list first), then hands off to the Phase 3 build.
3. Small TODO any session may take: make `test.bat lint` cover `tests/e2e` (tsc and Prettier; 6 spec files are not formatted).

## Current state (facts)
- Built in Phase 1: `GET`/`PUT /profile`, `GET`/`PATCH /settings`, `build_date` in `/health`, `folder_hint` in `GET /backups`, theme written into the served page, restyled boot page, the frontend shell (tokens, primitives, nav capsule and name menu, backup banner, first run, Settings: Profile, Appearance, Backup, About, not found), `test.bat` commands, `dev.bat` with Vite.
- This chat (phase 1.1): Phase 1 verification (`docs/reviews/phase-1-verification.md`, 8 probes) and the Phase 0 final pass (`docs/reviews/phase-0-verification.md`). Fixed test-first: `dev.bat`'s Vite never served a Windows edit (now polls; probe 18); the test stack retagged the live image (now `enderchest-app-test`, D-089, probe 19); a failed automatic backup was retried every 30 s (now 15 min, D-090); two wrong paths in CODE_MAP (`check_docs.py` now 0 errors). Added 4 browser tests (slow load, failing profile save x2, name menu by keyboard) and 3 integration tests.
- Results on the final code: lint clean; 68 pytest unit, 44 vitest; 93 integration; Playwright 38 + 3 (no `/backups`); probes 1 to 19 ALL PASSED.
- The LIVE stack (read-only look, 2026-10-23): `enderchest-app-1` runs a Phase 1 image built by a test run before D-089 (`build_date` null); the welcome screen was completed on it (name set, theme dark); the live backup folder holds only `auto-` files. `enderchest-app:latest` now points at a test build from this chat (same Phase 1 code, build date `probe19-…`), so **`build.bat` must run before `run.bat`**.
- Decisions D-089 to D-091 are this chat's.

## Owner runs next
1. `build.bat`, then `run.bat` (live gets the reviewed image with a real build date).
2. Switch the three themes; press Back up now in Settings and also run `backup.bat` once: a `manual-` file must appear in `%USERPROFILE%\Enderchest-Backups`.
3. Gate 1: look at `docs/logs/raw/phase-1/shots/*.png` and say "approved" or what looks wrong (note: in the name menu the "Dark" chip wraps onto its own line).
4. `.\test.bat probes -Only "4,9" -Live` (real `build.bat`/`run.bat`), then `restore.bat` once on a backup you choose.
5. Optional: delete container `great_gagarin` in Docker Desktop (a stray, no mounts).

## Known issues to carry
- Boot pages use system fonts (D-088). Dev reloads the whole page (D-086). The Settings page leaves the right half empty until later sections exist.
- `photos_missing` and backup `item_count` stay placeholders until Phase 2. `tests/fixtures/expiry_cases.csv` has CRLF (Phase 3 TODO). No request body cap until Phase 2's 12 MB upload cap.
- Throwaway test volumes (`enderchest_test_data_p10_*`, `_p11_*`, `_q1_*`) are kept by design; never delete volumes.
- 2026-10-23: Docker Desktop would not start from Claude (`docker desktop start`: registry key `SOFTWARE\Docker Inc.\Docker Desktop` missing); the owner fixed it. If `docker info` fails, record it in this file and stop.

## How to work on this laptop
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`. Claude's guard denies any command containing the live volume's name, volume removal, prune or `down -v`; retagging `enderchest-app:latest` is refused too. Use full paths; the shell folder resets between calls.
- `.\test.bat <what>` through `cmd /c "... > file 2>&1"`, then read `$LASTEXITCODE` (not `%errorlevel%` on the same cmd line). Commit messages with double quotes go through `git commit -F <file>`.
- A session that must start the next session waits for long background runs inside its own turn: a turn started by a task notification cannot start sessions.
- The Windows zip route is proven (`docs/PROCESS.md` 7: clone first, `tar -a -c -f ... -T zip-list.txt`).
