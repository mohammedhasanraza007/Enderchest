# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase2.zip`. The Phase 2 build session unzipped it into `D:\Projects\Enderchest-phase-2v\Enderchest` and made branch `phase-2-verify` there (D-091). Never unzip over an existing repo or worktree (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase N, a fresh session verifies Phase N, a fresh session builds Phase N+1, up to Phase 9; then one session on `main` merges, rebuilds and fixes bugs. Do not wait for "go". Keep `D:\Projects\enderchest-chain-state.txt` current (running at start; handing-off with the next step before `start_session`). UI bar "best" (D-097); `/design-sync` only after the Phase 9 final merge. Copy the rules into every next prompt.
- Last closed phase: none formally. Phases 0 and 1: verification PASS for Claude's part, owner checks pending. **Phase 2: built; `Verification: pending for phase 2`** (next session).
- Resume check: `git log --oneline -3` shows `phase2: checkpoint` on top.
- Do not rebuild what exists. Read `docs/CODE_MAP.md` and extend through it. Time-box bugs: fix once, simply, with a test; a second failure goes to the evidence log.

## Next steps, in this order
1. **Phase 2 verification** (fresh session, `PROCESS.md` 4, probe list first; prompt `D:\Projects\phase2v-next-prompt.txt`). Brief: `docs/reviews/phase-2-brief.md`. Screenshots to judge: `test-results/shots-phase-2/` (regenerate with `tests/e2e/inventory-shots.spec.ts`).
2. Then the Phase 3 build (`docs/specs/phase-3-capture.md`).
3. Small TODO any session may take: make `test.bat lint` cover `tests/e2e` (tsc and Prettier).

## Current state (facts)
- Built in Phase 2: migration 0002 (categories, locations, items, photos, drafts, events); categories and locations with tree rules; items with search, filters, cursor paging, edit, soft delete, 60 s undo (D-092), Trash, permanent delete (typed DELETE, backup under 24 h, photo files removed, D-096); photo pipeline (12 MB, HEIC refused, EXIF upright then stripped, 2560 px, 320 px thumbs, 12 per item); drafts and the add flow; QR labels (segno), label-printed, lookup with typed forms; first-run step marker and P-01 step 2 (D-093); multipart paths and body caps (D-095); start-up sweep of stray photo files; `items-1000` fixture. Screens: Inventory (virtualised), Item, item form sheet, Camera (add and scan, jsQR), review queue and confirm, Labels (A4 3 × 7 and 50 × 30 mm, print stylesheet), Trash, Settings Categories/Locations/Data; nav Inventory and Camera with LIVE badge.
- Fixed this session: a per-thread DB connection shared by two requests (now one per request, Phase 1 code); a committed empty `backend/scripts/export_openapi.py`; stale throwaway volumes in `test.bat e2e` (no-backups app) and probe 13.
- Results on the final code: lint clean; 87 pytest + 58 vitest unit; 182 integration; Playwright main 69 + no-backups 3; probes 1 to 19 PASS (13 after its fix). Budgets: first page 7 ms (150), 6.4 MB upload 328 ms (1.5 s).
- Decisions D-092 to D-097 are this session's.

## Owner runs next
1. `build.bat`, then `run.bat`: the live app migrates to schema 2 after a verified pre-migration backup (a `pre-migration-v1-to-v2-…` file appears in `%USERPROFILE%\Enderchest-Backups`).
2. Phase 2 acceptance (5 minutes, real hardware): add two items with your webcam; print one label on paper; hold it to the webcam in Scan mode and see the item open; delete an item, find it in Trash, restore it; stop and start the app and check everything is still there.
3. Look at `test-results/shots-phase-2/*.png` (and Phase 1's `docs/logs/raw/phase-1/shots/*.png`) and say "approved" or what looks wrong.
4. Still open from earlier phases: Back up now and `backup.bat` on live (a `manual-` file appears); `.\test.bat probes -Only "4,9" -Live`; `restore.bat` once on a backup you choose; optional: delete stray container `great_gagarin`.

## Known issues to carry
- Offset cursor paging can shift one tile if items change while scrolling (CODE_MAP 5). The scan and webcam tests use a canvas QR and Chromium's fake camera: regression only (D-056).
- Boot pages use system fonts (D-088). Dev reloads the whole page (D-086). `tests/fixtures/expiry_cases.csv` has CRLF (Phase 3 TODO).
- Throwaway test volumes (`enderchest_test_data_p10_*`, `_p11_*`, `_p13_*`, `_q1_*`, old anonymous ones) are kept by design; never delete volumes.
- Never leave a shell's working folder inside `test-results` (Windows locks it and Playwright cannot clean it). Bind-mount only folders that exist on both sides (a single-file mount inside a mounted folder leaves an empty placeholder in the repo).

## How to work on this laptop
- Docker Desktop is `D:\DockerDesktop\Docker Desktop.exe`. Claude's guard denies any command containing the live volume's name, volume removal, prune or `down -v`; retagging `enderchest-app:latest` is refused too. Use full paths.
- `.\test.bat <what>` through `cmd /c "... > file 2>&1"`, then read `$LASTEXITCODE`. The browser suite takes about 8 minutes (the crawler 6); run long jobs in the background and block on them inside your own turn (a turn started by a task notification cannot start sessions).
- The Windows zip route is proven (`docs/PROCESS.md` 7: clone first, `tar -a -c -f ... -T zip-list.txt`).
