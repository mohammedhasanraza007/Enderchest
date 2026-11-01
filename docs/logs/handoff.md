# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Folder: `D:\Projects\Enderchest-final\Enderchest`, branch `main`. Remote `github`: `mohammedhasanraza007/Enderchest` (private; the owner can make it public in GitHub's settings).
- All phases are built and verified, and the final merge's fixes are in. **Next task: finish the owner's full click-through of every control.** The workflow's four testers stopped at the weekly usage limit (2026-10-28) before writing any report, so no result exists. The prompt is `D:\Projects\final-ux-next-prompt.txt`; steps 2 and 3 are done, step 4 onward is not. `status: done` in the chain file, `ENDERCHEST-CHAIN-DONE.txt` and deleting the keeper task wait for that pass (the owner: "only then work done").
- Verification: phase 9 PASS WITH NOTES (`docs/reviews/phase-9-verification.md`). The final merge's fixes have tests but no separate verification report.
- Resume check: `git log --oneline -3` shows the `pack: final merge` commit on or near the top.

## What the final merge changed
- D-138: the save delivery follows the owner's video, compressed (`docs/reviews/delivery-video-comparison.md`).
- D-139: a pasted Gemini key is accepted in any shape Google could issue (the owner's real key was refused).
- D-140: word search also matches notes; the assistant is told how to answer a price question.
- D-141: a money question shows the named items' saved prices under the answer; prices still never go to Gemini.
- D-142, probe 29: installs on any drive, folder or Windows user name. `build.bat` crashed on a `)` in the user name and wrote `.env` in the old code page.
- Phase 6 N4: an unexpected error no longer ends the embedding loop.
- `release/`: the file list (`files.txt`) and README of the slim release zip. The root README is now the GitHub one, with images in `docs/images/`; the old pack README is `docs/history/README-pack-v5.1.md`.

## Results (`docs/logs/raw/final/`)
- `lint.log`, `unit.log`, `integration.log` exit 0. `e2e.log`: 175 passed, 6 failed.
- Five failures were my own `delivery-shots.spec.ts` leaving the test clock on 16 October (fixed); `e2e-rerun-lifecycle.log` 8 passed.
- The sixth is `coach.spec.ts` frame rate (median gap 49.9 ms, limit 35.4 ms) in the full run; `e2e-rerun-coach.log` 14 passed alone. A timing test that is sensitive to load; not investigated further. The whole e2e suite has not been re-run in one go since the clock fix.
- Probes 1 to 29: see `exit-codes.txt` and `probe-N.log`.
- Drive check (`raw/final-ux/`): real `build.bat`, `run.bat`, `backup.bat`, `stop.bat` from `C:\Ender Test (C drive)` with backups on D:, and from a virtual `Z:`. Passed. `restore.bat`'s prompts could not be driven (Docker holds redirected input during its listing), so its prompt path was not run here.

## Stacks and folders left from the tests (test data only; the owner may remove them)
- Running: `enderchest-ux` on 8472 (the owner's test copy, `D:\Projects\Enderchest-release-ux-4`, holds the owner's real Gemini key in its own volume `enderchest_ux_data`). Stopped: `enderchest-uxt1` to `uxt4` (ports 8473 to 8476), `enderchest-uxc` (8477, `C:\Ender Test (C drive)`).
- Volumes `enderchest_uxt_data_1` to `4`, `enderchest_uxc_data`. Backup folders `C:\Users\Admin\Enderchest-UX-Backups`, `Enderchest-UXT-Backups-1` to `4`, `D:\Projects\Ender UX Backups on D`. Zips `D:\Projects\enderchest-release*.zip`. Scratch: `D:\Projects\Ender Path Test (x86) & Co`.
- The isolation method: in an unzipped copy only, `.env` with its own port, backup folder and `COMPOSE_PROJECT_NAME`, plus a `compose.override.yaml` renaming the volume. Check `docker compose config` before running anything.

## Owner runs next
1. Live app: 8470 still runs the old image (schema 1) with the real profile, and has not been upgraded. Run `backup.bat`, then `build.bat` and `run.bat` from a clean copy, and check the profile survived.
2. `restore.bat` once on real prompts.
3. Real Gemini: `docker run --rm -e GEMINI_API_KEY -v <folder>\Enderchest\backend:/app -w /app enderchest-tools:latest pytest -q -s tests/live`. Phase 9 gates 1 to 3 stay BLOCKED until then (one real question and the price line were seen working on 8472).
4. Save the assistant reference image as `docs/design/reference-assistant.png`; screenshot approval of `/assistant` and the delivery (`docs/logs/raw/final/shots-delivery/`).
5. Decide the privacy line (phase 9 N2), and whether the repository goes public (no licence chosen yet).
6. Still open from earlier phases: Phase 8 60 fps, light mode and truck approval; Phase 7 and 6 gates; screenshot approval for Phases 1 to 8; acceptance runs; `test.bat bakeoff`.
7. After the click-through: run /design-sync in the merged main folder `D:\Projects\Enderchest-final\Enderchest`.

## How to work on this laptop
- Ryzen 5 5500, 16 GB, RX 6600 LE: small CPU models only. Never touch the live stack (127.0.0.1:8470) except read-only GETs; the test stack is 8471.
- Do not build next to a running suite: CPU contention times tests out. The test clock outlives `resetApp`: a spec that sets it must put it back.
- Computer use cannot click in browsers; use the built-in browser, which draws only while the Claude window is visible.
- Run `test.bat` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`; one probe per `-Only`. A targeted e2e: `docker compose -f compose.test.yaml --profile e2e run --rm e2e npx playwright test <spec names>` after building `app` and `e2e`.
- Edit with the editor tools, never shell here-documents (F-035).
