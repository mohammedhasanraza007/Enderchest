# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase7v.zip`. The Phase 7 verification session unzipped it into `D:\Projects\Enderchest-phase-8\Enderchest` and made branch `phase-8` there (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Do not wait for "go". Keep `D:\Projects\enderchest-chain-state.txt` current. UI bar "best" (D-097); `/design-sync` only after the Phase 9 final merge. If `start_session` is refused, message the top session "Enderchest phase 0 foundation".
- Last built phase: **Phase 7 (camera coach)**, Verification: **done for phase 7, PASS WITH NOTES** (`docs/reviews/phase-7-verification.md`; only a too-tight e2e bound fixed, no product change). Phase 6: PASS WITH NOTES; Phases 4, 5: PASS WITH NOTES; 0 to 3: PASS for Claude's part. Owner checks pending for all.
- Resume check: `git log --oneline -3` shows `pack: phase 7 verification (phase7v zip)` on top.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it. Time-box bugs: fix once, simply, with a test; a second failure goes to the evidence log.

## Next steps, in this order
1. **Phase 8 build** (polish and motion, `docs/specs/phase-8-polish.md`, branch `phase-8`; D-124 left the shutter fill ring and the pill's entrance to it).
2. Then the Phase 8 verification.
3. Small TODOs: Phase 7 notes N1, N2; unload OCR and embedding models after 10 idle minutes; Phase 6 notes N4 to N6; Phase 5 N1 to N3; Phase 4 N1, N2; Phase 2 N5 to N7; Phase 3 N1 to N3.

## Current state (facts)
- Phase 7 built: `POST /capture/frame` (in memory, never stored, 200 KB JPEG, `rate_limited` within 0.5 s, `busy` while the heavy worker has any job via `heavy.try_submit`, D-121); client tier every video frame on 320 px (`lib/coach.ts`), one 640 px frame about once a second when lit and sharp; prompt machine (300 ms hold, 1.5 s minimum, D-122); chips for model and date; Settings → Camera coach toggle (`coach_enabled`, no migration, schema 4); coach in Add and own modes only (D-120).
- Owner request during the build (D-126): cameras found and switched by themselves (devicechange, auto-start, exact-black cameras skipped on opening, Switch camera button, phone-app hint). Camera view capped at 58vh so the pill and shutter fit a laptop screen.
- Decisions D-120 to D-126 (brief `docs/reviews/phase-7-brief.md`). D-125: "move closer" at 3.5% box height (RapidOCR pads boxes).
- Final runs: lint clean; unit 258 + 108; integration 328; e2e 143 + 3; probes 1 to 27 ALL PASSED (26: /health under frames, none stored; 27: ten frames at once read one).
- Real webcam used with the owner present (Iriun phone camera): covered lens → "dark" correctly; server 210 to 365 ms per frame; blurred photos of a screen are not detected as blurry (moiré). Frames kept out of git.
- The live stack is untouched (still Phase 1 code until the owner runs `build.bat`).

## Owner runs next
1. `build.bat`, then `run.bat` (live app moves to Phase 7 code; migrations 0002 to 0004 with verified pre-migration backups).
2. **Phase 7 gate 1 (BLOCKED):** photos of real product labels named `dark-01.jpg`, `shake-01.jpg`, `glare-01.jpg`, `empty-01.jpg`, `far-01.jpg`, `good-01.jpg` (two each is plenty) in `tests\fixtures\private\phase7\`, then `.\test.bat coach`; the table lands in `docs\logs\raw\phase-7\coach\`. Watch the blur threshold (80 looks low for real frames) and a white label reading as glare.
3. **Phase 7 gate 4 (5 minutes):** open Camera with your webcam, hold a label: dark corner, shake, far, close; check the prompts, the Switch camera button and that the picture stays smooth (60 fps). Settings → Camera coach off: no tips.
4. Phase 6 gate 1 (20 photos, `test.bat ownership`) and acceptance; Phase 5 and 4 acceptance; screenshot approval for Phases 1 to 7 (`docs/logs/raw/phase-7/shots/*.png`).
5. Still open from Phase 3: gate 2 (`test.bat bakeoff`), gate 4 (Gemini key or waiver); from Phase 2: acceptance, `backup.bat`, probes 4 and 9 with `-Live`, `restore.bat` once.

## Known issues to carry
- Coach thresholds are starting values (evidence log); blur by Laplacian variance does not catch blurred screen photos; a pure-white card can read as glare. Headless Chromium paints at 30 fps, so 60 fps is only provable on the owner's laptop.
- The built-in browser pane of the desktop app blocks camera access; real-camera checks run in a normal browser.
- Embedding model and thresholds provisional until Phase 6 gate 1 (D-115, D-119); OCR engine provisional until Phase 3 gate 2.
- Never leave a shell's working folder inside `test-results`. Never edit `test.bat` while it runs. Edit files with the editor tools, not shell here-documents (F-035 happened again with sed on test.bat; caught and reverted).

## How to work on this laptop
- Ryzen 5 5500, 16 GB RAM, RX 6600 LE: small CPU models only. Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`; never touch the live volume.
- `.\test.bat <what>` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`; one probe per `-Only`. The browser suite takes about 18 minutes, the probes about 25.
- Quick loops: `MSYS_NO_PATHCONV=1 docker run --rm -v <repo>/backend:/app -w /app enderchest-tools:latest pytest …`; one Playwright spec: `docker compose -f compose.test.yaml --profile e2e run --rm -v <repo>/tests/e2e:/tests/e2e -v <repo>/frontend/src:/frontend/src:ro e2e npx playwright test <spec>` after `build app` and `up -d --wait app`.
