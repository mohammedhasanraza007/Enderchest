# ARCHITECTURE.md — How It Is Built and Run

> **Read when:** Phase 0 or 1, any new dependency, any script, any test tooling question. **Do not read when:** writing a screen or a single endpoint (use `PAGES.md` / `API.md`).
> **Sections:** 1 Host prerequisites · 2 Repo layout · 3 Containers · 4 Scripts · 5 Environment variables · 6 Backend rules · 7 Frontend rules · 8 Dependency allow-list · 9 Security · 10 Testing tooling · 11 Budgets.

Decisions D-035 to D-038, D-050, D-055, D-064, D-065 live here. These choices are made so no session spends time re-deciding them.

---

## 1. Host prerequisites (the owner's Windows laptop)
Needed: Windows 10/11, Docker Desktop (WSL2 backend), Git for Windows, Claude Code, Chrome or Edge. **Not needed and not assumed:** Python, Node, Playwright or any other tool on the host. Everything that builds, tests or screenshots runs in containers (D-035). Claude Code may run its commands in Git Bash or in its PowerShell tool; every command in the docs must work in both, and the deny rules cover both (`.claude/settings.json`).

## 2. Repo layout
```
Enderchest/
  CLAUDE.md  README.md  .env.example  compose.yaml  compose.test.yaml  Dockerfile
  build.bat run.bat stop.bat backup.bat restore.bat test.bat dev.bat
  backend/    pyproject.toml  requirements.lock
    app/      main.py config.py
              boot/         state machine, mount checks, lock, env marker (DATA_SAFETY 11)
              db/           connection.py, migrate.py, migrations/0001_*.sql …
              backup/       engine.py, restore.py, retention.py, cli.py
              api/          one router module per area of API.md; deps.py (security middleware)
              services/     business rules (lifecycle, matching, reconcile, dashboard numbers)
              repositories/ SQL only, every query takes user_id
              schemas/      pydantic request/response models
              integrations/ ocr/, gemini/, embeddings/
              scheduler/    reconcile loop
              static/boot/  boot pages (plain HTML)
    tests/    unit/ integration/ probes/
  frontend/   package.json  vite.config.ts  tsconfig.json
    src/      tokens/ primitives/ patterns/ screens/ api/ hooks/ routes.tsx main.tsx
    tests/    unit/
  tests/      e2e/ (Playwright)  fixtures/ (README.md, expiry_cases.csv, private/ is git-ignored)
  scripts/    check_docs.py  export_openapi.py
  assets/logo/  docs/
```
Dependencies flow one way: `api → services → repositories → db`. A router never touches SQL; a repository never imports a router.

## 3. Containers
- **`Dockerfile`, targets:** `frontend-build` (Node, builds the bundle), `runtime` (Python slim, non-root user `enderchest`, serves API + built frontend + boot pages, models baked in at build time), `tools` (Python + Node + dev dependencies, for lint, unit and integration tests, OpenAPI export).
- **E2E:** the official Playwright image pinned to the same version as `@playwright/test`, run by `test.bat`, talking to the test app over the compose network. Chromium's fake-camera flags feed a real fixture image for automated camera tests; this is regression evidence only (D-056).
- **`compose.yaml` (live):** project name `enderchest` pinned in the file; service `app`; volume `enderchest_data` with `external: true` and `name: enderchest_data`; bind mount `${ENDERCHEST_BACKUP_DIR}:/backups`; port `127.0.0.1:8470:8470`; `restart: unless-stopped`; `init: true`; `stop_grace_period: 30s`; `security_opt: [no-new-privileges:true]`; healthcheck using Python's standard library (slim images have no curl) that passes when `/health` answers.
- **`compose.test.yaml`:** project `enderchest-test`, volume `enderchest_test_data`, backup dir `./.test-backups`, port `127.0.0.1:8471:8470`, `ENDERCHEST_ENV=test`. Test containers are removed with `docker compose -p enderchest-test rm -sf`; the test database is reset with `POST /api/v1/test/reset`, never by deleting the volume.
- Image layers are ordered so editing code does not re-download models or reinstall dependencies.

## 4. Scripts (all `.bat`, each safe to run any number of times; behaviour details in `DATA_SAFETY.md` section 9)
| Script | Does |
|---|---|
| `build.bat` | checks Docker is running; creates folder `%USERPROFILE%\Enderchest-Backups` and writes `.env` (backup dir with forward slashes, port) if missing; `docker volume create enderchest_data` if missing; builds the `runtime` image. Never deletes anything |
| `run.bat` | `docker compose up -d --wait --wait-timeout 120`; reads `/health`; opens `http://127.0.0.1:8470` when the server answers; prints a plain warning if the state is not `ok` |
| `stop.bat` | `docker compose stop` (never `down`) |
| `backup.bat` | `POST /api/v1/backups` with the safety header; prints the file name, size and folder |
| `restore.bat` | lists backups via a one-off container, asks for the number, asks to type `RESTORE`, stops the app, runs the restore CLI in a one-off container, starts the app (`DATA_SAFETY.md` section 12) |
| `test.bat [unit\|integration\|e2e\|all]` | runs the chosen suites in containers against the test stack only; writes screenshots and reports to `./test-results/` (git-ignored) |
| `dev.bat` | starts the **test** stack with source mounted and hot reload (uvicorn reload plus Vite) on port 8471 for fast iteration; refuses to run if pointed at the live volume |

## 5. Environment variables
`ENDERCHEST_ENV` (`live` default, `test`), `ENDERCHEST_PORT` (8470), `ENDERCHEST_BACKUP_DIR` (set by `.env`), `ENDERCHEST_GEMINI_MODEL` (default `gemini-3.5-flash-lite`, chosen in Phase 3 from current Google docs, always overridable, D-102), `ENDERCHEST_GEMINI_URL` (default `https://generativelanguage.googleapis.com/v1beta`; the test stack sets a closed local port so no test calls Google), `ENDERCHEST_OCR_THREADS` (4: OCR threads, leaving cores for the API on the owner's 6-core laptop), `TZ` unset (the app uses the profile time zone). The Gemini API key is never an environment variable (`DATA_SAFETY.md` section 2).

## 6. Backend rules
- **Python:** one current stable 3.x supported by every pinned wheel (verify at install; fall back one minor version if `onnxruntime` or the OCR engine lacks wheels). Type-hinted; `ruff` clean.
- **Process model:** one uvicorn worker. Routes are plain `def` (run in the thread pool). Heavy work (OCR, embeddings, image resize) runs in a bounded executor of size 1 so `/health` and the API stay responsive. Models load lazily on first use and may unload after 10 idle minutes.
- **Database:** stdlib `sqlite3`, one connection per request thread, `BEGIN IMMEDIATE` for writes, pragmas from `DATA_MODEL.md` 1. No ORM.
- **Migrations:** `app/db/migrations/NNNN_name.sql`, applied in order inside one transaction by `migrate.py`, recorded in `meta.schema_version`, never edited after release, each preceded by a verified pre-migration backup. A migration test builds a realistic database at the previous version and migrates it.
- **Time:** all "today" logic goes through one `clock.today(user)` function that honours the test clock.
- **Errors:** one exception-to-JSON mapper producing the shape in `API.md` 1; unexpected exceptions return `internal_error` and log the traceback.
- **Logging:** structured lines to stdout (`level`, `event`, ids); never log keys, full OCR text of photos, or note contents.
- **Uploads:** ≤ 12 MB; JPEG, PNG or WebP only (HEIC is refused with a message to export as JPEG); Pillow `MAX_IMAGE_PIXELS` set; apply EXIF orientation then **drop all metadata**, re-encode (JPEG quality 92, long edge capped at 2560 px), name files by UUID, generate a 320 px thumbnail.
- **Shutdown:** on SIGTERM stop the scheduler, finish an in-flight backup, run `wal_checkpoint(TRUNCATE)`, close connections.
- **Scheduler:** an asyncio task calling the reconcile of `DATA_MODEL.md` 3.8; also the backup triggers of `DATA_SAFETY.md` 7. In-process; no cron, no Celery.

## 7. Frontend rules
- TypeScript strict. Components small and commented for a reader new to React (the owner).
- Routing `react-router`; server state `@tanstack/react-query` (stale-while-revalidate, invalidate on mutation); no global store beyond that and one small context for theme and profile.
- API types are **generated** from the backend: `scripts/export_openapi.py` writes `openapi.json`, `openapi-typescript` turns it into `frontend/src/api/schema.d.ts`; `frontend/src/api/client.ts` is the only code that calls `fetch` and always sends `X-Enderchest: 1` on writes. Regenerate whenever an endpoint changes; CI-style check: `test.bat unit` fails if the generated file is stale.
- Lists over 100 rows use `@tanstack/react-virtual`.
- No `localStorage` for data. Theme choice is stored through `PUT /api/v1/profile`; a tiny inline script in `index.html` applies the last theme from a cookie-free `data-theme` hint written by the server to avoid a flash.
- Offline means "this machine has no internet" (Gemini disabled, everything else works). There is no service worker and no PWA caching.
- Fonts come from the `@fontsource-variable/*` packages (Newsreader, DM Sans, JetBrains Mono) bundled into the build; no CDN. Check that `₹` renders; per-glyph fallback to the next font is acceptable.

## 8. Dependency allow-list (pre-approved; verify the current stable version at install, commit lockfiles, record versions in the evidence log)
**Backend:** `fastapi`, `uvicorn`, `pydantic` v2, `python-multipart`, `pillow`, `segno` (QR SVG), `httpx` (Gemini REST), `rapidfuzz`, `numpy`, `onnxruntime` (CPU), `tzdata`. **OCR engine and embedding model:** chosen in Phase 3 and Phase 6 from the candidates in those specs; any other is a spec amendment. Phase 3: `rapidocr` on `onnxruntime`, provisional until the bake-off on the owner's photos (D-099); its own requirements (`opencv-python-headless`, `pyclipper`, `shapely`, `omegaconf`, `requests` and the rest, pinned in the lock) come with it. The bake-off's other candidates (EasyOCR with PyTorch, docTR, Tesseract) live only in the separate `bakeoff` image target, never in the app image. **Dev:** `pytest`, `ruff`.
**Frontend:** `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `@tanstack/react-virtual`, `lucide-react`, `jsqr` (use `qr-scanner` instead only if `jsqr` fails to install or decode), `@fontsource-variable/newsreader`, `@fontsource-variable/dm-sans`, `@fontsource-variable/jetbrains-mono`. **Dev:** `vite`, `typescript`, `eslint` with `typescript-eslint`, `prettier`, `vitest`, `@testing-library/react`, `@playwright/test`, `openapi-typescript`. **Phase 8 only, and only if CSS cannot do it:** one animation library (`motion`).
Not allowed without an approved spec: any ORM, any CSS framework, any UI kit, any state library, any charting library, any CDN asset.

## 9. Security (a local app is still a web server)
- **Localhost API hardening (D-050):** middleware rejects any request whose `Host` is not `localhost`, `127.0.0.1` or `[::1]` with the app port (defeats DNS rebinding); rejects non-GET/HEAD requests without `X-Enderchest: 1`; rejects non-GET requests whose `Origin` is present and not the app's own origin; sends no CORS headers; rejects `text/plain` and form content types on JSON endpoints. The `.bat` scripts send the header. Tests prove each rejection (probe 12).
- Photo ids are unguessable UUIDs; photos are served only through the API, never as a static mount of `/data`.
- The Gemini key lives in `/data/secrets/gemini.key` (mode 0600, owned by the app user), is write-only through the API, and is never logged, returned or backed up.
- Container runs as non-root with `no-new-privileges`. The port is published on `127.0.0.1` only. Phase 10 (locked) is where real authentication and HTTPS arrive.
- Inputs validated at the API boundary with pydantic; all SQL parameterised; file names never come from the client.

## 10. Testing tooling
- `pytest` for unit, integration and probe tests; integration tests use a temporary data directory flagged `env_marker='test'`. Probes that need Docker are driven by `test.bat` against the test stack.
- `vitest` for component and logic tests.
- Playwright (container) for end-to-end: real browser, real backend, test volume. Camera pages use Chromium's fake device flags with a real fixture image; the **real webcam check is the owner's acceptance script**, never claimed by automation.
- **Dead-control crawler** (`tests/e2e/dead-controls.spec.ts`, written in Phase 1, extended every phase): on every route, activate each button, link, tab and toggle and require a navigation, a network request, an opened dialog or a visible state change. Anything else fails the build.
- **Contrast test:** reads computed colours of rendered text and its effective background in both themes and asserts the ratios in `DESIGN.md` 4.
- **Fixtures:** `tests/fixtures/expiry_cases.csv` (text only, supplied). Photo fixtures are the owner's real photos in `tests/fixtures/private/` (`tests/fixtures/README.md`). Synthetic images may be used in unit tests but never count as gate evidence (D-056).
- Test clock: `GET /api/v1/test/clock` reads it, `POST /api/v1/test/clock` sets or advances it.

## 11. Budgets (measured and recorded, not guessed)
First `/api/v1/items` page under 150 ms with 1,000 items; dashboard under 200 ms; photo upload including thumbnail under 1.5 s for a 4 MB image; idle app memory under 600 MB after models unload, under 2 GB while OCR runs; cold start to `ok` under 20 s on the owner's laptop; UI interactions at 60 fps on the owner's laptop (PC is not a gate, D-011). A failed budget is recorded with the measurement and either fixed or accepted by the owner in the gate review.
