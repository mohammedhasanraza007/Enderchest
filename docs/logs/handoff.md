# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase3.zip`. The Phase 3 build session unzipped it into `D:\Projects\Enderchest-phase-3v\Enderchest` and made branch `phase-3-verify` there (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Do not wait for "go". Keep `D:\Projects\enderchest-chain-state.txt` current (running at start; handing-off with the next step before `start_session`). UI bar "best" (D-097); `/design-sync` only after the Phase 9 final merge. Copy the rules into every next prompt. If `start_session` is refused, message the top session "Enderchest phase 0 foundation" (the owner's instruction, 2026-10-24).
- Last closed phase: none formally. Phases 0 to 2: verification PASS for Claude's part, owner checks pending. **Phase 3 (Capture) is built: Verification: pending for phase 3.**
- **Next task: the Phase 3 verification** (fresh session, `docs/PROCESS.md` 4, probe list first; prompt `D:\Projects\phase3v-next-prompt.txt`).
- Resume check: `git log --oneline -3` shows `phase3: checkpoint (phase3 zip)` on top.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it. Time-box bugs: fix once, simply, with a test; a second failure goes to the evidence log.

## Next steps, in this order
1. **Phase 3 verification** (fresh session; re-run everything, probes 1 to 21; add the build's failure kinds to `docs/reviews/failure-checklist.md`, see MISTAKES_TO_AVOID section O).
2. Then the Phase 4 build (Lifecycle), `docs/specs/phase-4-lifecycle.md`: it reads Gemini's suggested inspection interval from `drafts.gemini_result` through `committed_item_id` (D-102).
3. Small TODOs any session may take: make `test.bat lint` cover `tests/e2e` (tsc and Prettier; several older spec files are not Prettier-formatted); unload the OCR model after 10 idle minutes (ARCHITECTURE 6 allows it; about 410 MB stays resident); the Phase 2 notes N5, N6, N7.

## Current state (facts)
- Phase 3 built: expiry parser (35/35 supplied cases plus 10 more), local OCR (RapidOCR 3.10 on ONNX Runtime, provisional, D-099) in the shared size-1 `heavy` worker, field extraction (name, model, size, expiry), readings queued on draft creation and by Re-read (D-100), Gemini over REST with the key file, modes off/ask/auto, photos only when shared (D-101, D-102), the confirm screen with source tags, confidence dots, the "What was read" drawer, expiry confirmation and date pills, the queue's read names, Settings → Gemini. Bake-off harness `scripts/ocr_bakeoff.py` and image target `bakeoff` (`test.bat bakeoff`; all four engines load, models baked in).
- Results on the final code: lint clean; unit 160 pytest + 65 vitest; integration 198; Playwright main 82 + no-backups 3; probes 1 to 21 ALL PASSED (20: a photo read with no network, Gemini "could not be reached"; 21: `/health` median 3.4 ms, max 75.5 ms while three readings queued, readings 0.4 to 1.4 s).
- Decisions up to D-102. Failure kinds up to F-031 (the verification adds the build's).
- No migration in Phase 3 (the drafts table already had the reading columns). Live stack untouched (still Phase 1 code, schema 1, until the owner runs `build.bat`).

## Owner runs next
1. **Gate 2:** take 20 photos with the webcam as `tests/fixtures/README.md` says, put them and `labels.csv` in `tests\fixtures\private\phase3\`, correct every row, say "labels confirmed", then run `.\test.bat bakeoff` (offline; the table lands in `docs\logs\raw\phase-3\bakeoff\`). If another engine wins, only `backend/app/integrations/ocr/engine.py` changes (D-099).
2. **Gate 4 (optional):** Settings → Gemini: paste your key (Google AI Studio), choose "Ask each time", press "Test connection"; then on a confirm screen press "Improve with Gemini". Or write that you waive it.
3. `build.bat`, then `run.bat` (the live app moves to the Phase 3 code; schema 2 migration from Phase 2 runs first if not done yet, after a verified pre-migration backup).
4. Phase 3 acceptance (5 minutes): add three real items with the webcam; open "What was read"; correct a wrong field; confirm a date; check the saved item.
5. Look at `docs/logs/raw/phase-3/shots/*.png` (and the Phase 1 and 2 shots) and say "approved" or what looks wrong.
6. Still open from earlier phases: Phase 2 acceptance (webcam, printed label), Back up now and `backup.bat` on live, `.\test.bat probes -Only "4,9" -Live`, `restore.bat` once; optional: delete stray container `great_gagarin`.

## Known issues to carry
- The OCR engine and its 1600 px edge are provisional until gate 2. Drawn labels read perfectly; real packs will not (curved, glossy, small print): expect lower confidence and more "Not confirmed" taps.
- The Gemini request shape (`responseSchema` with `nullable`) is unverified against the real service until gate 4.
- Search case-folding is ASCII-only (D-098, N3). A hidden photo's file is still served by id (N4). Category and place counts include used, expired and discarded items (N9, check in Phase 4).
- Backup log times use the real clock while the test clock can move (F-031). Offset cursor paging can shift one tile (CODE_MAP 5).
- Throwaway test volumes (`enderchest_test_data_p10_*`, `_p11_*`, `_p13_*`, `_p20_*`, `_q1_*`, `_v1p_*`, old anonymous ones) and the images `enderchest-p1verify:latest`, `enderchest-bakeoff:latest` (3.3 GB with PyTorch; the app test image is 752 MB; remove with `docker image rm enderchest-bakeoff` once the bake-off is done) are kept by design; never delete volumes.
- Never leave a shell's working folder inside `test-results`. Bind-mount only folders that exist on both sides (F-028). Never edit `test.bat` while it runs.

## How to work on this laptop
- Owner's laptop: Ryzen 5 5500 (6 cores), 16 GB RAM, AMD RX 6600 LE: small CPU models only.
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`. Claude's guard denies any command containing the live volume's name, volume removal, prune or `down -v`; retagging `enderchest-app:latest` is refused too. Use full paths.
- `.\test.bat <what>` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`, then read the exit code. The browser suite takes about 12 minutes, the probes about 20; run long jobs in the background and wait inside your own turn.
- Probe scripts can run inside a container (`docker cp`, `docker exec`): `backend/tests/probes/capture_probe.py` (probes 20, 21).
- The Windows zip route is proven (`docs/PROCESS.md` 7: clone first, `tar -a -c -f ... -T zip-list.txt`).
