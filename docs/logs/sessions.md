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

## 2026-10-21 · phase0 · Phase 0 build
- Zip in: `pack-v5.1.zip` (Desktop). Its `.git` history was not used: baseline commit `e86aa59` (tag `pack-v4-baseline`) holds the owner's v4 files, `4e47ee2` adds v5.1 over it. Worktree `D:\Projects\Enderchest-phase-0`, branch `phase-0`.
- Zip out: `D:\Projects\phase0.zip`, made from a clean local `git clone` of branch `phase-0` (so `.git` carries the history) with the Windows `tar -a -c -f ... -T` route (see the evidence log).
- Phase worked on: 0, tasks 1 to 10, all built. Not closed: verification and owner acceptance pending.
- Checks: deny rules 16 of 16 refused; `test.bat all` 65 unit and 45 integration tests, ruff clean; probes 1 to 14 PASS on the test stack; boot pages checked in the browser pane; docs checker 0 errors.
- Failed and fixed: restore on an empty volume (missing folder), last good backup after a restore, and four defects in the probe scripts (all recorded in `raw/phase-0/probes-2026-10-21.txt`). Two mistakes of mine: extracting the zip over the worktree replaced its `.git` link (repaired), and a relative path wrote 7 empty `.bat` files into the main folder (removed).
- Blocked on owner: live-stack checks (`build.bat` x3, `run.bat`, `backup.bat`, `restore.bat`, live probes 4 and 9), see handoff "Owner runs next".
- Next: fresh-session verification of Phase 0; Phase 1 only after PASS and only when the owner says so.

## 2026-10-21 · phase0 · closing addendum (same chat)
- The owner ran `build.bat`, `run.bat`, `backup.bat`, `stop.bat`, `run.bat` on the laptop and reported that they work (recorded in the evidence log). Claude confirmed read-only that the live app is `ok`/`live`; it did not see a `manual-` backup file and found an unexplained container `great_gagarin` (both open in the evidence log).
- Added for the next chat: `docs/CODE_MAP.md` (listed in `CLAUDE.md` 2 and `INDEX.md`), `MISTAKES_TO_AVOID.md` section N, a fuller `handoff.md`. `phase0.zip` was rebuilt from the final commit (same recipe as above).
- Next: fresh-session verification of Phase 0, then Phase 1 only after PASS.

## 2026-10-21 · phase1.1 · Phase 0 verification and fix pass, then Phase 1 build (checkpoint)
- Zip in: `phase0.zip`. Zip out: `D:\Projects\phase1.1.zip` (a checkpoint inside Phase 1: the chat ran short of room). Worktree `D:\Projects\Enderchest-phase-1`, branch `phase-1` from `d6b71fa` (no phase-0 tag existed, D-082). Windows `tar` zip route used.
- Phase 0: partial fresh-session verification (`docs/reviews/phase-0-verification.md`) found F-1 `backup.bat` broken, F-2 first-run rule with an unwritable backup folder, F-3 name regex, and (probe 16) F-4 hourly backups of an idle database. All fixed test-first (`phase0-fix:` commits), probes 15 and 16 added.
- Phase 1 built: profile and settings API, typed responses, app serving with the theme written in, boot page restyle, the whole frontend, browser tests (Playwright), probe 17, Docker stages, `test.bat` commands, `dev.bat` Vite.
- Failed and fixed on the way: double click made two backups; Chrome's `Asia/Calcutta`; selected chip invisible in light; misleading "Working" chip; menu link that did nothing. Docker Desktop stopped once mid-run; the owner restarted it.
- Not done: Phase 1 and Phase 0 fresh-session verification, owner approval of screenshots, `dev.bat` run, live `run.bat`.
- Next: see `handoff.md` "Next steps".
