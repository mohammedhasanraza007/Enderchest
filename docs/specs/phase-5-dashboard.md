# Phase 5 — Dashboard

**Read list:** `CLAUDE.md` sections 0, 7, 8 · this file · `DESIGN.md` 6 (all), 12, 13, 14, 18.1, 20 · `PAGES.md` P-12 · `API.md` 2.13 · `DATA_MODEL.md` 3 (all) · open `docs/design/reference-dashboard.jpg` and `docs/design/ux-states.png`.
**Do not read:** OCR, lifecycle internals, `PROJECT_PLAN.md`.
**Owner supplies:** approval against the reference. **Milestone:** C.

## Goal
The home screen from the reference, wired to real data only. Static and correct first; motion is Phase 8.

## Build
1. `GET /api/v1/dashboard` and `GET /api/v1/dashboard/rings/{ring}` computing every number from `DATA_MODEL.md` 3 in one service module with unit tests for each formula and each exclusion rule (no active items, no tasks). `savings` and `streak` return `null` in this phase.
2. Components of `DESIGN.md` 6.7 to 6.11 (greeting, rings, Needs attention card, road, truck position, sparkle) using opaque surface tokens and status chips.
3. Needs attention rows and actions are those of `PAGES.md` P-11 (server `actions`); rows leave the card on success with Undo; "View all N" opens `/notifications`; ring click opens the breakdown sheet.
4. Nav gains Dashboard; `/` becomes the dashboard.
5. Test-stack fixtures `storyboard-1`, `storyboard-2`, `storyboard-3`: real rows (143, 142 and 141 active items) built so the *computed* scores are 82, 86 and 91 and the attention and road contents match the three frames of `ux-states.png`. Fixtures exist only in the test stack.
6. Empty database state per `PAGES.md` P-12 and `DESIGN.md` 13.

## Gate
1. Reference-match gate (`DESIGN.md` 18.1) on `storyboard-1`; measurements recorded; owner approves.
2. Every number equals its breakdown list (ring value, counts, score, item count, attention total) on all three fixtures and on a hand-built tiny database; the on-time and fresh edge cases are tested.
3. Frames 2 and 3 of the storyboard are reproduced by actions on the fixtures (resolving rows changes score, rows, truck position as the frames show).
4. Dashboard under 200 ms with 1,000 items.
5. Empty, loading, error, offline-Gemini-irrelevant, and no-task states render correctly; dead-control crawler and contrast test extended; both themes at 1024, 1280, 1536 px.
6. Verification pass.

## Owner acceptance (3 minutes)
Open the dashboard on the storyboard fixture (`dev.bat`) and on your own data; compare with the reference; click a ring and see what counts; use an item from the card.
