# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase6v.zip`. The Phase 6 verification session unzipped it into `D:\Projects\Enderchest-phase-7\Enderchest` and made branch `phase-7` there (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Do not wait for "go". Keep `D:\Projects\enderchest-chain-state.txt` current (running at start; handing-off with the next step before `start_session`). UI bar "best" (D-097); `/design-sync` only after the Phase 9 final merge. Copy the rules into every next prompt. If `start_session` is refused, message the top session "Enderchest phase 0 foundation".
- Last built phase: **Phase 6 (Do I own this? and savings)**, Verification: **done for phase 6, PASS WITH NOTES** (`docs/reviews/phase-6-verification.md`, N1 to N6). Next: **Phase 7 build** (prompt `D:\Projects\phase7-next-prompt.txt`). Phase 5: PASS WITH NOTES; Phase 4: PASS WITH NOTES; Phases 0 to 3: PASS for Claude's part. Owner checks pending for all.
- Resume check: `git log --oneline -3` shows `pack: phase 6 verification (phase6v zip)` on top.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it. Time-box bugs: fix once, simply, with a test; a second failure goes to the evidence log.

## Next steps, in this order
1. **Phase 7 build (camera coach)** (fresh session, branch `phase-7`, spec `docs/specs/phase-7-coach.md`, decisions from D-120).
2. Then the Phase 7 verification.
3. Small TODOs any session may take: unload the OCR and embedding models after 10 idle minutes; Phase 6 notes N4 to N6; Phase 5 notes N1 to N3; Phase 4 notes N1, N2; make `test.bat lint` cover `tests/e2e`; Phase 2 notes N5 to N7; Phase 3 notes N1 to N3.

## Current state (facts)
- Phase 6 built: migration 0004 (`savings`); DINOv2-small ONNX embeddings for every live photo by a background job (`scheduler/embeddings.py`, backfill included); `POST /ownership/check` (OCR + words + embedding, spec scoring table in `services/ownership_rules.py`, High / Medium / Possible, at most 5, active items only, writes nothing, no Gemini); savings `POST/GET/DELETE /savings` with Undo; the dashboard `savings` and the road pill on today; `/camera?mode=own` and `/savings`; nav gains Savings.
- Decisions D-114 to D-119 (brief `docs/reviews/phase-6-brief.md`; D-119 clarified by the verification: a look-alike whose size differs stays hidden). Failure kinds up to F-042.
- The Phase 6 verification fixed: "10,000 mAh" and "2 in 1" in size reading, the D-119 lift with a different size, focus return from the price sheet, the pill's stem over a truck on today; DATA_MODEL 2.11 event names. Its own probes: 28 unit, 32 integration, 7 browser.
- Final runs (after the verification's fixes): lint clean; unit 246 + 87; integration 320; probes 1 to 25 ALL PASSED; full e2e 117 + 3 before the fixes, then the Phase 6, dashboard, crawler, contrast and shell-reference specs (32) after them.
- Schema 4. The live stack is untouched (still Phase 1 code until the owner runs `build.bat`).

## Owner runs next
1. `build.bat`, then `run.bat` (the live app moves to the Phase 6 code; migrations 0002 to 0004 run after verified pre-migration backups; the image now holds the 88 MB embedding model, fetched once with a checksum).
2. **Phase 6 gate 1 (BLOCKED until then):** put 10 owned photos (`owned-NN-name.jpg`) and 10 not-owned (`not-owned-NN-name.jpg`) in `tests\fixtures\private\phase6\` with `labels.csv` (`file,public_id`, blank for not owned), press Back up now, then `.\test.bat ownership`; the table lands in `docs\logs\raw\phase-6\ownership\`. Include a not-owned product with a near-identical model number and the same name (verification N1: the look-alike +15 can turn Medium into a false High).
3. **Phase 6 acceptance (5 minutes):** Camera → Do I own this?, paste a product photo for something you own and something you do not, check both, record one saving and remove it on Savings. Look at `docs/logs/raw/phase-6/shots/*.png`.
4. **Phase 5 acceptance (3 minutes):** `dev.bat`, load the storyboard (or your own data), open `/`, compare with the reference, click the rings, use an item from Needs attention.
5. **Phase 4 acceptance (3 minutes):** a task due today and an item expiring tomorrow, see both under the bell, mark one done, snooze one, allow browser notifications and send a test one.
6. Look at the shots of Phases 1 to 5 and say "approved" or what looks wrong.
7. Still open from Phase 3: gate 2 (20 webcam photos, `labels.csv`, `.\test.bat bakeoff`), gate 4 (Gemini key, or a written waiver); from Phase 2: acceptance (webcam, printed label), Back up now and `backup.bat` on live, `.\test.bat probes -Only 4` and `-Only 9` with `-Live`, `restore.bat` once; optional: delete stray container `great_gagarin`.

## Known issues to carry
- The embedding model and its thresholds (0.80 / 0.70) are provisional until gate 1 (D-115); DINOv2 cosines run high (two different text labels 0.97), so unrelated label photos can show as Possible "Looks similar", and a look-alike alone is at most Possible (D-119). With the starting points only a model match reaches High; O/0 model misreads score 0 (verification N1 to N3). MobileNetV3-small and CLIP are compared then with `ownership_measure.py --model`.
- Browser notifications need an open Enderchest tab (said in the UI). The browser test runs on Chromium's new headless mode.
- A timed reconcile or embedding write on an idle database never fires the backup "changed" rule (D-108); an owner's write in the same moment is seen at the next change or the daily backup.
- The OCR engine and its 1600 px edge are provisional until gate 2; the Gemini request shape is unverified until gate 4.
- Search case-folding is ASCII-only (D-098). Category and place counts include used, expired and discarded items (N9). Offset cursor paging can shift one tile.
- Throwaway test volumes and the images `enderchest-p1verify`, `enderchest-bakeoff` (3.3 GB) are kept by design; never delete volumes. Never leave a shell's working folder inside `test-results`. Never edit `test.bat` while it runs.

## How to work on this laptop
- Owner's laptop: Ryzen 5 5500 (6 cores), 16 GB RAM, AMD RX 6600 LE: small CPU models only.
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`. Claude's guard denies any command containing the live volume's name, volume removal, prune or `down -v`; retagging `enderchest-app:latest` is refused too. Use full paths.
- `.\test.bat <what>` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`; write each log file name out in full (a shell variable inside the cmd string was not expanded in Phase 6). `-Only 24,25` through cmd splits at the comma: run one probe number per call. The browser suite takes about 17 minutes, the probes about 25; wait inside your own turn (PowerShell `Wait-Process` on the cmd's id).
- Quick loops: `MSYS_NO_PATHCONV=1 docker run --rm -v <repo>/backend:/app -w /app enderchest-tools:latest pytest …` (Git Bash rewrites `/app` without it); Playwright specs with `-v <repo>/tests/e2e:/tests/e2e` on `docker compose -f compose.test.yaml --profile e2e run --rm e2e npx playwright test <spec>`.
- The Windows zip route is proven (`docs/PROCESS.md` 7: clone first, `tar -a -c -f ... -T zip-list.txt`).
