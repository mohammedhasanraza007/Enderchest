# MISTAKES_TO_AVOID.md — Enderchest

> **Read when:** before each phase and each review, and only the section for your area (A to M). **Do not read when:** mid-task on a different area.

A list of things not to do. Each item says what to avoid and why. Read it before every phase and every review. If a plan item conflicts with something here, stop and ask the owner.

Related: settled decisions are in `DECISIONS.md` (never revert one without the owner's explicit approval); data-loss rules in `DATA_SAFETY.md`; visual rules in `DESIGN.md`; process in `PROCESS.md`.

---

## A. Settled decisions

Moved to `DECISIONS.md` (sections A to C), which is the single source. In short: SQLite not MongoDB; FastAPI only, Node for the frontend build only; React frontend; pretrained OCR and embeddings only; Gemini extracts and assists but never decides ownership; Google sign-in not before the website phase; Docker local app first (laptop only for now); scheduler plus in-app and browser notifications; one flexible item model.

---

## B. Architecture mistakes

- Don't write two backends. One FastAPI backend only; Node is for building the React app.
- Don't use MongoDB. It adds install friction and a second moving part for no benefit here.
- Don't put item data in the QR, and don't encode a URL. A `localhost` address on a printed label only works on the host machine and breaks when the address changes. Encode the short public ID only (D-018).
- Don't let routes talk to the database directly. Keep routes thin, logic in services, queries in repositories.
- Don't add `user_id` later. Add it to every table now, or multi-user becomes a rewrite.
- Don't build separate database files per user. One database with strict `user_id` scoping is simpler and safer to migrate.
- Don't add a dependency that isn't in the approved spec.

---

## C. OCR, matching and Gemini mistakes

- Don't train a neural network from scratch. A pretrained OCR will beat anything built on a hobby dataset.
- Don't treat OCR as "understanding". It only returns text; matching needs normalisation, fuzzy matching and confirmation.
- Don't rely on visual similarity to tell near-identical items apart (two wrench sizes, two nail lengths). Text and size lead; appearance only proposes candidates.
- Don't make the OCR require a GPU. The target machine may not have one.
- Don't use a heavy CLIP-class vision model on a phone. Matching runs on the backend.
- Don't download OCR models at run time. Bundle them into the image at build time so the app works offline (D-021).
- Don't send every camera frame to the OCR engine. Measure sharpness, brightness and glare in the browser; ask the server for text at a low rate with one request in flight (D-023).
- Don't load OCR or embedding models on every request. Load once at startup or first use.
- Don't run OCR on full-resolution images. Resize first.
- Don't send the whole inventory to Gemini and ask it to decide ownership. It is slow, costly, inaccurate and leaks data. Extract structured fields, then match in your own code.
- Don't treat Gemini output as fact. Maintenance intervals and extracted fields are suggestions: show them as "unverified", keep them editable, and show a source when available.
- Don't trust extracted expiry dates without user confirmation. Printed dates are one of the least reliable things to read.
- Don't present a guess as a certainty in the ownership check. Show candidates with a confidence level.
- Don't build "scan a whole shelf" bulk recognition in the early phases. It is a much harder problem than one-item-at-a-time capture.
- Don't let the app depend on Gemini. It must be usable offline with reduced features.

---

## D. Docker and Windows mistakes

- Don't forget the data volume. Without it, rebuilding the container wipes all data and photos. Don't rely on a default Compose volume either: its name depends on the folder name (see K).
- Don't assume the container can use the laptop webcam on Windows. Capture in the browser and send the image to the backend.
- Don't assume `build.bat` can install Docker. Docker Desktop, WSL2 and virtualisation must already exist. Check and explain clearly instead of failing silently.
- Don't make `build.bat` and `run.bat` fail silently or continue after an error. Stop at the first failure with a plain-language message.
- Don't open the browser from `run.bat` before the app reports healthy.
- Don't rebuild everything on each run. Order Dockerfile layers so dependencies are cached.
- Don't bake the Gemini key, `.env` files or data into the image or the repository.
- Don't write shell scripts with Windows line endings. `.bat` files are CRLF; everything else LF (`.gitattributes`).
- Don't assume port 8470 is free. `run.bat` checks and says what to do.
- Don't put the SQLite database on a Windows bind mount. Use the named volume (D-016).
- Don't promise a "two-click" experience to end users unless Docker is already set up. For the owner's own machines, it is fine.
- Don't expect a phone to reach the camera on a laptop-hosted app over plain HTTP. Phone camera access over a network needs HTTPS.

---

## E. Notification mistakes

- Don't try to show Windows desktop toasts from inside a Linux container. Use the in-app notification centre and the browser Notification API (open tab only). Web push is not built.
- Don't claim reminders arrive while the app is closed. A browser notification needs an open tab; the in-app notification centre is the source of truth and the UI says so (D-061).
- Don't send notifications with no action. Every notification should let the user mark used, mark expired, snooze or inspect.
- Don't use alarming wording for maintenance. Say "inspection suggested", not "replacement required".
- Don't make maintenance reminders mandatory. Provide a per-item on/off toggle.
- Don't test time-based features by waiting. Build a controllable clock (test environment only).
- Don't store an expiry date as a UTC moment. It is a calendar date with no timezone; compare it with the user's local date (D-019).
- Don't run two scheduler instances (multiple workers) and don't create a notification without a dedupe key. Restarts must not repeat notifications.
- Don't forget the startup check. If the app was closed when something expired, it must catch up when it starts.

---

## F. Data and performance (things that cause slowness)

- Don't store photos as database blobs. Store files on the volume and paths in the database.
- Don't block the API with heavy OCR or image work. Run it off the main request path.
- Don't skip indexes on QR identifier, user, expiry date and state.
- Don't poll the backend aggressively from the browser. Poll the notification count every 60 seconds and on window focus; nothing faster (D-038).
- Don't re-render the whole dashboard on every update. Update only what changed.
- Don't animate layout properties (width, height, top, left). Animate transform and opacity only.
- Don't put heavy animation on the capture screen. The camera view must stay smooth.
- Don't load large images into lists. Use thumbnails.
- Don't edit the database by hand or change the schema without a versioned migration and a safe backup.
- Don't hard-delete by default. Use soft deletion and an audit trail.

---

## G. Security and privacy mistakes

- Don't expose the Gemini key or any secret to the browser, logs, repository or image. Don't store it in the database either, because backups copy the database (D-024).
- Don't keep GPS data in uploaded photos. Strip EXIF location and apply orientation before saving.
- Don't call Gemini from the browser. Calls go through the backend only.
- Don't build a custom password system. The website phase uses Google sign-in only.
- Don't skip `user_id` scoping on any query, even in single-user mode.
- Don't accept uploads without checking type, size and file name.
- Don't hide that images leave the machine. Show it in the UI and provide a switch.
- Don't log full image data or secrets.
- Don't publish the port on all network interfaces. Publish on `127.0.0.1` only. (Don't "fix" that by binding the server to localhost inside the container; there it must bind `0.0.0.0` or the host cannot reach it.)

---

## H. Product and scope mistakes

- Don't build Google sign-in, per-user databases, HTTPS, a phone layout or a bottom tab bar. Phase 10 is locked (D-011).
- Don't build category-specific features (cosmetics, food, tools) in early phases. Use the shared flexible item model.
- Don't count "duplicates avoided" savings automatically. Count only after the user confirms "I didn't buy it" and a price is confirmed. Never inflate the number.
- Don't let delight features come before core features. Motion and polish are late-phase work.
- Don't claim Enderchest is an SAP product or a "full SAP-level system". It is SAP-inspired at personal scale, and should be described that way in interviews.
- Don't make adding an item slow. If capture takes more than a few seconds of effort, the habit loop breaks.
- Don't add features nobody asked for. Record ideas in the evidence log instead.

---

## I. Process and model-role mistakes

- Don't let Opus 5.5 write source code, configuration, Docker files, scripts or tests. It writes design notes and reviews only.
- Don't let Sonnet 5.5 change architecture, the data model, API contracts, the Docker layout or dependencies without escalating.
- Don't keep retrying the same failing approach. After two failed attempts on the same problem or gate, escalate to Opus 5.5 as a stuck problem (`PROCESS.md` 1).
- Don't start a phase without an approved spec.
- Don't mark a phase done without recorded evidence from real runs.
- Don't say "should work" or "looks good". Run it, read it back, show the output.
- Don't re-run a whole gate after a small fix when only the failed level and below need re-checking, but also don't skip re-verification.
- Don't silently narrow or reinterpret an ambiguous requirement. Ask one clear question, or state the assumption.
- Don't revert a decision in `DECISIONS.md` without the owner's explicit approval.
- Don't rewrite a whole file when a targeted edit would do.
- Don't expect token or time savings from model switching to be dramatic. Use the split because it keeps design and implementation separate and reviewed, not because of a guaranteed speed-up.
- Don't read every doc every session. `CLAUDE.md` section 2 says what to read for each task; extra reading costs the owner's Claude Pro usage.

---

## J. UX and camera coach mistakes

- Don't show a static list of camera rules. The coach reacts to what the camera sees.
- Don't have the coach talk constantly. Short, specific, helpful prompts only, and quiet when everything is fine.
- Don't tell the user to "focus on the model number" when no text is detected. Prompt based on the real situation.
- Don't ignore the system "reduce motion" setting.
- Don't ship dark mode or light mode as an afterthought. Define design tokens for both in Phase 1.
- Don't make glass effects hurt readability. Check contrast in both themes.
- Don't let the moving-truck style animations block taps or delay input.
- Don't make the user type what the camera can read, but always let them correct it.

---

## K. Data loss (the owner's top concern)

Full contract in `DATA_SAFETY.md`. The short list:

- Don't run `docker compose down -v`, `docker volume rm/prune`, or `docker system prune --volumes`. Don't put them in a script.
- Don't let the Compose project or volume name depend on the folder name. Pin both (D-015).
- Don't create a new empty database whenever a database is not found. A missing database with photos or backups present is a recovery situation, not a first run (D-017).
- Don't use `create_all`, drop-and-recreate, or seed data in the live database.
- Don't copy a live SQLite file with a plain file copy. Use the online backup API.
- Don't run tests, seeds or reset helpers against the live volume. Test volume only.
- Don't migrate without a verified backup first. Don't let an older app open a newer database.
- Don't let the app write to the container layer when the volume is missing. Check the mount and refuse.
- Don't hard-delete photos or rows by default. Don't delete a backup that is the newest good one.

---

## L. Design, logo and visual source of truth

- Don't start front-end work without opening `docs/design/reference-dashboard.jpg`, `docs/design/ux-states.png` and the logo preview first (`CLAUDE.md` section 0). Don't describe an image you did not open.
- Don't recolour, restyle, outline, glow or animate the logo, and don't pick UI colours from it. It is exempt from the palette rules, not a source for them (D-012).
- Don't copy the star watermark, the sample names or numbers, or the "₹1,240 saved" pill on a future date from the images. They are illustrative defects (`DESIGN.md` 2.2 and 20).
- Don't show nav items for screens that do not exist yet (D-025).
- Don't hard-code the user's name, item counts, dates or scores anywhere in the UI.
- Don't treat the two design images as identical. They differ in glow strength (open question O-001); until the owner answers, use the JPG values.
- Don't put spaces in file names (`UX OF ENDERCHEST.png` was renamed `ux-states.png`); they break scripts and tooling.

---

## M. Added by the v4 review (each one was a real gap or a verified fact)

- Don't build glass surfaces as `rgba` tints from the alpha table; use the opaque tokens (`DESIGN.md` 4.3). Don't put semantic status colours on glass; use the dark StatusChip (4.5).
- Don't trust `Bash(docker compose down:*)` style rules: they are prefix matches and miss `docker compose -f x.yml down -v`. Rules must be glob patterns, mirrored for PowerShell, and proven with harmless `--help` forms (`DATA_SAFETY.md` 13).
- Don't open a SQLite database on `/backups` or any Windows bind mount; stage on the volume, verify, copy out as a plain file, rename atomically.
- Don't replace a database file without moving its `-wal` and `-shm` aside; a stale WAL can corrupt the restored database.
- Don't make a failed boot check exit the process; with `restart: unless-stopped` that is a crash loop. Serve a boot page.
- Don't rely on `BarcodeDetector`: Chrome does not provide it on Windows. Use `jsqr` and always offer typed-ID entry.
- Don't leave the local API open to web pages: Host allow-list, `X-Enderchest` header, Origin check, no CORS.
- Don't rename the folder Claude is working in to test the pinned names; copy it to a sibling and run from the copy.
- Don't use `docker volume rm` to reset the test database; use `POST /api/v1/test/reset` (test stack and marker only).
- Don't default the backup folder under `Documents` (often redirected into OneDrive).
- Don't count an empty ring as 0 in the score, and don't let unknown-expiry tools drag the Fresh ring down: category defaults and the exclusion rule exist (`DATA_MODEL.md` 3.4).
- Don't call time-based inspection "predictive maintenance".
- Don't mark a gate PASS using generated images, a fake camera feed or a mocked service where real input is required: it is BLOCKED (D-056).
- Don't read the whole pack, or more than three documents at once; open the phase spec and its Read list (`PROCESS.md` 6).
- Don't use the lead-in "expiring" as a status word; use the defined words (`DATA_MODEL.md` 3.2).

## N. Added by the Phase 0 build (each one happened)
- Don't extract a pack zip over a git worktree: the zip carries its own `.git`, which replaces the worktree's `.git` link and makes `git status` look clean when it is not. Extract into a new empty folder (`tar` from PowerShell; Git Bash's `tar` cannot read zips).
- Don't use .NET file calls (`[IO.File]::ReadAllText`) or relative paths in a Claude shell after `cd`: the process folder can still be the main checkout, and a write there creates files in the wrong repository. Use full paths.
- Don't pass embedded double quotes to a native command from Windows PowerShell 5.1 (they are mangled); use single quotes inside the string or a file. Don't pass `-Only 6,12` to a script run with `-File`: it arrives as one string.
- PowerShell variable names are case-insensitive: a probe variable `$project` overwrote the library's `$script:Project` and started a stray compose stack. Give script-level variables distinctive names.
- Don't write a probe that needs a "fresh" Docker volume with a fixed name: after one run it is no longer fresh, and volumes cannot be removed (the guard blocks it). Use a new name per run.
- Don't run a clone, copy or zip step without checking it worked: a failed `git clone` let the next commands run in the previous folder. Stop on the first error.
- A first-run rule must treat existing backups as "not fresh" (it did, correctly): a test or probe that expects a brand-new database on a volume whose backup folder holds backups will get `recovery`.
- Don't rely on `backup_log` alone for "last good backup": after a restore the log is the old file's log. The folder is the fallback (`services/backups.py`).
- Docker Desktop at `D:\DockerDesktop\Docker Desktop.exe` cannot be kept running by a Claude shell; the owner starts it. Windows paths in the scratchpad are too long for `git clone`; use a short temp folder.
