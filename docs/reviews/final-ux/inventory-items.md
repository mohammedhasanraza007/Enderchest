# Final UX check: inventory-items

App http://127.0.0.1:8473, user Ravi. Browser pane emulated 1280x800 and 1024x768, light and dark. No screenshots saved to the shots folder (screenshots were only used to judge layout).
Items added through the form: Bosch cordless drill GSR 12V, Paracetamol 650 mg strip, Amoxicillin syrup 60 ml (past date), Greek yogurt 400 g, a 118-character flask name (qty 0, Not sure). Plus a duplicate, later deleted permanently. Two items from the first run were moved to Kitchen fridge by the bulk Move.

## P-05 Item form
| control | did | happened | result |
|---|---|---|---|
| Enter manually, Close, Esc | opened, Esc empty and with edits | closes, focus returns to opener; with edits asks "Discard your changes?" (Discard changes / Keep editing); Esc dismisses the guard | PASS |
| Name | empty, spaces, 118 chars, maxlength 120 | "Enter a name of 1 to 120 characters", Save disabled with reason, trimmed on save | PASS |
| Category + New category | picked; added Pharmacy; added "medicine" | Pharmacy auto-selected; duplicate shows "A category with that name already exists." | PASS |
| Location + New location, nested | Workbench drawer under Garage; Kitchen fridge top level | both created, selected, path shown | PASS |
| Quantity, steppers | 2.5, 99999999999, 0, 3 | whole-number message and Save disabled; 0 saved; message says "0 or more" but gives no upper limit | PASS |
| Expiry Has date / No expiry / Not sure | all three, typed date, past date | category default respected (Home Has date, Tools No expiry); empty date blocks Save with reason; days left correct (134, 4) | PASS |
| Price | abc, -5, 32.755, 4,299.50, 1,85,000, 32 | bad ones blocked "Enter an amount like 1240 or 1240.50."; item shows ₹4,299.50 | PASS |
| Attributes | + model, + brand, + Other "Capacity", empty value, comma list | "Give each attribute a value." blocks Save; list saved as list | ISSUE inventory-items-1 |
| Notes | text with html and script tags | shown as plain text | PASS |
| "I don't need a printed label" | toggled | Home default is on, so my click turned it off; item then appears in labels, yogurt skipped | PASS |
| Enter submits, Save item | Enter in a field | saves, "Item saved." | PASS |
| Edit prefill, Duplicate | edit renamed and added brand; duplicate | all fields prefilled, "(copy)" added to name; saved to a new id | PASS |
| Tab / focus ring | Skip link, Close, fields | visible ring on Skip link and Enter manually; Tab order not exhaustively walked (keyboard Tab presses were inconsistent in this harness) | PASS (partial) |

## P-03 Inventory
| control | did | happened | result |
|---|---|---|---|
| Search | name, "dolo" (model attr), "12V-35", "zebrawood" (notes only), "100%_'\"<" | each finds the right single item; special characters give "Nothing matches these filters." with Clear filters; q in URL | PASS |
| Clear filters | clicked | resets search and filters, 10 items | PASS |
| Category, Location | Medicine, Garage, Bathroom cabinet | correct; Garage includes child places | PASS |
| State | Used, All | Used gives no-match state; All 10 | PASS |
| Expiry | soon, today, past, none, unknown | correct; "soon" is empty with 4 days left because lead time is 3 days (not shown on the page) | PASS |
| Photo | With, Without | none have photos so With is empty, Without all | PASS |
| Sort | Newest, Name A-Z, Expiry soonest | correct orders | PASS |
| Sort select width at 1024 | measured | "Newest first" needs 160px, select is 141px, text truncated | ISSUE inventory-items-2 |
| Print labels (select mode) | toggled, selected 2 then 4 | bar shows "No items chosen" with disabled actions and "Choose items first", then "2 chosen" | PASS |
| Move to location | dialog, Esc, move 2 to Kitchen fridge | Esc closes and focus returns; "2 items moved."; data correct | PASS |
| Print labels (go) | 4 chosen | opens /labels?ids=... | PASS |
| Tile layout | 1280 and 1024, both themes | no horizontal overflow (scrollWidth 1265 and 1009), long name truncated with ellipsis, grid 4 columns at 1280, 3 at 1024 | PASS |
| Bulk Delete | not run (would trash two of the first-run items) | | BLOCKED: not exercised to keep the first-run data; single delete tested on P-04 |

## P-04 Item
| control | did | happened | result |
|---|---|---|---|
| Use it | clicked at qty 2, then at qty 1 | "Used one. 1 left. Undo"; at 1 becomes Used, quantity 0, banner "Used up. Reactivate it if you have more." | PASS |
| Undo toast | clicked | Discard undo worked; the "Used" and "Mark expired" toasts timed out before my slow click, so only Discard undo and Reactivate were confirmed | PASS (partial) |
| Reactivate | clicked on used and expired | state active, quantity 1 | PASS |
| Mark expired | clicked | banner "Marked expired." with Reactivate, history entry | PASS |
| Discard | clicked, Undo | back to active | PASS |
| Edit | rename, add brand, Enter | saved, title updated, focus back on Edit | PASS |
| Overflow menu | opened, Esc, Duplicate, Delete | menu shows Duplicate and Delete; Esc closes with focus back | PASS |
| Delete | from menu | "Moved to Trash. Undo", returns to Inventory | PASS |
| Maintenance plan | 0, 5000, 90 with first due date | 0 and 5000 block Save with "Inspect every 1 to 3650 days."; saved "Every 90 days . next due 1 Dec" | PASS |
| Reminders toggle | off | "Inspection reminders off.", card says "switched off" | PASS |
| Inspect now sheet | Worn plus note | "Inspection suggested: worn.", listed under Inspections, Mark discarded offered | PASS |
| Copy ID | clicked | "ID copied." | PASS |
| Print label link | read href | /labels?ids=<id>, not clicked as Print | PASS |
| Unknown / purged id | opened purged id | "That item doesn't exist" with Go home | PASS |
| Add photo, inspection photo | not run | needs a file upload | BLOCKED: needs a file upload |
| Light and dark 1024 | item page | no overflow; action buttons wrap to two rows | PASS |

## P-08 Labels
| control | did | happened | result |
|---|---|---|---|
| Sheet preview | 4 ids | 3 labels plus a "Skipped" card for the no-label item; QR 30 mm on A4, 25 mm on single | PASS |
| Layout picker | A4, Single label | radio state changes, QR size changes | PASS |
| Download QR | read hrefs only | links to qr.svg with download name; not clicked (download needs permission) | BLOCKED: needs owner permission to download |
| Print | not clicked (instruction) | | BLOCKED: needs a real print |
| "Did the labels print?" confirmation | | only appears after Print | BLOCKED: needs a real print |

## P-09 Trash
| control | did | happened | result |
|---|---|---|---|
| Trash list | opened from inventory menu | lists name, "Moved to Trash <time>", Restore, Delete permanently | PASS |
| Delete permanently dialog | opened | says photos removed and older backups still contain it; needs typing DELETE | PASS |
| Typed confirmation | "delete", "DELETE" | lowercase keeps button disabled with "Type DELETE in capitals first."; capitals enable | PASS |
| Permanent delete | confirmed on my test copy | "... was deleted permanently."; a good backup (auto 21:05) existed so no Back up now step appeared | PASS |
| No backup under 24 h branch | | cannot be reached, backups cannot be removed | BLOCKED: needs no backup younger than 24 h |
| Restore | clicked | "Cordless drill 18V restored.", "Trash is empty." | PASS |

Console: two errors, a 409 (duplicate category, expected) and a 404 (purged item page, expected).

## Issues
- inventory-items-1 (cosmetic) P-05 attribute name box too narrow: custom names such as "Capacity" are clipped (box about 95 px, text needs 115 px), and long values like "GSR 12V-15, GSR 12V-35" are clipped at 1024. Steps: form, + Other, type Capacity in Name. Expected: whole name visible or box wider.
- inventory-items-2 (cosmetic) P-03 at 1024 px the Sort select (141 px) truncates "Newest first" to "Newest..." (text 88 px plus 72 px padding). Expected: full label visible.
