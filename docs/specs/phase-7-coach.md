# Phase 7 — Camera coach

**Read list:** `CLAUDE.md` sections 0, 7, 8 · this file · `DESIGN.md` 9 · `API.md` 2.15 · `PAGES.md` P-06 · `PROJECT_PLAN.md` section 11 · `ARCHITECTURE.md` 6.
**Do not read:** dashboard, data model.
**Owner supplies:** a live check with the real webcam. **Milestone:** E (optional).

## Goal
Short, calm prompts on the live camera ("Hold steady", "Too dark", "Glare on the label", "Move closer", "Model found", "Date found") that help the owner get a good capture. Delight, never a blocker: capture always works without the coach.

## Build
1. **Client tier (every frame, cheap):** on a 320 px grayscale copy compute sharpness (variance of the Laplacian), mean brightness, and glare (fraction of pixels with luma above 250 forming one blob). **Starting values to tune on real captures and then record:** blurry below 80, dark below 60, glare when the blob exceeds 4% of the frame.
2. **Server tier (about 1 per second):** the client sends one 640 px JPEG to `POST /api/v1/capture/frame` only when sharpness and light pass; at most one request in flight (a `busy` reply drops the frame). `text_found` means at least 3 boxes with confidence ≥ 0.5; "move closer" when the median text box is under 2% of the frame height (3.5% for the engine's padded boxes, D-125). The OCR tier reuses the Phase 3 engine through the same size-1 executor.
3. Prompt state machine: one prompt at a time, minimum 1.5 s on screen, no flicker, priority dark > blur > glare > no text > too far > found. Respects `coach_enabled` and reduced motion.
4. Settings → Camera coach toggle.

## Gate
1. Deliberately bad and good captures (dark room, hand shake, glossy label, empty desk, far away, close and sharp) each produce the right prompt; thresholds recorded.
2. Camera view stays at 60 fps while OCR runs; `/health` answers within 200 ms throughout.
3. Disabling the coach removes all prompts and all server calls.
4. The owner's live check on the real webcam is recorded; **automation with a fake feed is regression only**.
5. Verification pass.
