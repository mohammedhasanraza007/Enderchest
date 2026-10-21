# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Pack: v5.1 plus the Phase 0 build. This zip: `phase0.zip`.
- Last closed phase: none. Phase 0 is BUILT but not closed.
- Verification: pending for phase 0. The next chat's first job is the fresh-session verification (`docs/PROCESS.md` 4), written to `docs/reviews/phase-0-verification.md`. Phase 1 starts only after its PASS. The owner said: do not start Phase 1 or later in the Phase 0 chat.
- Next task after PASS: Phase 1 (`docs/specs/phase-1-*.md`), only when the owner says so.
- Resume check: the newest commit subject must be `phase0: close chat (handoff, sessions, evidence)`. The history in this zip is the worktree's: baseline `e86aa59` (tag `pack-v4-baseline`, pack v4 content), then `4e47ee2` (pack v5.1 over v4), then the `phase0:` commits. The hashes `2abbefc`, `7aebb6a`, `7f710cb` named in older notes are NOT in this history.
- Owner answers still open: O-010 (where Docker probes run; they ran on the laptop, the default).

## Current state
- Phase 0 tasks 1 to 10 are done. Task 1 (deny rules): 16 of 16 refused. Lint, 65 unit and 45 integration tests pass in `test.bat all`. Probes 1 to 14 PASS on the laptop against the TEST stack (`docs/logs/raw/phase-0/`).
- Gate item 4 (`build.bat` three times) and the owner acceptance are NOT done: they use the live volume. See "Owner runs next".
- Docker Desktop is at `D:\DockerDesktop\Docker Desktop.exe`; Claude cannot keep it running, the owner starts it.

## Done (with commit ids)
- `e86aa59` baseline · `4e47ee2` pack v5.1 · `ef800c8` deny-rule proof · then skeleton, database layer, backup and restore, boot and API, scripts, tests, probes, decisions D-072 to D-081, fixes (see `git log --oneline`).

## Owner runs next
1. Start Docker Desktop. In the project folder run `build.bat`, then `run.bat`: the browser shows the foundation status page. Run `backup.bat`: a new `.sqlite3` appears in `%USERPROFILE%\Enderchest-Backups`. `stop.bat`, then `run.bat`: the page returns. Tell Claude "accepted" or what looked wrong.
2. Gate 4 and the live variants: `test.bat probes` already ran 4 and 9 on the test stack. For the live ones: `powershell -File backend\tests\probes\run-probes.ps1 -Only "4,9" -Live` (uses the real `build.bat`/`run.bat`; creates the live volume on first use).
3. `restore.bat` (try it once on a real backup): it lists, asks a number, asks you to type RESTORE.
4. Optional: remove old throwaway test volumes `enderchest_test_data_p10*`, `_p11*`, `_p13` (Docker Desktop or `docker volume rm`, by hand; Claude's guard blocks it).

## Blocked on the owner
- Nothing blocks the verification pass. Phase 0 cannot CLOSE until the owner acceptance above is reported.

## Decisions made so far (also in `docs/DECISIONS.md`)
- D-067 to D-071 (zip workflow). D-072 to D-081 (Phase 0 build: Python 3.13 and pins, empty frontend stage, file-name backup listing, API additions, Host ports, UTC default zone, migration needs backup folder, stale WAL means recovery, test endpoint guard, PowerShell probes).

## Known issues to carry
- `tests/fixtures/expiry_cases.csv` has CRLF endings while `.gitattributes` says LF (Phase 3 TODO).
- `photos_missing` and backup `item_count` are placeholders until Phase 2's tables exist (evidence-log TODO).
- The pack zip contains `.git`; extracting it over a git worktree replaces the worktree's `.git` link. Extract to a new empty folder.
- Windows zip route: see the `sessions.md` entry for how `phase0.zip` was made.

## Commands that matter
- `test.bat unit|integration|lint|probes|all` (from cmd use `.\test.bat`). Probes: `powershell -File backend\tests\probes\run-probes.ps1 -Only "6,12"` (a quoted string, not a bare list).
- `build.bat`, `run.bat`, `stop.bat`, `backup.bat`, `restore.bat`, `dev.bat` (live stack except `test.bat` and `dev.bat`).
