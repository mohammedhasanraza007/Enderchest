# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Pack: v5.1 plus the Phase 0 build. This zip: `phase0.zip`. Work in a NEW empty folder: unzip it there (the folder inside is `Enderchest/`, with `.git`), then `git checkout -b phase-1` for Phase 1 work. Do not unzip over an existing repo or worktree (D-067; `MISTAKES_TO_AVOID.md` N).
- Last closed phase: none. Phase 0 is BUILT and the owner reported the live acceptance run as working (evidence log, 2026-10-21). It is not closed until its fresh-session verification passes.
- `Verification: pending for phase 0`. FIRST JOB of this chat: the fresh-session verification of Phase 0 (`docs/PROCESS.md` 4, spec `docs/specs/phase-0-foundation.md`), written to `docs/reviews/phase-0-verification.md`. Re-run `test.bat all` and the probes you judge riskiest (`test.bat probes`), read the evidence rather than trusting it, and close the two open items: did `backup.bat` make a `manual-` file, and what is the container `great_gagarin` (evidence log).
- After a PASS (or a PASS WITH NOTES the owner accepts): Phase 1, `docs/specs/phase-1-shell.md`. The owner has said they want to start the next phase in this chat, so that counts as the go. After a FAIL: fix, re-verify, no Phase 1.
- Resume check: the newest commit subject must be `phase0: close chat (handoff, sessions, evidence)` or later `phase0:` commits from the owner's session; run `git log --oneline -20`. History: baseline `e86aa59` (tag `pack-v4-baseline`), `4e47ee2` pack v5.1 over v4, then `phase0:` commits. Older notes naming `2abbefc`, `7aebb6a`, `7f710cb` refer to history that is NOT in this repo.
- Owner answers still open: O-010 (where Docker probes run; default applies: the laptop).

## Current state (facts)
- Backend built (about 2,000 lines): boot state machine, migration 0001, backup and restore, security middleware, scheduler, test endpoints, boot and status pages. Read `docs/CODE_MAP.md` before touching code; it lists every module and how to extend it. No frontend yet.
- Checks that ran: ruff clean; 65 unit and 45 integration tests; probes 1 to 14 PASS on the TEST stack (`docs/logs/raw/phase-0/`); deny rules 16 of 16 refused; docs checker 0 errors.
- The LIVE stack exists on the laptop: project `enderchest`, volume `enderchest_data` (created by the owner's `build.bat`), backups in `%USERPROFILE%\Enderchest-Backups`, app at `http://127.0.0.1:8470`. It holds the owner's real (still empty) database. Never run tests, resets or probes against it; the test stack is `enderchest-test` on port 8471.
- Decisions D-072 to D-081 are this phase's. `docs/DECISIONS.md` and `docs/API.md` carry the amendments.

## Owner runs next
- Nothing is required before the verification. Still unreported by the owner: `restore.bat` once on a real backup, `build.bat` three times in a row, and the `-Live` probes 4 and 9 (`powershell -File backend\tests\probes\run-probes.ps1 -Only "4,9" -Live`).
- Optional tidy: old throwaway test volumes `enderchest_test_data_p10*`, `_p11*`, `_p13` may be deleted by hand in Docker Desktop (Claude's guard blocks it).

## Blocked on the owner
- Nothing for the verification. Phase 1 may need the owner's real name and time zone at first run; check `docs/OWNER_TASKS.md` for Phase 1.

## Known issues to carry
- `photos_missing` (restore) and backup `item_count` are placeholders until Phase 2 adds `items` and `photos` (evidence-log TODO).
- `users.timezone` starts as `UTC` until Phase 1 first run (D-077). Node is not in the `tools` image yet and `frontend-build` makes an empty `dist` (D-073): Phase 1 changes both. Nothing serves `frontend-dist` yet.
- `tests/fixtures/expiry_cases.csv` has CRLF endings while `.gitattributes` says LF (Phase 3 TODO).
- Probes 10 and 11 leave one tiny throwaway test volume per run.

## How to work on this laptop (learned the hard way; details in `MISTAKES_TO_AVOID.md` N)
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`; the owner starts it. `docker info` must answer before any container work.
- Claude's guard denies any command containing `enderchest_data`, `volume rm`, `down -v`, prune. If a check seems to need them, ask the owner. Use full paths; the shell folder resets between calls and can be the main checkout `D:\Projects\Enderchest`.
- Commands: `.\test.bat unit|integration|lint|probes|all` from cmd or PowerShell; probes `-Only "6,12"` as a quoted string. Zip: `docs/PROCESS.md` 7, made from a clean local clone of the working branch in a SHORT temp path (so `.git` carries the history), with PowerShell's `tar -a -c -f out.zip -T zip-list.txt`, then verified by extracting into a temp folder.
- Starter prompt for the next chat: attach `phase0.zip` and write "START phase 1" (the pack starts itself, D-071); the zip out will be `D:\Projects\phase1.zip`.
