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

## Results
(filled below)
