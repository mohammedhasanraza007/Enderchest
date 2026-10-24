# Phase 6 brief — "Do I own this?" and savings

Written 2026-10-25 by the Phase 6 build session (chain, D-091: no "go" awaited).

## What I will build
1. **Migration 0004** (`savings` table per DATA_MODEL 2.13, index on `photos` embeddings; `photos.embedding` and `embedding_model` already exist from 0002), after the boot's verified pre-migration backup, with a migration test from a realistic v3 database.
2. **Embedding pipeline** (`integrations/embedding/`): one ONNX image model on ONNX Runtime CPU, loaded lazily in the shared size-1 heavy executor; an embedding is computed in the background for every new item photo and draft photo, and a backfill job at start-up fills photos that have none (or an older `embedding_model`). Vectors are L2-normalised float32 blobs.
3. **`POST /api/v1/ownership/check`** (API 2.14): image and/or text. Image: the Phase 3 OCR pipeline → fields (`extraction.propose`), and the embedding → cosine similarity against active items' live photos. Text: fields from the typed words. **Scoring** exactly as the spec's table (`rapidfuzz`, on the allow-list), levels High / Medium / Possible, image-only at most Possible, at most 5, active items only, a one-line reason per candidate. Nothing is written; the query photo is not kept. Gemini is not called (D-117).
4. **Savings**: `POST /savings`, `GET /savings?period=`, `DELETE /savings/{id}` with events `saving_added` / `saving_removed` and Undo through `services.undo` (60 s). Totals in integer paise; "this month" by the profile time zone. The dashboard's `savings` becomes `{month_paise, pill_date}` from real rows; the road draws the pill only when `pill_date` is today (DESIGN 6.11: never on a future date).
5. **Screens**: P-13 as the camera hub's third mode pill (`/camera?mode=own`: shutter, upload, paste and drop, text box, Check, candidate rows with confidence pill and why line, Open item, Not the same, None of these → Add it to my inventory / I'll buy it, I didn't buy it → price sheet → toast with Undo); P-14 Savings at `/savings` (serif ₹ total, This month / All time, list with Remove + confirm + Undo, empty state); nav gains Savings. Page copy says "Check before you order" (desk-side).
6. **Tests and probes**: unit (scoring, size normalisation, levels, never "certain"), integration (check by text and image, active only, image-only cap, nothing saved, savings totals and time zone, undo), e2e (own mode, savings, crawler and contrast on `/savings` and own mode), and new probes: no inventory data in any outgoing request; the words "certain" / "you own this" / "100%" never in a response or the page; savings only after a confirmed price.
7. **Measurement harness** `test.bat ownership` for gate 1: runs the real check on `tests/fixtures/private/phase6/` and writes the results table. **BLOCKED** until the owner supplies the 20 photos.

## Conflicts and gaps (settled in DECISIONS.md)
1. **D-114** API 2.14 names the lowest level `low`, the spec and P-13 say "Possible". The API keeps `low`; the UI shows it as "Possible".
2. **D-115** The model is to be chosen by measurement on the owner's 20 photos, which do not exist yet, and MobileNetV3-small has no published ONNX export (it needs a PyTorch export). Provisional: **DINOv2-small** (onnx-community export, fp32, 88 MB, pinned by sha256, baked into the image), like the OCR engine in D-099. The harness can run any ONNX image model file, so the comparison runs when the photos arrive.
3. **D-116** Spec Build 4 says the pill appears "only on the date the latest confirmed saving was made", DESIGN 6.11 says it shows the month total anchored to today and never a future date. Both hold: `pill_date` = the latest active saving's local date; the road shows the pill (with the month total) only when that date is today, the road's first day.
4. **D-117** Gemini in the check: allowed only to read the query photo, never the inventory. Phase 6 does not call it (the check must answer in seconds offline, and local OCR already gives fields); `engine.gemini_used` is always `false`. No Gemini control appears on the page.
5. **D-118** "Add it to my inventory" with a text-only query has no photo to make a draft from: it opens the new-item form with the typed text as the name (still saved only on the owner's tap).

## Owner inputs
- **10 owned + 10 not-owned photos** in `tests/fixtures/private/phase6/` with `labels.csv` (`tests/fixtures/README.md`); until then gate 1 and the model measurement are **BLOCKED**.
- Owner acceptance (5 minutes, spec) and screenshot approval: owner runs after `build.bat`.
