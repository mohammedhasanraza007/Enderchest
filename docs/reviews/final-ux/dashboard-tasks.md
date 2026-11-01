# Final UX check: dashboard-tasks (P-12, P-10, P-11, P-14, P-15)

App: http://127.0.0.1:8473, user Ravi, today 2026-11-01 (IST 22:19, greeting "Good night"). Dark theme 1280 px first; light and 1024 px at the end (see "Themes and widths").
Added through Camera > Enter manually: Paracetamol 500 mg strip (today), Orange juice 1 L (+1), Fresh paneer 200 g (+2), Whole wheat bread loaf (+5), Basmati rice 5 kg (+20).

## P-12 Dashboard

| control | did | happened | result |
|---|---|---|---|
| Greeting and subtitle | Read after adding items | "Good night, Ravi"; "5 things need you today" (2 expired + 3 expiry reminders: today, +1, +2). Count matches the bell (5) and tab title | PASS |
| Ring button / centre number | Clicked | Sheet "What counts" opens; Escape closes; focus returns to the ring button | PASS |
| Rings numbers | Opened Documented, Located, Fresh pills | Documented 0/18 (needs photo and printed label), Located 8/18 = 44, Fresh 14/18 = 78, On time "—" (no tasks then). Score 45 = (0x25+44x20+78x35)/80, matches DATA_MODEL 3.5. Lists match | PASS |
| Ring sheet summary line | Read "8 of 18 count: 44" | Reads as a typo; the number is a percentage with no % sign | ISSUE dashboard-tasks-1 |
| Needs attention rows | Read | Shows 2 rows plus "View all 5" (API had 3 rows; the card keeps room for the link, D-027) | PASS |
| Mark expired / Snooze / More (Use it, Discard) | Opened the More menu, Escape | Menu opens, Escape closes | PASS |
| Snooze dialog | Snooze Cough syrup, Tomorrow | Dialog readable, toast "Snoozed until 2 Nov", row left, count 5 to 4 | PASS |
| Use it (Paracetamol, expires today) | Clicked, then Undo | Toast "Paracetamol 500 mg strip used up. Undo"; Undo restored the row and the count | PASS |
| View all N | Link | Goes to /notifications | PASS |
| Road days | Read 14 days, hover day 12 | Tooltip "12 Nov: Oat Milk 1 L expires, Oat Milk 1 L expires"; notches for 1,2,3,5,6,12 | PASS |
| Road day dialog | Clicked 12 Nov | Dialog lists both Oat Milk rows as links; Escape closes, focus returns to the day | PASS |
| Truck | Looked | Parks on 2 Nov labelled "Orange juice 1 L" (next job after today, D-110) | PASS |
| Savings pill | Looked | Not shown (no savings yet, per spec) | PASS |
| Keyboard | Tab x12 | Focus ring 1.7 px cream outline, visible | PASS |

## P-10 Tasks

| control | did | happened | result |
|---|---|---|---|
| Empty state | Opened with no tasks | "Overdue, or due in the next 7 days." "No tasks yet." and a New task button | PASS |
| New task sheet | Opened | Title, Item, Repeat, First due, Notes; Save disabled with hint "Give the task a title." | PASS |
| Title too long | Typed 249 chars | Silently cut at 120, no counter or message | PASS (minor, see notes) |
| Repeat interval | Typed 0, abc, 99999 | Save stays disabled, hint "Repeat every 1 to 3650 days."; letters are accepted into the box but rejected | PASS |
| Save by Enter (recurring, 30 days, from completion) | Enter in interval | Task added, toast "Task added.", row "every 30 days", due today chip | PASS |
| Item picker by mouse (edit) | Typed "hammer", clicked suggestion | Item chip with Remove item, saved, row shows linked item | PASS |
| Item picker by keyboard | Typed "bosch", ArrowDown, Enter | Form submitted with NO item chosen; the task was saved unlinked and nothing warned | ISSUE dashboard-tasks-2 |
| Item picker no match | Typed a title into the item box | "No item matches ..." | PASS |
| Mark done (recurring) | Clicked | Toast "Done. Next due 1 Dec. Undo" | PASS |
| Mark done early (one-off due 4 Nov) | Clicked | Leaves Due soon, appears in Done tab "done 1 Nov" | PASS |
| More menu: Skip | Clicked by accident, then Undo | Row left, "Done. Undo", Undo restored it | PASS |
| More menu: Edit | Changed item, date, note | "Task saved.", row shows "due in 3 days, 4 Nov" | PASS |
| Edit Save with no change | Opened Edit | Save disabled "Change something to save." | PASS |
| Filter pills Due soon / All / Done | Clicked each | Lists change, text under pills explains each | PASS |
| Switch on (done one-off) | Looked | Button shown for a finished one-off | PASS |
| 30-day road | Looked | Same component as dashboard; due tasks listed in the day label | PASS |

| More menu: Delete | Clicked on a finished one-off | Row gone, toast "Oil the drill chuck deleted. Undo"; no confirm (spec: undo only) | PASS |
| Light 1024 | Opened with a due-today task | Row, chip, Mark done and More aligned; no horizontal overflow; no text under 4.5:1 contrast | PASS |

## P-11 Notifications

| control | did | happened | result |
|---|---|---|---|
| Bell | Looked, clicked | Badge count matches open rows (5, 4, 3 ... 0 gone when empty); it is a link to /notifications, no separate panel | PASS |
| Tab title | Watched | "(N) Enderchest" follows the count, plain title at 0 | PASS |
| Tabs Open / Snoozed / Resolved | Clicked each | Rows correct; Snoozed shows "Snoozed until 2 Nov"; Resolved shows "Done" and "No longer needed" with due date | PASS |
| Snooze dialog | Opened from Orange juice | Text "It comes back on 2 Nov at the latest: a reminder never hides an item past its date"; Tomorrow / In 3 days / Next week; Escape closes and focus returns to the Snooze button | PASS |
| Snooze Next week (expiry in 1 day) | Chose it | Capped to 2 Nov as the dialog said | PASS |
| Snooze dialog corners, dark | Zoomed corners | Rounded, looks clean | PASS |
| Snooze dialog corners, light 1024 | Opened on a task row | Panel is rounded but a square shadow band shows under and around its corners, so the corners look square | ISSUE dashboard-tasks-3 |
| Mark expired | Clicked, saw toast | "Amoxicillin syrup 60 ml marked expired. Undo", row animates out | PASS |
| Use it | Clicked twice | Rows leave, "Fresh paneer 200 g used up. Undo" | PASS |
| Expiry-today row | Looked | Only Use it (no Snooze), because a reminder may not hide past its date (D-047) | PASS |
| Empty state | Cleared all open rows | "Nothing needs you right now." | PASS |
| Browser-notification banner | Permission is "denied" in this pane | No banner shown; cannot test the "default" state here | BLOCKED: needs a browser profile with notification permission undecided |
| Inspection finding rows | Not reachable without an inspection | Not tested | BLOCKED: needs an inspected item with worn or defective result |

## P-14 Savings

| control | did | happened | result |
|---|---|---|---|
| Empty state | Opened | "Nothing saved yet. When you skip a purchase because you already own it, it appears here." and a rupee 0 total | PASS |
| I didn't buy it (from Do I own this?) | Searched "cordless drill", opened the sheet | Sheet asks price (required) and note; Save disabled with "Type an amount such as 1,240 or 1240.50." for empty, -5 and 0 | PASS |
| Typed price | Entered 12,34,567.50 | Accepted; page shows the total ₹12,34,567.50 and the row ₹12,34,567.50 with Indian grouping; row says "Saving recorded" on the candidate | PASS |
| This month / All time | Clicked both | Captions change ("Saved this month ..." / "Saved since you started ..."), total same | PASS |
| Dashboard pill | Opened dashboard | "₹12,34,567.50 saved" pill on the road at 1 Nov | PASS |
| Remove | Clicked, confirmed, Undo | Confirm text says undo works "for a minute"; toast Undo restored the entry and the total | PASS |
| Second entry (Bosch, 4500) | Typed and pressed Enter, then navigated away at once | Not saved. I navigated before the request finished, so this is my own race, not counted as an app fault | NOT VERIFIED |
| 1024 light | Looked | Big number fits, list aligned | PASS |

## P-15 Assistant (no key)

| control | did | happened | result |
|---|---|---|---|
| Unavailable state | Opened | Privacy line, glass card "The assistant needs a Gemini key. Add one in Settings, then switch on Use the assistant.", no input | PASS |
| Settings link and Open Gemini settings | Clicked | Both go to /settings#assistant-switch; the page lands with the "Use the assistant" switch (Off) in view | PASS |
| Skeleton while loading | Opened in light | A blank rounded card flashes before the text | PASS |
| Dark and light, 1280 and 1024 | Looked | No overflow, text readable | PASS |

## Themes and widths

Dark 1280 (all five screens), light 1024 (dashboard, tasks, notifications, savings, assistant), dark 1024 (dashboard). Light 1280 and dark 1024 on tasks, notifications, savings were not looked at separately. No horizontal overflow (scrollWidth at or under innerWidth), no contrast failures under 4.5:1 on dashboard and tasks in light. No console errors seen. Viewport reset to desktop and the tab closed.

## Issues

- **dashboard-tasks-1** (cosmetic) P-12 rings sheet, dark and light 1280: the summary reads "8 of 18 count: 44". The 44 is a percentage with no sign and "count" is a stray word. Expected: "8 of 18 count (44%)" or "8 of 18 items, 44%".
- **dashboard-tasks-2** (major) P-10 New task and Edit sheet, item picker: typing "bosch" in Item and pressing ArrowDown then Enter submits the form instead of choosing the first suggestion. The task is saved with no item, no message. Mouse picking works. Expected: arrow keys move through suggestions and Enter picks one, never submits with a half-typed item.
- **dashboard-tasks-3** (cosmetic) P-11 snooze dialog in light theme at 1024: a rectangular shadow band shows around the rounded dialog panel, so the corners look square. Dark theme is clean. Likely the shadow is on the inner panel while the dialog element clips it with overflow:auto. Screenshot: docs/logs/raw/final-ux/shots/dashboard-tasks/snooze-dialog-square-corners-light-1024.jpg

Notes, not issues: title field silently stops at 120 characters with no counter; the Assistant privacy line says text "is sent to Gemini" even when the assistant is unavailable and nothing is sent.
