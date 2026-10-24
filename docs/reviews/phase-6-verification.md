# Phase 6 verification — "Do I own this?" and savings

Fresh session, 2026-10-25, chain step (D-091). Builder and verifier are the same model family (Opus 5.5): read sceptically. Spec re-read: `docs/specs/phase-6-ownership.md`; decisions D-114 to D-119; API 2.14, PAGES P-06/P-13/P-14, DATA_MODEL 2.7, 2.11, 2.13.

## Probe list (written before running anything)
1. **Re-run every suite** on the zip's code: `test.bat lint`, `unit`, `integration`, `e2e`, `probes` (1 to 25 stay green, one number per `-Only`).
2. **Scoring table by hand** against `services/ownership_rules.py`: +60 model equal, +35 fuzzy ≥ 92 (and not both), +20 size equal, −30 size different, 0 to +30 name/brand overlap, +5 category, +15 / +8 image ≥ 0.80 / ≥ 0.70. Levels at the exact boundaries 24/25, 44/45, 74/75; High needs (model match or size match) **and** name overlap ≥ 80, so 75+ without that is Medium; image-only capped at Possible; D-119 strong look-alike Possible, weaker hidden. Score with only negative signals never shows.
3. **Normalisation:** 1 L = 1000 ml, 0.5 kg = 500 g, 13 mm vs 1.3 cm, inches (`"`, `in`, `inch`), mixed kinds (13 mm vs 13 g must not match or penalise as "different size"?), a `sizes` list on the item, decimals with commas; model numbers with spaces, dashes, case, O/0 and I/1 look-alikes.
4. **Active only:** used, expired, discarded, in Trash (soft-deleted) and purged items never appear, even with an exact model number; a hidden photo's embedding never matches.
5. **At most five** candidates with ten equal matches; ordering stable (score, then something deterministic).
6. **Never certain:** the words "certain", "you own this", "100%" nowhere in API answers (reasons), frontend source or the rendered page.
7. **A check writes nothing:** row counts of every table, `events`, files in photos/thumbs/upload-tmp before and after text and photo checks (including a failing one: bad type, too big, empty); the query photo is not kept.
8. **Offline and no Gemini (D-117):** with a key stored, mode `auto` and photo sharing on, a check makes no outgoing request; text-only check works with the network off.
9. **Input validation:** text > 200 chars, empty text and no image, whitespace-only text, HEIC, a PNG renamed .jpg, zero-byte file, 13 MB file, JSON body instead of multipart → the one error shape, no stack trace.
10. **Embeddings:** new item photo and draft photo get a vector; backfill fills old photos; hidden photo not used; an unreadable file gets a marker and does not loop; a model-name change re-embeds.
11. **Savings validation:** price as string "100", float 10.5, 0, −5, huge (> 2^63), bool `true`; missing name and no item; item in Trash or purged; unknown public id; `item_name` empty/whitespace/over 120; with an item the stored name is the item's even if a different `item_name` is sent.
12. **Savings totals:** `total_paise` and `month_paise` equal the sum of the listed rows (all pages); removed rows excluded; this month in Asia/Kolkata across a month boundary (a saving at 20:00 UTC on the last day of the month is next month's in Kolkata).
13. **Undo:** saving_added and saving_removed undo once within 60 s; second undo refused; after 60 s refused; undoing a removed saving restores it; event kinds match DATA_MODEL 2.11.
14. **Idempotency-Key** on `POST /savings`: same key twice → one row, same id; different key → two rows.
15. **Dashboard pill (D-116):** `savings` null with no saving; pill only when the latest active saving's local date is today; a removed latest saving moves `pill_date` back; a future-dated row (clock moved back) never shows a pill; position beside the truck at the start of the road.
16. **UI flows:** own mode by words "Add it" opens the new-item form with the text as name (D-118); with a photo it makes a draft; "Not the same" hides a row; "None of these" always present; "I didn't buy it" sheet requires a price; paste and drop; keyboard only; reduced motion; Savings empty, loading and error states; Remove with confirm and Undo.
17. **Look (D-097):** own mode, Savings and the dashboard pill at 1280 px dark and light and 1024 px against the reference; contrast and crawler green.
18. **Migration 0004** from a realistic v3 database (items, photos, tasks, notifications): counts preserved, `savings` table and index exist, pre-migration backup verified.
19. **Reality audit:** grep shipped code for mock/fake/dummy/lorem/stub/TODO/FIXME and fixed numbers; no ₹ shown that is not from a row.
