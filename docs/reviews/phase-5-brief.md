# Phase 5 brief — Dashboard (2026-10-24)

Chain session (D-091): no owner "go" is awaited; the owner reads this later. Spec `docs/specs/phase-5-dashboard.md`.

## What I will build
1. **Backend:** `services/dashboard.py`, one module for every number of `DATA_MODEL.md` 3.3 to 3.6 (active items, the four rings, the score, the road, the truck date, the greeting part, the subtitle), with a unit test per formula and per exclusion (no active items, no tasks, unknown expiry, expiry today, task due today). Routes `GET /api/v1/dashboard`, `GET /api/v1/dashboard/rings/{ring}` and `GET /api/v1/dashboard/road?days=14|30` (D-113). `savings` and `streak` are `null`. A reconcile runs first when the last one is over 60 s old (3.8).
2. **Frontend:** `screens/Dashboard.tsx` with `patterns/Greeting`, `HealthRings` (SVG, four arcs, accessible name with the real values), `AttentionCard` (reuses `ReminderList` from `patterns/Reminders.tsx`; at most three rows, "View all N"), `Road` (one component, 14 days on the dashboard and 30 on Tasks, D-103), `Truck`, and the ring breakdown sheet. Nav gains Dashboard; `/` becomes the dashboard. No sparkle or star (DESIGN 2.2 wins over the spec's word "sparkle"). Static first; motion stays Phase 8.
3. **Test stack only:** fixtures `storyboard-1`, `storyboard-2`, `storyboard-3` (real rows; computed scores 82, 86, 91; 142, 142, 141 active items, D-109), built so 2 and 3 are 1 plus the scripted actions (D-111).
4. **Gates:** F-020 "every number equals its breakdown" test on the three fixtures and a tiny hand-built database; storyboard actions test; 1,000-item timing (< 200 ms); empty, loading, error and no-task states; crawler and contrast extended to `/`; screenshots at 1024, 1280, 1536 px in both themes and 1376 × 768 for the reference gate.

## Conflicts and gaps (decisions D-109 to D-113)
1. **Item counts.** The spec says 143, 142, 141; DESIGN 20 says 142, 142, 141, and frame 1 to 2 is "completing a task" which cannot change the count. DESIGN 20 wins (D-109).
2. **The truck vs DATA_MODEL 3.6.** Read literally ("earliest event in the window"), frame 1 parks the truck on today (Oat Milk expires today, Baby Spinach's inspection is due today), not on the 18th. The truck parks at the next task due after today; with none, the next event after today; else today. Only the truck's day carries a label under its tick; other events are notches with a tooltip and the screen-reader list (D-110).
3. **The storyboard's one-action jumps.** With 142 items, using one item moves a ring by under one point; only On time (a few tasks) can move the score by 4 or 5. The fixture holds four overdue chores the owner had snoozed (so the card shows the frame's three rows); each transition also completes two of them, and frame 2 to 3 snoozes Greek Yogurt (two rows leave, the count drops by one) (D-111).
4. **On time's task set and the breakdown shape.** On time counts the tasks the reconcile counts (enabled, not deleted, item active if any). The breakdown returns one entry shape for items and tasks with a short reason ("no photo", "date not set", "3 days overdue"), up to 200 per list (D-112).
5. **The Tasks page's road** needs a 30-day window that `GET /dashboard` does not give: `GET /dashboard/road?days=30` from the same service. Greeting hours and the "View all N" rule are fixed too (D-113).

Also noted: the reference orders the rows Oat Milk, Greek Yogurt, Baby Spinach; the server's urgency order (D-106) puts Baby Spinach (due today) before Greek Yogurt (2 days left). The order is kept; the names, words and actions match.

## Owner inputs
- Approval of the dashboard screenshots against the reference (gate 1) and the acceptance run on the owner's own data: BLOCKED until the owner does them (listed in `handoff.md`, "Owner runs next").
- O-004 (score weights 25/20/35/20) stays the default.
