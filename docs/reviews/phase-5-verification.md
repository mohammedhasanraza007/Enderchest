# Phase 5 verification — Dashboard

Fresh session, 2026-10-24, chain step (D-091). Builder and verifier are the same model family (Opus 5.5): read sceptically. Spec re-read: `docs/specs/phase-5-dashboard.md`; decisions D-109 to D-113.

## Probe list (written before running anything)
1. **Re-run every suite** on the zip's code: `test.bat lint`, `unit`, `integration`, `e2e`, `probes` (1 to 23 stay green).
2. **F-020 on my own data:** a hand-built database (not the storyboard) with mixed items: in Trash, used, discarded, unknown expiry, expiry today, expired, no photo, deleted photo, no location, label printed or not; tasks enabled, disabled, deleted, on a trashed item, due today, overdue. Each ring value, count, score, item count and attention total equals its breakdown list.
3. **Degenerate data:** no items, no tasks; only unknown expiries; only items in Trash; only used items; tasks but no items. No division by zero, no NaN, rings shown honestly.
4. **Truck rule (D-110):** road whose only events are today; expiries only; a busy day (label "+N"); an event on the window's last day; nothing in the window.
5. **Local midnight, Asia/Kolkata:** move the test clock across 18:30 UTC; the road's first day, the greeting and the "today" events roll with the local date, not UTC.
6. **Greeting words by hour** at the D-113 boundaries (04/05, 11/12, 16/17, 20/21 local).
7. **Needs attention card:** ≤3 rows shows all; 4+ shows two rows and "View all N"; Use it / Snooze / Mark done remove the row, Undo restores it, the score updates.
8. **Ring sheet:** every ring opens its breakdown; links go to real items/tasks; "and N more" above 200.
9. **Road endpoint bounds:** `days` 0, 1, 30, 31, -1, text → validation error in the one error shape; no stack trace.
10. **Storyboard gate 3:** frames 2 and 3 reproduced by actions (scores 82 → 86 → 91, rows, truck 18 → 21 → 26).
11. **Performance:** 1,000 items under 200 ms.
12. **Accessibility and look:** keyboard only through rings, card and road; reduced motion; contrast and crawler green; screenshots at 1280 dark/light and 1024, plus 1376 × 768 against the reference (D-097).
13. **Reality audit:** grep for mock/fake/dummy/lorem/stub/TODO/FIXME in shipped code; fixtures only in the test stack; the empty database shows the real empty state.

## Results (per probe)
| # | Probe | Result | How |
|---|---|---|---|
| 1 | Re-run all suites | PASS | lint clean; unit 207 + 83; integration 255; e2e 107 + 3; probes 1 to 23 ALL PASSED (`docs/logs/raw/phase-5v/`) |
| 2 | F-020 on own data | PASS | `test_phase5_verification.py` uses the build's `assert_numbers_equal_their_breakdowns` on my own sets (unknown-only, trashed, tasks-only, Kolkata midnight); the build's tiny-database tests cover used, trashed, disabled tasks |
| 3 | Degenerate data | PASS | no items/no tasks; only unknown (Fresh 0/2, score 0); all trashed (score null, every den 0); tasks only (On time 100, score null, honest "Add items" path) |
| 4 | Truck rule (D-110) | PASS | only-today → truck today; expiries only → next event (29 Oct, the window's last day); busy day `mixed`, count 3, task first; nothing → today |
| 5 | Kolkata midnight | PASS | 23:59 IST: today 16, Milk fresh; 00:01 IST (18:31 UTC, UTC still the 16th): today 17, road 17–30, Fresh 0, yesterday's expiry off the road |
| 6 | Greeting hours | PASS | 9 boundary moments, D-113 words |
| 7 | Card rows, View all, Undo | PASS | build's `dashboard.spec.ts` (Use it + Undo, >3 rows → two + View all) re-run green; integration total = open rows |
| 8 | Ring sheet | PASS | e2e re-run; cap 200 with whole counts on 1,000 items (own probe) |
| 9 | Road `days` validation | PASS | 0, -1, 31, x, 1.5 → 422, body only `{error}`, no traceback |
| 10 | Storyboard gate 3 | PASS | integration and e2e re-run: 82 → 86 → 91; 142, 142, 141; truck 18 → 21 → 26; frame 3 screenshot shows one row (Baby Spinach) |
| 11 | 1,000 items < 200 ms | PASS | integration re-run green (build measured 12.4 ms median) |
| 12 | Keyboard, contrast, crawler, looks | PASS | new `dashboard-keyboard.spec.ts`; contrast and crawler specs green; screenshots looked at (notes below). Reduced motion: no motion exists yet (Phase 8); the shot spec runs with `reducedMotion: reduce` |
| 13 | Reality audit | PASS | grep hits only in `client.test.ts` (vitest); storyboard and `/test/*` routes mounted only when `env == "test"` (`app/main.py`); the empty dashboard shows "—", "Add your first item", "Nothing needs attention", "No tasks or expiries in the next 14 days" |

## Part 1, spec conformance
Build 1 (endpoints, one service, unit tests per formula and exclusion; savings/streak null): MET. Build 2 (greeting, rings, card, road, truck; sparkle deliberately omitted per D-110/DESIGN 2.2): MET. Build 3 (P-11 actions, Undo, View all → `/notifications`, ring → sheet): MET. Build 4 (nav, `/`): MET. Build 5 (fixtures, test stack only; 142/142/141 per D-109): MET. Build 6 (empty state): MET. No new dependency; no migration; DATA_SAFETY untouched (live stack not used).

## Part 2, does it work
On the test stack: yes (all suites). `build.bat` then `run.bat` on the live stack: NOT VERIFIED here — owner-only (D-091), listed in handoff.

## Notes (minor, none blocking)
- **N1** Only the truck's day carries a label, and it reads "Pantry Refill +1" where the reference reads "Pantry Refill" (the 18th also holds Greek Yogurt's expiry). Honest by D-110; the owner may prefer the bare name.
- **N2** At 1024 px the greeting takes its own row and the rings and card sit below it, leaving the top right empty; legible and within the tokens, but less balanced than at 1280.
- **N3** The empty dashboard still shows the truck parked on today beside "No tasks or expiries in the next 14 days" (D-110's fallback); consider hiding the truck when the road has no events.

## Verdict
**PASS WITH NOTES** (N1 to N3 minor; owner acceptance and screenshot approval BLOCKED on the owner, as for every phase). Builder and verifier are the same model family; I re-derived the probes from the spec and decisions and wrote 21 new checks rather than trusting the build's.
