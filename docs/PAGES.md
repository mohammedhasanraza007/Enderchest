# PAGES.md — Every Screen, What It Does, What It Calls

> **Read when:** building or verifying any screen. **Do not read when:** doing backend-only, Docker or token work.
> **Sections:** 1 Route map and nav by phase · 2 Shared behaviour · P-01 Welcome · P-02 Settings · P-03 Inventory · P-04 Item · P-05 Item form · P-06 Camera hub · P-07 Review queue and confirm · P-08 Labels · P-09 Trash · P-10 Tasks · P-11 Notifications · P-12 Dashboard · P-13 Own check · P-14 Savings · P-15 Assistant · P-16 Boot pages · P-17 Not found.
> Open **only the page your phase spec names**. How things *look* (tokens, glass, pills, motion) is in `DESIGN.md`; this file says *what exists, what each control does and which endpoint it calls*. The dashboard's look and motion are in `DESIGN.md` section 6; its data wiring is P-12 here.

Shell data loaded on every page: `GET /api/v1/profile` (name, theme, time zone, first-run flag) and `GET /api/v1/settings`. Rules that apply to every row below: no control exists unless its action works (`CLAUDE.md` section 8); wireframes show structure at 1280 px, not styling; every list has loading, empty and error states; every endpoint is written `METHOD /api/v1/path` and exists in `API.md`.

---

## 1. Route map and nav by phase

| Route | Page | Phase | Reached from |
|---|---|---|---|
| `/welcome` | P-01 First run | 1 | automatic until a name is saved |
| `/settings` | P-02 Settings | 1 (sections arrive later) | name pill menu |
| `/inventory` | P-03 Inventory | 2 | nav |
| `/items/:publicId` | P-04 Item | 2 | tile, scan, search |
| `/camera?mode=add\|scan\|own` | P-06 Camera hub | 2 (`own` in 6) | nav |
| `/add`, `/add/:draftId` | P-07 Review queue / confirm | 2 (OCR in 3) | camera, Inventory chip |
| `/labels?ids=…` | P-08 Labels | 2 | Item page, Inventory select mode |
| `/trash` | P-09 Trash | 2 | Inventory overflow, Settings |
| `/tasks` | P-10 Tasks | 4 | nav |
| `/notifications` | P-11 Notifications | 4 | bell |
| `/` | P-12 Dashboard | 5 | nav, logo |
| `/savings` | P-14 Savings | 6 | nav |
| `/assistant` | P-15 Assistant | 9 | Assistant tab after Savings (D-133) |
| (server-rendered) | P-16 Boot pages | 0 | automatic when state is not `ok` |
| `*` | P-17 Not found | 1 | automatic |

**Nav capsule contents by phase (D-034).** Nav items appear only when their page works.
| After phase | Centre items | Right side | `/` goes to |
|---|---|---|---|
| 1 | none | name pill | `/settings` |
| 2, 3 | Inventory, Camera | name pill | `/inventory` |
| 4 | Inventory, Camera, Tasks | bell, name pill | `/inventory` |
| 5 | Dashboard, Inventory, Camera, Tasks | bell, name pill | Dashboard |
| 6 to 8 | Dashboard, Inventory, Camera, Tasks, Savings | bell, name pill | Dashboard |
| 9 | Dashboard, Inventory, Camera, Tasks, Savings, Assistant (D-133) | bell, name pill | Dashboard |
Name pill menu: Settings, theme (three small pills), Trash, backup status line, no Assistant entry (it is a tab from Phase 9, D-133). No Sign out exists before the locked phase. The `LIVE` badge shows on the Camera item only while a camera stream is running.

---

## 2. Shared behaviour (do not re-decide per page)

- **States:** *loading* = skeleton shaped like the final content; *empty* = one sentence and one real action; *error* = what happened, what to do, a Retry button that retries the same request; *locked* (HTTP 503 `locked`) = redirect to the boot page.
- **Undo:** every reversible action (use, mark expired, discard, delete, task done or skip, savings entry) shows a toast "Done. Undo" for 10 seconds calling `POST /api/v1/events/{id}/undo`.
- **Unsaved changes:** a form with edits asks before navigating away.
- **Double submit:** primary buttons disable while a request runs and send an `Idempotency-Key` on creates.
- **Dates** shown as `16 Oct 2026` (or `16 Oct` when the year is the current one); money as `₹1,240` with Indian grouping from integer paise; times 12-hour.
- **Photos** use the thumb endpoint in lists and the file endpoint on detail; broken image shows a neutral tile with the item's initial.
- **Keyboard:** every control reachable by Tab; sheets close on Escape; focus returns to the opener.
- **Errors from the server** show the `message` from the error shape; never a stack trace.

---

## P-01 Welcome (`/welcome`, Phase 1)
Three steps in one frosted card on the page background, logo mark 72 px above.
1. **Name** (required, 1 to 40) and **Time zone** (select, pre-set from the browser, editable). Button "Continue" calls `PUT /api/v1/profile`.
2. **Starter categories** (Phase 2 onwards; skipped before it exists): six chips from `DATA_MODEL.md` 2.4, all optional. "Continue" calls `POST /api/v1/categories` once per ticked chip; "Skip" creates none.
3. **Done:** greeting by name and one real action: "Add your first item" (`/camera?mode=add`, from Phase 2) or "Open settings" (Phase 1 only).
Guard: if `first_run_complete` is true, redirect to `/`. Test: closing the tab on step 2 and returning resumes at step 2 (name already saved).

## P-02 Settings (`/settings`, Phase 1, sections added by phase)
One column of frosted section cards, each with a serif title. A section appears only when its feature exists.
| Section (phase) | Contents and actions |
|---|---|
| Profile (1) | name, time zone; "Save" → `PUT /api/v1/profile`. A banner offers to update the time zone if the browser's differs |
| Appearance (1) | System / Light / Dark pills → `PUT /api/v1/profile` (`theme`) and applied instantly |
| Backup (1) | status line (last good backup time, size), warnings, list of recent backups, folder path hint, "Back up now" → `POST /api/v1/backups`. List from `GET /api/v1/backups` |
| Categories (2) | list with item counts; list from `GET /api/v1/categories`; add (`POST /api/v1/categories`); rename or toggle the three defaults (`PATCH /api/v1/categories/{id}`); delete (if in use a dialog asks which category to move items to, then `DELETE /api/v1/categories/{id}?reassign_to=`) |
| Locations (2) | indented tree with item counts; add child, rename, move (parent picker), delete with reassign. list from `GET /api/v1/locations`; add (`POST /api/v1/locations`); rename or move (`PATCH /api/v1/locations/{id}`, a refused move shows the `cycle` message); delete (`DELETE /api/v1/locations/{id}?reassign_to=`) |
| Notifications (4) | "Warn me N days before expiry" (1 to 14), browser permission state with an "Allow browser notifications" button (calls `Notification.requestPermission()`), "Send a test notification" (fires a real browser notification locally). `PATCH /api/v1/settings` (`lead_days`). Text states: "Reminders appear here and as browser notifications while an Enderchest tab is open." |
| Gemini (3) | key status, "Set or replace key" (`PUT /api/v1/gemini/key`), "Remove key" (`DELETE /api/v1/gemini/key`), model name, mode Off / Ask each time / Automatic, "Send photos to Gemini" toggle with the disclosure text, "Test connection" (`POST /api/v1/gemini/test`). State loaded from `GET /api/v1/gemini`; toggles via `PATCH /api/v1/settings` |
| Camera coach (7) | toggle `coach_enabled` via `PATCH /api/v1/settings` |
| Data (2) | link to Trash |
| About (1) | logo 96 px, app version, schema version, build date (from `GET /health`) |

## P-03 Inventory (`/inventory`, Phase 2)
```
[ Inventory (serif) ]                         [To review (3)] [Print labels] [＋ Add item]
[ search pill ........ ] [Category ▾] [Location ▾] [State ▾] [Expiry ▾] [Photo ▾]  sort ▾
┌ tile ┐ ┌ tile ┐ ┌ tile ┐ ┌ tile ┐     (virtualised grid, 4 / 3 / 2 columns by width)
```
- Data: `GET /api/v1/items` with the filter and sort state in the URL query so Back restores it. Infinite scroll via `cursor`; `total` shown as "143 items".
- Tile: thumb (`GET /api/v1/photos/{id}/thumb`), name, "Category · Location", quantity badge when more than 1, status chip (`StatusChip`, expiry word). Click → P-04.
- "＋ Add item" → `/camera?mode=add`. "To review (N)" appears when `GET /api/v1/drafts` has open drafts → `/add`. Overflow menu: Trash.
- "Print labels" toggles select mode (checkboxes). A bar offers **Print labels** (→ `/labels?ids=`), **Move to location** (location picker, `PATCH /api/v1/items/{public_id}` per item), **Delete** (`DELETE /api/v1/items/{public_id}` per item, one undo for the batch).
- States: empty ("No items yet" + Add item); no matches ("Nothing matches these filters" + Clear filters); error with Retry.
- Performance: 1,000 items scroll smoothly; first 100 within the budget in `ARCHITECTURE.md` 11.

## P-04 Item (`/items/:publicId`, Phase 2; lifecycle and maintenance Phase 4)
```
┌ photo frame (carousel, ‹ ›, "Add photo", ★ primary, trash) ┐  ┌ card ───────────────────────────┐
│                                                            │  │ Name              [status chip]  │
└────────────────────────────────────────────────────────────┘  │ Category · Location (path)       │
 thumbnails strip                                               │ Quantity · Price · Expiry        │
                                                                │ Attributes (key — value rows)    │
 ┌ Label card: QR + ENDR-XXXXXXXX [Copy] [Print label] ┐        │ Notes                            │
 └ "Printed 3 Oct" or "Not printed" (hidden if no_label_needed) ┘ │ [Edit] [⋯]                       │
 ┌ Maintenance (4): toggle, every N days, next due, [Inspect now] ┐└──────────────────────────────────┘
 ┌ History (timeline of events) ┐
```
- Loads `GET /api/v1/items/{public_id}`; history from `GET /api/v1/items/{public_id}/events` (paged).
- Photos shown from `GET /api/v1/photos/{id}/file`. "Add photo" opens file picker (or camera) → `POST /api/v1/items/{public_id}/photos`; ★ → `PUT /api/v1/items/{public_id}/primary-photo`; trash → `DELETE /api/v1/photos/{id}` with undo wording "Photo hidden" (file kept).
- Edit opens the item form sheet (P-05). Overflow ⋯: Duplicate (opens P-05 pre-filled, new item), Delete (`DELETE /api/v1/items/{public_id}`, then toast with Undo and return to Inventory).
- Label card: **Print label** opens `/labels?ids=<id>`; QR image from `GET /api/v1/items/{public_id}/qr.svg`; Copy copies the ID.
- Phase 4 actions (shown when state is `active`): **Use it** (`POST /api/v1/items/{public_id}/use`), **Mark expired** (`POST /api/v1/items/{public_id}/mark-expired`), **Discard** (`POST /api/v1/items/{public_id}/discard`). For non-active items: banner with state and **Reactivate** (`POST /api/v1/items/{public_id}/reactivate`).
- Maintenance card (4): toggle and interval save via `PUT /api/v1/items/{public_id}/maintenance`; **Inspect now** opens the inspection sheet: result Good / Worn / Defective (maps to `ok`/`worn`/`defective`), note, optional photo, "Save inspection" → `POST /api/v1/items/{public_id}/inspections`; list of past inspections from `GET /api/v1/items/{public_id}/inspections`. A Gemini-suggested interval shows "suggested, unverified" until the user presses Confirm.
- States: unknown id → P-17 variant "That item doesn't exist"; deleted item → banner "In Trash" with **Restore** (`POST /api/v1/items/{public_id}/restore`).

## P-05 Item form (sheet, Phase 2; used by P-03, P-04, P-07)
Fields in order: Name*; Category (select + "New category" inline → `POST /api/v1/categories`); Quantity (integer, minimum 0 shown with steppers); Location (tree picker + "New location" inline → `POST /api/v1/locations`); Expiry (segmented: **Has date** / **No expiry** / **Not sure**, date field when Has date; defaults from the category, `DATA_MODEL.md` 2.4); Price (₹, optional); Attributes (key/value rows, suggestions size, model, part_no, brand, colour; comma-separated values become a list); Notes; "I don't need a printed label" toggle.
Save → `POST /api/v1/items` (new) or `PATCH /api/v1/items/{public_id}` (edit). Validation inline under each field; Save disabled with a stated reason while invalid; unsaved-changes guard.

## P-06 Camera hub (`/camera`, Phase 2; `own` Phase 6; coach Phase 7)
Mode pills at the top: **Add item**, **Scan label**, **Do I own this?** (last one from Phase 6). Live view fills the card; round shutter; **Upload photos** button; drag-and-drop and paste (Ctrl+V) accept images. The stream stops when the page is left or the tab is hidden. Device picker and a Switch camera button appear only with more than one camera; the list follows cameras connected or removed, and a camera sending only black is skipped on opening (D-126). Preferred 1280×720.
- **Camera states:** asking permission (explains why); denied or no device (steps to enable it in the browser, plus Upload and "Enter manually" which opens P-05); in use elsewhere; stream lost mid-session (recovers or says why).
- **Add mode:** shutter or upload → `POST /api/v1/drafts` (one draft per image, up to 20) → for one image go to `/add/:draftId`; for several go to `/add`. After saving, the camera stays open ("Add next item" is the default).
- **Scan mode:** a JavaScript QR decoder (D-055) reads frames at about 5 per second. A code matching `ENDR-XXXXXXXX` calls `GET /api/v1/lookup/{code}` and opens the item; an unknown code shows "No item with that ID" and keeps scanning. A "Type the ID" field (accepts lowercase and typed look-alikes) calls the same endpoint.
- **Own mode (6):** see P-13.

## P-07 Review queue and confirm (`/add`, `/add/:draftId`, Phase 2; OCR parts Phase 3)
**Queue (`/add`):** list of open drafts (`GET /api/v1/drafts`): thumb, detected name or "Untitled", age, OCR state. Buttons: Review, Discard (`DELETE /api/v1/drafts/{id}`), "Review next". Empty: "Nothing waiting for review."
**Confirm (`/add/:draftId`):** loads `GET /api/v1/drafts/{id}`; left photos (add more via `POST /api/v1/drafts/{id}/photos`); right the P-05 fields, saved as you edit via `PATCH /api/v1/drafts/{id}`.
- Phase 3 additions: each field shows a source chip (**Read from photo** / **Gemini** / **You**) and a confidence dot; **Re-read** (`POST /api/v1/drafts/{id}/extract` with `local`), **Improve with Gemini** (same call with `gemini`, only when allowed in Settings), and a drawer "What was read" showing the raw text.
- **Expiry rule:** a parsed date shows "Not confirmed" until the user taps it. Ambiguous day/month shows both readings as two pills to pick from. Save is blocked with the reason "Confirm the expiry date" (`expiry_unconfirmed`).
- Footer: **Save item** (`POST /api/v1/drafts/{id}/commit`), **Save and add next** (commit, then next draft or the camera), **Discard draft**.

## P-08 Labels (`/labels?ids=`, Phase 2)
Preview of the sheet. Layout picker: **A4 sheet, 3 × 7 (63.5 × 38.1 mm)** and **Single label (50 × 30 mm)**. Each label: QR (at least 25 mm), ID in the mono font, name (one line). **Print** calls `window.print()` using a print stylesheet; afterwards a banner asks "Did the labels print?" with **Yes, mark as printed** (`POST /api/v1/items/label-printed`) and **No**. **Download QR** per item uses `GET /api/v1/items/{public_id}/qr.svg`. Items marked `no_label_needed` are listed as skipped.

## P-09 Trash (`/trash`, Phase 2)
List from `GET /api/v1/items?deleted=only&state=all`. **Restore** (`POST /api/v1/items/{public_id}/restore`). **Delete permanently** opens a dialog: states that older backups still contain the item, requires typing `DELETE`, and, when no good backup under 24 hours exists, offers **Back up now** first (`POST /api/v1/backups`); then `DELETE /api/v1/items/{public_id}/permanent`. Empty: "Trash is empty."

## P-10 Tasks (`/tasks`, Phase 4)
Top: the 30-day road (same component as the dashboard road, longer window; it arrives with the road component in Phase 5, D-103). Below: frosted card with filter pills **Due soon / All / Done** (`scope` `due`, `all`, `done`, D-106) and rows (title, item link, repeat, next due word). `GET /api/v1/tasks?scope=`.
- **New task** sheet: title*, item (optional picker), repeat (None / every N days), schedule (From completion / Fixed dates), first due date*, notes → `POST /api/v1/tasks`.
- Row actions: **Mark done** (`POST /api/v1/tasks/{id}/done`), **Skip** (`POST /api/v1/tasks/{id}/skip`), **Edit** (`PATCH /api/v1/tasks/{id}`), **Delete** (`DELETE /api/v1/tasks/{id}`, undo). Maintenance tasks show **Inspect now** (opens the inspection sheet of P-04).
- Empty: "No tasks yet" + New task.

## P-11 Notifications (`/notifications`, Phase 4)
Tabs **Open / Snoozed / Resolved** (`GET /api/v1/notifications?status=`). Rows are the same as the dashboard's Needs attention rows. The server supplies each row's `actions`; the client renders them: *expiry_soon* Use it (`POST /api/v1/items/{public_id}/use`) and Snooze; *expired* Mark expired and Snooze, more: Use it, Discard; *inspection_due* Inspect now and Snooze, more: Skip, Discard; *task_due* Mark done and Snooze, more: Skip; *inspection_finding* (D-104) Mark discarded and Keep using (`POST /api/v1/notifications/{id}/dismiss`). **Snooze** opens three options Tomorrow / In 3 days / Next week → `POST /api/v1/notifications/{id}/snooze`. Opening the page calls `POST /api/v1/notifications/read-all`; opening a single row marks it read (`POST /api/v1/notifications/{id}/read`). A banner invites enabling browser notifications when permission is not granted.
**Live behaviour:** the app polls `GET /api/v1/notifications/count` every 60 seconds and on window focus; new unseen rows fire a browser notification (if allowed) then `POST /api/v1/notifications/{id}/shown`. The tab title shows `(N) Enderchest` while N is above zero. Empty: "Nothing needs you right now."

## P-12 Dashboard (`/`, Phase 5; look in `DESIGN.md` section 6)
One request: `GET /api/v1/dashboard`. Bindings: greeting and subtitle from `greeting` and `subtitle`; ring values from `rings`; centre number from `score` and `item_count`; Needs attention rows from `attention.rows` (three at most, then "View all N" → `/notifications`); road from `road`; savings pill from `savings` only when `pill_date` is set. Ring click opens a sheet from `GET /api/v1/dashboard/rings/{ring}` listing what counts and what does not, each linking to its item or task. Row actions are those of P-11, with the row animating out on success. Subtitle examples (computed, never invented): "3 things need you today", "Everything is on track", "Add items to see your overview". Empty database: rings empty, centre shows an em dash and "Add your first item" (→ `/camera?mode=add`).

## P-13 Do I own this? (`/camera?mode=own`, Phase 6)
Input: shutter, upload, paste or drop an image, and/or type text (for example "13 mm spanner"). **Check** → `POST /api/v1/ownership/check`. Result: up to five candidate rows (photo, name, location path, quantity, confidence pill **High / Medium / Possible**, one "why" line such as "Same model number" or "Looks similar"). Per candidate: **Open item**, **Not the same** (hides it). Footer, always present: **None of these** → two buttons: **Add it to my inventory** (creates a draft from the image via `POST /api/v1/drafts`) and **I'll buy it**.
When the user owns it and decides not to buy: **I didn't buy it** → sheet asking the price saved (pre-filled from the item's price when known, required, ₹) → `POST /api/v1/savings`; toast with Undo. The page never says "you own this" or "100%"; it always asks. Nothing is saved to inventory without the user's tap.

## P-14 Savings (`/savings`, Phase 6)
Dominant element: the rupee total in the serif display type with segmented pills **This month / All time** (`GET /api/v1/savings?period=`). Below: frosted list of confirmed entries (date, item name or link, price, note) with **Remove** (`DELETE /api/v1/savings/{id}`, confirm, undo). Empty: "Nothing saved yet. When you skip a purchase because you already own it, it appears here." No estimates, ever.

## P-15 Assistant (`/assistant`, Phase 9)
As in the owner's reference (`docs/design/reference-assistant.md`, D-132): a centred column with the serif title "Assistant", the privacy line "This chat and the matching item rows are sent to Gemini. Notes, photos and prices stay on this laptop." with a Settings link (D-135), and one glass card. Questions are cream pills on the right; answers are darker 16 px boxes on the left whose item names (`segments` with a `public_id`) are underlined links to `/items/:id`, with "From your inventory · N items checked" under an answer when `rows_checked > 0`. The foot is a pill input "Ask about your things…" with a round cream ↗ Send button; an empty send says "Type a question first.".
States: unavailable (no key, or "Use the assistant" off: explains which and links to `/settings#assistant-switch`, no input), empty, sending (input and Send disabled, "Checking your inventory…"), an answer, the honest miss, and an error (offline, bad key, limit) with Retry. The conversation lives in `sessionStorage` (this tab only), so an item link and Back keep it; "Start over" clears it; the newest 20 messages are sent. Read-only: the assistant cannot change data. `POST /api/v1/assistant/chat`.
Settings → Gemini has the "Use the assistant" switch (`assistant_share_item_text`, default off) with a note saying what leaves; the photo mode's Off note reads "never called for photos" (D-136).

## P-16 Boot pages (server-rendered, Phase 0; styled with the tokens CSS from Phase 1)
Served by the backend as plain HTML with a little JavaScript, **not** by the React app, so they work when the database does not. They read `GET /api/v1/boot`. One page per state of `DATA_SAFETY.md` section 11:
| State | Headline | Content |
|---|---|---|
| `starting` | "Starting Enderchest…" | auto-refreshes every 2 s |
| `locked` / no data volume | "Your data volume isn't attached" | what happened, nothing was changed, steps (start Docker Desktop, run `run.bat`), "Copy details" |
| `locked` / second instance | "Enderchest is already running" | where |
| `locked` / newer data | "This data is newer than this app" | versions, "Update the app" |
| `recovery` | "We found existing backups" | backup list (date, size, items) with **Restore this backup** (typed `RESTORE`, `POST /api/v1/boot/restore`) and a discouraged **Start empty anyway** (typed `START EMPTY`, `POST /api/v1/boot/start-empty`) |
| `failed` | "An update could not be applied" | safe backup name, what to send |

## P-17 Not found (`*`, Phase 1)
Calm full-card message, the logo mark, and "Go home". Unknown item ids use the same card with "That item doesn't exist".
