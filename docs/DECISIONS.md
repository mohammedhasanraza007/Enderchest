# DECISIONS.md — Decision Ledger

Settled decisions. Do not revert one without the owner's explicit approval. Add new entries at the bottom (ID, date, decision, reason, status). The owner mirrors this file into his Obsidian vault.

Status values: **Owner** = stated by the owner; **Audit fix** = applied during the 2026-10-16 audit; **Review fix (v4)** = applied in the v4 plan review (`docs/PLAN_REVIEW.md`), proposed by Claude, the owner may change it; **Open** = needs an owner answer (a safe default applies meanwhile).

> **Read when:** a rule feels ambiguous or you are about to change one. Search the topic; do not read top to bottom.

---

## A. Carried over from planning (v1/v2)

| ID | Topic | Earlier idea | Decision | Status |
|---|---|---|---|---|
| D-001 | Database | MongoDB | SQLite with JSON attributes. Zero install, one file | Owner |
| D-002 | Backend | Node.js backend | FastAPI (Python) only. Node is frontend build tooling only | Owner |
| D-003 | Frontend | Unspecified | React, frontend only | Owner |
| D-004 | OCR size | Small ~50 MB model | Size is not a constraint, but it must run on CPU alone | Owner |
| D-005 | Models | Train a ~1–2M parameter network | Pretrained OCR and embeddings only; never train from scratch | Owner |
| D-006 | Gemini role | "Just a classifier" | Structured extraction and a narrow assistant; the app's own logic decides "do I own this?" | Owner |
| D-007 | Auth | Google sign-in early | Not until the website phase; `user_id` on every table from the start | Owner |
| D-008 | Delivery | Website first | Docker local app first; phone website last | Owner |
| D-009 | Notifications | Unspecified | Scheduler + in-app centre + browser notifications. Windows toasts from Docker are impossible | Owner |
| D-010 | Scope | Tools and electronics only | One flexible item model for tools, groceries, cosmetics, chores | Owner |

## B. Owner decisions, 2026-10-16

| ID | Decision | Reason | Status |
|---|---|---|---|
| D-011 | **Laptop app only for now.** Phase 10 (website, phone, HTTPS, Google sign-in; was Phase 8 in v3) is locked. The PC check is later, not a gate | Focus; the website depends on a solid local app | Owner |
| D-012 | **The logo (`assets/logo/`) is part of the product** and is exempt from the "no purple / palette" rules. It is used as supplied, never recoloured | Owner intends its look | Owner |
| D-013 | **Re-running the app must never delete data** | Core requirement; see `docs/DATA_SAFETY.md` | Owner |
| D-014 | **At session start Claude opens the two design images and the logo** before anything else | Keeps every session aligned with the approved look | Owner |

## C. Audit fixes, 2026-10-16 (proposed by Claude; the owner may change any)

| ID | Decision | Reason | Status |
|---|---|---|---|
| D-015 | Live database on an **external, explicitly named Docker volume** (`enderchest_data`) with a pinned Compose project name; host backups in a folder outside Docker (default moved to `%USERPROFILE%\Enderchest-Backups` by D-053) | Compose volume names depend on the folder name; renaming the folder looks like data loss. External volumes survive `down -v` | Audit fix |
| D-016 | SQLite on a named volume, **not** a Windows bind mount | Locking and WAL are unreliable and slow on WSL2 bind mounts | Audit fix |
| D-017 | App refuses to start empty when data or backups exist (recovery state, no silent new DB) | A wrong mount must not look like a fresh install | Audit fix |
| D-018 | **QR encodes a short public ID** (`ENDR-` + 8 Crockford base32 chars), not a URL. Scanned inside the app | A `localhost` URL on a printed label only works on the host machine, and breaks when the address changes | Audit fix |
| D-019 | **Expiry and due dates are plain dates (no timezone)**; timestamps are UTC; the user's IANA timezone is stored in settings | Storing an expiry date as a UTC moment shifts it by a day across timezones | Audit fix |
| D-020 | Container binds `0.0.0.0`; the host port is published on `127.0.0.1` only | "Bind to localhost" inside a container makes the app unreachable | Audit fix |
| D-021 | OCR models are **bundled into the image at build time** | Otherwise first run downloads them and the app is not offline-capable | Audit fix |
| D-022 | Single backend worker; notifications deduplicated by key `(item, kind, due date)` | A second scheduler would double every notification | Audit fix |
| D-023 | Camera coach is two-tier: client-side image metrics (about 5 fps, downscaled) and server OCR at ≤1.5 fps with one request in flight | CPU OCR cannot keep up with live frames | Audit fix |
| D-024 | Gemini key stored in `/data/secrets/gemini.key`, outside the database and outside backups; never returned by the API | Database backups would otherwise leak the key | Audit fix |
| D-025 | Nav shows only built screens; no dead controls | DESIGN rule 3.3 conflicts with showing Camera/Tasks/Savings before they exist | Audit fix |
| D-026 | Health ring "Documented" = photo **and** label printed (not "has a QR"). Refined by D-044 and D-045 | Every item gets a QR automatically, so the old definition was always true | Audit fix |
| D-027 | Needs attention card height fits its rows (as in `ux-states.png` frame 3); empty state keeps a minimum height | The old spec and the UX image disagreed; the image is newer | Audit fix |
| D-028 | Savings price is typed by the user; no price lookup | Closes the open question in the plan; avoids a network dependency | Audit fix |
| D-029 | Web push is an optional stretch in Phase 4, off unless approved | Needs VAPID keys, service worker and an internet push service; low value for a local app | Audit fix |
| D-030 | Process docs split out of `CLAUDE.md` into `docs/PROCESS.md` | `CLAUDE.md` loads every session; v2 cost about 6k tokens each time | Audit fix |
| D-031 | Utility scripts `stop.bat`, `backup.bat`, `restore.bat` added beside `build.bat`/`run.bat` | "Only two scripts" left no safe way to stop or restore | Audit fix |
| D-032 | `.claude/settings.json` denies destructive Docker commands | A rule in prose is not a lock | Audit fix |
| D-033 | UI text is sentence case even where the images use Title Case ("Inventory health", "Next 14 days", "142 items") | DESIGN 4.6 already requires it; the images contradict it and one frame has "Items" | Audit fix |

## D. Review fixes, v4 (2026-10-17; proposed by Claude, the owner may change any)

| ID | Decision | Reason | Status |
|---|---|---|---|
| D-034 | **New phase order:** 0 Foundation, 1 Shell, 2 Inventory, 3 Capture, 4 Lifecycle, 5 Dashboard, 6 Ownership, 7 Coach, 8 Polish, 9 Assistant, 10 Locked. Milestones A to E (`PROCESS.md` 2) | v3's Phase 0 was overloaded; the coach is a delight feature that sat before the daily-value loop; the dashboard had no data until late | Review fix (v4) |
| D-035 | All build, test and screenshot tooling runs in containers; the host needs only Docker Desktop, Git, Claude Code, a browser | Python and Node on the owner's host were never specified | Review fix (v4) |
| D-036 | Stdlib `sqlite3`, plain SQL migrations, no ORM; `DATA_MODEL.md` is the single source for data shapes | Least magic; easiest to verify | Review fix (v4) |
| D-037 | TypeScript strict; API types generated from the backend OpenAPI | Catches front/back drift at build time | Review fix (v4) |
| D-038 | Notifications reach open tabs by polling every 60 s and on focus; no SSE, no websocket, no service worker | Simplest thing that works for a local app | Review fix (v4) |
| D-039 | Items are addressed by `public_id` in URLs and the API | A scan can navigate directly; the id is immutable | Review fix (v4) |
| D-040 | One `tasks` table: a maintenance plan is a task of kind `maintenance` attached to an item | v3 had two near-identical entities | Review fix (v4) |
| D-041 | Sets and kits are dropped from scope; multi-value attributes (for example `sizes`) cover wrench sets | v3 promised sets but never modelled them | Review fix (v4) |
| D-042 | Categories are created by the user (starter chips at first run); each carries defaults for expiry, maintenance, label | Without defaults every wrench drags the Fresh ring down | Review fix (v4) |
| D-043 | `expiry_mode` is `unknown` / `none` / `date` | "No expiry" must be a deliberate answer | Review fix (v4) |
| D-044 | Rings with no denominator are excluded from the score and drawn empty; Documented = photo and (label printed or "no label needed") | A user with no tasks would otherwise be capped at 80; labelling a carton of milk is silly | Review fix (v4) |
| D-045 | "Label printed" is set only when the owner confirms after printing | The browser cannot know whether a print happened | Review fix (v4) |
| D-046 | "Use it" subtracts one from quantity; the item becomes `used` at zero; different expiry dates are different items | State is per row but quantity can exceed 1 | Review fix (v4) |
| D-047 | Snooze offers Tomorrow / In 3 days / Next week, capped at the due date for expiry reminders | v3 had Snooze with no meaning | Review fix (v4) |
| D-048 | Recurring tasks reschedule **from completion** by default; "fixed dates" is optional | Late completion semantics were undefined | Review fix (v4) |
| D-049 | Add flow creates server-stored **drafts**; up to 20 photos at once; review queue | Cold start: entering 100+ items one at a time is where adoption dies | Review fix (v4) |
| D-050 | Localhost API hardening: Host allow-list, `X-Enderchest` header on writes, Origin check, no CORS | A local server is still reachable by web pages the owner visits | Review fix (v4) |
| D-051 | The app never exits on a failed boot check; it serves a boot page (`DATA_SAFETY.md` 11) | Exit plus `restart: unless-stopped` is a silent crash loop | Review fix (v4) |
| D-052 | Backups are staged on the volume, verified, copied out and renamed atomically; also change-triggered (about hourly); `synchronous=FULL`; retention in `DATA_SAFETY.md` 7 | v3 wrote SQLite onto a bind mount and could lose up to 24 h | Review fix (v4) |
| D-053 | Default backup folder is `%USERPROFILE%\Enderchest-Backups`, not `Documents` | Documents is often redirected into OneDrive | Review fix (v4) |
| D-054 | The database records an `env_marker`; the app refuses to start if it differs from `ENDERCHEST_ENV` | Volume names are a weak guard against tests touching live data | Review fix (v4) |
| D-055 | QR decoding uses a JavaScript library (`jsqr`); a typed-ID field is always offered | Chrome's native `BarcodeDetector` is not available on Windows | Review fix (v4) |
| D-056 | Gates that need real photos, webcam, printer or key stay **BLOCKED** until supplied; synthetic stand-ins never count as gate evidence | Prevents simulated evidence | Review fix (v4) |
| D-057 | Every phase ends with a short owner acceptance script | Only the owner can check real hardware | Review fix (v4) |
| D-058 | Lean process: specs are pre-written; a phase starts with a brief and the owner's "go"; Opus only when stuck; proportionate screenshot review | v3's loop multiplied usage on a Pro plan | Review fix (v4) |
| D-059 | Glass surfaces are implemented as **opaque tokens**; status colours only on dark chips; darker light-mode text variants | The alpha recipe and the hex table disagreed and failed contrast (`DESIGN.md` 4.3, 4.5) | Review fix (v4) |
| D-060 | Say "preventive (time-based) maintenance", not "predictive"; the SAP mapping lists only what is built, and Inspection records are a real table | Honesty about SAP claims | Review fix (v4) |
| D-061 | UI and docs state plainly that browser notifications need an open tab | v3 implied reminders arrive while the app is closed | Review fix (v4) |
| D-062 | OCR engine chosen by a measured bake-off on the owner's 20 photos (candidates in the Phase 3 spec) | Accuracy on real packaging cannot be guessed | Review fix (v4) |
| D-063 | English OCR only; no GPU support in scope | Devanagari and GPU passthrough are time sinks | Review fix (v4) |
| D-064 | Pre-approved dependency list in `ARCHITECTURE.md` 8 | Removes per-phase approval delays | Review fix (v4) |
| D-065 | `test.bat` and `dev.bat` exist; tests never run against the live stack | v3 had no home for tests and a slow rebuild loop | Review fix (v4) |
| D-066 | Reading discipline: one file at a time, sections not files, `docs/logs/handoff.md` as memory | Token cost and forgetting across sessions | Review fix (v4) |

## E. Open questions for the owner

| ID | Question | Default until answered |
|---|---|---|
| O-001 | **Background glow strength.** `reference-dashboard.jpg` has a subtle brown corner glow (`#4F3C2E`); `ux-states.png` has a strong gold one (`#835D30` to `#C69143`). Which is the target? | The JPG values (they are the measured, approved tokens). The PNG's stronger glow is recorded as a token option `--bg-glow-corner-strong` |
| O-002 | Is "10% more opaque" 10 percentage points (as built) or a 10% relative increase? | 10 percentage points |
| O-003 | Truck illustration: draw once as SVG and get approval | Draw in Phase 5, approve at the Phase 8 gate |
| O-004 | Health score weights | Documented 25, Located 20, Fresh 35, On time 20 (changeable) |
| O-005 | Light mode has no reference image. Approve a light-mode screenshot before locking it | Build it from tokens, mark "unapproved" until approved |
| O-006 | Should the app auto-start with Docker Desktop (`restart: unless-stopped`)? | Yes, so the scheduler keeps reconciling and reminders are waiting when you open the app; `stop.bat` stops it until the next `run.bat`. Browser notifications appear only while an Enderchest tab is open (D-061) |
| O-007 | Host-side Windows toast helper so reminders show while the browser is closed | Not built; revisit after Milestone C if the owner misses reminders |
| O-008 | CSV export of the inventory | Not built (idea list in `docs/logs/evidence-log.md`) |
| O-009 | OCR languages beyond English (for example Devanagari) | English only (D-063) |
