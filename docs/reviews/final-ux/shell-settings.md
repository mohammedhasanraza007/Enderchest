# Final UX check: shell-settings

App under test: http://127.0.0.1:8473 (release zip, built with build.bat in D:\Projects\Enderchest-ux-a\Enderchest, own data). Tester: fresh session, first user of a brand-new install. Browser: built-in browser pane, emulated 1280x800 (and 1024x768 later), colour scheme emulation dark/light.

Preflight: `docker compose config` in D:\Projects\Enderchest-ux-a\Enderchest shows project `enderchest-uxa`, published port 8473, volume `enderchest_uxa_data` (external), backup bind `C:/Users/Admin/Enderchest-UXA-Backups`. Confirmed, scripts allowed.

Result key: PASS, ISSUE <id>, BLOCKED: needs <what>.

## P-01 Welcome (first run, dark, 1280 px)

Note: a first run cannot be repeated (the guard redirects /welcome to / once a name is saved, and the test endpoints are off), so Welcome was checked once, in dark at 1280 px only. Light theme and 1024 px for Welcome: BLOCKED: needs a second fresh install.

| control | did | happened | result |
|---|---|---|---|
| Page load `/` on empty install | opened http://127.0.0.1:8473/ | redirected to `/welcome`, logo mark above one frosted card, "Welcome to Enderchest", help line "Tell it your name and time zone. Both stay on this computer." | PASS |
| Time zone select default | read value | pre-set to Asia/Kolkata (browser reports Asia/Calcutta, app maps it) | PASS |
| Continue, empty name | clicked Continue | stays on step 1, message "Enter a name of 1 to 40 characters." with icon under the field, aria-invalid set; focus stays on the button (not moved to the field) | PASS (see shell-settings-1 for the stale message) |
| Name, 66 characters | typed "Ravindranath Subramaniam Venkataraghavan Iyer the Third of Chennai", pressed Enter | Enter submits; rejected with the same message, no request sent, still step 1; the field has no maxlength and no counter | PASS |
| Name, spaces only | typed 5 spaces, Enter | rejected with the same message | PASS |
| Keyboard | Tab through step 1 | name, time zone, Continue in order; each shows a solid 1.7 px light outline (focus-visible) | PASS |
| Name valid after an error | typed "Ravi" after the error | the red message and aria-invalid="true" stay on screen next to a valid name, also after Tab away; only clears on submit | ISSUE shell-settings-1 |
| Continue with "Ravi" / Asia/Kolkata | clicked Continue | step 2 "Start with some categories?"; profile saved (GET /api/v1/profile: name Ravi, timezone Asia/Kolkata) | PASS |
| Resume on step 2 | reloaded the tab on step 2 | came back to step 2, name already saved | PASS |
| Category chips (6: Tools, Electronics, Food and drink, Cosmetics, Household, Other) | ticked Tools, Food and drink, Household, then unticked Food and drink | chips toggle, tick icon plus outline when on, aria-pressed true/false correct; but the tick makes a chip wider, so ticking Tools pushed Household from row 1 to row 2 and the chips move under the pointer (screenshots welcome-step2-before-ticks.jpg and welcome-step2-after-ticks-household-moved-to-row-2.jpg) | ISSUE shell-settings-13 |
| Continue (step 2) | clicked Continue with Tools and Household ticked | step 3; GET /api/v1/categories returns exactly Household and Tools (Tools has maintenance default on) | PASS |
| Skip (step 2) | not pressed (would have changed the run) | Skip is present and enabled; its path is not exercised because the first run cannot be repeated | BLOCKED: needs a second fresh install |
| Step 3 Done | read the card | "Good evening, Ravi" (browser hour 17), "You are set up. Everything stays on this computer.", one action "Add your first item" linking to /camera?mode=add. No "Open settings" (correct after Phase 2) | PASS |
| Focus after each step change | read activeElement after Continue (step 1 to 2, 2 to 3) | focus drops to BODY both times, so a keyboard user has to Tab from the top again | ISSUE shell-settings-2 |
| Guard | opened /welcome after finishing | redirected to `/` (Dashboard) | PASS |

## The shell (nav capsule, logo, bell, name menu), dark 1280 px unless stated

| control | did | happened | result |
|---|---|---|---|
| Logo link "Enderchest home" | clicked from /trash | went to `/` (Dashboard) | PASS |
| Nav tab Dashboard / Inventory / Camera / Tasks / Savings / Assistant | clicked each | each opens its route, tab shows aria-current and the active pill, page title follows ("Inventory · Enderchest" etc.), no horizontal scroll. Camera asks for the camera on load, which the pane blocks (expected; the page says "The camera is blocked" with Try again, Upload photos, Enter manually) | PASS |
| Bell (link "Notifications") | clicked | goes to `/notifications` (a page, not a panel; PAGES.md P-11 says the same). Filters Open / Snoozed / Resolved are radios, each switches and shows an honest empty line ("Nothing needs you right now.", "Nothing is snoozed.", "Nothing resolved yet.") | PASS |
| Name pill (button, aria-expanded) | clicked, Enter, Escape, click outside | opens a panel with Settings, Trash, three theme chips and "Last backup 1 Nov, 5:54 pm". Escape closes it and focus returns to the pill; click outside closes it; Enter then Tab goes Settings, Trash in order with a focus ring; choosing a link closes it | PASS |
| Menu link Settings | clicked | opens `/settings` | PASS |
| Menu link Trash | clicked | opens `/trash` ("Trash is empty.") | PASS |
| Theme chips System / Light / Dark | clicked each | applied at once, saved to the profile (`GET /api/v1/profile` shows system, light, dark), aria-checked and tick follow; System follows the emulated colour scheme | PASS |
| Theme chips layout | measured the panel | the three chips need 258 px but the row has 247 px, so "Dark" always drops to a second row and the row looks ragged (also in light) | ISSUE shell-settings-3 |
| Backup status line in the menu | read | "Last backup 1 Nov, 5:54 pm" agrees with the automatic backup file in the backup folder (12:24 UTC) | PASS |
| Name pill with a 40-character name (the allowed maximum) | saved "Ravindranath Subramaniam Venkataraghavan" | at 1280 the pill truncates with an ellipsis (title keeps the full name), nav still inside the capsule | PASS |
| Same name at 1024 px | resized to 1024 | the pill (220 px) sticks out of the nav capsule by about 56 px on the right and the page gets a horizontal scrollbar (scrollWidth 1013 vs 1009) | ISSUE shell-settings-5 |
| Same name on the Dashboard greeting at 1280 | opened `/` | third line "Venkataraghavan" is 397 px in a 358 px box and runs into the outer ring | ISSUE shell-settings-6 |
| Skip to content link | read | present as first link (`#main`) | PASS |

## P-02 Settings (`/settings`), sections in page order

Sections found: Profile, Appearance, Categories, Locations, Backup, Notifications, Gemini, Camera coach, Data, About (matches the P-02 table plus Camera coach). One left-aligned column 720 px wide, frosted cards with serif titles.

### Profile

| control | did | happened | result |
|---|---|---|---|
| Your name | cleared, pressed Save | "Enter a name of 1 to 40 characters.", nothing saved | PASS |
| Your name, 45 characters, Enter | typed, Enter | same message, server name unchanged | PASS |
| Your name, 40 characters (limit), Enter | typed, Enter | saved; toast "Profile saved."; name pill updated and truncates with an ellipsis; Save goes grey with "Change your name or time zone to save." | PASS (long-name layout problems at 1024 and on the Dashboard: ISSUE shell-settings-5, shell-settings-6) |
| Time zone select | chose America/New_York, Save | saved (API shows America/New_York) and a banner appears: "Your browser says you are in Asia/Kolkata, but Enderchest is set to America/New_York." | PASS |
| Banner button "Use Asia/Kolkata" | pressed | only fills the select and hides the banner; nothing is saved and nothing says "now press Save" (API still America/New_York a second later) | ISSUE shell-settings-4 |
| Leave the page with an unsaved time zone | clicked Inventory | no prompt; the change was dropped; PAGES.md section 2 says a form with edits asks before navigating away | ISSUE shell-settings-4 |
| Restore | set Asia/Kolkata and name Ravi, saved | API shows Ravi, Asia/Kolkata | PASS |

### Appearance

| control | did | happened | result |
|---|---|---|---|
| System / Light / Dark chips | clicked Light | applied at once, saved (API theme light), tick moves; the name menu chips stay in step | PASS |

### Categories

| control | did | happened | result |
|---|---|---|---|
| New category, empty | looked | Add disabled with "Type a name first." | PASS |
| New category "tools" (duplicate of Tools, other case) | typed, Enter | "A category with that name already exists." | PASS |
| New category, 77 characters | typed, Enter | accepted with no limit; row wraps onto two lines cleanly, Rename and Delete stay aligned | PASS |
| Rename (Household to Home) | pressed Rename, typed, Escape, Enter | inline field with Name, Save, Cancel; saved to "Home". Escape does not cancel the edit, and after pressing Rename (and after saving) keyboard focus is on the page body, not in the field | ISSUE shell-settings-7 |
| Three switches per category (expiry date, "Maintenance on", printed label) | toggled all three on Home | each saved at once (API expires_default, maintenance_default, label_default flipped). The label "Maintenance on" sits next to a switch that may be off, which reads as a contradiction | ISSUE shell-settings-8 |
| Delete (empty category) | pressed Delete on the 77-character category | removed at once: no confirmation, no toast, no undo. (The in-use dialog needs items and is another screen's data.) | ISSUE shell-settings-9 |

### Locations

| control | did | happened | result |
|---|---|---|---|
| New place | added "Garage" | listed with "0 items"; focus stays in the field for the next one | PASS |
| Add inside | added "Shelf 2" under Garage | indented child, API path Garage > Shelf 2 | PASS |
| Move (dialog) | opened for Shelf 2, Escape, reopened, moved to top level, then back inside Garage | dialog "Move Shelf 2 / Put it inside" with a select; Escape closes and focus returns to the Move button; moves saved | PASS |
| Move Garage into its own child | chose "Garage > Shelf 2" in Move Garage, Move | refused with "A place cannot go inside itself or a place inside it." in the dialog, nothing changed | PASS |
| Rename (empty) | pressed Rename on Garage, cleared, Enter | Save stays disabled ("Type a name first."); but a leftover red line "A place cannot go inside itself or a place inside it." from the earlier Move attempt shows under the rename field | ISSUE shell-settings-10 |
| Delete a place that has a child | pressed Delete on Garage | "Move or delete the places inside it first." | PASS |
| Delete the leaf, then check the parent | deleted Shelf 2 | Shelf 2 gone at once (no confirmation or toast, same as categories) but Garage kept the red line "Move or delete the places inside it first." although it has no places inside | ISSUE shell-settings-10 |
| Delete last place | deleted Garage | list shows "No places yet. Add one above." | PASS |
| 5-deep nesting limit | not exercised | text says "Places nest up to 5 deep"; the sixth level was not tried | NOT VERIFIED |

### Backup

| control | did | happened | result |
|---|---|---|---|
| Status chip and line | read | chip "Working", "Last backup 1 Nov, 5:54 pm", "Newest good backup: 200 KB. It was checked when it was made.", "Folder: C:/Users/Admin/Enderchest-UXA-Backups", list "1 Nov, 5:54 pm, automatic, 200 KB" | PASS |
| Back up now | pressed | toast "Backup saved (200 KB)."; list gains "1 Nov, 6:06 pm, manual, 200 KB"; status line updates; file `manual-20261101T123655Z.sqlite3` (204,800 bytes) appeared in C:\Users\Admin\Enderchest-UXA-Backups | PASS |

### Notifications

| control | did | happened | result |
|---|---|---|---|
| Warn me this many days before expiry (text field, 1 to 14) | typed 15, abc, 0, then 7 | 15, abc and 0 are refused ("Choose 1 to 14 days.", Save days disabled); 7 saved with toast "You will be warned 7 days before."; restored to 3. The same sentence shows twice (above and beside the button) | PASS |
| Browser notifications | read | pane reports permission denied: "Blocked in this browser. Allow them in the browser's site settings for this page." No Allow button is offered (honest, since the browser would ignore it) | PASS |
| Send a test notification | read | disabled with "Allow browser notifications first." | PASS |
| Allow browser notifications button and a real test notification | not reachable | permission is already denied in the pane | BLOCKED: needs a normal browser window where notification permission is still "ask" |

### Gemini (no key set, nothing sent anywhere)

| control | did | happened | result |
|---|---|---|---|
| Intro and privacy wording | read | "Optional. Enderchest reads photos on this computer and works fully without Gemini. When Gemini is used, the text read from a photo goes to Google, and the photo itself only if "Send photos to Gemini" is on. Its answers are suggestions, marked unverified." Status chip "No key". Clear and honest | PASS |
| Gemini API key, whitespace paste | pasted 3 spaces | Save key stays disabled, "Paste a key first." | PASS |
| Gemini API key, "not a key" | typed, Enter | refused locally: "The key has a space or line break inside it. Copy it again in one piece."; nothing stored (GET /api/v1/gemini key_set false). After clearing the field the red sentence stays while the hint "Paste a key first." returns | ISSUE shell-settings-1 |
| When to use Gemini (Off / Ask each time / Automatic) | chose each, back to Off | saved each time (gemini_mode off, ask, auto). Notes change honestly: "Gemini is never called for photos." / "An Improve with Gemini button appears on the confirm screen. It needs a key first." / "Gemini is asked only when the photo reading found neither a name nor a model. It needs a key first." | PASS |
| Send photos to Gemini switch | on, then off | saved; the on text reads "On: the photo is sent too, scaled down and without its location or camera details." while the mode is Off and no key exists, so it says a photo is sent when nothing can be | ISSUE shell-settings-11 |
| Use the assistant switch | on, then off | it is not disabled in this build (no `disabled`, works without a key). On: "On: your questions and the matching item rows (name, category, place, quantity, expiry) are sent to Gemini. Notes, photos and prices stay on this computer. It needs a key first." Off: "Off: the Assistant page sends nothing." The wording does say why it cannot work yet | PASS |
| Model | emptied, "gemini pro!", "gemini-3.5-flash", back to default | empty and bad characters refused with "Use a model name such as gemini-3.5-flash-lite: letters, digits, dots and dashes."; valid one saved ("Gemini model saved."); default restored | PASS |
| Test connection | read | disabled, "Set a key first." | PASS |
| Remove key, Test connection with a key, "Improve with Gemini" | not reachable | needs a real key, which this check must not use | BLOCKED: needs a real Gemini key from the owner |
| Deep link `/settings#assistant-switch` from the Assistant page ("Open Gemini settings") | clicked | lands on the Gemini section with the "Use the assistant" row visible under the nav | PASS |

### Camera coach, Data, About

| control | did | happened | result |
|---|---|---|---|
| Show camera tips switch | off, on | saved (coach_enabled false then true); toast "Camera tips are on." | PASS |
| Open Trash link | clicked | opens `/trash` | PASS |
| About | read | logo 96 px as supplied; App version 0.1.0; Database version "4 of 4 supported"; Build date 2026-11-01 | PASS |

### Categories, in-use delete dialog (needed one real item, see the note at the end)

| control | did | happened | result |
|---|---|---|---|
| Delete a category that has an item | added the item "Torque wrench 3/8 inch" in Tools, pressed Delete on Tools | dialog "Delete Tools / 1 item uses this category. Choose where to move them first. / Move them to (No category, Home) / Move and delete / Cancel"; Move and delete to Home removed Tools and the item now shows Home (API) | PASS |
| That dialog closed with Escape | pressed Escape | closes, nothing changes; keyboard focus lands on the page body, not on the Delete button that opened it (PAGES.md section 2: focus returns to the opener; the places Move dialog does return it) | ISSUE shell-settings-7 |
| Locations: delete a place that has items (reassign dialog) | not exercised | needs an item that has a place | NOT VERIFIED |
| Places nest up to 5 deep | not exercised | would need five nested adds | NOT VERIFIED |

## P-17 Not found

| control | did | happened | result |
|---|---|---|---|
| `/nothing-here` | opened | logo mark 72 px centred above one card: "That page doesn't exist", "The address may be mistyped, or the page may have moved.", button "Go home"; nav capsule stays, no tab highlighted; title "Not found · Enderchest" | PASS |
| `/items/ENDR-ZZZZZZZZ` | opened | same card with "That item doesn't exist" | PASS |
| `/boot` | opened | the app's own Not found card (no boot page is served while the state is ok) | PASS |
| `/api/v1/nothing` | fetched | HTTP 404 with the one error shape `{"error":{"code":"not_found","message":"That does not exist.","details":{}}}`, no stack trace | PASS |
| Go home (mouse and Enter) | clicked, and Enter on the focused link | goes to `/` (Dashboard). One earlier mouse click did nothing because the browser pane had been resized under my emulation and delivered the click at the wrong spot; after re-applying the size it worked, so that was a test-tool artefact, not an app fault | PASS |

## P-16 Boot pages

| control | did | happened | result |
|---|---|---|---|
| starting / locked / recovery / failed pages | not reachable | they appear only when the backend is not in state `ok` (GET /api/v1/boot says ok, schema 4 of 4); forcing that means detaching or damaging the data volume | BLOCKED: needs the owner to reproduce a bad state on a throw-away copy |
| What a user sees when the app is stopped (stop.bat) | opened http://127.0.0.1:8473 while stopped | the browser's own "can't connect" error page (nothing from Enderchest can show while the container is down) | PASS (expected) |

## Scripts (D:\Projects\Enderchest-ux-a\Enderchest, run through `cmd /c` with the full path)

Preflight `docker compose config`: project `enderchest-uxa`, port 8473 published on 127.0.0.1, volume `enderchest_uxa_data`, backups bind C:/Users/Admin/Enderchest-UXA-Backups. Only that stack was touched; `docker ps` before and after shows the 8470 and 8472 containers untouched.

| script | did | happened | result |
|---|---|---|---|
| backup.bat (app running) | ran | prints "Backup made and verified: manual-20261101T124038Z.sqlite3 (200 KB)" and "Folder: C:/Users/Admin/Enderchest-UXA-Backups"; exit 0; the file appeared in the folder and in Settings > Backup | PASS |
| backup.bat (app stopped) | ran after stop.bat | "No backup was made. Unable to connect to the remote server / Is Enderchest running? Start it with run.bat"; exit 1; no file created. "remote server" is wrong for a program on this computer | ISSUE shell-settings-15 |
| stop.bat | ran | Docker lines, then "Enderchest stopped. Your data is untouched. Start it again with run.bat"; only enderchest-uxa-app-1 stopped | PASS |
| run.bat | ran twice (after stop) | Docker lines, "Enderchest is running at http://127.0.0.1:8473", "To stop it: stop.bat    To back up now: backup.bat"; it opened a browser window by itself (expected); profile, categories and backups were intact afterwards | PASS |
| restore.bat | read the file, did not run it | its prompts ("Number of the backup to restore", "Type RESTORE (capital letters) to continue") cannot be driven by redirected input | BLOCKED: needs the owner to run it by hand |
| restore.bat wording (from reading) | read | first line prints "Enderchest restore (docs/DATA_SAFETY.md 12)." (a developer file reference); backups are listed in "bytes" while backup.bat, the app and the Backup card say KB; two messages tell the user to run "docker compose logs app" | ISSUE shell-settings-15 |

## Theme and width matrix (DOM checks for clipping, off-screen items and text contrast, plus screenshots)

| screen | dark 1280 | light 1280 | dark 1024 | light 1024 |
|---|---|---|---|---|
| Welcome | checked (steps 1, 2, 3) | BLOCKED (first run cannot repeat) | BLOCKED | BLOCKED |
| Shell: nav, bell page, name menu | PASS (theme chips wrap: -3) | PASS (-3) | PASS (-3) | PASS |
| Settings, all ten sections | PASS | PASS | PASS | PASS |
| Not found | PASS | PASS | PASS | PASS |
| Long name in the nav | PASS | PASS | ISSUE shell-settings-5 | ISSUE shell-settings-5 |

Contrast: no text under 4.5:1 (3:1 for large text) in any of the combinations above, apart from disabled buttons. Off-state switches in light are very faint (shell-settings-14). Console: only failed-request lines that match my own invalid inputs (422, 409) and probes (404); no script errors.

## Data left behind in the 8473 instance

Name Ravi, time zone Asia/Kolkata, theme System, all Gemini settings back to defaults (mode Off, model gemini-3.5-flash-lite, no key), notification lead 3 days, category Home (its three switches were changed from the default: expiry on, maintenance on, label off), no places, one item "Torque wrench 3/8 inch" in Home (created by the Enter-key slip in shell-settings-12), three backups in C:\Users\Admin\Enderchest-UXA-Backups.

## Issues

Ids with severity, screen, and title. Steps, expected and actual for each are in the structured result returned with this record.

| id | severity | screen | title |
|---|---|---|---|
| shell-settings-1 | minor | Welcome, Settings > Gemini | Red validation messages stay after the field is fixed or cleared |
| shell-settings-2 | minor | Welcome | Keyboard focus drops to the page body after every step |
| shell-settings-3 | cosmetic | Name menu | The three theme chips never fit on one row; "Dark" wraps |
| shell-settings-4 | minor | Settings > Profile | "Use Asia/Kolkata" does not save and the banner disappears; leaving with an unsaved change gives no warning |
| shell-settings-5 | major | Shell nav | At 1024 px the name pill sticks out of the nav capsule for any name over about 15 characters, including "Mohammed Hasan Raza" |
| shell-settings-6 | minor | Dashboard greeting | A 40-character name overflows its column and runs into the ring |
| shell-settings-7 | minor | Settings > Categories | Rename and the Delete dialog leave focus on the page body; Escape does not cancel a rename |
| shell-settings-8 | cosmetic | Settings > Categories | "Maintenance on" sits next to a switch that may be off |
| shell-settings-9 | minor | Settings > Categories, Locations | Delete of an unused category or place is instant: no confirm, no toast, no undo |
| shell-settings-10 | minor | Settings > Locations | Old row errors stay on screen and show under the wrong control |
| shell-settings-11 | cosmetic | Settings > Gemini | "Send photos to Gemini" on says the photo "is sent too" while Gemini is Off and has no key |
| shell-settings-12 | major | Add an item sheet | Pressing Enter in "New location name" saves the whole item and closes the sheet; the typed place is lost |
| shell-settings-13 | minor | Welcome step 2 | Ticking a category chip makes it wider and the next chips jump to another row under the pointer |
| shell-settings-14 | minor | Settings (light) | Off-state switches are almost invisible (about 1.05:1 against the page) |
| shell-settings-15 | cosmetic | backup.bat, restore.bat | Script wording: "remote server", docs path, bytes vs KB, docker commands |
| shell-settings-16 | cosmetic | Settings | The 720 px column hugs the left edge and leaves about 495 px empty at 1280 |

Screenshots are in docs/logs/raw/final-ux/shots/shell-settings/ (files dated 2026-10-28 in that folder are from an earlier run, not this one).

