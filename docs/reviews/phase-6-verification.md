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

## Results (per probe)
| # | Probe | Result | How |
|---|---|---|---|
| 1 | Re-run all suites | PASS | before fixes: lint clean; unit 218 + 87; integration 288; e2e 117 + 3 (17.0 min). After fixes: lint clean; unit 246 + 87; integration 320; probes 1 to 25 ALL PASSED; Phase 6, dashboard and my specs 25 passed; crawler (own mode, dashboard), contrast (both themes), shell reference 7 passed (`raw/phase-6v/`) |
| 2 | Scoring table by hand | PASS after fix | `test_phase6_verification_rules.py`: every signal's points, levels at 24/25, 44/45, 74/75, High needs a model match or size + overlap ≥ 80. **F1 (minor, fixed):** D-119 lifted a look-alike whose size differs (score −15, "Different size · Looks similar") to Possible; root cause confirmed: the lift tested "no positive text support" only |
| 3 | Normalisation | PASS after fix | 1 L = 1000 ml, 0.5 kg, 1.3 cm, 0.5 in, `1"`, `1,5 l`, sizes lists, mixed kinds say nothing, model case/space/dash/dot. **F2 (minor, fixed):** "10,000 mAh" was read as 10 mAh (−30 against "10000 mAh"); **F3 (minor, fixed):** "2 in 1 USB cable" was read as 2 inches and hid the owner's own cable. Root causes confirmed (`_SIZE` regex and `float(n.replace(",", "."))`) |
| 4 | Active only | PASS | used, expired, discarded found while active and gone after; Trash (builder test); a hidden photo's vector stops matching; draft photos embedded but never candidates |
| 5 | At most five | PASS | ten equal High matches → five, by item id |
| 6 | Never certain | PASS | reasons are a closed set; grep of shipped code finds only comments; probe 25 scans the page; e2e scans the body |
| 7 | A check writes nothing | PASS | every table's row count and the photo, thumb and upload-tmp files equal before and after 3 good and 5 refused checks (HEIC 415, empty 422, truncated 415, garbage 415, 12 MB+ 413) |
| 8 | Offline, no Gemini | PASS | probe 24 (`--network none`, key set, `auto`, sharing on: 0 requests during checks, 1 after Test connection as the control); builder's in-process network-off test |
| 9 | Input validation | PASS | JSON body and no parts 422; 200 characters accepted, 201 refused; one error shape, no traceback |
| 10 | Embeddings | PASS | new photo, backfill, hidden skipped, a broken file marked once (empty blob, current model) and not retried, a model-name change re-embeds every photo |
| 11 | Savings validation | PASS | "100", 10.5, 10.0, 0, −5, true, null, 10^12 + 1, 10^30 → 422; empty, blank, 121-character names 422; with an item the item's name wins; unknown id, item in Trash 404; a purged item keeps its saving by name |
| 12 | Totals | PASS | paging by 2 sums to `total_paise`; removed rows excluded; Kolkata month boundary (builder test) |
| 13 | Undo | PASS | twice within 60 s changes once; 61 s → 409 `undo_expired`; kinds `saving_added`, `saving_undone`, `saving_removed`. Doc mismatch fixed: DATA_MODEL 2.11 said `savings_added` |
| 14 | Idempotency-Key | PASS | same key → same id, one row; another key → a second row |
| 15 | Dashboard pill | PASS after fix | `pill_date` follows the latest live saving, moves back on remove, a future date is never today; pill and truck on today do not overlap each other or the title at 1024 and 1280. **F4 (minor, fixed):** the lifted pill's 46 px stem was drawn through the truck when the truck stood on today |
| 16 | UI flows | PASS after fix | paste and drop give the photo to check; keyboard only through own mode and Savings; Savings loading skeleton, error with Retry; D-118 (builder spec). **F5 (minor, fixed):** Escape on "I didn't buy it" left focus on the page body (PAGES 2: focus returns to the opener); root cause confirmed: `SavingSheet` unmounted its `<dialog>` instead of closing it |
| 17 | Look (D-097) | PASS (owner approval BLOCKED) | own results 1280 dark/light and 1024, price sheet, Savings 1280 both themes, pill 1280 both themes and 1024, pill and truck on today 1024 and 1280: tokens only, status only on dark chips, cream pill as in the reference. The nav over "Camera" in the dark full-page shot is the sticky nav in a full-page capture, not the layout |
| 18 | Migration 0004 | PASS | a v3 database used through the API (category, place, items in three states, photos, a draft, a chore, reminders, events): every old table's count equal, `savings` empty, integrity ok, version 4, verified pre-migration backup, the check finds the item after |
| 19 | Reality audit | PASS | no mock/fake/stub/TODO in Phase 6 code (one index named `photos_embedding_todo`); every ₹ on screen is a sum of `savings` rows (DATA_MODEL 2.13) or a row's price |

## Part 1, spec conformance
Build 1 migration 0004 MET; embeddings for every saved photo by a background job and backfill MET; model chosen by measurement **BLOCKED** (D-115 provisional DINOv2-small). Build 2 MET (image and/or text, OCR fields, cosine against active items). Build 3 MET after F1 to F3 (table, levels, image-only at most Possible, five, active only). Build 4 MET (P-13 incl. paste/drop, words, None of these, Add it per D-118, I didn't buy it with a required price; P-14; nav Savings; pill per D-116, F4 fixed). Build 5 MET (third mode pill). Gate 1 **BLOCKED** (owner's 20 photos). Gates 2, 3, 4, 5 MET. API 2.14 shapes and errors MET. No new dependency beyond the allow-list (`rapidfuzz`, `onnxruntime`, `numpy`); no scope creep. MISTAKES C (text and size lead, appearance only proposes; never a certainty) and H (savings only after confirmation) respected; DATA_SAFETY: the live stack was not touched.

## Part 2, does it work
On the test stack: the image rebuilt and started (`test.bat e2e`, probes 3, 4, 9), the main flows driven in Chromium (words check, photo check, paste, drop, price sheet, Undo, Savings, dashboard pill). `build.bat`/`run.bat` on the live stack are the owner's (BLOCKED).

## Notes (minor, logged; none blocking)
- N1. **DINOv2 at 0.80 barely separates pictures:** two different text labels score 0.970, two different shape scenes 0.946, two flat colours 0.887 (`raw/phase-6v/embedding-cosines.txt`); a check with an unrelated label photo brought 2 of 6 labelled items in as "Possible · Looks similar" (`look-alike-flood.txt`). The +15 can also lift a not-owned item with a fuzzy model match and the same name from Medium (65) to High (80): gate 1 must look for that false High. Provisional until gate 1 (D-115); tune the thresholds there.
- N2. With the spec's starting points, High through "size match and name overlap ≥ 80" is unreachable (30 + 20 + 5 + 15 = 70 < 75); only a model match reaches High. Tune at gate 1.
- N3. OCR look-alikes in model numbers (O/0, S/5) score 0: the fuzzy ratio ≥ 92 helps only models of 13 or more characters. Consider folding O→0 and I→1 on both sides at gate 1.
- N4. The embedding loop stops until restart if a tick raises something other than `OSError`, `ValueError` or `sqlite3.Error` (for example an ONNX Runtime error); hypothesis from reading `scheduler/embeddings.py`, not reproduced.
- N5. Removing the photo after a photo check keeps the results, and "Add it to my inventory" then opens the words form instead of a draft.
- N6. "This month" has no upper bound: a saving dated in a later month (test clock moved back) counts in this month; the list and the totals still agree.

## Verdict
**PASS WITH NOTES.** Five minor failures were found and fixed in this session test-first (F1 to F5, new failure kinds F-040 to F-042), plus one doc mismatch. Notes N1 to N6 are minor and logged; the owner's agreement is pending (D-091). BLOCKED on the owner: gate 1 (20 photos, `test.bat ownership`), the acceptance run, screenshot approval.
