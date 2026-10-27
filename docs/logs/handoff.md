# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase8v.zip`, unzipped into `D:\Projects\Enderchest-phase-9\Enderchest` on branch `phase-9` (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Keep `D:\Projects\enderchest-chain-state.txt` current. UI bar "best" (D-097); `/design-sync` only after the Phase 9 final merge. If `start_session` is refused, message the top session "Enderchest phase 0 foundation". The owner makes reference images with Gemini on request: ask, never guess a visual (D-132).
- Last built phase: **Phase 8 (polish and motion)**, Verification: **done for phase 8, PASS WITH NOTES** (`docs/reviews/phase-8-verification.md`, N1 to N3 minor). Phase 7, 6, 5, 4: PASS WITH NOTES; 0 to 3: PASS for Claude's part. Owner checks pending for all.
- Resume check: `git log --oneline -3` shows `pack: phase 8 verification (phase8v zip)` on top.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it.

## Next steps, in this order
1. **Phase 9 build** (assistant; `docs/specs/phase-9-assistant.md`; `docs/design/reference-assistant.md`; no `reference-assistant.png` saved yet). Gemini key needed for its real gate: BLOCKED; tests use a recorded fake only.
2. Phase 9 verification, then the final merge on `main`.
3. Small TODOs: Phase 8v N1 (reopen history for the streak, needs a migration), N2 (item actions wrap at 1280); lazy-load camera modules; Phase 7 N1, N2; unload OCR and embedding models after 10 idle minutes; older notes as before.

## Current state (facts)
- Phase 8 built (brief `docs/reviews/phase-8-brief.md`, D-127 to D-132): streak `{days}` on `GET /dashboard` (shown from 2 days, never a break); dashboard entrance once per tab session (any input ends it), ring sweep and glide by `stroke-dashoffset`, count-up on real changes, one flare per improved ring, milestone delivery (7, 30, 100 days); truck on a clipped transform lane, wheels turn only while moving; reminder rows slide out; page arrival on route change; save delivery from the road truck to the logo; shutter fill ring and coach pill lift (D-124); hover colour fades removed; item page one action row and History empty state.
- Suites: lint clean; unit 273 + 114; integration 332; e2e 150 + the coach fix (re-run 31 passed); probes 1 to 27 ALL PASSED. Bundle 203 KB gzipped.
- The live stack is untouched (still Phase 1 code until the owner runs `build.bat`).

## Owner runs next
1. `build.bat`, then `run.bat` (live app moves to Phase 8 code).
2. **Phase 8 (BLOCKED):** open the dashboard on the laptop: the entrance, a "Use it" on a card row and saving a new item should all feel smooth (60 fps); approve light mode and the truck from `docs/logs/raw/phase-8/shots/` (O-003, O-005) or say what to change.
3. Phase 7 gate 1 label photos and gate 4 live check; Phase 6 gate 1 and acceptance; screenshot approval for Phases 1 to 8.
4. Still open from Phases 2 and 3: acceptance, `backup.bat`, `restore.bat` once, `test.bat bakeoff`, a Gemini key (needed for Phase 9 too).

## Known issues to carry
- Coach thresholds are starting values (evidence log); blur by Laplacian variance does not catch blurred screen photos; a pure-white card can read as glare. Headless Chromium paints at 30 fps, so 60 fps is only provable on the owner's laptop.
- The built-in browser pane of the desktop app blocks camera access; real-camera checks run in a normal browser.
- Embedding model and thresholds provisional until Phase 6 gate 1 (D-115, D-119); OCR engine provisional until Phase 3 gate 2.
- Never leave a shell's working folder inside `test-results`. Never edit `test.bat` while it runs. Edit files with the editor tools, not shell here-documents (F-035 happened again with sed on test.bat; caught and reverted).

## How to work on this laptop
- Ryzen 5 5500, 16 GB RAM, RX 6600 LE: small CPU models only. Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`; never touch the live volume.
- `.\test.bat <what>` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`; one probe per `-Only`. The browser suite takes about 18 minutes, the probes about 25.
- Quick loops: `MSYS_NO_PATHCONV=1 docker run --rm -v <repo>/backend:/app -w /app enderchest-tools:latest pytest …`; one Playwright spec: `docker compose -f compose.test.yaml --profile e2e run --rm -v <repo>/tests/e2e:/tests/e2e -v <repo>/frontend/src:/frontend/src:ro e2e npx playwright test <spec>` after `build app` and `up -d --wait app`.
