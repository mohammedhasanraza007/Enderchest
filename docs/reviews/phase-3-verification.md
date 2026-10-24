# Phase 3 verification — Smart capture

Fresh session, 2026-10-24 (chain D-091). Builder and verifier are the same model (Opus 5.5), so this pass is deliberately sceptical: it re-reads the spec gate and the code, not the builder's summary.

## Probe list (written before running anything)
| # | Probe | Kind |
|---|---|---|
| P1 | Re-run lint, unit, integration, e2e (main + no-backups), probes 1 to 21 | all gates |
| P2 | Expiry parser: the 35 cases plus my own adversarial inputs (EXP vs MFD, BEST BEFORE n months, 2-digit years, 31/02, month names, no date) | gate 1 |
| P3 | D-100: a read value never overwrites a field the owner typed, cleared or removed, before or after a reload | gate 6 |
| P4 | An unconfirmed read expiry cannot be saved, by the UI or by the API | gate 6 |
| P5 | No test or test stack can call Google: `ENDERCHEST_GEMINI_URL` in every test service and in pytest's settings | gate 3, D-102 |
| P6 | The Gemini key never leaves its file: not in a response, a log line, the database or a backup | data safety |
| P7 | Network off and Gemini failing: clear message, no hang (probe 20); `/health` under OCR (probe 21) | gates 3, 5 |
| P8 | Bake-off harness refuses to run without the owner's photos and confirmed labels | gate 2 |
| P9 | Reality audit: fake markers, placeholders, empty states, dead controls, contrast | Part 3 |
| P10 | Screenshots at 1280 dark/light (1024 dense) against the reference | D-097 |

## Results
| # | Result | Evidence |
|---|---|---|
| P1 | PASS | On `84eaf22`: lint clean; unit 160 pytest + 65 vitest; integration 198; Playwright 82 + no-backups 3; probes 1 to 21 ALL PASSED. After the fix: unit 160 + 66, integration 199, Playwright 82 + 3, lint clean. `docs/logs/raw/phase-3v/` |
| P2 | PASS | The 35 cases are unit tests (green). 13 own inputs (`raw/phase-3v/parser_probe.py`): MFD only gives no expiry; 31/02 and 13/13 are `invalid`; "BEST BEFORE 12 MONTHS FROM MFD" is computed from the MFD; "1O/O3/2O27" is fixed and flagged `ocr_fix` plus `ambiguous`; 2099 is `far_future`; batch digits before EXP are ignored |
| P3 | **FAIL, fixed** (minor) | In the session the form never overwrote an owner's field (`owned` set, unit tests). After a reload it did: a field the owner cleared or a read attribute row they removed was stored as "" or missing, and `ownedFields` treats empty as untouched, so the reading refilled it. Root cause confirmed by a failing vitest. Fix `819b2f4`: the draft stores `owned` (validated list of the six proposal fields), the screen restores it, commit drops it; integration test checks it never reaches the item. F-032 |
| P4 | PASS | UI: Save disabled with "To save: Confirm the expiry date." (screenshots, e2e). API: commit refuses `expiry_unconfirmed` when `expiry_confirmed` is false (integration test). Readings never write `fields` (`services/reading.py`, `services/gemini.py`), so a read date reaches `fields` only through the confirm screen, which sends `expiry_confirmed: false` until tapped. Note N1: a raw API client that PATCHes a date without the flag can commit it; that is a typed date, not a read one, so it meets the rule |
| P5 | PASS | `compose.test.yaml` sets `ENDERCHEST_GEMINI_URL=http://127.0.0.1:9/v1beta` on all three app services; `tests/conftest.py` uses `CLOSED_GEMINI_URL`; Gemini client tests use `httpx.MockTransport`. Probe 20 runs with `--network none` |
| P6 | PASS | Key in `/data/secrets/gemini.key` (0600, atomic write); `GET /gemini` returns only `key_set`; sent only in the `x-goog-api-key` header; logs carry field names and timings, not values; backups copy the database and `photos/` only (`backup/engine.py`); the database has no key column |
| P7 | PASS | Probe 20: Google unreachable, local reading done, Gemini "could not be reached". Probe 21: three readings at once (1.5, 0.5, 0.5 s), 33 `/health` samples all far under 200 ms |
| P8 | PASS (tooling) / gate 2 BLOCKED | `test.bat bakeoff` exits 2 with a plain message before building when `labels.csv` is missing; the container runs `--network none` with the photos read-only. The measurement needs the owner's 20 photos |
| P9 | PASS | No `mock`, `fake`, `dummy`, `lorem`, `stub`, `TODO`, `FIXME` in `backend/app` or `frontend/src` outside tests. Placeholders are input hints from earlier phases (`1240`, `ENDR-7K2M9QXA`, search hint), note N2. Crawler 0 dead controls, contrast 0 failures (both inside the green e2e run) |
| P10 | PASS (Claude's look; owner approval pending) | Looked at confirm-read dark 1280, confirm-ambiguous light 1280, settings-gemini dark 1280, read-drawer light 1280: tokens and pills match the reference, text on opaque surfaces, the "Not confirmed" chip is a dark status chip, the drawer is opaque. Note N3: the native date input shows the browser's locale order (03/14/2027 in the en-US test browser); the confirm button and pills show "14 Mar 2027", so the date is never ambiguous |

## Spec gate
1 PASS (35/35). 2 **BLOCKED: needs the owner's 20 photos and confirmed labels.csv**. 3 PASS. 4 **BLOCKED: needs the owner's Gemini key, or a written waiver**. 5 PASS. 6 PASS after the fix. 7 this pass.

## Notes (minor, for the owner)
- N1: the API trusts the client's `expiry_confirmed`; only the confirm screen proposes dates. Acceptable for a single-user laptop app.
- N2: input placeholder hints (`1240`, a sample public ID) are format hints, not data; they predate Phase 3.
- N3: the date field's digit order follows the browser locale; on an en-IN browser it is day first.

## Verdict
**PASS for Claude's part** (one minor defect found and fixed test-first; no blocker or major). PASS WITH NOTES needs the owner: gates 2 and 4, the acceptance run, screenshot approval, live `build.bat`/`run.bat`, and agreement to N1 to N3.
