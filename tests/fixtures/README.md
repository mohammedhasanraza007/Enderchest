# Test fixtures

## Supplied now
- `expiry_cases.csv`: 35 text-only expiry-date cases (raw text, expected ISO date, flags). Used by the Phase 3 parser tests. No photos needed. The test clock date for `far_past` and `far_future` is 2026-10-17.

## Supplied by the owner (real photos; Claude cannot make these)
Photos stay in `tests/fixtures/private/` (git-ignored: they are your belongings and may carry location data). Never copy them anywhere else.

### Phase 3 set: 20 items (`private/phase3/`)
Take one or two photos of each with the laptop webcam (the real capture path); phone photos may be added as extras. Mix: 6 packaged food or drink with a printed date, 4 cosmetics or medicine strips with a date, 4 electronics or modules with a model label, 3 tools with stamped sizes, 3 awkward ones (curved, glossy, tiny text).
Name files `NN-short-name.jpg` (for example `07-oat-milk.jpg`). Fill `private/phase3/labels.csv` with columns `file,name,model,size,expiry_date,notes` (`expiry_date` as `YYYY-MM-DD`, blank if none). Claude may draft this file from the photos; **you correct every row** and then tell Claude "labels confirmed". Until then the Phase 3 gate is BLOCKED.

### Phase 6 set: 10 owned + 10 not owned (`private/phase6/`)
Ten items that are in your inventory, photographed again from another angle or in other light (`owned-NN-name.jpg`, with `owned-NN` matching the item's `public_id` in `labels.csv`), and ten similar-looking products you do **not** own (`not-owned-NN-name.jpg`).
