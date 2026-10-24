# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase2v.zip`. The Phase 2 verification session unzipped it into `D:\Projects\Enderchest-phase-3\Enderchest` and made branch `phase-3` there (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Do not wait for "go". Keep `D:\Projects\enderchest-chain-state.txt` current (running at start; handing-off with the next step before `start_session`). UI bar "best" (D-097); `/design-sync` only after the Phase 9 final merge. Copy the rules into every next prompt.
- Last closed phase: none formally. Phases 0, 1 and 2: verification PASS for Claude's part, owner checks pending (`docs/reviews/phase-2-verification.md`: no blocker or major; two minor defects fixed; notes N3 to N9).
- **Next task: the Phase 3 build (Capture), `docs/specs/phase-3-capture.md`** (prompt `D:\Projects\phase3-next-prompt.txt`).
- Resume check: `git log --oneline -3` shows `phase2-verify: checkpoint` on top.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it. Time-box bugs: fix once, simply, with a test; a second failure goes to the evidence log.

## Next steps, in this order
1. **Phase 3 build** (fresh session; brief first, then build; D-091 no "go").
2. Then the Phase 3 verification (fresh session, `PROCESS.md` 4, probe list first; re-run the relevant kinds in `docs/reviews/failure-checklist.md`, now F-001 to F-031).
3. Small TODOs any session may take: make `test.bat lint` cover `tests/e2e` (tsc and Prettier); the Phase 2 notes N5 (unknown draft shows only Retry), N6 (price hint "1240" reads like a value), N7 (layout nits at 1024 px).

## Current state (facts)
- Phase 2 (inventory) is built and verified: categories, locations, items, search and filters, photos, drafts and the add flow, QR labels, scan and typed lookup, Trash, permanent delete, undo (D-092 to D-096). Screens: Inventory, Item, item form, Camera (add and scan), review queue and confirm, Labels, Trash, Settings (Categories, Locations, Data).
- Fixed by the verification: search matches name, public id and attribute values, never keys (D-098, F-029); duplicate category and place names compare with casefold (D-098, F-030). New `tests/e2e/labels-print.spec.ts` checks the printed PDF (page sizes, page count, 21-up pitch) and decodes the served QR.
- Results on the final code: lint clean; 87 pytest + 58 vitest unit; 184 integration; Playwright main 69 + no-backups 3, plus labels-print 3; probes 1 to 19 ALL PASSED. First page of 100 from items-1000: 5 to 6 ms (budget 150).
- Live stack (read-only check): schema 1, Phase 1 code, `ok`. The upgrade to schema 2 was rehearsed on a throwaway volume made by the Phase 1 image: pre-migration backup first, name and settings kept, first run not repeated (V1).
- Decisions up to D-098. Failure kinds up to F-031.

## Owner runs next
1. `build.bat`, then `run.bat`: the live app migrates to schema 2 after a verified pre-migration backup (a `pre-migration-v1-to-v2-…` file appears in `%USERPROFILE%\Enderchest-Backups`).
2. Phase 2 acceptance (5 minutes, real hardware): add two items with your webcam; print one label on paper; hold it to the webcam in Scan mode and see the item open; delete an item, find it in Trash, restore it; stop and start the app and check everything is still there.
3. Look at `docs/logs/raw/phase-2/shots/*.png` (and Phase 1's `docs/logs/raw/phase-1/shots/*.png`) and say "approved" or what looks wrong; read the notes N3 to N9 in `docs/reviews/phase-2-verification.md` and say whether they can wait.
4. Still open from earlier phases: Back up now and `backup.bat` on live (a `manual-` file appears); `.\test.bat probes -Only "4,9" -Live`; `restore.bat` once on a backup you choose; optional: delete stray container `great_gagarin`.

## Known issues to carry
- Offset cursor paging can shift one tile if items change while scrolling (CODE_MAP 5). The scan and webcam tests use a canvas QR and Chromium's fake camera: regression only (D-056).
- Search case-folding is ASCII-only (D-098, N3). A hidden photo's file is still served by id (N4). Category and place counts include used, expired and discarded items: check against DATA_MODEL 3.3 when Phase 4 makes those states reachable (N9).
- Backup log times use the real clock, the app clock can be moved on the test stack: a probe that moves the clock must move it back before making a backup (F-031).
- Boot pages use system fonts (D-088). Dev reloads the whole page (D-086). `tests/fixtures/expiry_cases.csv` has CRLF (Phase 3 TODO).
- Throwaway test volumes (`enderchest_test_data_p10_*`, `_p11_*`, `_p13_*`, `_q1_*`, `_v1p_*`, old anonymous ones) and the image `enderchest-p1verify:latest` are kept by design; never delete volumes.
- Never leave a shell's working folder inside `test-results`. Bind-mount only folders that exist on both sides (F-028).

## How to work on this laptop
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`. Claude's guard denies any command containing the live volume's name, volume removal, prune or `down -v`; retagging `enderchest-app:latest` is refused too. Use full paths.
- `.\test.bat <what>` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"` (PowerShell's `Set-Location` does not move `cmd`), then read `$LASTEXITCODE`. The browser suite takes about 8 minutes, the probes about 15; run long jobs in the background and block on them inside your own turn (a turn started by a task notification cannot start sessions).
- A probe script can run inside the test app container (`docker cp`, `docker exec enderchest-test-app-1 python /tmp/x.py`; set `MSYS_NO_PATHCONV=1` in Git Bash): example `docs/logs/raw/phase-2v/probes_v.py`.
- The Windows zip route is proven (`docs/PROCESS.md` 7: clone first, `tar -a -c -f ... -T zip-list.txt`).
