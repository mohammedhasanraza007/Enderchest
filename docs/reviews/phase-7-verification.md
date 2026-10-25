# Phase 7 verification — Camera coach

Fresh session, 2026-10-25, branch `phase-7-verify`, on the code of `phase7.zip` (`aeff652`). Read sceptically: the build was written by the same model family.

## Probe list (written before running anything)
1. A frame never queues behind a draft reading (busy at once); the page never has two frames in flight.
2. Coach off: zero `/capture/frame` requests and no pill, also after toggling while on the Camera page.
3. Scan mode never sends a frame.
4. A frame is never written to `/data` or upload-tmp, including refused ones: PNG, over 200 KB, over 1280 px, truncated, empty.
5. One error shape; `rate_limited` is decided before `busy`; a `busy` refusal does not use up the 0.5 s gap.
6. An OCR failure inside a frame frees the worker (no permanent `busy`).
7. Prompt priority dark > blur > glare > no text > far > found; 300 ms hold and 1.5 s minimum (no flicker).
8. D-125: 3.5% "move closer" rule on padded OCR boxes; flat frames say "no label" and are not sent.
9. The pill is a polite live region and readable in both themes over any video.
10. Chips land on the right lines under `object-fit: cover` with a 4:3 camera.
11. D-126: exact-black cameras skipped only on opening, never when the owner picked one; devicechange auto-start; Switch camera only with two or more cameras; front/back naming.
12. Reduced motion; Gemini never called; `/health` under 200 ms while frames are read.
13. The camera view fits 1280x720 and 1024 wide with pill and shutter visible.

## How each probe was tested
- 1, 4 (PNG, >200 KB, stored), 5 (rate_limited, busy), 12 (/health, ten frames) — the build's integration tests and probes 26, 27, re-run here.
- 4 (empty, truncated, >1280 px), 5 (busy keeps the gap free), 6 — new: `backend/tests/unit/test_coach_verify.py` (V1 to V6), all pass. Code read: `rate_limited` is checked under the lock before `try_submit`; `_last_accepted` is set only after a job starts; `heavy._start` counts out in `finally`.
- 2, 3, 7, 8, 9, 10, 11, 13 — the build's vitest and Playwright coach specs, re-run here; code read of `useCoach.ts` (the effect's cleanup aborts the request and clears the pill; `active` is false in Scan mode and when `coach_enabled` is off) and `lib/coach.ts` (`worthReading` refuses flat frames).
- 13 and D-097 — looked at `docs/logs/raw/phase-7/shots/coach-found-*-1280.png` and `*-1024.png`, dark and light: tokens and glass match the reference; chips sit on the model and date lines; pill and shutter fit. The feed is the fake test camera: regression only.

## Suite results
See "Results" below and `docs/logs/raw/phase-7v/`.

## Results
(filled in after the runs)
