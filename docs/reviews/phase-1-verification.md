# Phase 1 — Verification (fresh session)

- Date: 2026-10-23. Input: `phase1.1.zip` unzipped into the new empty folder `D:\Projects\Enderchest-phase-1b`; branch `phase-1`, commit `a227f46` (`phase1: checkpoint`), clean tree before anything ran.
- Verifier: Opus 5.5 in a fresh chat. **The builder was also a Claude model working from the same pack**, so this review is deliberately sceptical: it re-runs instead of trusting the evidence log.
- Spec used: `docs/specs/phase-1-shell.md` (Gate 1 to 8). `handoff.md` was read only for the open items.
- Live stack rule: nothing here writes to the live stack (`CLAUDE.md` 3). Live facts are read-only (`docker ps`, `GET /health`).

## Probe list (written before any probe ran)

| # | Probe | Why it is risky | How |
|---|---|---|---|
| Q1 | First run on a **really new** database: a brand-new volume, the app creates the file itself, `/` goes to `/welcome`, the name is saved, survives `stop` then `start` of the container | the browser tests reset an existing test database; the live database is new and empty and the owner's first `run.bat` lands on this path | test stack with a throwaway volume `enderchest_test_data_q1_<time>`, curl plus Playwright |
| Q2 | Theme on a slow load: stored theme `light`, every script and the tokens CSS delayed 2 s; the page must never paint the dark theme first | the no-flash test runs on a fast local network | Playwright with delayed routes, sample `data-theme` and the body background before the scripts arrive |
| Q3 | A failing `PUT /profile`: the server answers 500, or the network drops, on Welcome and on Settings | only the "empty or too long name" case is tested; a failure path that loses the typed name or leaves a button dead is a real defect | Playwright route that fails the request; check message, kept value, usable button, nothing saved |
| Q4 | The name menu by keyboard only: Tab to the name pill, Enter opens, focus inside, Escape closes and returns focus, Settings reachable by Enter | no test drives it by keyboard; DESIGN 14 requires keyboard use | Playwright keyboard only |
| Q5 | `dev.bat` (Vite) runs and serves the app and the API | written but never run (handoff "Known issues") | stop the test app, run `dev.bat`, request the page and `/health` through it, stop it |
| Q6 | The new write endpoints refuse what they must: `PUT /profile` and `PATCH /settings` without the safety header, with a foreign `Origin`, with `text/plain`; bad values (41 characters, spaces only, a number, an extra field); a patch with one good and one unknown key changes nothing | new endpoints in this phase; a partial patch would break "applied whole or not at all" | curl against the test stack, then read back |
| Q7 | Routing truth: an unknown `/api/...` path is a JSON 404 not the app shell; a deep link `/settings` carries the stored theme; `/` redirects to `/settings` after first run | the catch-all page route could shadow the API | curl against the test stack |
| Q8 | Reality audit part (a): `mock`, `fake`, `dummy`, `lorem`, `stub`, `TODO`, `FIXME`, sample arrays, fixed numbers in `frontend/src` and `backend/app` outside tests and the gallery | D-056 | `grep` |

Gate 1 (owner approves the screenshots) and Part 2 on the **live** stack (`build.bat`, `run.bat`) are owner-only: `run.bat` recreates the live container.

## Verdict: no blocker or major; every check Claude can run PASSES; gate 1 and the live run are BLOCKED on the owner

One defect was found (dev.bat, minor, tooling only) and fixed with a probe that failed before and passes after. Phase 1 can close as **PASS WITH NOTES** once the owner (a) approves the screenshots (gate 1) and (b) runs `run.bat` on the live stack and completes the welcome screen there. Until then `handoff.md` keeps `Verification: pending for phase 1` (NOT VERIFIED never counts as PASS).

## Results

| # | Result | Real output |
|---|---|---|
| Q1 | **PASS** | Brand-new volume `enderchest_test_data_q1_20261023193440`, empty backup folder: the app created the database itself (`database_created`), state `ok` about 1.8 s after the container started. In the built-in browser `/` went to `/welcome` (theme dark from System, zone Asia/Kolkata from the browser); after Continue: "Good evening, Mohammed". `docker compose stop` then `start`: profile `Mohammed / Asia/Kolkata / first_run_complete true`; `/` lands on `/settings` with the name pill, `/welcome` cannot be repeated. One backup only (the start-up one), none extra after the restart (`raw/phase-1-verification/q1-up.txt`, `q1-restart.txt`) |
| Q2 | **PASS** | New browser test (`theme.spec.ts`): stored System, OS dark then light, every stylesheet and script 2 s late: `data-theme` is already right and the first paint comes after the last stylesheet. Measured: no delay, first paint 52 ms after stylesheets at 34 ms; 2 s delay, first paint 2052 ms after stylesheets at 2041 ms. The inline theme script sits after the tokens link, so Chrome holds it and the paint until the CSS arrives |
| Q3 | **PASS** | Two new browser tests (`first-run.spec.ts`): Welcome with a 500 that is not JSON shows "Something went wrong. Nothing was lost."; with the network refused shows "Enderchest is not answering…"; the typed name stays, nothing is saved, the same button saves once the server is back. Settings with a 500 in the error shape shows the server's message, keeps "Mo" in the field, shows no "Profile saved.", the capsule still says Mohammed, the stored name is unchanged; the retry saves |
| Q4 | **PASS** | New browser test (`name-menu.spec.ts`), keyboard only, from the 404 page: Tab reaches the pill, Enter opens (`aria-expanded` true), Tab lands on Settings, Tab to Light and Space switches the theme, Escape closes and focus returns to the pill, Enter, Tab, Enter goes to `/settings` and the menu closes |
| Q5 | **FAIL, then fixed (minor, tooling)** | `dev.bat` starts (Vite 8.3.5 in 301 ms, uvicorn with StatReload), serves `/`, `/tokens.css`, the logo and `/src/main.tsx`, and proxies `/health`, `GET` and `PUT /api/v1/profile` (`q5-requests.txt`). A backend edit reloads uvicorn. **A frontend edit was never served**: a changed heading still showed the old text after a full page reload. Root cause, confirmed: Vite watched the bind-mounted Windows folder with file events, which do not reach the container. Fix: `server.watch.usePolling` in `vite.config.ts` (commit `f0a17f2`). New probe 18 writes a throwaway module, changes it, and needs Vite to serve the new text within 15 s: FAIL before, PASS after (`probe18-before-fix.txt`, `probe18-after-fix.txt`) |
| Q6 | **PASS** | `PUT /profile`: no safety header 403, foreign Origin 403, `Origin: null` 403, `text/plain` 422, 41 characters, spaces only, a number, an extra field, an unknown zone, a control character and broken JSON all 422 in the one error shape with the field named; the profile read back unchanged (`name null`); 40 characters with spaces around them saved trimmed. `PATCH /settings`: one good key with one unknown key, one good key with one bad value, a string for a number, `null`, 15 days, no header: all refused and the settings read back unchanged; a valid patch 200 (`q6-q7.txt`) |
| Q7 | **PASS** | Unknown `/api` path (GET and POST) and `DELETE /profile`: JSON 404, never the shell; `/gallery.html` 404 (the test gallery is not shipped); a missing asset JSON 404; `/settings` carries `data-theme-pref="light"`; `/` is the app shell; a look-alike host 403; no `Access-Control-*` header on any answer |
| Q8 | **PASS** | `mock|fake|dummy|lorem|stub|TODO|FIXME|sample|demo` in `frontend/src` and `backend/app`: hits only in `client.test.ts` and the test-only `gallery/`; the runtime image copies only `frontend/dist` (the app build, no gallery). No fixed numbers in screen text. The only `placeholder`s are the boot page's two typed-confirmation boxes |

## Part 1, spec conformance (`phase-1-shell.md` gate)

| Gate | Status | How |
|---|---|---|
| 1 Shell reference and screenshot | numbers MET (capsule within 1 px, `raw/phase-1/shell-reference.json`); **owner approval BLOCKED** | evidence read; screenshots looked at: settings dark 1376 and light 1280, name menu dark 1280 |
| 2 Contrast | MET | `contrast.spec.ts` re-run in this session: pass both themes |
| 3 Dead-control crawler | MET | re-run: zero dead controls on `/welcome`, `/settings`, 404 |
| 4 First run resume; name survives a restart | MET on the test stack (browser test, probe 17, Q1 on a new volume); live `stop.bat` then `run.bat` is the owner's | re-run |
| 5 Back up now makes a file; banner when the folder is gone | MET | `backups.spec.ts`, `nobackups.spec.ts` re-run |
| 6 Theme persists, no flash, reduced motion | MET | `theme.spec.ts` re-run plus Q2 |
| 7 Generated types current; ₹ renders | MET | `test.bat unit` types check; `primitives.spec.ts` rupee test |
| 8 Verification pass | this file | |

Scope and dependencies: `frontend/package.json` holds only allow-listed packages plus `@types/*` for them; no backend dependency changed; nothing of a later phase is on screen (no bell, no Inventory, `LiveBadge` unused). `MISTAKES_TO_AVOID.md` and `DATA_SAFETY.md`: nothing in this session wrote to the live stack; the probes and Q1 used test projects and kept their throwaway volumes.

## Notes (all minor; for the owner's PASS WITH NOTES)

- N1. `dev.bat` frontend edits were never served: **fixed** (Q5, probe 18).
- N2. `test.bat lint` does not cover `tests/e2e`: `tsc` includes only `frontend/src` and the configs, and 6 spec files are not Prettier-formatted (`contrast`, `helpers`, `nobackups`, `primitives`, `shell-reference`, `theme`; the lines added this session are clean). Logged in the evidence log for Phase 2.
- N3. A form shows nothing when a `validation_error` names a field that is not on the form (`fieldProblems` is not empty, so the general message is skipped). Unreachable today (each form sends only its own fields); a trap for Phase 2 forms. Logged.
- N4. Broken JSON is reported with the character position as the field (`"field": "8"`). Unreachable from the app.
- N5. In the name menu the three theme chips wrap, "Dark" alone on a second line (`name-menu-dark-1280x720.png`). Cosmetic; the owner judges it at gate 1.
- N6. The Vite dev proxy writes the app's own `Origin` on every proxied call, so the Origin check is moot under `dev.bat` (test stack only, by design of D-087).

## Evidence
`docs/logs/raw/phase-1/p11-lint.txt`, `p11-unit.txt`, `p11-integration.txt`, `p11-e2e.txt` (the step-a re-run); `docs/logs/raw/phase-1-verification/`: `q1-stack.ps1` and its outputs, `q2-q4-e2e-first.txt`, `q5-devbat.txt`, `q5-requests.txt`, `q6-q7.sh` and `q6-q7.txt`, `probe18-before-fix.txt`, `probe18-after-fix.txt`.
