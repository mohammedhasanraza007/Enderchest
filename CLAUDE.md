# CLAUDE.md — Enderchest Rulebook (v4)

Loaded every session, so it is deliberately short. **Never read the whole pack.** This file routes you to the one file you need next.

---

## 0. Session start — do exactly this, in this order

1. **Open the three visuals** with the Read tool, before anything else:
   `docs/design/reference-dashboard.jpg` (the approved style) · `docs/design/ux-states.png` (three dashboard states in sequence) · `assets/logo/enderchest-logo-preview.png` (the logo; the SVG beside it is the source, read it as text only to edit or embed it).
   State in one line each what you actually see. If a file will not open, say so and stop; never describe a visual you did not open.
2. **Read this file** (you are doing it), then **`docs/logs/handoff.md`** (the memory from the last session; it says the current phase and the next step).
3. **Open the current phase spec** `docs/specs/phase-N-*.md`. Its **Read list** names every other file and section you may open for this phase. Open those sections and nothing else. `docs/INDEX.md` maps any other question to one file and one section.
4. **Discipline:** at most three documents open per step; open a section, not a file (`grep -n "^## " <file>`, then view the range); do not read `docs/history/`, `docs/PLAN_REVIEW.md` or other phases' specs unless the owner asks. Reading the pack wastes the owner's limited Claude Pro usage and you will forget it anyway; the files are the memory.
5. Reply with a **phase brief** (`docs/PROCESS.md` 3): what you will build, at most five real conflicts or gaps found, owner inputs needed (`docs/OWNER_TASKS.md`). Wait for "go". Do not rewrite specs; amend only for a real gap and record it in `docs/DECISIONS.md`.

---

## 1. What this project is

Enderchest is a camera-driven personal inventory and maintenance app. The owner photographs items; the app reads what it can (name, size, model or part number, expiry date), gives each item a QR label, and helps with "do I already own this?", "this is about to expire or needs inspection", and "keep my stuff organised". It is **SAP-inspired** (PM and QM ideas at personal scale), never an SAP implementation, and the docs and UI say so.

Owner: Mohammed, 2nd-year mechanical engineering student aiming at SAP QM/PM. A real, daily-use portfolio project, not a mock-up. Every design choice must be explainable in one or two sentences in an interview. The owner has limited React experience: small, simple, commented components.

**Current scope (owner decision, D-011):** laptop app only, Phases 0 to 9. Phase 10 (website, phone layout, HTTPS, Google sign-in) is **locked**: do not build, scaffold or design for it beyond `user_id` on user tables. What the laptop scope can and cannot do is stated honestly in `docs/PROJECT_PLAN.md` 0.

---

## 2. File map (read by task; the phase spec's Read list wins)

| File | Holds |
|---|---|
| `docs/INDEX.md` | task → file → section router |
| `docs/specs/phase-N-*.md` | the working document of each phase, with its Read list and gate |
| `docs/DATA_SAFETY.md` | the data-persistence contract (blocker if violated) |
| `docs/DATA_MODEL.md` | tables, rules, derived numbers |
| `docs/API.md` | every endpoint |
| `docs/PAGES.md` | every screen: layout, controls, endpoints, states |
| `docs/DESIGN.md` | tokens, components, motion, logo rules, storyboard |
| `docs/ARCHITECTURE.md` | environment, layout, scripts, dependencies, security, testing, budgets |
| `docs/PROCESS.md` | phases, gates, verification, evidence rules |
| `docs/DECISIONS.md` | settled decisions (never revert without the owner) |
| `docs/MISTAKES_TO_AVOID.md` | pitfalls by area |
| `docs/PROJECT_PLAN.md` | product, theory, SAP mapping |
| `docs/OWNER_TASKS.md` | what only the owner can provide, and when |
| `docs/logs/handoff.md`, `evidence-log.md` | session memory and evidence |

**Authority when instructions conflict:** 1) the owner's latest chat instruction; 2) this file; 3) the specialist file for the area (`DATA_SAFETY.md` for data, `DATA_MODEL.md` for data shapes, `API.md` for endpoints, `PAGES.md` for behaviour, `DESIGN.md` for look); 4) `PROJECT_PLAN.md`; 5) `MISTAKES_TO_AVOID.md`. If two files disagree, say so and ask one question; do not pick silently.

---

## 3. Never run (data protection)

The owner's data must survive every rebuild, restart and re-run. Never run these, never put them in a script, never suggest them without a clear owner request in the current chat:
- `docker compose down` in any form with `-v` or `--volumes`; `docker volume rm`, `docker volume prune` (any flags), `docker system prune` (any flags). Use `docker compose stop` (via `stop.bat`) to stop; `docker compose rm -sf` to remove a container.
- Any command that names the live volume `enderchest_data`, or deletes or overwrites anything inside `/data` or the host backup folder, or deletes `*.sqlite3`.
- Creating a new database when an old one or a backup exists; restoring a database file without moving its `-wal` and `-shm` aside (`DATA_SAFETY.md` 12).
- Running tests, seeds or "reset" helpers against the live stack (`test.bat` and the test endpoints use the test stack only).
- Pointing a command at Docker Desktop's Reset, Clean or Purge features.

`.claude/settings.json` denies these in Bash **and** PowerShell form as a best-effort guard; the rule still binds you. If a command is blocked, do not look for a way around it; tell the owner what you need.

---

## 4. Locked stack (details and the dependency allow-list: `docs/ARCHITECTURE.md`)

Backend: Python, FastAPI, one process and one worker, stdlib `sqlite3` with SQL migrations, no ORM. Frontend: React + TypeScript (strict) built with Vite, Node is build tooling only. Database: SQLite (WAL, `synchronous=FULL`) with JSON attributes; `user_id` on every user-owned table. Photos are files on the data volume; the database holds paths. OCR: pretrained, local, CPU only, models baked into the image, engine chosen by measurement in Phase 3. Matching: text first, image embeddings only to propose candidates, never trained from scratch. Cloud AI: Gemini, backend only, optional and switchable, model name configurable. Scheduler: in-process and idempotent. Notifications: in-app centre is the source of truth plus the browser Notification API (open tab only). Packaging: Docker Compose; scripts `build.bat`, `run.bat`, `stop.bat`, `backup.bat`, `restore.bat`, `test.bat`, `dev.bat`. All tooling runs in containers; the host has only Docker Desktop, Git, Claude Code and a browser. A dependency outside the allow-list needs an approved spec. Pin everything, commit lockfiles, verify current stable versions at install time.

---

## 5. Coding rules

- Clean, boring, readable code. Small functions, clear names, one responsibility per module. Layers: routes → services → repositories → db; schemas validate; integrations isolate OCR and Gemini. Routes never touch SQL.
- Validate input at the API boundary. One error shape (`docs/API.md` 1). Never leak stack traces.
- No dead code, no commented-out blocks, no TODO without an entry in `docs/logs/evidence-log.md`. Comments explain why, not what.
- Config through environment variables and the Settings screen; no hard-coded paths, URLs, ports or secrets. Log what happened and which id; never secrets, photos or note text.
- Time: timestamps UTC; calendar dates (expiry, due) plain dates compared with the user's local date. Money: integer paise shown as ₹ with Indian grouping.
- Schema changes only through numbered forward migrations after a verified pre-migration backup.
- `.bat` files CRLF; everything else LF (`.gitattributes`).
- One concern per commit; commit after each working increment; smallest change that meets the spec; no unrelated refactors; targeted edits over whole-file rewrites.

---

## 6. Product rules (short form)

- Every OCR or Gemini value is shown for confirmation before it is trusted. Expiry dates are always confirmed; reading is day/month/year first.
- The QR encodes only the public ID (`ENDR-` + 8 characters), never a URL or item data. "Label printed" is set only when the owner confirms after printing.
- "Do I own this?" (Phase 6) is a desk-side check: text and fuzzy match first, image similarity only to add candidates, ranked with confidence, the owner decides. Never "certain". Gemini never decides and never receives the inventory.
- Savings (₹) count only after the owner confirms "I didn't buy it" and types the price.
- Maintenance wording is "inspection suggested", never "replacement required"; maintenance is a per-item on/off toggle; Gemini-suggested intervals are labelled "suggested, unverified".
- Soft-delete with an audit trail; permanent delete is typed-confirmation, only after a good backup under 24 hours exists.
- Data leaving the machine (Gemini) is stated in the UI and can be switched off; the app works with no internet and no key.
- Uploads: check type, size, name; drop metadata; no path traversal. The port is published on `127.0.0.1` only; the API is hardened against web pages (`docs/ARCHITECTURE.md` 9).

---

## 7. UX and design rules (short form)

Style is locked to the reference; `docs/DESIGN.md` is the full spec and `docs/PAGES.md` the behaviour. The ones that bite:
1. **No fake data, no dead controls** (section 8).
2. Text-bearing surfaces are **opaque tokens**; status colours appear only on dark status chips on glass (`DESIGN.md` 4.3, 4.5). Glass is used sparingly; animate only `transform` and `opacity`; respect reduced motion; motion is Phase 8.
3. **The logo is shown as supplied**: never recoloured, restyled, outlined, glowed or animated; exempt from the palette rules.

---

## 8. Reality rules — nothing simulated or fake (D-056)

1. Every page, control, number, date and status in the product is real: wired to the backend and the database. No mock, stub, fake, placeholder or demo content or behaviour ships. No seeded data in the live database. No "coming soon" control. A feature not built yet is not on screen (the nav shows built pages only).
2. Test fixtures, the fake camera feed and test-stack data live in test code and the test stack only. They are regression tools. **They are never gate evidence** where a real photo, webcam, printer, key or the owner's judgement is required: that gate is **BLOCKED** until the owner supplies it. Say "BLOCKED: needs <what>"; never write PASS on a simulation.
3. If something cannot truly work (no key, no hardware, no network), the UI says so plainly and degrades; it never pretends.
4. Empty states are the real empty state of real data. Every displayed number traces to a query or formula in `DATA_MODEL.md`.
5. Wording is honest: reminders need an open tab; the ownership check is desk-side; SAP is an inspiration, not a claim.
6. The dead-control crawler (`ARCHITECTURE.md` 10) and the reality audit (`PROCESS.md` 4, Part 3) enforce this every phase.

---

## 9. Process and communication

- Each phase: brief and owner "go" → build in small increments (commit each) → evidence (≤ 15 lines, long output in `docs/logs/raw/`) → owner acceptance script → fresh-session verification (`docs/PROCESS.md`) → fix → close, then update `docs/logs/handoff.md`.
- Default model Sonnet 5.5 high effort. Opus 5.5 only when stuck twice (`PROCESS.md` 1). Do not struggle silently past two failed attempts.
- Direct and technically honest. Report failures plainly: what failed, why, what was tried, what is next. Never claim something works without running it; never fabricate output; read every file back after writing.
- **Ask the owner only when** the answer is costly to undo and not already in the docs, or when an owner-only input is needed. Otherwise state the assumption and continue. Batch questions (at most five).
- Do not expand scope. Worthwhile extras go in `docs/logs/evidence-log.md`.
- Log decisions in `docs/DECISIONS.md` (the owner mirrors it into Obsidian).
- End each session with: done, passed, failed, blocked, next step, and update `handoff.md`.

---

## 10. Definition of done (per phase)

Brief approved; every gate check has recorded real evidence or is explicitly BLOCKED on the owner; owner acceptance run recorded; verification pass written to `docs/reviews/phase-N-verification.md` with verdict PASS (or owner-approved PASS WITH NOTES); nothing in `docs/MISTAKES_TO_AVOID.md` or `docs/DATA_SAFETY.md` violated; the owner can run `build.bat` then `run.bat`, restart, and find all data intact.
