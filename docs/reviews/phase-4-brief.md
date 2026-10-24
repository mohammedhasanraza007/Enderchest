# Phase 4 brief — Lifecycle, maintenance and notifications

Written 2026-10-24 by the Phase 4 build session (chain of sessions, D-091: no "go" is awaited).

## What this session builds (spec build order)
1. **Migration 0003** (`tasks`, `inspections`, `notifications`), after the verified pre-migration backup the boot already makes; a migration test from a realistic v2 database. Repositories `tasks`, `inspections`, `notifications`. The existing `clock` module stays the only "now"; the test clock already moves through `/test/clock`.
2. **Lifecycle services** (API 2.10): use (quantity minus amount; `used` at 0), mark expired, discard, reactivate; each writes its event with `payload.before`; undo (60 s) gains `item_used`, `item_expired_marked`, `item_discarded`, `task_done`, `task_skipped`, `task_deleted`.
3. **Tasks and maintenance** (API 2.11, DATA_MODEL 2.9, 2.10): the completion rule for both schedule modes, `PUT /items/{id}/maintenance`, inspections that complete the task; `worn` and `defective` raise an "inspection suggested: worn/defective" row that offers Mark discarded. `ItemDetail.maintenance` is filled; a Gemini interval (from `drafts.gemini_result` through `committed_item_id`, D-102) is offered as "suggested, unverified".
4. **Reconcile** (DATA_MODEL 3.8) in the existing scheduler loop: at start, every 15 minutes, when the local date changes, before notification reads when the date moved, and after every write that changes what is due. `scheduler_state` keeps `last_reconcile_at` and `last_local_date`.
5. **Notification endpoints** (API 2.12) with server-supplied `actions` per kind (P-11), snooze capped at the due date for `expiry_soon`.
6. **Pages:** Tasks (P-10), Notifications (P-11), Item page lifecycle actions, maintenance card and inspection sheet (P-04), Settings → Notifications (P-02). Nav gains Tasks and the bell with the real open count; polling every 60 s and on focus; one browser notification per row; tab title `(N) Enderchest`.
7. Item page status chips keep the server's expiry words (DATA_MODEL 3.2).
Tests: unit (completion rule, words, snooze cap, reconcile desired set), integration (every endpoint, gates 1 to 7 on the test clock, restarts), browser (pages, undo toasts, bell, browser notification once across reloads and two tabs, crawler, contrast, screenshots), probes 22 and 23 (reconcile across restarts and a moved clock; notification `shown` race).

## Real conflicts and gaps (decisions recorded in `DECISIONS.md`)
1. **P-10 puts the 30-day road on top of Tasks**, but the road component, its data (DATA_MODEL 3.6) and its endpoint (`GET /dashboard`, API 2.13) are Phase 5. Building a second road now would be thrown away. The Tasks road arrives with the Phase 5 road component (D-103); Phase 4's Tasks page has no road and no placeholder.
2. **A worn or defective inspection must "add an attention row"**, but the four notification kinds have none for it. Migration 0003 adds a fifth kind, `inspection_finding` (word "inspection suggested: worn" or "…: defective"; actions Mark discarded and Keep using → resolution `dismissed`). Reconcile makes the table match the desired set: rows no longer desired become `superseded`; a resolved row that is desired again (undo, restore, reactivate) reopens unless the owner dismissed it (D-104).
3. **Gate 7 says discarding resolves as `superseded`; DATA_MODEL 2.12 lists `discarded`, `used`, `expired_marked`.** Data shapes follow DATA_MODEL: a lifecycle action resolves the item's open rows with its own resolution when the item leaves `active`; delete resolves them as `superseded`; the gate's point (no open row is left behind) is tested for both (D-105).
4. **Undefined shapes:** `NotificationView.urgency`, the row and task `word`s, and P-10's pills Due soon / All / Done against `scope` open/due/all. Defined in D-106: `urgency` is `overdue`, `today` or `upcoming`; `scope` gains `done`; "Due soon" is overdue or due within 7 days, stated on screen.
5. **"Fires once per row across two tabs"** cannot hold if `shown` only records: both tabs see an unshown row. `POST /notifications/{id}/shown` becomes an atomic claim that answers `{claimed: true|false}`; a tab fires only when it claimed, and the notification carries the row id as its `tag`. `GET /notifications/count` adds `unshown` (open rows never shown, at most 5) (D-107).

## Assumptions (no decision needed)
- Gate 2's "is `expired` after start" means the item's `expired` notification exists and its expiry status is `expired`; the item's state changes only when the owner taps Mark expired (DATA_MODEL 3.8 step 1).
- Use with an amount above the quantity is refused (`validation_error` on `amount`). Reactivate keeps the quantity when above 0, else 1, unless one is sent.
- Snooze is not offered where it cannot move the row (an `expiry_soon` due today); the API refuses it with `conflict`.

## Owner inputs (`OWNER_TASKS.md`)
- The 3-minute acceptance run (a task due today, an item expiring tomorrow, done, snooze, allow browser notifications, test notification). BLOCKED until the owner runs it; never stops the chain.
- Screenshot approval of the new screens (Tasks, Notifications, Item lifecycle and maintenance, Settings → Notifications).
