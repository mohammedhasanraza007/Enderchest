# Phase 2 — Inventory core

**Read list:** `CLAUDE.md` sections 0, 5, 6, 8 · this file · `DATA_MODEL.md` 1, 2.4–2.8, 2.11, 3.1–3.3 · `API.md` 1, 2.4–2.8 · `PAGES.md` 1, 2, P-01 (step 2), P-02 (Categories, Locations, Data), P-03 to P-09 · `ARCHITECTURE.md` 6 (Uploads), 8 · `DESIGN.md` 7, 12, 13 only for empty and error states.
**Do not read:** `PROJECT_PLAN.md`, OCR or Gemini material, other phase specs.
**Owner supplies:** the acceptance run below. **Milestone:** A.

## Goal
A real, fast, safe inventory: add things with the webcam or from files (one or many at once), find them, label them, delete and restore them, and scan a printed label back to its item.

## Build order
1. Migration 0002 and repositories (`DATA_MODEL.md` 2.4 to 2.8, 2.11). Public id generator with the Crockford rules and typed-input normalisation.
2. Categories and locations: endpoints, Settings sections, tree rules (depth 5, cycle refusal, reassign on delete). First-run step 2 (starter categories).
3. Items: create, read, update, soft delete, restore, permanent delete (typed confirm, backup under 24 h, `item_purged` event), search and filters (`API.md` 2.5), event timeline.
4. Photos: upload pipeline (`ARCHITECTURE.md` 6 Uploads), thumbnails, serving with immutable caching, per-item limit 12, set primary, hide.
5. Pages: Inventory (virtualised), Item, Item form sheet, Trash. Nav gains Inventory and Camera; `/` → `/inventory`.
6. Drafts and the Camera hub, **Add mode**: webcam capture, upload, drag and drop, paste, multi-file (up to 20), review queue, confirm screen without OCR (manual fields), commit with idempotency. Camera state handling per `PAGES.md` P-06; `LiveBadge` live only while a stream runs; stream stops on leaving or hiding the tab.
7. QR and labels: `qr.svg`, Labels page with the two layouts and the print-confirm banner, `label-printed`, **Scan mode** with the JavaScript decoder and the typed-ID field, `lookup`.
8. Fixture `items-1000` for the test stack.

## Rules worth repeating
- A draft is not an item and counts nowhere. Closing the browser loses nothing.
- Label is "printed" only when the owner confirms after printing.
- Quantity above 1 means identical units with one expiry date.
- HEIC and oversize files get a clear refusal; nothing half-written remains.
- No OCR, no Gemini, no lifecycle actions in this phase; the item page shows no controls for them.

## Gate
1. Add by webcam (fake device regression) and by upload, one and many; items and photos survive stop/start and a container rebuild.
2. Search and every filter return correct results on `items-1000`; first page within budget (`ARCHITECTURE.md` 11); scrolling stays smooth.
3. Soft delete, undo, Trash restore and permanent delete (with the backup rule) behave exactly as `PAGES.md` says; photo files stay on disk after "Delete photo".
4. Labels: sheet and single layouts render at the right physical sizes in the print preview; marking printed works; **a printed label scanned in Scan mode opens the right item**; typed `endr-7k2m9qxa` style input works; an unknown code is handled; the id survives editing the item.
5. Category and location rules: reassign on delete, cycle refused, duplicate names refused case-insensitively.
6. Upload failures: wrong type, oversize, truncated, concurrent double submit; nothing half-written.
7. Dead-control crawler and contrast test extended to all new routes; both themes.
8. Verification pass.

## Owner acceptance (5 minutes, real hardware)
With your real webcam add two items; print one label on paper; hold it to the webcam in Scan mode and see the item open; delete an item, find it in Trash, restore it; stop and start the app and confirm everything is still there.
