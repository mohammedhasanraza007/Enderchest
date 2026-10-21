# PROCESS.md — Phases, Gates, Model Roles, Verification

> **Read when:** at the start of each phase (section 2 row + section 3) and before each verification (section 4). **Do not read when:** mid-build; the phase spec is your working document.
> **Sections:** 1 Model roles · 2 Phases, milestones and gates · 3 The loop · 4 Phase Verification Gate · 5 Testing and evidence rules · 6 Reading discipline and handoff.
Scope: **laptop app only** (Phases 0 to 9). Phase 10 is locked (`CLAUDE.md` section 1).

---

## 1. Model roles (D-058)

**Default: Sonnet 5.5 (high effort) does everything**: build, tests, Docker, scripts, fixes, docs, verification. The owner is on a Claude Pro plan, switching models forces a re-read of context, and v4 removes most reasons to switch because the structural decisions are already written (`DATA_MODEL.md`, `API.md`, `PAGES.md`, `ARCHITECTURE.md`, phase specs, matching and coach starting values).

**Opus 5.5 is for being stuck, nothing else.** Escalate when the same problem or gate failed twice, or an intermittent failure has no root cause after a serious attempt. Procedure: Sonnet writes a short brief (problem, what was tried, constraints, file names) and tells the owner "I recommend switching to Opus 5.5 for: <topic>"; Opus writes one design note in `docs/specs/` (no code); the owner switches back. Optional, owner's choice: an Opus review of the Phase 5 and Phase 8 screenshots.

---

## 2. Phases, milestones and gates (D-034)

A phase may not start until the previous gate has a recorded PASS **and** a PASS verification verdict. Gates are run, not assumed. A gate that needs something only the owner can supply is **BLOCKED**, not PASS (D-056).

| Ph | Name | Spec | Owner must supply | Gate in one line |
|---|---|---|---|---|
| 0 | Foundation and data safety | `phase-0-foundation.md` | nothing | All 14 probes in `DATA_SAFETY.md` 10 PASS; deny rules proven |
| 1 | App shell and design system | `phase-1-shell.md` | approve shell screenshot | Shell matches the reference; contrast and dead-control tests pass; first run, settings, backup UI work |
| 2 | Inventory core | `phase-2-inventory.md` | 5-minute acceptance run with real webcam and a printed label | Add by webcam and upload; persist across stop/start; printed label scans back to the item; Trash and drafts work |
| 3 | Smart capture | `phase-3-capture.md` | **20 real photos + labels file**; Gemini key (optional) | Per-field accuracy measured on real photos; every value editable; works offline |
| 4 | Lifecycle and maintenance | `phase-4-lifecycle.md` | 3-minute acceptance run | With the test clock: no duplicate or missed notifications; actions, undo and inspections work |
| 5 | Dashboard | `phase-5-dashboard.md` | approve dashboard vs reference | Reference-match gate; every number equals its breakdown; storyboard states reproduced |
| 6 | Ownership check and savings | `phase-6-ownership.md` | **10 owned + 10 not-owned photos** | Results recorded on the 20; savings only after confirmation |
| 7 | Camera coach | `phase-7-coach.md` | live check with real webcam | Prompts follow real conditions; camera stays smooth; API stays responsive |
| 8 | Polish and motion | `phase-8-polish.md` | approve light mode and truck | Reduced motion respected; budgets met; full storyboard reproduced; light theme approved or deferred |
| 9 | Assistant | `phase-9-assistant.md` | Gemini key | Answers only from real data; refuses to invent; degrades offline |
| 10 | **Locked** | none | the owner unlocks it | Website, HTTPS, Google sign-in, per-user isolation, phone layout |

**Milestones (natural stopping points; each leaves a coherent, usable app):**
- **A, Safe and usable inventory:** Phases 0 to 2.
- **B, Smart capture:** Phase 3.
- **C, Keeps you on time (daily value starts here):** Phases 4 and 5.
- **D, Don't buy twice:** Phase 6.
- **E, Delight and assistant (optional):** Phases 7 to 9.

---

## 3. The loop for every phase (lean, D-058)

1. **Brief, not a new spec.** The spec already exists in `docs/specs/`. Read only what `CLAUDE.md` section 0 and the spec's Read list say. Reply to the owner with one short brief: what will be built, any real conflict or gap found in the docs (at most five, batched), and the owner inputs needed. The owner answers or says "go". Do not rewrite specs; amend them in place only for a real gap and note it in `docs/DECISIONS.md`.
2. **Build** in small increments; run cheap checks first (lint, unit, integration, end-to-end, acceptance); commit after each working increment.
3. **Evidence** in `docs/logs/evidence-log.md`: at most 15 lines per entry; long outputs go to `docs/logs/raw/phase-N/` and the entry links to them.
4. **Owner acceptance run:** the short manual script at the end of the phase spec, performed by the owner, results recorded.
5. **Verification pass** (section 4) in a fresh session, written to `docs/reviews/phase-N-verification.md`.
6. **Fix and re-verify** until PASS (same failed probes, everything downstream, quick regression of earlier probes).
7. **Close** only with a gate PASS and a PASS verdict. Update `docs/logs/handoff.md`.

---

## 4. Phase Verification Gate

**Why:** builders check against what they believe the spec says and miss failures that appear only when things go wrong.
**Who:** Sonnet 5.5 in a fresh session, re-reading only the phase spec (not the builder's summary) and re-running what it needs. State in the report that builder and verifier are the same model and be extra sceptical.
**Size:** proportionate. Write the probe list (typically 5 to 10 riskiest checks) **before** running anything.

**Part 1, spec conformance:** each behaviour, field, endpoint, error case and budget is MET / NOT MET / PARTIAL with how it was verified. Check scope creep, unapproved dependencies, violations of `docs/MISTAKES_TO_AVOID.md` and `docs/DATA_SAFETY.md`.

**Part 2, does it work:** from a clean state, `build.bat` then `run.bat`, then the main flows against the real app.

**Part 3, reality audit (D-056):** (a) search the code for `mock`, `fake`, `dummy`, `lorem`, `stub`, `TODO`, `FIXME`, hard-coded arrays of sample items, and fixed numbers shown in the UI; each hit is justified (test-only) or fixed. (b) Start from an empty database and open every route: each shows its real empty state, nothing pretends. (c) Run the dead-control crawler (`ARCHITECTURE.md` 10): zero dead controls. (d) Every number on screen traces to a query or a formula in `DATA_MODEL.md`.

**Part 4, failure probing** (choose by phase; add your own):
- Client disconnects mid-request or mid-upload; container killed or removed mid-operation; folder copied and run from the copy.
- Slow, failing or absent dependency (OCR error, Gemini offline, no internet): clear message, no hang, no stack trace.
- Malformed, empty, oversized, wrong-type input; bad file names; HEIC upload.
- Double submit and concurrent requests on one item; unknown identifiers; SQLite contention.
- Missing or invalid config at start; clean shutdown; API responsive under heavy work; resource growth over repeated calls.
- Time: UTC versus local date, DST, expiry as a date, app closed when something became due, duplicate or missed notifications after downtime.
- Data-safety probes from `DATA_SAFETY.md` 10 that the phase could affect.

**Visual review is proportionate (D-058):** automated overflow and contrast checks at 1024, 1280 and 1536 px in both themes; the **reviewer looks at** 1280 px dark and 1280 px light for each *new or changed* screen, plus 1024 px for screens with dense layouts. Do not open dozens of screenshots.

**Output and verdict rules:** probe list; per probe PASS / FAIL / NOT VERIFIED with real output; per failure severity (blocker / major / minor), reproduction, root cause marked "confirmed" or "hypothesis". Any blocker or major → FAIL. PASS WITH NOTES only when everything left is minor, logged and agreed by the owner. NOT VERIFIED never counts as PASS. Two failed fix attempts on one failure → escalate (section 1). New failure kinds go into `docs/reviews/failure-checklist.md`; turn probes into permanent automated tests where practical.

---

## 5. Testing and evidence rules

- Success criteria come from the spec, defined before running anything.
- Evidence is real output, real read-back, real test results. "It should work" is never evidence.
- **No synthetic stand-ins as gate evidence (D-056).** Rendered fake labels, generated images, mocked services and a fake camera feed may exist in unit and regression tests, but a gate that depends on real photos, a real webcam, a real printer or a real Gemini key is **BLOCKED** until the owner supplies them. Say so plainly; never mark PASS on a simulation.
- External calls (Gemini, OCR): check the response body and the real effect, not just the status code.
- Time-based features use the test clock (test stack only).
- Tests use the test stack only (`DATA_SAFETY.md` 8).
- A capability with no verification is a gap and must be flagged. Never mark a phase done with a known FAIL.

---

## 6. Reading discipline and handoff (D-066)

Fresh sessions forget; files do not. Therefore:
1. **Never read the whole pack.** `CLAUDE.md` section 0 gives the reading order; `docs/INDEX.md` maps a task to one file and one section. Read the phase spec first; it lists exactly which other files and sections to open.
2. **Open sections, not files.** Find the heading with `grep -n "^## " <file>` or the section index in the file's header, then view only that line range.
3. **At most three documents open per step.** Close the habit of "just checking" a fourth.
4. **`docs/logs/handoff.md` is the memory.** Update it at the end of every session and whenever the context is about to be cleared: what is done (with commit ids), what is next, what is blocked and on whom, decisions made, commands that matter. A new session reads `handoff.md` right after the images, before anything else except `CLAUDE.md`.
5. Use `/clear` between phases and `/compact` when a session grows long. Commit often so the repository, not the chat, holds the state.
