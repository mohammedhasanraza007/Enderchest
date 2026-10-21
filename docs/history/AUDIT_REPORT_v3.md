> **Historical.** This is the v3 audit. Phase numbers, section letters and file names in it refer to the v3 pack. The current review is `../PLAN_REVIEW.md`. Do not read this file in a build session.

# AUDIT_REPORT.md — Review of the v2 pack and what changed (2026-10-16)

Reviewer: Claude. Scope: idea, logic, documents, design assets, logo. Method: read all four documents line by line, opened both design images and zoomed into them, rendered the logo and inspected its fills, recomputed every contrast ratio in `DESIGN.md`, and cross-checked the documents against each other.

## What this review could not do

- **There is no application code in the upload.** The zip held four Markdown files, two images and the logo. The "re-run deletes old data" problem therefore could not be reproduced. The fix is preventive: `docs/DATA_SAFETY.md` closes every known cause and makes each one a gate probe.
- Nothing was run in Docker or on Windows. Library and model versions were not checked (they must be checked at install time). The design skills named in `DESIGN.md` section 0 could not be verified as installed.
- Contrast was recomputed from the hex values, not measured on rendered composite pixels.

## Verdict on the idea

Sound and well scoped. Camera-first capture, a stable QR identity, a text-first ownership check, and a lifecycle with closed loops is a coherent product, and the SAP PM/QM mapping is honest ("inspired by, not an implementation"). The weaknesses were in the engineering details, in three places where documents contradicted each other, and in a process that cost more than it needed to.

## Findings and fixes

Severity: **Blocker** = would have broken the product or a gate. **Major** = wrong or misleading, would cause rework. **Minor** = polish or consistency.

### Blockers

| # | Finding | Fix |
|---|---|---|
| B1 | **Data loss on re-run.** Compose derives a named volume's name from the folder name, so moving or renaming the project folder creates a new empty volume. Nothing stopped the app from creating a fresh database when it did not find one, or from writing into the container layer when the volume was missing. `down -v` and prune commands were not forbidden. Tests could run against live data. | `DATA_SAFETY.md`: pinned project name, external explicitly named volume, mount check, first-run rule (never silently start empty), recovery page, migrations only, backups to a host folder, test isolation, ten Phase 0 probes. `CLAUDE.md` section 3 never-run list and `.claude/settings.json` deny rules. (D-013, D-015, D-017, D-032) |
| B2 | **QR could encode a URL.** A `localhost` address printed on a label works only on the host and dies if the address changes; the Phase 1 gate ("a printed QR opens the correct item") could not be tested as written. | QR encodes a public ID (`ENDR-` + 8 base32 characters), scanned inside the app, printed under the code. (D-018) |
| B3 | **"Bind to localhost"** was specified for the app. Inside a container that makes it unreachable. | Server binds `0.0.0.0` in the container; the host port is published on `127.0.0.1`. (D-020) |
| B4 | **"Works offline" contradicted OCR model downloads.** Most OCR engines fetch models on first use. | Models bundled in the image at build time; Phase 2 gate tests with the network disabled. (D-021) |
| B5 | **Expiry stored as UTC.** "Dates stored in UTC" turns an expiry date into a moment, which shifts a day across timezones and DST. | Expiry and due dates are plain dates; timestamps are UTC; the user's timezone is in settings. (D-019) |
| B6 | **Nav showed screens that do not exist** (Camera, Tasks, Savings) while the same document banned dead controls; Phase 0 delivers the nav, Phase 6 the dashboard. | Nav shows only built screens. (D-025) |
| B7 | **Logo and images were not in the process.** `DESIGN.md` said "no logo mark"; neither the logo nor the UX image was referenced anywhere; nothing told a new Claude session to look at the design before building. | `CLAUDE.md` section 0 (open three visuals first and report what is seen), logo spec in `DESIGN.md` 4.9, storyboard spec in `DESIGN.md` section 20. (D-012, D-014) |

### Major

| # | Finding | Fix |
|---|---|---|
| M1 | **Health rings measured the wrong things.** "Documented" counted having a QR, which every item has automatically, so it was always true. "Fresh" counted items with no date as fresh. "On time" with no tasks would read 100%. | Redefined (`PROJECT_PLAN.md` 14, `DESIGN.md` 6.8): Documented = photo and label printed; Fresh needs an explicit "no expiry"; empty On time is shown as empty. Default weights proposed. (D-026, O-004) |
| M2 | **The two images disagree.** The storyboard's corner glow is strong gold (`#835D30`–`#C69143`); the JPG and the tokens are subtle brown (`#4F3C2E`). The JPG card has fixed height; the storyboard card shrinks. | Rule table in `DESIGN.md` 2.3: JPG values stay, `--bg-glow-corner-strong` recorded as an option, card fits its rows. Glow strength is **open question O-001**. (D-027) |
| M3 | **The storyboard was undocumented.** It encodes behaviour: score 82→86→91, item count 142→142→141, rows 3→3→1, truck moving 18→21→26 as events resolve. | New `DESIGN.md` section 20 and a truck-moves rule in 6.11. |
| M4 | **Live camera coach was not feasible as written.** CPU OCR cannot process every frame. | Two-tier design: browser metrics at about 5 fps, server OCR at ≤1.5 fps, one request in flight. Thresholds stay an Opus item. (D-023) |
| M5 | **Gemini key stored in the database** would be copied into every backup. | Separate secrets file, excluded from backups, never returned by the API. (D-024) |
| M6 | **Scheduler could run twice or repeat notifications** (multiple workers, restarts). | Single worker; dedupe key `(item, kind, due date)`. (D-022) |
| M7 | **SQLite on a Windows bind mount** is slow and its locking is unreliable under WSL2. | Named volume for the live database; host folder for backups only. (D-016) |
| M8 | **Web push** needs VAPID keys, a service worker and an internet push service, for little value in a local app. | Optional stretch, off unless approved. (D-029) |
| M9 | **Phase 0 gate required laptop and PC;** the owner now wants laptop only. Phase 8 content was woven into the front-end spec. | Laptop only; Phase 8 locked; phone content moved to `DESIGN.md` section 21. (D-011) |
| M10 | **`CLAUDE.md` was 24 KB, loaded every session** (about 6k tokens), mostly process detail; its read order omitted `DESIGN.md`; the authority order omitted it too. Costly on Claude Pro. | Core rulebook about half the size (24.6 KB to 11.7 KB), process moved to `PROCESS.md`, a "read by task" file map, authority order covering all files. (D-030) |
| M11 | **Only two scripts** left no safe way to stop, back up or restore. | `stop.bat`, `backup.bat`, `restore.bat` added; the two daily scripts are unchanged. (D-031) |
| M12 | **Unresolved blockers for later phases:** OCR engine unspecified; savings price entry undecided; Playwright, needed for the required screenshots and contrast checks, would have been an "unapproved dependency". | Phase 2 selects the OCR engine by measurement; price is typed by the user; tooling pre-approved in `CLAUDE.md` section 4. (D-028) |

### Minor

| # | Finding | Fix |
|---|---|---|
| m1 | Windows pitfalls absent: CRLF in shell scripts, port conflicts, spaces in file names, EXIF GPS in photos. | `.gitattributes`, port check in `run.bat` spec, file renamed, EXIF stripping rule. |
| m2 | Title Case in the images ("Inventory Health", "Next 14 Days", "142 Items") against the sentence-case rule. | Sentence case wins. (D-033) |
| m3 | Defects in the images: star watermark (and a stray triangle in frame 3), "₹1,240 saved" on a future date in every frame, static slogan subtitle. | Listed in `DESIGN.md` 2.2 and 20 as things not to copy. |
| m4 | Contrast table is accurate (all values within 0.05), but two pairs are razor-thin: on-clay 4.55:1, muted page text on the corner glow 4.55:1. Light-mode muted is 5.6:1, not 5.7. | Noted in `DESIGN.md` 4.3; re-measure on real pixels. |
| m5 | The pack called the roles "Architect" and "Builder" in one file and "Sonnet/Opus" in another. | Model names used throughout. |
| m6 | The design reference path `docs/design/...` did not exist; the UX file was a PNG named with spaces (the request said "2 jpg"). | Both in `docs/design/`, renamed `ux-states.png`. |
| m7 | Phase 0 scope differed between `CLAUDE.md` (tokens only) and `DESIGN.md` (tokens, primitives, nav, reference check). | One definition in `PROCESS.md`. |
| m8 | Light mode has no reference image, so its look is unapproved. | Marked unapproved until the owner approves a screenshot. (O-005) |

## The logo

- **Colour:** every fill in `LOGO.svg` is teal, green or a near-neutral dark grey (hues 83° to 206°; the only dark grey at 240° has 7% saturation) plus one white bead. **There is no purple in the file.** If it looks purple to you, that is how your screen is showing the dark teal-grey tile, or a different file was intended. Either way, you said the look is intentional, so the logo is exempt from the palette rules and must never be recoloured (D-012). If you meant a different logo, send it.
- **Defects fixed:** the outline rectangle was clipped by the viewBox edge (visible as a flattened border), and the root had `width="100%" height="100%"`, which can blow the icon up to fill its container. The working copy insets the outline and uses 64 × 64; the original is kept as `enderchest-logo.original.svg`. The beads are untouched.
- **Added:** `favicon.ico`, 16/32/48/180/192/512 px icons, a 512 px preview PNG (so Claude can see the logo; an SVG cannot be viewed directly), and placement rules.
- **Fit:** teal and green against the warm brown UI is a strong contrast. It works as a self-contained app-icon tile, which is how the spec uses it (not inside glass, not recoloured).

## What changed, file by file

| File | Change |
|---|---|
| `CLAUDE.md` | Rewritten: session-start visual loading, file map, never-run list, laptop-only scope, locked stack, short rules. Process detail moved out |
| `docs/PROCESS.md` | New: model roles, phases (revised gates), loop, verification gate |
| `docs/DATA_SAFETY.md` | New: persistence contract and ten Phase 0 probes |
| `docs/DECISIONS.md` | New: settled decisions D-001 to D-033, open questions O-001 to O-006 |
| `docs/DESIGN.md` | Edited: logo, image conflicts, storyboard, nav, rings, card, truck, laptop-only responsive, deferred phone section |
| `docs/PROJECT_PLAN.md` | Edited: scope, QR ID, dates, data model, coach split, health score, deployment, risks |
| `docs/MISTAKES_TO_AVOID.md` | Edited: decisions moved out, new data-loss and design sections, corrected items |
| `.claude/settings.json`, `.gitignore`, `.gitattributes`, `.dockerignore` | New |
| `assets/logo/`, `docs/design/` | Logo set, design images in place |

## Still needs the owner

See `DECISIONS.md` section D (six open questions, each with a safe default). The one that changes how the app looks is **O-001**, the corner glow strength.
