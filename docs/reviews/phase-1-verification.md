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
