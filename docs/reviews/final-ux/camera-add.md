# Final UX check: camera-add (P-06, P-07, P-13, save delivery)

App: http://127.0.0.1:8473 (user "Ravi"). Browser: desktop built-in browser, 1280 and 1024 wide, dark and light. Test image: 1200x800 JPEG with "Oat Milk 1 L / BEST BEFORE 12/11/2026 / Model AB-1234", posted with curl.exe to `/api/v1/drafts` (field `images[]`, header `X-Enderchest: 1`). My first image clipped the date at the right edge ("12/11/202"), so the OCR year was ambiguous (2020); that is my test image, not an app defect. Screenshots were judged in-session only; none copied to the shots folder.

## P-06 Camera hub

| Control | Did | Happened | Result |
|---|---|---|---|
| Camera state (add) | Opened /camera?mode=add | "The camera is blocked", steps, Try again, Upload photos, Enter manually, drop/paste hint with limits | PASS |
| Try again | Clicked | Stays blocked; scan mode says "Tried again once; it is still not working." | PASS |
| Mode radios Add / Scan / Own | Clicked, URL follows (?mode=) | Switch correctly, selected state shown | PASS |
| Upload photos input | Inspected | accept JPEG/PNG/WebP, multiple. Native picker not clicked (browser cannot upload) | PASS (picker BLOCKED: needs real file dialog) |
| Enter manually | Clicked (1024 light) | Opens "Add an item" sheet, Save disabled with "Enter a name of 1 to 120 characters.", Escape closes | PASS |
| Device picker / Switch camera | - | Not shown (no devices) | BLOCKED: needs a real camera |
| Live view, shutter, QR decode | - | Browser blocks cameras | BLOCKED: needs a webcam |
| Scan: Type the ID, empty | Clicked Open item | Button disabled, reason "Type an ID first." | PASS |
| Scan: Type the ID, unknown `endr-0o1l2345` | Enter, then click | Request goes out (404) but the page shows nothing | ISSUE camera-add-1 |
| Keyboard | Tab x11 on own mode | Visible ring (about 1.7 px) on nav link | PASS |
| Overflow | scrollWidth vs innerWidth at 1280 and 1024 | No horizontal overflow | PASS |

## P-07 Review queue and confirm

| Control | Did | Happened | Result |
|---|---|---|---|
| Empty queue | /add with no drafts | "Nothing waiting for review." + Add an item | PASS |
| Upload, bad type (txt) | curl | 415 "Use a JPEG, PNG or WebP photo." | PASS |
| Queue rows | 1 and 2 drafts | Thumb, name "Oat Milk 1 L", "Added 1 Nov, 10:05 pm · read" (local time right), Review, Discard, Review next, Open the camera | PASS |
| Reading progress | Opened queue after upload | OCR (about 1.4 s) finished before the page loaded, "pending" state not seen | NOT VERIFIED (too fast to catch) |
| Confirm page | Opened | "Filled 4 fields from the photo. Check each one before saving.", chips "Read from photo, high confidence", model and size attributes read | PASS |
| What was read | Opened, Escape | Shows engine, time and raw text; Escape closes, focus returns to the button | PASS |
| Expiry gate | Save item with date unconfirmed | Both save buttons disabled, "To save: Confirm the expiry date." | PASS |
| Ambiguous pills | Clicked "12 Nov" | "Confirmed", Save enabled | PASS |
| Typed expiry | Set date by hand | Chip changes to "You", counts as confirmed | PASS |
| Name validation | Emptied; typed 151 chars | Reason shown; input capped at 120 | PASS |
| Quantity | 0, "-3x99999", 5 plus "One more" | 0 allowed (by design), junk blocked with "Enter a whole number, 0 or more.", stepper works | PASS |
| Price | "1,2x", "1,23,456.50" | "Enter an amount like 1240 or 1240.50."; grouped value accepted | PASS |
| New location | Typed "Pantry shelf", Enter | Added inline and selected, form not submitted | PASS |
| Save item | Clicked | Item created, lands on /items/ENDR-R85ABEXW, "Item saved" toast | PASS |
| Save and add next / Enter in name | requestSubmit | Saves | PASS |
| Discard draft (confirm page) | Clicked | Draft gone at once, back to /add, no confirm, no undo, no toast | ISSUE camera-add-3 |
| Discard (queue row) | Clicked | Row removed, same | ISSUE camera-add-3 |
| Discarded draft URL | Opened /add/<discarded id> | "This photo is done. It was already discarded." + Back to the review list | PASS |
| /add/does-not-exist | Opened | "That draft does not exist." with a Retry button only | ISSUE camera-add-4 |
| Light 1024 | Screenshot | Layout clean, no overflow | PASS |
| Console | Read errors | Only the expected 404s from my bad IDs | PASS |

## P-13 Do I own this?

| Control | Did | Happened | Result |
|---|---|---|---|
| Layout | Opened own mode | Honest blocked state, intro "You decide; nothing is saved unless you tap.", text field, Upload a photo | PASS |
| Check, text "Bosch cordless drill" | Enter | "2 items may be the same", pills "Possible", reason "Same name", location path, quantity | PASS (never "certain" or "100%") |
| Photo/image check | - | Needs a real upload | BLOCKED: needs a file picker |
| Not the same | Clicked | Row hidden, count text updates to "One item may be the same" | PASS |
| I didn't buy it | Clicked | Sheet, price prefilled, required; empty/"abc"/0 give reasons ("Type the price you did not spend.", "Type an amount such as 1,240 or 1240.50.", "The price must be more than ₹0.") | PASS |
| Save 123456.5 | Enter | Toast "₹1,23,456.50 saved on ...", Indian grouping right | PASS |
| Undo | Clicked | Savings total back to 0 | PASS |
| After saving, same row | - | The row still offers I didn't buy it again | cosmetic, see camera-add-5 |
| None of these | Clicked | "Then you probably do not have it yet." + Add it to my inventory, I'll buy it | PASS |
| I'll buy it | Clicked | Results clear with no message | PASS (quiet but fine) |
| No match ("Garden hose 20 m") | Enter | "Nothing in your inventory looks like this" | PASS |
| Add it to my inventory (text only) | Clicked | Opens the form prefilled with the typed name, but titled "Duplicate item" | ISSUE camera-add-2 |
| Sheet Escape | Pressed | Closes, focus back on the button | PASS |

## Save delivery (D-138)

| Check | Result |
|---|---|
| Save click to delivery element removed | 1202 ms measured with a MutationObserver (animation element added at 39 ms, removed at 1202 ms; about 1.16 s of animation). Right at the 1.2 s limit; measurement includes observer latency | PASS (borderline, 1.16 s) |
| Item saved at once | Item page and "Item saved" toast appear within 44 ms | PASS |
| Click during it | Clicked the Tasks nav link 365 ms in, while the delivery was drawn: navigated to /tasks, delivery cleared | PASS |

## Issues

- camera-add-1 (major): P-06 scan mode, no camera. Typing an unknown ID and pressing Open item sends the lookup (404) but nothing is shown. The "No item with that ID" message is set in state but the status box only prints the "Scanning needs the camera" line when the camera is not live (Camera.tsx ScanControls, line 360). A user typing a label ID without a camera gets no answer.
- camera-add-2 (minor): P-13 "Add it to my inventory" without a photo opens the item form titled "Duplicate item" (ItemFormSheet.tsx line 106: any prefill counts as a duplicate). Should read "Add an item".
- camera-add-3 (minor): P-07 Discard draft (confirm page and queue row) discards immediately with no confirmation, no undo and no toast, so one stray click loses the edits and the draft (photo untouched on disk, but no way back in the UI).
- camera-add-4 (minor): P-07 /add/does-not-exist shows "That draft does not exist." with a Retry button that cannot help and no link back to the review list (the "already discarded" state has one).
- camera-add-5 (cosmetic): P-13 after "I didn't buy it" is saved, the candidate row looks unchanged and offers the button again, so a second entry for the same item is one click away. A "Saved" mark would help.
