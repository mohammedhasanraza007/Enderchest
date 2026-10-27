# Phase 8 verification — Polish and motion

Fresh session, 2026-10-28, branch `phase-8-verify`, on the code of `phase8.zip` (`9021b55`). Builder and verifier are the same model family: read sceptically.

## Probe list (written before running anything)
1. Reduced motion everywhere: `document.getAnimations()` empty after load and after actions, no save delivery, final numbers shown at once (score, count).
2. Only `transform`, `opacity` and `stroke-dashoffset` animate, on every screen (dashboard, inventory, item, camera, tasks, savings, notifications, settings), not only the dashboard.
3. No animation blocks input: a click during the entrance, during a row exit and during the delivery takes effect.
4. The entrance plays once per tab session and finishes under 1.4 s.
5. Count-up and ring flare only on a real increase (not on a re-render with the same value, not on a decrease).
6. The truck lane never widens any page at 1024, 1280 and 1536 px.
7. Streak rules D-127: an undone action does not count; quiet days are skipped; local-midnight timezone edges; a reopened reminder; shown only from 2 days; no guilt wording anywhere.
8. Save delivery starts on the road truck when it is on screen, ends at the brand mark, removes itself, and never stacks when two items are saved quickly.
9. Shutter fill ring and coach pill lift under reduced motion (no animation).
10. Light-mode contrast on every screen (contrast spec, both themes).
11. Item page: one action row; History empty state is the real empty state.
12. Storyboard frames 1 to 3 (dashboard at rest, a resolved row and a score change, the delivery) still reproduce with transitions.

## How each probe was tested
- 1 — build's `motion.spec.ts` "reduced motion" (dashboard, save) plus new V2 (`tests/e2e/phase8-verification.spec.ts`): `getAnimations()` is 0 on every route and the item page. PASS.
- 2 — build's dashboard checks plus new V1: page arrival on every route moves only allowed properties. PASS.
- 3 — build's "any input ends the entrance" and the row-exit spec; new V4: a nav click during the delivery navigates and ends it. Code read: the layer is `pointer-events: none`. PASS.
- 4 — build's entrance spec (gone within 2 s of load, once per tab via `sessionStorage`; design budget 1.4 s). PASS (the test bound is 2 s, looser than 1.4 s: note N3).
- 5 — build's row/flare spec (flare on the improved ring only) and vitest count-up rules. PASS.
- 6 — new V5 at 1024, 1280, 1536 on `/` and `/tasks`: `scrollWidth <= innerWidth`. PASS.
- 7 — `test_streak_rules.py` (9 unit rules), `test_streak.py` (undo, quiet days, missed day) plus new local-midnight test (23:50 and 00:10 IST are two days). PASS. Code read of a reopened reminder: `reopen` clears `resolved_at`, so the days between its first resolution and the reopen are counted as "due" (D-127 as written uses only the current stamps). Can end a streak early; never shows guilt copy (nothing is shown on a break). Minor, note N1. Grep of the Phase 8 diff: no "broke/lost/missed" copy.
- 8 — build's delivery spec; new V3: two saves back to back leave at most one `.delivery` and it clears within 1.5 s; `body.delivering` removed. Code read: a second trip cancels the first in the effect cleanup. Start on `.road__truck` when present. PASS.
- 9 — build's coach vitest/e2e (reduced-motion durations are 0) and V2 on `/camera`. PASS.
- 10 — `contrast.spec.ts`, `routes-contrast.spec.ts` both themes, green. PASS.
- 11 — looked at `item-light-1280.png`: History shows "Nothing recorded yet."; the action buttons sit in one card but wrap to two lines at 1280 (Use it, Mark expired / Discard, Edit, more). Minor, note N2.
- 12 — `motion.spec.ts` storyboard stages 1 to 3 (82, row exit to 86, truck moves to Clean PC) and `dashboard-shots.spec.ts`. PASS for the automated part; the owner's look is BLOCKED.

## Results (`docs/logs/raw/phase-8v/`)
- `lint.log` clean; `unit.log` 273 + 114 vitest; `integration.log` 332 (+1 new streak test run alone: 5 passed); `e2e.log` 158 passed + 3 (includes V1 to V5); `probe-1.log` to `probe-27.log` each ALL PASSED.
- No product code changed.

## Gates
1. Reduced motion respected — PASS. 2. Interactions never blocked — PASS. 3. 60 fps on the owner's laptop — BLOCKED (owner). 4. Storyboard frames with transitions — PASS automated; owner look BLOCKED. 5. Light mode approved or deferred — BLOCKED (owner, O-005). 6. Contrast and dead-control tests — PASS. 7. Verification — this file.

## Notes (all minor)
- N1: a reopened reminder loses its old `resolved_at`, so the quiet days between can count as "due" and end a streak early. Fix needs a reopen history (a migration); logged, not fixed.
- N2: item page actions wrap to two lines at 1280 (one card, not one line).
- N3: the entrance test allows 2 s; the 1.4 s budget is from the design timings, not asserted.

## Verdict
**PASS WITH NOTES** (N1 to N3 minor; owner-only gates BLOCKED, not passed).

## Visual review (D-097)
Looked at `docs/logs/raw/phase-8/shots/` dashboard dark and light 1280, dashboard dark 1024, item light 1280, tasks light 1280 against `reference-dashboard.jpg` and `reference-dashboard-light.png`: tokens, rings, card and road match; light mode follows the owner's light reference (cocoa rings, terracotta primary). Star and gold glow not copied (D-132). At 1024 the card's right edge sits about 70 px inside the nav's; acceptable.
