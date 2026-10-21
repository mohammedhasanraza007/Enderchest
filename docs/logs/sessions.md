# sessions.md — One entry per chat (zip in, zip out)

Append only. Newest entry at the bottom. A new chat reads the LAST entry only, after the "Resume here" block of `handoff.md` (`CLAUDE.md` section 0). Keep each entry to at most 12 lines.

Entry fields: date · zip in · zip out · phase worked on · built · checks run · failed · blocked on owner · next.

---

## 2026-10-21 · pack-v5 · zip-workflow setup
- Zip in: `DOC-20261017-WA0002.zip` (pack v4, no git history). A baseline commit was made in the worktree before any change.
- Zip out: `pack-v5.zip` (includes `.git`).
- Phase worked on: none. Pack change only: D-067 to D-069, O-010, O-011.
- Read: the whole pack, every file, and the three visuals.
- Built: no code, no Docker, no phase gate run.
- Checks: `scripts/check_docs.py` (recorded in `docs/logs/evidence-log.md`). Zip listing check run (see evidence log).
- Failed: none.
- Blocked on owner: O-010 and O-011 (defaults apply until answered).
- Next: Phase 0 task 1, in a new chat with `pack-v5.zip`.

## 2026-10-21 · pack-v5.1 · owner changes
- Zip in: `pack-v5.zip` (commit `7aebb6a`).
- Zip out: `pack-v5.1.zip` (includes `.git`).
- Phase worked on: none. Pack change only.
- Changed: the phase-0 spec no longer excludes the visuals (D-070; O-011 answered). "Wait for go" wording removed from CLAUDE.md 0, PROCESS.md 3, README and OWNER_TASKS. A chat starts on paste (D-071), with a one-time project instruction as the trigger.
- Checks: `scripts/check_docs.py`; a search for remaining "go" wording and for image exclusions in the specs (see evidence log).
- Failed: none.
- Blocked on owner: O-010 (open; its default applies).
- Next: Phase 0 task 1. Paste `pack-v5.1.zip` into a new chat in the Enderchest project; nothing else is needed.
