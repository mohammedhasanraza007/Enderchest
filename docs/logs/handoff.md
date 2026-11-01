# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- The chain is finished. Folder: `D:\Projects\Enderchest-final\Enderchest`, branch `main`, remote `github`: public at https://github.com/mohammedhasanraza007/Enderchest.
- There is no next build task. Pick up only from "Owner runs next" or a new owner request.

## What the final merge changed (D-138 to D-151)
- Save delivery follows the owner's video (D-138). Any Gemini key shape (D-139). Notes in search and saved prices shown locally (D-140, D-141).
- Install: any drive and user name (D-142); `build.bat` and `run.bat` keep a `logs\*.txt` and keep the window open (D-143, D-145); `build.bat` installs Docker Desktop and WSL after one question (D-148, `scripts/install-docker.ps1`).
- Click-through fixes: D-144, D-146, D-149, D-150; reports in `docs/reviews/final-ux/`.
- Gemini waits 60 s per call, 120 s per turn; empty inventory says so; `run.bat` waits for a busy port (D-151).
- `release/files.txt` and `release/README.md` make the slim zip. The old pack README is `docs/history/README-pack-v5.1.md`.

## Results
- `docs/logs/raw/final-2/`: e2e 200 passed in one run (`e2e-full-2.log`). Lint, unit: clean on the code before the last test-only fix. Integration and probes 1 to 29 passed on commit `ed36de1`; after that only the backend tests touched, lint, unit and probe 29 were re-run.
- Click-through (`docs/reviews/final-ux/`): 313 controls, 276 passed, 24 real issues fixed. The Group 1 to 3 fixes were tested by specs, not by a second click-through.
- Second PC: Windows 11 laptop with no Docker or WSL, using commit `5db9e9f`: `build.bat` installed Docker, then after a restart and Docker sign-in it built and ran. It held an earlier backup, so it was not fully clean, and it showed the recovery page once. Commit `6b16214` has not been re-run there.
- `run.bat` waiting on a busy port after `stop.bat`: not observed; the port was free in the real re-test.

## Owner runs next
1. GitHub two-factor login, required by 2026-11-11. Choose a licence if others may reuse the code.
2. `git pull` on the laptop, rebuild, and check the 60-second Gemini wait there.
3. Checks needing real hardware or a person: camera and QR scanning, printing, upload through the file picker, photo-based ownership check, `restore.bat`'s prompts, browser notifications, a completely clean PC.
4. Real Gemini gates: `docker run --rm -e GEMINI_API_KEY -v <folder>\Enderchest\backend:/app -w /app enderchest-tools:latest pytest -q -s tests/live`.
5. Run /design-sync in the merged main folder `D:\Projects\Enderchest-final\Enderchest`.
6. Decide the privacy line (phase 9 N2); screenshot approvals; `test.bat bakeoff`.

## Known gaps
- Leaving Settings with an unsaved edit does not ask: `BrowserRouter` has no blocker.
- Welcome in light and at 1024 px, boot pages, Undo after Use it and Mark expired, permanent delete with no recent backup, and bulk delete were not exercised by hand.
- The live app on 8470 was upgraded by the owner from `E:\Enderchest-main` (schema 4, pre-migration backup made); inventory is empty there.

## Left from the tests (test data; the owner may remove them)
- Running: `enderchest-ux` on 8472 (`D:\Projects\Enderchest-release-ux-4`, holds the owner's real key in its own volume). Stopped: `enderchest-uxa`, `uxc`, `uxt1` to `uxt4`.
- Volumes `enderchest_ux_data`, `enderchest_uxa_data`, `enderchest_uxc_data`, `enderchest_uxt_data_1` to `4`. Backup folders `C:\Users\Admin\Enderchest-UX*`, `D:\Projects\Ender UX Backups on D`. Folders `D:\Projects\Enderchest-ux-*`, `Enderchest-uxt*`, `Enderchest-release-ux*`, `Enderchest-clone-check`, `Ender Path Test (x86) & Co`, `C:\Ender Test (C drive)`. Zips `D:\Projects\enderchest-release*.zip`.

## How to work on this laptop
- Never touch the live stack (127.0.0.1:8470) except read-only GETs; the test stack is 8471. Probe 7 needs port 8472 free.
- Do not build next to a running suite. The test clock outlives `resetApp`: a spec that sets it must put it back.
- Computer use cannot click in browsers; the built-in browser draws only while the Claude window is visible. Scripts run by automation: set `ENDERCHEST_NO_PAUSE=1` and `ENDERCHEST_NO_INSTALL=1`.
