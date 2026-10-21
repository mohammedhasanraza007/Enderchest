# Phase 3 — Smart capture (OCR, expiry parsing, Gemini)

**Read list:** `CLAUDE.md` sections 0, 5, 8 · this file · `DATA_MODEL.md` 2.8 · `API.md` 2.8 (extract), 2.9 · `PAGES.md` P-02 (Gemini), P-07 · `ARCHITECTURE.md` 6, 8, 10 · `tests/fixtures/README.md` · `PROJECT_PLAN.md` sections 8 and 9 (extraction pipeline) only if a question remains.
**Do not read:** `DESIGN.md`, dashboard material.
**Owner supplies:** **20 real photos and `labels.csv` (see `tests/fixtures/README.md`)**; a Gemini key (optional). Without the photos the real-photo gate is **BLOCKED**. **Milestone:** B.

## Goal
Point the camera at a product and get a correct, editable draft: name, model, size, expiry date. Nothing is trusted until the owner confirms it.

## Build
1. **Engine bake-off.** Candidates: RapidOCR (ONNX Runtime), EasyOCR, docTR, Tesseract (as a baseline). English only, CPU only, no GPU support (D-063). Run each on the 20 photos at long edges 1024 and 1600. Record per field (name tokens, model, size, expiry date) correct / partial / wrong, median and p95 latency, memory, image-size cost. Choose by weighted accuracy (expiry ×3, model ×2, name ×1, size ×1) subject to median latency ≤ 4 s; record the table and the choice in `docs/DECISIONS.md`. Models are baked into the image at build time.
2. **Pipeline** (`integrations/ocr/`): resize → OCR lines with boxes and confidences → field extraction → proposals with `source`, `confidence`, `flags`. Runs in the size-1 executor, never on the request thread; `POST /api/v1/drafts/{id}/extract` returns 202 and the client polls the draft.
3. **Expiry parser** (`services/expiry_parser`): implements the rules below; **all 35 cases of `tests/fixtures/expiry_cases.csv` must pass** (test clock date 2026-10-17).
4. **Other fields:** model or part number = tokens of 4+ characters containing a digit and at least one letter or dash; size = number plus unit (mm, cm, m, in, ", ml, l, g, kg, v, a, w, mah, gb, tb, pcs); name = the strongest line (text height × confidence) that is not a date, model, size or boilerplate line.
5. **Gemini** (`integrations/gemini/`): REST via `httpx`; Settings page per `PAGES.md` P-02; the key stored per `DATA_SAFETY.md` 2; timeout 20 s; prompt requests strict JSON with name, brand, model, size, category guess, expiry text and a suggested inspection interval; the response is validated and every value labelled "Gemini, unverified". Images are sent only when `share_images_with_gemini` is on. Mode `ask` shows a button; `auto` runs only when local OCR found neither a name nor a model; `off` never calls. Offline or error: clear message, local result unaffected.
6. **Confirm screen** additions of `PAGES.md` P-07 (source chips, confidence dots, Re-read, Improve with Gemini, raw-text drawer, expiry confirmation, ambiguous-date pills).
7. Suggested inspection interval from Gemini pre-fills the maintenance toggle's *suggestion* only; the toggle itself is Phase 4.

## Expiry rules (summary; the CSV is the exact test)
Label words: EXP, Expiry, Exp. Date, Use by, Use before, Best before, BB, B.B., Consume before. A date after an EXP-type label is the expiry; a date after MFD/MFG/PKD/Packed on is **never** the expiry. Day-first for numeric dates (India); if both readings are valid and different, flag `ambiguous` and offer both. Month and year only → last day of the month, flag `month_only`. Two-digit years mean 2000+yy. "N months from manufacture" computes from the manufacture date (month-only → end of that month plus N), flag `computed`. In digit positions read O as 0, I and l as 1. Impossible dates are `invalid`. More than 10 years past or 15 years future of today: flag. Nothing is ever saved as an expiry without the owner's confirmation tap.

## Gate
1. 35 of 35 expiry cases pass.
2. Real-photo measurement table (20 photos) recorded with the engine choice; labels confirmed by the owner. **BLOCKED until then.**
3. Works with the network disabled; Gemini failures and absence are handled with clear messages.
4. Gemini real round trip verified with the owner's key, or recorded as BLOCKED and waived by the owner in writing.
5. API `/health` stays under 200 ms while OCR runs; two OCR requests at once queue, none crash.
6. Every extracted value is editable; unconfirmed expiry blocks Save with the stated reason.
7. Verification pass.

## Owner acceptance (5 minutes)
Add three real items with the webcam; read the raw-text drawer; correct a wrong field; confirm a date; check the saved item.
