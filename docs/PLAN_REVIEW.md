# PLAN_REVIEW.md — Is the v3 plan sound enough to hand to Claude Code?

Review date 2026-10-17. Scope: plan quality only; no application was built. Method: read every file and both images; recomputed the design numbers; checked doc cross-references by script; checked outside facts by search. This file is for the owner. A build session never needs to read it.

## 1. Verdict

**v3 was a strong rulebook with a thin spec.** The data-safety thinking, process discipline and design lock were sound. But it was **not** ready to hand over: only the dashboard was specified. Every other screen was a one-line table row, and there was no data model, no API contract, no statement of where tests run, and a few verified defects. Claude Code would have spent its time inventing the missing 80%, which is what you asked to avoid. **v4 fixes that.** It is now a plan Claude Code can execute with very little deliberation, provided you supply the few real-world inputs in `OWNER_TASKS.md`.

## 2. Does the product matter?

Honest answer, in two parts.
- **As a product for other people: modestly.** Free self-hosted tools already do plain inventory well: HomeBox has photos, locations, custom fields, printable QR labels and maintenance logs; Grocy covers groceries, expiry and chores. Enderchest does not beat them on basics. What is genuinely different: camera-first OCR capture, an image-plus-text "do I own this?" check, a QM-style inspection loop, a designed experience, and local-first privacy.
- **As your portfolio and learning project: yes, if it is finished and honest.** It joins mechanical engineering and SAP PM/QM thinking to real engineering (Docker, SQLite safety, OCR, a scheduler, tests, measured accuracy). The strongest interview story is the *process design* and an accurate SAP mapping ("inspired by PM and QM; here is what is and is not like SAP"), not "an inventory app". v4 makes that mapping accurate (no "predictive maintenance", no low-stock claim, a real Inspection table).
- **Two limits the laptop-only scope creates** (now stated plainly in `PROJECT_PLAN.md` 0): the "in the shop" check and phone-style label scanning need the locked phone phase, and browser reminders need an open tab. Without these stated, the app would have overpromised.
- **Biggest risk is scope, not value.** Ten phases is a lot on a Claude Pro plan. v4 adds milestones A to E so you can stop at a coherent product: **A + C (Phases 0 to 2, 4, 5) is already a useful daily app.** Phases 7 to 9 are optional delight.

## 3. Can Claude Code actually do it? (the "is it possible by you" question)

| Kind of work | Verdict |
|---|---|
| Backend, database, migrations, backups, restore, Docker, scripts, API, tests, dashboard numbers, scheduler, matching logic | Yes, reliably, and it can verify itself |
| Matching the glass look to the reference | Yes with a screenshot loop; slower and token-heavy; v4 limits visual review to what matters |
| OCR accuracy, coach thresholds, ownership scoring | Yes to build and measure, **but only with your real photos**; starting values are supplied |
| Real webcam, real printed label, real Gemini key, judging how it looks to you, Docker Desktop health | **No: only you.** v4 makes these explicit acceptance steps and makes the gate BLOCKED rather than faking it |
| Finishing in one session | No. Expect many sessions; `handoff.md` and one-file-at-a-time reading exist for this |

## 4. What was wrong, and what v4 did

Severity: **B** blocker, **M** major, **m** minor. "Verified" means I recomputed or checked it, not just judged it.

| # | Sev | Finding | Fix in v4 |
|---|---|---|---|
| 1 | B | Only the dashboard was specified; ~14 other screens were one table row each; no data model, API or per-phase specs | `PAGES.md`, `DATA_MODEL.md`, `API.md`, `ARCHITECTURE.md`, ten phase specs |
| 2 | B | **Verified:** glass colours failed contrast if built as written. The alpha recipe does not produce the hex table (29% taupe over base is `#4A413A`, not `#52473F`); over the corner glow the inner panel text is 4.23:1 and the Snooze pill 3.74:1 | Opaque surface tokens (`DESIGN.md` 4.3) |
| 3 | B | **Verified:** dark status colours are 2.3 to 3.2:1 on glass (danger 2.30:1); light success and warning text are 4.05 and 3.30:1 | Dark StatusChip, darker light text variants (4.5) |
| 4 | B | **Verified:** deny rules `docker compose down:*` are prefix matches that miss `docker compose -f x.yml down -v`; they ignore the PowerShell tool, which Claude can fall back to | Glob and substring rules in Bash and PowerShell form, proof step first in Phase 0 |
| 5 | B | Tests and tooling had no home: host Python and Node unspecified, no test or dev script, and the deny rule blocked resetting the test volume | Tools in containers, `test.bat`, `dev.bat`, test reset endpoint, environment marker |
| 6 | B | Restore could corrupt: replacing the DB while a stale `-wal` remained; `restore.bat` could not restore into a running app; SQLite backups were written onto a Windows bind mount that the plan itself calls unreliable | Staging flow, WAL move-aside, one-off restore container (`DATA_SAFETY.md` 7, 12) |
| 7 | B | Refuse-to-start plus `restart: unless-stopped` is a silent crash loop | Boot state machine; the app serves a boot page, never exits (11) |
| 8 | B | The local API was open to any web page the owner visits (CSRF, DNS rebinding) | Host, header and Origin hardening, probe 12 |
| 9 | B | No QR decoder: **verified** Chrome's `BarcodeDetector` is not available on Windows | `jsqr` plus typed-ID fallback |
| 10 | M | Phase 0 held data safety, scripts, design tokens, primitives and nav in one gate; the coach (a delight feature) sat before the daily-value loop; no valid home page before the dashboard existed | New phase order, nav-by-phase table, milestones |
| 11 | M | Scheduler and actions undefined: fire-events vs reconcile; Snooze meaning; "Use it" with quantity above 1; "Inspect now" had no record | Idempotent reconcile, snooze options, use rule, `inspections` table |
| 12 | M | Health score: no tasks capped the score at 80; unknown expiry on tools dragged Fresh down; labelling milk was demanded | Exclusion rule, category defaults, `no_label_needed` (`DATA_MODEL.md` 3.4) |
| 13 | M | Cold start: one-item-at-a-time webcam entry for 100+ items | Server-side drafts, up to 20 photos at once, review queue |
| 14 | M | Pages missing from the plan: Locations and Categories management, Trash (soft-delete had no UI), Labels print, Scan, Review queue, recovery pages, notifications, assistant | All in `PAGES.md` |
| 15 | M | Claims the product could not support: reminders "arrive" while closed; "predictive maintenance"; "sets and kits"; low-stock in the SAP mapping | Honest wording, scope trimmed, mapping corrected |
| 16 | M | OCR and matching gates need photos only you can supply; risk Claude fakes images and writes PASS | BLOCKED rule (D-056), fixture protocol, 35 supplied expiry cases |
| 17 | M | Process cost on Claude Pro: spec writing, approval, fresh verification, Opus escalations, dozens of screenshots per screen | Pre-written specs, "brief and go", proportionate review, Opus only when stuck |
| 18 | M | Probes not runnable as written (renaming the working folder kills Claude's session; "older build"; kill during write) | Copy-folder probe, version-bump probe, test write loop; 14 probes |
| 19 | m | Backup default under `Documents` (OneDrive redirection); up to 24 h of lost entries; `synchronous` left undecided | `%USERPROFILE%\Enderchest-Backups`, change-triggered backups, `FULL` |
| 20 | m | Stale references the v3 audit said were fixed ("Architect", "(9.3)", "laptop and PC", gate pointer) | Fixed; checker script ships (`scripts/check_docs.py`) |
| 21 | m | `.gitignore` would publish your private photos; `.env.*` hid `.env.example`; missing binary types | Fixed |
| 22 | m | No reading discipline: a fresh session would load the whole pack | Router in `CLAUDE.md`, `docs/INDEX.md`, Read list per spec, `handoff.md` |

## 5. What I could not verify (please keep in mind)
- I could not run Docker, Claude Code or a browser here. Everything about Windows, Docker Desktop and Claude Code behaviour is from documentation and search, not from running it. The first task of Phase 0 proves the deny rules on your machine; the `PowerShell(...)` rule form follows Claude Code's `Tool(pattern)` convention and is the one thing most worth checking in `/permissions`.
- Contrast numbers are calculated from hex values; the Phase 1 test re-measures rendered pixels.
- The 35 expiry cases were generated by date arithmetic from the stated rules, not by a parser; they are a specification to test against, and a case you disagree with is yours to change.
- Whether the chosen fonts contain `₹` is unchecked (per-glyph fallback covers the worst case).
- Chrome's `BarcodeDetector` status comes from Chromium's own thread; the plan does not depend on it either way.
- Matching weights, coach thresholds and OCR choice are starting points that Phases 3, 6 and 7 must measure.

## 6. Decisions that are yours
All have safe defaults in `DECISIONS.md`: O-001 corner-glow strength, O-004 score weights, O-005 light-mode approval, O-007 host Windows toast helper, plus everything marked **Review fix (v4)** (D-034 to D-066), any of which you may change.
