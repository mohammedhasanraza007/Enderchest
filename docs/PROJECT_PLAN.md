# Enderchest — Project Plan and Theory

This document explains what Enderchest is, what problem it solves, and which technologies it uses and why. It deliberately contains no code. Build rules are in `../CLAUDE.md`; phases and gates in `PROCESS.md`; data rules in `DATA_SAFETY.md`; visuals in `DESIGN.md`; settled decisions in `DECISIONS.md`; pitfalls in `MISTAKES_TO_AVOID.md`.

> **Read when:** writing or explaining a feature, or preparing the SAP interview mapping. **Do not read when:** building (use the phase spec and the contract files). Sections 0, 8, 9 are the ones most often needed.

**Current scope (owner decision D-011):** the laptop app only. Sections about the website and phone describe the later Phase 10, which is locked.

## 0. What Phases 0 to 9 deliver, honestly (D-061)

**It does:** a safe, local, camera-assisted inventory with printed QR labels, expiry and inspection reminders, a dashboard of real numbers, a desk-side "do I own this?" check, and optional Gemini help.
**It does not (until the locked phone phase):**
- *No in-shop check.* A laptop with Docker is not carried into a shop and a phone cannot reach it. "Do I own this?" is a **desk-side** check: before ordering online, while tidying, or holding a product to the webcam. Pasting a product photo from a browser tab is the intended online-shopping path.
- *QR labels are scanned at the laptop's webcam.* The sticker helps for items you bring to the desk or for typing the printed ID; it does not yet open an item from a phone on a shelf.
- *Reminders need an open tab.* The app reconciles in the background while Docker runs, and every due item is waiting in the notification centre, but a browser notification can only appear while an Enderchest tab is open. A host-side Windows toast helper is an idea (O-007), not built.
- *One user, one machine, English text only, Windows with Docker Desktop.*

**Where it competes.** Free self-hosted tools already cover plain inventory (for example HomeBox: photos, locations, custom fields, printable QR labels, maintenance logs; and Grocy for groceries, expiry and chores). Enderchest's differences are camera-first OCR capture, the image-plus-text ownership check, a QM-style inspection loop and the designed experience. For the owner, the strongest story is the *process design* and its honest SAP mapping, backed by tests and measured accuracy, not "yet another inventory app".

---

## 1. Product

**Name:** Enderchest

**One-line pitch:** Point a camera at anything you own, and Enderchest remembers it, labels it with a QR code, tells you whether you already own it when you are about to buy another, and reminds you before it expires or needs inspection.

**What it is:** a camera-driven digital inventory with a maintenance and quality layer, designed for ordinary people, hobbyists and engineers. It runs as a local Docker application on Windows (browser UI on localhost). A phone-friendly website is a possible later phase and is not part of the current scope.

**What it is not:** an industrial ERP, a warehouse system, or an SAP implementation. It borrows ideas from SAP PM and QM and applies them at personal scale.

**Purpose for the owner:** a real, usable portfolio project that connects mechanical engineering studies (maintenance engineering, quality management) with SAP QM/PM interests and software skills.

---

## 2. The problem

- People buy things they already own because they cannot remember what they have (a wrench size, a nail length, a camera module, a shade of makeup).
- Things expire or wear out unnoticed: food, cosmetics, blades, filters.
- Recurring upkeep is forgotten: cleaning a PC, sharpening a blade, inspecting equipment.
- Existing inventory tools exist, but they are data-entry heavy, dull to use, and rarely answer the shopping-aisle question: "do I already own this?"
- Industrial systems solve these problems well, but are not usable by individuals at home.

Enderchest closes the gap with a camera-first experience that is fast to fill, rewarding to maintain, and useful at the moment of decision.

---

## 3. Who it is for

- Mechanical and electrical engineering students and hobbyists with many parts, tools and modules.
- Households that want to avoid duplicate purchases and wasted food or cosmetics.
- Anyone who wants to keep a tidy digital version of an untidy physical life.

The product is not limited to engineers. Categories are flexible, so the same app works for tools, electronics, groceries, cosmetics, and chores.

---

## 4. Core ideas (pillars)

1. **Camera-first capture.** Taking a photo is the main way to add or find things.
2. **QR identity.** Every item or set gets a short public ID (for example `ENDR-7K2M9QXA`) shown as a QR code that can be printed and stuck on it. Scanning it with the app's own camera screen opens the item instantly. The QR holds the ID only, never a web address, so a printed label keeps working when the app's address or data changes.
3. **"Do I own this?"** Show a product, get a ranked answer from the inventory.
4. **Lifecycle and maintenance.** Items have a life: active, used, expired, discarded. Upkeep tasks recur on a schedule. The app prompts, and the user closes the loop.
5. **Delight and habit.** A live camera coach, an inventory health score, streaks and a "duplicates avoided" savings counter make keeping things tidy feel good.

---

## 5. User journeys (in prose)

**Adding an item.** The user opens the camera. The camera coach guides them: hold steady, move closer to the label, tilt to avoid glare. When it sees a model number or date it says so. The app extracts what it can and shows a confirmation screen with editable fields. The user saves; the app generates a QR code and offers a printable label.

**Finding out before buying.** In a shop, the user opens the camera on a product. The app reads the text, finds matching inventory entries, and shows the best candidates with confidence levels and the user's saved photos. The user confirms whether it is the same item. If they decide not to buy, they confirm "I didn't buy it", enter or confirm the price, and the savings counter grows.

**Staying ahead of expiry.** A few days before an expiry date, the user receives a notification: use it, mark it used, mark it expired, or snooze. If nothing happens by the expiry date, the app asks and offers to mark it expired. Each answer updates the inventory and the health score.

**Recurring upkeep.** The user adds a task such as "clean the PC every 14 days" with a photo. When it falls due, the app prompts. The user marks it done or skipped. Completion streaks build.

**Setting up.** The user enters their name, picks a theme, optionally adds a Gemini key, and starts. The app works without internet and without the Gemini key, with reduced features.

---

## 6. Feature areas

**Inventory**
- Items with name, category, quantity, location, photos, notes, expiry date (a calendar date), price, and flexible extra attributes (size, model number, part number, colour, shade, voltage, and so on).
- Multi-value attributes (for example a wrench set stored as one item with a `sizes` list). Sets as separate parent and child items are out of scope (D-041).
- Locations (room, shelf, box) for tidiness.

**Capture and recognition**
- Browser camera capture on the laptop webcam (file upload as an alternative).
- Local OCR for text on labels and packaging.
- Gemini structured extraction as a stronger, online option.
- Confirmation screen for every extracted value.

**Camera coach**
- Real-time friendly prompts based on what the camera actually sees: blur, glare, darkness, distance, whether text is found, whether text is readable, whether a date or model number is detected. Cheap image measurements run in the browser; text detection runs on the backend at a low rate (section 11).
- Short, specific, encouraging language, never a rule list.

**Ownership check**
- Text matching on model names, part numbers and sizes.
- Visual similarity to propose extra candidates.
- Ranked results with confidence and the user's own photos for comparison.

**Lifecycle and maintenance**
- States: active, used, expired, discarded.
- Expiry reminders, optional per-item maintenance reminders, recurring tasks.
- Notification centre and browser notifications. Web push is an optional stretch.
- Maintenance toggle per item. Wording is "inspection suggested".

**Dashboard and engagement**
- Inventory health score, user name, streaks, savings counter, upcoming events.
- Glassmorphism styling, dark and light themes, personalisation, motion.

**Assistant (later)**
- A narrow Gemini-powered chat that can answer questions about the inventory and explain what it found. It answers only from real inventory data.

---

## 7. How "Do I own this?" works (theory)

OCR gives text, not understanding. A reliable answer needs layers:

1. **Read.** Extract text from the shown product: names, sizes, model and part numbers.
2. **Normalise.** Clean the text (case, spacing, common OCR confusions such as 0/O and 1/l) and parse sizes and units. Dates default to day/month/year (India); ambiguous dates are flagged and always confirmed.
3. **Match on text first.** Fuzzy-match against inventory fields. Exact part numbers and sizes are the strongest evidence.
4. **Match on appearance second.** Compute an image embedding for the shown product and compare it with stored photo embeddings to propose extra candidates, especially when no readable text exists. Embeddings are small vectors stored in the database next to the photo record; at personal scale (thousands of items) a plain similarity scan is fast enough and needs no vector database.
5. **Rank and explain.** Present the top candidates with a confidence level and the stored photo.
6. **Confirm.** The user decides. The app never claims certainty it does not have.

Honest limits: visually near-identical items (two wrench sizes, two nail lengths) cannot be told apart by appearance alone. Text and size are the reliable signals; appearance only proposes candidates.

Gemini helps by extracting structured fields from a photo, especially when local OCR is weak. The matching decision stays in the app's own logic.

---

## 8. Lifecycle and maintenance model (theory)

An item moves through states: **active** (owned and in use), **used** (consumed or finished), **expired** (past its date without being used), **discarded** (thrown away or given away). Every change is recorded with a time.

Three kinds of time-based prompts exist:
- **Expiry prompts** before a date: "use it before it expires".
- **Maintenance prompts** based on a plan: "inspection suggested after N days".
- **Recurring tasks** not tied to an item's lifespan: "clean the PC every 14 days".

The user closes the loop each time (used, expired, done, skipped, snoozed). Closing loops is what keeps the data accurate, so the product design rewards it with score, streaks and visible wins.

This is **preventive, time-based maintenance** (inspect every N days, from the last completion), not predictive maintenance: nothing here reads sensors or learns from usage, and the docs and the owner must not call it predictive (D-060). Intervals suggested by Gemini are labelled as suggestions, are editable, and are never shown as certain facts. Users can switch maintenance prompts off per item.

---

## 9. Mapping to SAP concepts (for interviews)

| Enderchest concept | SAP concept it echoes |
|---|---|
| Item | Equipment / material master |
| QR label and location | Equipment tag and functional location |
| Quantity | Stock quantity (MM concept); no reorder point is built |
| Expiry date | Shelf-life expiration date on a batch |
| Maintenance task attached to an item (every N days) | Time-based maintenance plan (PM) |
| "Needs attention" alert | Maintenance notification (PM) |
| Task such as "clean the PC" | Maintenance order or task list (PM) |
| Inspection record (good, worn, defective; a real table) | Inspection lot and results (QM) |
| Outcome (used, expired, discarded) | Usage decision (QM) |
| Inventory health score | Quality key figure |

State this accurately: Enderchest is inspired by these concepts at personal scale. It is not an SAP implementation and should never be described as one.

---

## 10. Data model (theory)

**Authority:** `DATA_MODEL.md` holds the exact tables, fields and formulas; this section is the theory behind them. Each user-owned table has a `user_id` from the very first version so multi-user support later needs no redesign.

- **User:** identity, display name, theme, IANA timezone (set from the browser at first run), notification preferences.
- **Item:** name, category, quantity, location, lifecycle state, expiry date (**calendar date, no timezone**), price (integer paise), public ID (the QR content, unique), label-printed time, flexible attributes (stored as JSON), created and updated times, soft-delete time.
- **Photo:** the item it belongs to, file path on the volume, thumbnail path, capture time, which one is primary, image embedding (small vector).
- **Location:** a named place with an optional parent (room → shelf → box).
- **Task:** one table for both maintenance (attached to an item) and chores (D-040): interval or one-off, schedule mode, enabled, source (user or Gemini-suggested and unverified), last done, next due.
- **Inspection:** a result (good, worn, defective) with a note and optional photo, which also completes the item's maintenance task.
- **Draft:** an unsaved item with its photos and OCR result, stored on the server so nothing is lost (D-049).
- **Event / state change:** an append-only history of changes and outcomes.
- **Notification:** what, why, when, status (unread, snoozed, resolved), link to item or task.
- **Savings entry:** which item, price, date, confirmed by the user.
- **Settings:** image-sharing switch, OCR preferences, coach on/off. The Gemini key is **not** in the database: it lives in a separate secrets file on the data volume (`DATA_SAFETY.md` section 2).
- **Meta:** schema version and creation time, used by migrations and the downgrade guard.

Photos are stored as files on the volume; the database stores only paths. Extra item attributes are flexible so tools, groceries and cosmetics share one structure.

**Dates and time.** An expiry or due date is a calendar date (`2027-03-14`) with no timezone, because "expires 14 March" means the same day everywhere. Moments (created, state changed, notified) are UTC timestamps. "Is it due or expired?" compares the date with the **user's local date**, using the timezone stored in settings, so daylight saving changes cannot shift a due date.

**Public ID.** `ENDR-` followed by 8 characters from the Crockford base32 alphabet (no I, L, O, U), generated randomly and checked for uniqueness. It is printed under the QR so a damaged code can still be typed.

---

## 11. Architecture overview

Components and their jobs:

- **Browser UI (React):** camera capture, camera coach overlay, QR scanning, dashboard, forms, notifications. Runs on the laptop. Layout is fluid down to a small laptop window; a phone layout belongs to Phase 10.
- **Backend (FastAPI, Python):** the only server. Provides the API, runs OCR and matching, talks to Gemini, runs the scheduler, sends notifications.
- **Database (SQLite):** one file on a Docker volume, holding all structured data.
- **File storage:** item photos on the same volume.
- **OCR engine:** a pretrained local OCR model, running on CPU only (no GPU support in scope, D-063). Models are bundled into the image at build time, so the running app never downloads anything. Phase 3 compares the candidates in its spec (RapidOCR on ONNX Runtime, EasyOCR, docTR, Tesseract as a baseline; verify what is current at install time) on the owner's 20 real photos and records accuracy and CPU latency before choosing.
- **Image embedding model:** a pretrained model used to compare product appearance.
- **Gemini adapter:** a thin backend layer for structured extraction and the narrow assistant; the key never leaves the backend.
- **Scheduler:** runs inside the backend; checks expiries and due tasks on startup and on a fixed cadence.
- **Notification channels:** in-app notification centre (source of truth), browser notifications. Web push is an optional stretch.
- **Backup engine:** consistent database backups and incremental photo copies to a host folder (`DATA_SAFETY.md`).

Important consequence: the Docker container cannot see the laptop's webcam, so the browser captures images and sends them to the backend.

**Camera coach split.** A live coach cannot send every frame to a CPU OCR engine. So: (1) in the browser, on a downscaled frame about five times a second, measure sharpness, brightness and glare (cheap); (2) about once per second at most, with one request in flight and old frames dropped, send a small frame to the backend for text detection and confidence. Messages combine both. Starting thresholds are in `specs/phase-7-coach.md`; Phase 7 tunes and records them on real captures.

**Browser camera rule.** `getUserMedia` works on `http://localhost`. It will not work on a plain-HTTP network address, which is one reason phone use is deferred to the HTTPS phase.

---

## 12. Technology choices and reasons

| Choice | Reason |
|---|---|
| FastAPI (Python) | Python has the best OCR and image libraries; FastAPI is clean, fast and well documented |
| React (frontend only) | Component model suits a dashboard and camera overlay; the owner has some experience, so components stay small and commented |
| Node.js (build tooling only) | Needed to build and bundle the React app; not a second backend |
| SQLite with JSON attributes | Zero install, one file, perfect for local use; JSON handles varied item types |
| Pretrained OCR | Far better than anything trainable on a hobby dataset; training from scratch is not worthwhile |
| Pretrained image embeddings | Gives candidate suggestions without training a model |
| Gemini API | Strong structured extraction from messy photos; optional and switchable |
| In-process scheduler | Simple, reliable, no extra service for a local app |
| Browser notifications (open tab) | Works from a container; Windows desktop toasts do not. Web push is not built |
| Docker with `build.bat` and `run.bat` | Reproducible setup and a two-click daily experience on Windows. The data volume is external and explicitly named so rebuilds and folder moves never touch it |
| Named Docker volume for SQLite, host folder for backups | SQLite locking is unreliable on Windows bind mounts; plain-file backups outside Docker survive a Docker reset |
| HTTPS (Phase 10, locked) | Required for phone camera access over a network |
| Google sign-in (Phase 10, locked) | No password handling; cleanly separates users |

Versions are pinned at build time and verified against current releases, not assumed from memory.

---

## 13. Deployment and delivery plan

**Stage 1 — Local Docker (current target, laptop only).** The owner's daily actions are `build.bat` once and `run.bat` whenever he wants to use it; `stop.bat`, `backup.bat` and `restore.bat` are utilities. Docker Desktop with WSL2 and virtualisation must already be available (the owner confirmed both on his machines). The PC is a later check using the same scripts.

**Stage 2 — Hardened local release.** Prebuilt image so `run.bat` can simply start the app without building. Backup and restore of data.

**Stage 3 — Website and phone (locked).** HTTPS, Google sign-in, one isolated dataset per user, responsive phone layout, deployment to a host. The phone uses the browser camera; low-end phones send photos to the backend rather than running models. This stage starts only when the owner unlocks it, after Phases 0 to 7 pass on the laptop.

---

## 14. Gamification design

- **Inventory health score:** a weighted average of four values, each computed from real data (the dashboard rings, `DESIGN.md` 6.8):
  1. **Documented:** share of active items that have a photo **and** a label marked printed. (Having a QR is not enough: every item gets one automatically.)
  2. **Located:** share of active items with a location.
  3. **Fresh:** share of active items that are not past their expiry date. An item with no date counts as fresh only if the user marked it "no expiry"; an item whose expiry is simply unknown does not count.
  4. **On time:** share of due tasks and prompts that are not overdue. With no tasks yet the ring is shown empty with "no tasks yet", not as 100%.
  Default weights: 25, 20, 35, 20 (open question O-004). With no items the score is shown as an em dash, never 0 or 100.
- **Duplicates avoided:** a running ₹ total of purchases the user confirmed they skipped because they already owned the item.
- **Streaks:** consecutive days or weeks of closing prompts and completing tasks.
- **Win moments:** a small celebration when an expiring item is used in time, a task is completed, or a score milestone is reached.
- **Camera coach personality:** short, warm, specific, reactive.

Principle: delight cannot fix friction. If adding an item is slow, the rest does not matter. Speed of capture and accuracy of the ownership check are the real hooks.

---

## 15. Non-goals (for now)

- Bulk "scan a whole shelf" recognition.
- Training custom neural networks from scratch.
- Windows desktop toast notifications from inside Docker.
- Multi-user accounts, Google sign-in, HTTPS, phone layout and public hosting (Phase 10, locked).
- Category-specific special features beyond the shared flexible item model.
- Any claim of being an SAP product.

---

## 16. Risks and open questions

- OCR on curved, glossy or tiny text is unreliable; the confirmation screen is the safety net.
- Expiry-date formats vary widely; parsing needs careful testing on real packaging.
- Visual matching of near-identical items is inherently weak; text and size must lead.
- Browser notifications need an open tab; the in-app notification centre is the source of truth and the honest limit is shown in the UI (D-061).
- Gemini outputs can be wrong; they are always editable and labelled when unverified.
- Gemini usage may be limited by quota and cost; the app must work without it.
- Savings prices are typed by the user; there is no lookup (decision D-028).
- Docker Desktop can be reset, uninstalled or cleaned, which would remove a Docker volume: this is why host backups exist and why the backup status is visible in the UI.
- CPU OCR latency may be too slow for a smooth live coach; the two-tier split and the low server rate are the mitigation, and Phase 7 measures it (Phase 3 measures raw OCR latency).
- OCR models bundled into the image make the image large and the first build slow; accepted in exchange for offline use.
- Windows line endings can break shell scripts inside the Linux container; `.gitattributes` enforces LF for non-`.bat` files.

---

## 17. Roadmap summary

Phase 0 foundation and data safety → 1 app shell and design system → 2 inventory core → 3 smart capture → 4 lifecycle, tasks and notifications → 5 dashboard → 6 ownership check and savings → 7 camera coach → 8 polish and motion → 9 Gemini assistant → 10 website and phone (**locked**). Milestones A to E and detailed gates are in `PROCESS.md`; each phase has a spec in `specs/`.
