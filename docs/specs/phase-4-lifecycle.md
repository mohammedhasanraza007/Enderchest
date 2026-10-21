# Phase 4 — Lifecycle, maintenance and notifications

**Read list:** `CLAUDE.md` sections 0, 5, 6, 8 · this file · `DATA_MODEL.md` 2.9–2.12, 3.1, 3.2, 3.7, 3.8 · `API.md` 1, 2.10–2.12 · `PAGES.md` P-04 (lifecycle and maintenance parts), P-10, P-11, P-02 (Notifications) · `ARCHITECTURE.md` 6 (Scheduler).
**Do not read:** `DESIGN.md` except 6.5 (Bell) and 6.9 (rows), OCR material.
**Owner supplies:** the acceptance run. **Milestone:** C.

## Goal
The app keeps the owner on time: items are used, expire or are discarded; things are inspected on a schedule; reminders reach the owner. Honest limit, stated in the UI: reminders appear in the app and as browser notifications **while an Enderchest tab is open**.

## Build
1. Migration 0003; repositories; the `clock` module with test-clock support.
2. Lifecycle services: use (quantity minus amount, state `used` at 0), mark expired, discard, reactivate, undo through `events.payload.before`.
3. Tasks and maintenance: completion rule of `DATA_MODEL.md` 2.9 (from completion and fixed); the item's maintenance task through `PUT /api/v1/items/{public_id}/maintenance`; inspections complete the task; `worn` and `defective` produce the "inspection suggested" attention wording.
4. Reconcile (`DATA_MODEL.md` 3.8) as the in-process loop (start, every 15 minutes, date change, before dashboard reads) with `scheduler_state`.
5. Notification endpoints; server-supplied `actions` per kind (`PAGES.md` P-11); snooze options capped at due date.
6. Pages: Tasks, Notifications, Item page additions, Settings → Notifications. Nav gains Tasks and the bell with unread count. Polling every 60 s and on focus; browser notification once per row (`shown` endpoint); tab title `(N) Enderchest`.
7. Item page status chips use the expiry words of `DATA_MODEL.md` 3.2.

## Gate (use the test clock)
1. An item expiring in 2 to 3 days produces exactly one `expiry_soon`; restart the app three times and advance the clock a day at a time: no duplicates, no gaps.
2. An item that expired while the app was off is `expired` after start; its old `expiry_soon` is `superseded`.
3. A 14-day task becomes due on day 14, completes, and reschedules per both modes; a task 30 days late creates one notification, not two.
4. Use it on quantity 3 leaves 2 active; on quantity 1 sets `used` and resolves its notification; Undo restores quantity, state and notification.
5. Snooze cannot push an expiry reminder past its date; snoozed rows return when due.
6. Inspection results: ok completes; worn and defective add the right wording and offer Mark discarded.
7. Deleting or discarding an item resolves its open notifications as `superseded`.
8. Browser notification fires once per row across reloads and two tabs (real Chromium); tab title updates.
9. Dead-control crawler and contrast test extended; both themes.
10. Verification pass.

## Owner acceptance (3 minutes)
Create a task due today, an item expiring tomorrow; open the app; see both; mark one done, snooze one; allow browser notifications and trigger the test notification.
