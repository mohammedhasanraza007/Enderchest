# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Pack: v5.1 (D-067 to D-071). This zip: `pack-v5.1.zip`.
- Last closed phase: none. Phase 0 is not started.
- Next phase: 0. Next task: 1, prove the deny rules (`docs/specs/phase-0-foundation.md`, task 1).
- Verification: none pending.
- Resume check: the newest commit subject must be `pack: v5.1 visuals checked every chat, start on paste (D-070, D-071)`. The baseline is `2abbefc`; the v5 commit is `7aebb6a`.
- Owner answers still open: O-010 (where Docker probes run). Its default applies. O-011 is answered (D-070).

## Current state
- Phase: 0 (not started)
- Gate status: none run
- Commit subjects: `phase<N>:` for phase work, `pack:` for workflow and docs.

## Done (with commit ids)
- `2abbefc` baseline: DOC-20261017-WA0002.zip (pack v4, no prior git history).
- `7aebb6a` pack v5: zip-in/zip-out workflow (D-067 to D-069).
- Newest commit: pack v5.1 (subject in Resume check): the visuals are checked every chat (D-070), a chat starts on paste (D-071), and every "wait for go" wording is removed from the rules.

## Next
1. Phase 0, task 1 (`docs/specs/phase-0-foundation.md`): prove the deny rules in `.claude/settings.json` with the harmless `--help` forms, in Bash and PowerShell. Needs Claude Code on the laptop. If this chat cannot run them, record NOT VERIFIED and list the owner's commands under "Owner runs next".
2. Then Phase 0 tasks 2 to 10, in order.

## Owner runs next
- Nothing yet. Phase 0 acceptance (`docs/specs/phase-0-foundation.md`, owner acceptance) happens on the laptop after Phase 0 is built.

## Blocked on the owner
- Nothing blocks Phase 0 task 1.

## Decisions made so far (also in `docs/DECISIONS.md`)
- D-067 zip in, zip out. D-068 resume is compulsory. D-069 verification runs first in the next chat. D-070 the three visuals are checked every chat. D-071 a chat starts on paste, with no confirmation step.

## Known issues to carry
- `tests/fixtures/expiry_cases.csv` has CRLF line endings while `.gitattributes` says LF. Harmless to the CSV reader; normalise in Phase 3 (TODO in `docs/logs/evidence-log.md`).
- The zip command is proven on Linux only. The Windows `tar` route is unproven until the first laptop chat (TODO in `docs/logs/evidence-log.md`).
- Start-on-paste depends on the one-time project instruction (`docs/OWNER_TASKS.md`, Once). Without it, the fallback line is needed.

## Commands that matter
- `build.bat`, `run.bat`, `stop.bat`, `backup.bat`, `restore.bat`, `test.bat`, `dev.bat` (after Phase 0 creates them).
