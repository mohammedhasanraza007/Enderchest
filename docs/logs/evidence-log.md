# Evidence Log

Real results only: command output, read-backs, test results, measurements. One section per phase. Also the place for "TODO" items and worthwhile extra ideas (owner decides). Decisions go in `../DECISIONS.md`.

## Format
`YYYY-MM-DD — Phase N — what was run — result (paste or path to output) — PASS / FAIL / NOT VERIFIED`

## Entries

- 2026-10-16 — Pre-phase — Documentation pack audited and rebuilt (`../history/AUDIT_REPORT_v3.md`). No code exists yet. — n/a
- 2026-10-17 — Pre-phase — v3 pack reviewed and rebuilt as v4 (`../PLAN_REVIEW.md`): page specs, data model, API contract, architecture, phase specs added; verified defects fixed. No code exists yet. — n/a
- 2026-10-21 — Pre-phase — Pack v4 upload read in full (67 zip entries, 52 files), three visuals opened, baseline commit `2abbefc` made in the worktree. Zip-in, zip-out workflow set up in pack v5 (D-067 to D-069, O-010, O-011); handoff and sessions log written. No code exists yet. — `scripts/check_docs.py`: 31 md files, 80 endpoints, 80 referenced, 0 errors, 0 warnings — PASS (docs check only)
- 2026-10-21 — Pre-phase — Zip exclusion rule tested on a dirty copy: a dummy private photo, a dummy `.env`, a dummy Gemini key, a dummy database and a dummy backup were added to the worktree; the zip command of `docs/PROCESS.md` 7 was run and the listing checked. The dummies were then deleted. — result: 140 zip entries; `.git/`, `CLAUDE.md`, `handoff.md` present; dummy private photo, `.env`, `secrets/gemini.key`, `data/*.sqlite3`, `backups/*.sqlite3` all absent; `.env.example` present — PASS
- 2026-10-21 — Pre-phase — TODO (Phase 3): `tests/fixtures/expiry_cases.csv` has CRLF line endings while `.gitattributes` says LF (git warns). Harmless to the CSV reader; normalise when the Phase 3 parser tests are written. — n/a
- 2026-10-21 — Pre-phase — TODO (first laptop chat): prove the Windows zip route (`tar -a -c -f <zip> -T zip-list.txt`, then `tar -tf`) on the owner's laptop. Only the Linux route is proven. — n/a
- 2026-10-21 — Pack v5.1 — phase-0 spec: "do not read ... the images" removed and amended in place (D-070; O-011 answered). Check: `grep -rniE 'do not read[^.]*image' docs/` returns only the O-011 and D-070 rows, which describe the decision; no spec excludes the visuals now. — PASS
- 2026-10-21 — Pack v5.1 — "wait for go" wording removed from CLAUDE.md 0, PROCESS.md 3, README.md and OWNER_TASKS.md; a chat starts on paste (D-071). Check: `grep -rnwE 'go' --include='*.md' . | grep -v history/` leaves only the ledger rows D-058 and D-067, the v4 review row 17 in PLAN_REVIEW.md, the two entries that describe the removal, and ordinary English. — PASS
- 2026-10-21 — Pack v5.1 — `scripts/check_docs.py`: 31 md files, 80 endpoints, 80 referenced, 0 errors, 0 warnings — PASS (docs check only)
- 2026-10-21 — Phase 0 task 1 — Deny-rule proof. All 8 commands of `docs/specs/phase-0-foundation.md` task 1 were run through Claude Code's Bash tool and again through its PowerShell tool, one call each, in a session started in the main checkout (`.claude/settings.json` identical to the phase-0 worktree). — result: 16 of 16 refused with "Permission to use <tool> with command ... has been denied" and none ran; no fix to `.claude/settings.json` needed — PASS (the refusal text does not say deny rule or prompt; the owner did not decline any of them)

## Idea list (not in scope; the owner decides)
- Host-side Windows toast helper so reminders show with the browser closed (O-007).
- CSV export of the inventory (O-008).
- Devanagari OCR (O-009).
- Parent/child sets (D-041).
