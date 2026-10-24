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
