# Phase 4 verification — Lifecycle, maintenance and notifications

Fresh-session reviewer, 2026-10-24, branch `phase-4-verify` from `phase4.zip` (top commit `phase4: checkpoint (phase4 zip)`). Process: `PROCESS.md` 4, probe list first.

## Verdict: PASS WITH NOTES
Every Phase 4 gate Claude can run is green on re-run, and seven new independent probes of the reconcile pass. Gate 10 is this pass. The owner's acceptance run and screenshot approval are BLOCKED (owner only). Notes N1 to N3 are cosmetic or wording and do not block Phase 5 (D-091: the chain goes on).

## Probe list (written before running anything)
1. F-019: reconcile twice, across restarts, a clock moved forward and back: no duplicate, no lost row.
2. Snooze never hides an expiry past its date (snoozed `expiry_soon` while the item expires).
3. A dismissed finding never comes back (delete, restore, discard, reactivate, a new day).
4. A date edit and back: the same row reopens, no second row.
5. Completion rule both modes, done early (DATA_MODEL 2.9 reading of "strictly after D").
6. Undo: restores exactly; refused after 60 s and after a later change (use, mark expired, discard, task done, skip, delete).
7. Wording: "inspection suggested", never "replacement required"; Gemini interval "suggested, unverified"; "while an Enderchest tab is open".
8. Browser notification once per row across tabs and reloads (real Chromium channel, F-036); ten concurrent claims.
9. Purge of an item with tasks, inspections and reminders.
10. F-022 regression (idle reconcile writes nothing), crawler, contrast, all data-safety probes.
11. Reality audit and screenshots against the reference (D-097).

## Results
| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | reconcile duplicates / restarts / moved clock | PASS | probe 22; new `test_a_clock_moved_forward_and_back_makes_no_duplicate` (D, D+8, D, D+8, D+12, D+8, D+12: 2 rows, keys unique) |
| 2 | snooze vs expiry | PASS | new `test_a_snoozed_expiry_reminder_never_hides_the_expiry` (snoozed a week; at D+3 `expired` open, `expiry_soon` superseded); snooze capped at date (build test) |
| 3 | dismissed finding stays closed | PASS | new test: delete, restore, discard, reactivate, next day: one row, `dismissed`. Code: `resolve` skips resolved rows; reopen excludes `dismissed` |
| 4 | date edit and back | PASS | new test: 1 row, open |
| 5 | completion rule | PASS | new test: 14-day task done 4 days early: fixed → D+28, from completion → D+24. See N3 |
| 6 | undo | PASS | build tests (60 s, `changed` after reactivate, task delete undo); new `test_undo_of_task_done_is_refused_after_a_later_change` |
| 7 | wording | PASS | grep: no "replacement required" in shipped text; chips "suggested, unverified" in MaintenanceCard and Tasks; Settings says "while an Enderchest tab is open" |
| 8 | browser notification once | PASS | `browser-notifications.spec.ts` in the e2e run; probe 23: 10 claims, 1 claimed, 9 not |
| 9 | purge | PASS | `test_permanent_delete_removes_the_items_tasks_inspections_and_reminders` in integration |
| 10 | suites | PASS | lint 0, unit 0, integration 0, e2e main 93/0, no-backups 3/0, probes 1 to 23 ALL PASSED (16: 0 idle backups) |
| 11 | reality and look | PASS WITH NOTES | 20 shots reviewed (Tasks, Notifications, item finding 1024, snooze, both themes): real rows only, nav shows built pages, tokens match the reference's warm glass |

## Notes (not blocking)
- N1: the snooze dialog shot (`snooze-dark-1280.png`) shows a small square corner at its bottom-right, outside the rounded edge (a backdrop or shadow box not clipped). Fix in Phase 8 polish or earlier if seen live.
- N2: item page at 1024 px wraps the lifecycle actions 2 + 1 (Use it, Mark expired / Discard). Readable; Phase 5 or 8 may tidy it.
- N3: DATA_MODEL 2.9 "next date of the original series strictly after D" read literally keeps the old `next_due` when done early; the code always moves at least one step ("the occurrence just done is satisfied"). The code's reading is the sensible one; the DATA_MODEL sentence should say so (doc-only, any session).
- Process: the e2e/lint/unit/integration logs of this run were overwritten by a shell quoting slip (all went to one file); exit codes were recorded (all 0) and the Playwright JSON summaries are kept in `docs/logs/raw/phase-4v/`. The probes log is complete.

## Blocked on the owner
Phase 4 acceptance (task due today, item expiring tomorrow, done, snooze, allow browser notifications, test notification as a real system alert); screenshot approval of `docs/logs/raw/phase-4/shots/`.

## Failure kinds added
F-036 to F-039 in `failure-checklist.md` (headless shell "denied", gallery fetching, duplicate accessible names, Prettier outside its config).
