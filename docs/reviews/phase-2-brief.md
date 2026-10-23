# Phase 2 brief — Inventory core

Written 2026-10-23 by the Phase 2 build session (chain of sessions, D-091: no "go" is awaited).

## What this session builds (spec build order)
1. Migration `0002_inventory.sql`: `categories`, `locations`, `items`, `photos`, `drafts`, `events` (DATA_MODEL 2.4 to 2.8, 2.11) with a v1 → v2 migration test. Public id generator (Crockford alphabet, `secrets`, collision retry, never reuses a purged id) and typed-input normalisation.
2. Categories and locations: endpoints (API 2.4), tree rules (depth 5, `cycle`, duplicate names refused case-insensitively, reassign on delete), Settings sections Categories, Locations and Data. First-run step 2 (starter categories) with a stored step marker (D-084, D-093).
3. Items: create, read, update, soft delete, restore, permanent delete (typed `DELETE`, good backup under 24 h, `item_purged` event), search and filters (API 2.5), event timeline, Idempotency-Key on create.
4. Photos: upload pipeline (12 MB, JPEG/PNG/WebP, HEIC refused by name, EXIF orientation then metadata dropped, re-encode, 320 px thumb, UUID names, size-1 executor), immutable caching, 12 per item, primary, hide.
5. Pages: Inventory (virtualised grid, filters in the URL), Item, Item form sheet, Trash. Nav gains Inventory and Camera; `/` goes to `/inventory`; the name menu gains Trash.
6. Drafts and the Camera hub in Add mode: webcam, upload, drag and drop, paste, up to 20 files, review queue, confirm screen with manual fields, commit with idempotency; camera states; `LiveBadge` only while a stream runs.
7. QR and labels: `qr.svg` (segno), Labels page with both layouts and the print-confirm banner, `label-printed`, Scan mode (jsqr) and the typed-ID field, `lookup`.
8. Fixture `items-1000` for the test stack.
New dependencies, all on the allow-list: `python-multipart`, `pillow`, `segno`; `@tanstack/react-virtual`, `jsqr`.

## Conflicts and gaps (decided by the authority order, CLAUDE.md 2)
1. **Undo and the fixture endpoint are listed for later phases** (`POST /events/{id}/undo` is Phase 4 in API 2.10; `POST /test/fixtures/{name}` is Phase 5 in 2.17), but Phase 2 needs both: `DELETE /items` returns an `event_id` "undoable", PAGES 2 shows a 10 s Undo toast for delete and "Photo hidden" for a photo, and the gate needs `items-1000`. Decision **D-092**: both are built now, limited to what exists (undo for `item_deleted`; fixture `items-1000` only). Later phases extend them.
2. **First-run step marker (D-084).** Decision **D-093**: settings key `first_run_step` (`categories` or `done`). The first `PUT /profile` that saves a name also stores `categories`; `first_run_complete` is "name saved and the marker is not `categories`", so an owner who finished first run in Phase 1 (no marker) is never sent back. `GET /profile` gains `first_run_step` (`name`, `categories`, `done`); `PATCH /settings` accepts `first_run_step: "done"` (Continue or Skip on step 2). DATA_MODEL 2.3 and API 2.2 amended.
3. **Deleting a location that has child locations, and "no category".** Not specified. Decision **D-094**: a location with live children cannot be deleted (`in_use`, `details.reason = "has_children"`, message says to move or delete the places inside first); `reassign_to=none` moves the items to "no category" or "no location". Items in Trash are reassigned too, so a restore never points at a deleted row.
4. **Multipart paths are templated** (`/items/{id}/photos`, `/drafts`, `/drafts/{id}/photos`), but `security.MULTIPART_PATHS` is a set of exact paths. Decision **D-095**: it becomes a tuple of anchored regular expressions; the middleware also caps request bodies (JSON 1 MB; multipart 12 MB per image route, 20 × 12 MB for `POST /drafts`), counted while streaming, answered `payload_too_large`.
5. **Gate evidence that needs hardware.** Gate 1 (real webcam), gate 4's printed label held to a webcam, and the owner acceptance run need the owner's webcam, printer and real items: **BLOCKED** and listed under "Owner runs next". The fake-camera feed (Chromium flags with a generated QR video) runs as regression only (D-056).

## Owner inputs
- None needed to build. After the build: the 5-minute acceptance run (webcam, printer, real items), screenshot approval for the new pages, `build.bat` then `run.bat` (migration 0002 runs on live after a verified pre-migration backup).
