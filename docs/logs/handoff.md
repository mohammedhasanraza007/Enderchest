# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase5v.zip`. The Phase 5 verification session unzipped it into `D:\Projects\Enderchest-phase-6\Enderchest` and made branch `phase-6` there (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Do not wait for "go". Keep `D:\Projects\enderchest-chain-state.txt` current (running at start; handing-off with the next step before `start_session`). UI bar "best" (D-097); `/design-sync` only after the Phase 9 final merge. Copy the rules into every next prompt. If `start_session` is refused, message the top session "Enderchest phase 0 foundation".
- Last built phase: **Phase 5 (Dashboard)**, Verification: **done for phase 5: PASS WITH NOTES** (N1 to N3 minor, `docs/reviews/phase-5-verification.md`). Next: Phase 6 build (prompt `D:\Projects\phase6-next-prompt.txt`). Phase 4: PASS WITH NOTES; Phases 0 to 3: PASS for Claude's part. Owner checks pending for all.
- Resume check: `git log --oneline -3` shows `pack: phase 5 verification (phase5v zip)` on top.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it. Time-box bugs: fix once, simply, with a test; a second failure goes to the evidence log.

## Next steps, in this order
1. **Phase 6 build** (Do I own this?, `docs/specs/phase-6-ownership.md`, branch `phase-6`); it fills the dashboard's `savings` pill.
2. Then the Phase 6 verification (fresh session).
3. Small TODOs any session may take: Phase 5 notes N1 to N3 (truck label "+1", 1024 px balance, truck on an empty road); Phase 4 notes N1 (snooze dialog corner), N2 (item actions at 1024 px); make `test.bat lint` cover `tests/e2e`; unload the OCR model after 10 idle minutes; Phase 2 notes N5 to N7; Phase 3 notes N1 to N3.

## Current state (facts)
- Phase 5 built: `GET /dashboard`, `/dashboard/rings/{ring}`, `/dashboard/road?days=` from one service (`services/dashboard.py`, formulas in `derived.py`); the dashboard at `/` (greeting, rings, Needs attention reusing `ReminderList`, 14-day road with truck, breakdown sheet, empty/loading/error); the 30-day road on Tasks; storyboard fixtures 1 to 3 (test stack only); body `flow-root` fix for a 50 px page scroll on every page.
- Verification re-run (2026-10-25): all suites green again, plus 20 new integration probes (`test_phase5_verification.py`) and `dashboard-keyboard.spec.ts`. Build results: lint clean; unit 207 + 83; integration 255; Playwright 107 + 3; probes 1 to 23 ALL PASSED; contrast 0 failures (14 routes, 515 pieces per theme); crawler 0 dead controls incl. `/`; dashboard 12.4 ms median on 1,000 items; reference frame within 7 px except the last road tick (−17 px, noted).
- Decisions up to D-113. Failure kinds up to F-039 (none added).
- Schema 3 (no migration in Phase 5). The live stack is untouched (still Phase 1 code until the owner runs `build.bat`).

## Owner runs next
1. `build.bat`, then `run.bat` (the live app moves to the Phase 4 code; migrations 0002 and 0003 run after verified pre-migration backups).
2. **Phase 4 acceptance (3 minutes):** create a task due today and an item expiring tomorrow; open the app and see both under the bell; mark one done, snooze one; Settings → Notifications → "Allow browser notifications", then "Send a test notification" and check the system alert appears (an Enderchest tab must be open).
3. **Phase 5 acceptance (3 minutes):** `dev.bat`, load the storyboard (or your own data), open `/`, compare with the reference, click the rings, use an item from Needs attention. Look at `docs/logs/raw/phase-5/shots/*.png` too.
4. Look at `docs/logs/raw/phase-4/shots/*.png` (and the Phase 1 to 3 shots) and say "approved" or what looks wrong.
5. Still open from Phase 3: gate 2 (20 webcam photos, `labels.csv`, `.\test.bat bakeoff`), gate 4 (Gemini key, or a written waiver), the Phase 3 acceptance; notes N1 to N3.
6. Still open from earlier phases: Phase 2 acceptance (webcam, printed label), Back up now and `backup.bat` on live, `.\test.bat probes -Only "4,9" -Live`, `restore.bat` once; optional: delete stray container `great_gagarin`.

## Known issues to carry
- Browser notifications need an open Enderchest tab (said in the UI); a closed browser shows nothing (idea O-007). The browser test runs on Chromium's new headless mode: the headless shell always reports "denied".
- An owner's write landing in the same moment as a timed reconcile is seen by the backup "changed" rule only at the next change or the daily backup (D-108, like D-083).
- The OCR engine and its 1600 px edge are provisional until gate 2; the Gemini request shape is unverified until gate 4.
- Search case-folding is ASCII-only (D-098). Category and place counts include used, expired and discarded items (N9, still to decide). Offset cursor paging can shift one tile (CODE_MAP 5).
- Throwaway test volumes and the images `enderchest-p1verify`, `enderchest-bakeoff` (3.3 GB) are kept by design; never delete volumes. Never leave a shell's working folder inside `test-results`. Never edit `test.bat` while it runs.

## How to work on this laptop
- Owner's laptop: Ryzen 5 5500 (6 cores), 16 GB RAM, AMD RX 6600 LE: small CPU models only.
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`. Claude's guard denies any command containing the live volume's name, volume removal, prune or `down -v`; retagging `enderchest-app:latest` is refused too. Use full paths.
- `.\test.bat <what>` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`. The browser suite takes about 13 minutes, the probes about 25; run long jobs in the background and wait inside your own turn (PowerShell `Wait-Process` on the cmd's id works; foreground sleep is blocked).
- Quick loops without rebuilding: `docker run --rm -v <repo>/backend:/app -w /app enderchest-tools:latest pytest …`; Playwright specs with `-v <repo>/tests/e2e:/tests/e2e` on `docker compose … --profile e2e run --rm e2e npx playwright test <spec>`. Prettier on files outside `frontend/` needs `--config /frontend/.prettierrc.json`.
- The Windows zip route is proven (`docs/PROCESS.md` 7: clone first, `tar -a -c -f ... -T zip-list.txt`).
