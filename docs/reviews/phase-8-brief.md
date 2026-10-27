# Phase 8 brief — Polish and motion

Session 2026-10-27, branch `phase-8`, on `phase7v.zip` (`1658507`). Chain mode (D-091): no "go" wait; owner-only gates stay BLOCKED.

## What I will build
1. **Streak** (DATA_MODEL 3.7, D-127): `GET /dashboard` answers `streak: {days}`; a pure rule in `derived.py`, the facts from `events` and `notifications`; undone actions do not count. The greeting shows "N days in a row" only from 2 days; nothing is shown when a streak breaks (no guilt copy).
2. **Motion system** (DESIGN 10, D-128 to D-131), CSS and the Web Animations API, no library:
   - Dashboard entrance once per browser session: nav settles, greeting, ring sweep (`stroke-dashoffset`), card, truck roll-in (at most 700 ms); under 1.4 s; any key, click or wheel ends it at the final state.
   - Count-up of the score and item count only when the real value changes (and on the entrance).
   - Truck moves by `transform` on a full-width lane (no `left` animation); wheels turn only while it moves.
   - Win moments: an improved ring extends and its glow pulses once; a streak milestone (7, 30, 100 days) sends the truck on one short delivery.
   - Reminder rows leave with opacity and a slide before the list refreshes; only rows that really resolve.
   - Page transitions: the main region fades and lifts 6 px on a route change (WAAPI, no remount).
   - Saving a new item: a box drops onto a small truck that drives to the brand mark in the nav (under 1.2 s, never blocks input, any input skips it).
   - Coach (D-124): the shutter's `--ring-arc` ring fills while a capture completes; the coach pill enters with a 6 px lift.
   - Reduced motion: every duration token is 0; JS motion checks the media query and shows final states at once.
3. **Light theme pass:** every screen at 1280 px light, fixes; approval stays the owner's (O-005).
4. **Budgets** (ARCHITECTURE 11, DESIGN 16) measured: route JS gzipped, dashboard time, frame timing in headless (30 fps cap noted).
5. **Production checklist** (DESIGN 18.2) per screen in the evidence log.

## Conflicts and gaps (at most five)
1. DATA_MODEL 3.7 "days on which nothing was due are skipped" needs history of what was due. Gap closed by D-127: a day had something due when a reminder row was open or snoozed at any time that local day (from `created_at` and `resolved_at`).
2. DESIGN 10.3 "the truck drives to the logo mark … and the item count ticks up": the nav has no item count. D-130: the delivery ends at the brand mark; the dashboard's count ticks up the next time it shows the new number.
3. DESIGN 10.2 scroll-linked edge road, nav compaction, parallax: nav compaction exists (Phase 1); the edge road is open in DESIGN 19 and no page is long enough to need it; parallax is not in the Phase 8 spec. D-131: not built now (logged).
4. "Milestone" is undefined (DESIGN 10.4). D-129: streak days 7, 30 and 100.
5. 60 fps on the owner's laptop and the light-mode and truck approvals are owner-only: BLOCKED, listed under "Owner runs next".

## Owner inputs
Approve light mode and the truck from `docs/logs/raw/phase-8/shots/` (O-003, O-005); run the dashboard on the laptop and check it stays smooth (60 fps gate).
