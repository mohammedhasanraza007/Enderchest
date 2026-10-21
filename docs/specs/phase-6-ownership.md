# Phase 6 — "Do I own this?" and savings

**Read list:** `CLAUDE.md` sections 0, 5, 8 · this file · `DATA_MODEL.md` 2.7, 2.13, 3.8 (only for events) · `API.md` 2.14 · `PAGES.md` P-13, P-14 · `ARCHITECTURE.md` 6, 8 · `tests/fixtures/README.md`.
**Do not read:** `DESIGN.md` except 6.12 for list rows.
**Owner supplies:** **10 owned and 10 not-owned photos (`tests/fixtures/README.md`)**; without them the measurement gate is **BLOCKED**. **Milestone:** D.

## Honest scope
This is a **desk-side** check: before ordering online, while tidying, or holding a product to the laptop webcam. It cannot run in a shop; that arrives with the locked phone phase. State this in the page copy ("Check before you order").

## Build
1. Migration 0004. Embedding pipeline: compute an image embedding for each saved photo in the background (and a backfill job); store in `photos.embedding` with `embedding_model`. Choose the model by measurement on the 20-photo set from candidates MobileNetV3-small, DINOv2-small, CLIP ViT-B/32 (all via ONNX Runtime CPU); record in `docs/DECISIONS.md`.
2. `POST /api/v1/ownership/check`: image and/or text. Image path: OCR (Phase 3 engine) → fields; embedding → cosine similarity against active items' embeddings. Text-only path: fields from the text.
3. **Scoring** (starting values; tune on the 20 photos, record the final values):
| Signal | Points |
|---|---|
| Normalised model or part number equal | +60 |
| Same, fuzzy ratio ≥ 92 (`rapidfuzz`) | +35 |
| Size equal after unit normalisation (value in the item's `size`/`sizes` attribute) | +20 |
| Size present on both but different | −30 |
| Name and brand token overlap (`token_set_ratio`) | 0 to +30 |
| Same category | +5 |
| Image similarity ≥ 0.80 / ≥ 0.70 | +15 / +8 |
Levels: **High** ≥ 75 and (a model match or size match with name overlap ≥ 80); **Medium** 45 to 74; **Possible** 25 to 44; below 25 hidden. A candidate supported only by image similarity is at most Possible. Show at most 5. Only `state='active'` items qualify. The UI never says "certain" or "you own this".
4. Page P-13 including paste and drop, text query, "None of these", "Add it to my inventory" (draft from the image), "I didn't buy it" with the required confirmed price; page P-14; nav gains Savings; dashboard savings pill appears only on the date the latest confirmed saving was made (`pill_date`) per `DESIGN.md` 6.11.
5. Camera hub gains the third mode pill.

## Gate
1. Results table for the 10 owned and 10 not-owned photos recorded: for each, top candidate, level, correct or not; false "High" on a not-owned item is a **major** defect.
2. Text-only query works with the network off.
3. ₹ is added only after the owner confirms a price; Undo and Remove work; totals equal the list; this-month total uses the profile time zone.
4. Nothing is saved to inventory or savings without a tap.
5. Dead-control crawler and contrast test extended; verification pass.

## Owner acceptance (5 minutes)
Paste a product photo from a browser tab for something you own and something you do not; check both results; record one saving and remove it.
