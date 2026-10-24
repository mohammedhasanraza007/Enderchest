# Failure Checklist

Kinds of failure found by verification probes. Re-run the relevant ones in later phases. Add new kinds as they are found (what broke, how to trigger it, how to check it is fixed).

## Seeded from the data-safety contract (`../DATA_SAFETY.md` section 10, 14 probes in v4)

| ID | Probe | First phase |
|---|---|---|
| F-001 | Stop and start: data present | 0 |
| F-002 | Container removed (`docker compose rm -sf`) and started: data present | 0 |
| F-003 | Image rebuilt with `--no-cache`: data present | 0 |
| F-004 | Project folder **copied** to a sibling name, scripts run from the copy: data present | 0 |
| F-005 | Container removed and recreated via Compose: data present | 0 |
| F-006 | `docker kill` during a write loop: `quick_check` passes, no half-written record | 0 |
| F-007 | Volume detached: app refuses, creates nothing | 0 |
| F-008 | Database deleted in the test volume with a backup present: recovery page, restore matches | 0 |
| F-009 | `build.bat` ×3 then `run.bat` ×3: no error, no data change | 0 |
| F-010 | Newer `schema_version` in a test database: state `locked / newer_data`, data untouched | 0 |
| F-011 | Backup round trip as the non-root user to the host folder, restore into a fresh test volume, photos match by SHA-256 | 0 |
| F-012 | Wrong Host, missing `X-Enderchest`, foreign Origin, `text/plain` body refused; no CORS headers | 0 |
| F-013 | Environment marker mismatch (live config on test database and reverse) refuses | 0 |
| F-014 | Backup killed mid-way: no `.partial` listed as a backup; next backup succeeds | 0 |
| F-015 | Deny rules refuse the harmless `--help` forms in Bash and PowerShell | 0 |
| F-016 | Restore leaves no stale `-wal`/`-shm` beside the restored database | 0 |
| F-017 | Dead-control crawler reports zero dead controls on every route | 1 |
| F-018 | Contrast test passes on rendered pixels in both themes, including status chips | 1 |
| F-019 | Notification reconcile run twice, and across restarts, creates no duplicate and loses none | 4 |
| F-020 | Every number on screen equals its breakdown list | 5 |

## Found during phases

| ID | What broke, how to trigger it | How to check it is fixed | Found |
|---|---|---|---|
| F-021 | A helper script calls the API differently from the probes (`backup.bat` sent no JSON body and was refused); probes that use `curl` never notice | run the real script against the test stack (probe 15) | Phase 0 verification |
| F-022 | A background rule counts the app's own bookkeeping write as a user change (the backup's log row made the "changed" rule fire every hour) | move the test clock past the rule's window on an idle database; nothing may fire (probe 16) | Phase 0 verification |
| F-023 | A file watcher in a container never sees an edit made in the Windows folder (bind mounts carry no file events), so dev tools serve stale code even after a reload | change a throwaway file on Windows and require the new text to be served (probe 18) | Phase 1 verification |
| F-024 | A form swallows a `validation_error` for a field it does not show: no field message, and the general message is skipped because the problem list is not empty | answer the form's request with a problem for an unknown field (route in a browser test); a message must be visible | Phase 1 verification (not reachable yet; check every new form) |
| F-025 | The scheduler retries a failing automatic backup on every 30 s tick, all day | make the backup fail (backup folder read-only) with no good backup since 03:00; count attempts over a few ticks | Phase 0 verification |
| F-026 | A database connection handed out by a sync dependency is used by its route in another thread (FastAPI runs a sync dependency and a sync route in different pool threads), so a per-thread connection is shared by two requests at once: 500 "bad parameter or other API misuse" under load | many concurrent reads (the 240-read integration test) and parallel writes on one item (V3); no 500, `integrity_check` ok | Phase 2 build |
| F-027 | A reused throwaway test volume still holds an older phase's database, so a new image waits for a pre-migration backup it can never make, or refuses: a setup failure that looks like a product failure | every throwaway volume is new per run (timestamped name, or `--renew-anon-volumes`); grep the scripts and probes for fixed throwaway volume names | Phase 2 build |
| F-028 | A single-file bind mount inside a mounted folder leaves an empty placeholder file on the host side; it gets committed and blanks the real file in the next image | bind-mount folders only; before a checkpoint, no committed file is empty unless meant to be: `git ls-files` checked for zero-byte files | Phase 2 build |
| F-029 | A test computes its expected answer with the same SQL as the code, so it agrees with the code's bug (search matched attribute JSON keys because both used `attributes LIKE`: "size" found every item with a size, "{" found everything) | build expected results from the spec's meaning, independently of the code's query (V6 filters items-1000 in Python); search a key such as `size` and the character `{` | Phase 2 verification |
| F-030 | SQLite's `NOCASE` and `LIKE` fold only A to Z: a "case-insensitive" rule lets "Ölfarben" and "ölfarben" both exist | duplicate-name tests include a non-ASCII pair (fixed for names); search is still ASCII-only for case (logged) | Phase 2 verification |
| F-031 | Two clocks compared: backup log times use the real clock while a rule compares them with the app clock, which the test endpoints move; a probe that moves the clock sees a fresh backup as old (live is unaffected, both are real there) | when a rule compares two stored times, check both come from the same clock; probes that move the clock move it back before acting | Phase 2 verification |
| F-032 | A form that refills untouched fields from proposals cannot tell "cleared by the owner" from "never touched" after a reload, because both are stored empty; the read value comes back | clear or remove a read field, reload the draft: it must stay empty (`proposals.test.ts`, the `owned` list) | Phase 3 verification |
| F-033 | A test reset that clears the database but not files beside it (the Gemini key file) leaves state behind, so the next test starts with a key | after the reset endpoint, `GET /gemini` says `key_set: false`; grep every reset for files outside the database | Phase 3 build |
| F-034 | A batch file edited while cmd runs it: cmd re-reads by byte offset, runs a fragment and may start a second suite | never edit `test.bat` (or any running `.bat`) during a run; edit only after the run exits | Phase 3 build |
| F-035 | Windows paths written through a Python here-document or string turn backslash-f, backslash-r and backslash-b into control characters inside the file (it happened again while writing this row) | write paths with forward slashes or raw strings; before commit, grep changed files for control characters (`grep -nP` for the byte range 0x00 to 0x1f other than tab, newline and carriage return) | Phase 3 build |
| F-036 | Chromium's headless shell answers every notification permission query with "denied", even after it is granted, so a browser-notification test there passes or fails for the wrong reason | run notification specs on channel "chromium" (new headless) and assert one notification was actually shown (`browser-notifications.spec.ts`) | Phase 4 build |
| F-037 | A test-only gallery page renders real components that start asking the server for data (the bell's count), so the gallery fails or shows a server error where no server exists | gallery pages seed every component's data; the gallery spec fails on any request to `/api/` | Phase 4 build |
| F-038 | Two buttons with the same accessible name on one page ("Save" twice in Settings) break older tests that look buttons up by name, and confuse screen readers | one accessible name per action per page; grep specs' `getByRole(..., { name })` hits for more than one match (Playwright strict mode) | Phase 4 build |
| F-039 | Prettier run on files outside `frontend/` without the frontend config reformats them at its default 80 columns | outside `frontend/` pass `--config /frontend/.prettierrc.json`; `git diff --stat` after formatting touches only the intended files | Phase 4 build |
| F-040 | Number parsing that treats every comma as a decimal comma reads "10,000 mAh" as 10 mAh (and a word such as "in" in "2 in 1" as a unit), so a true match is penalised as "Different size" | a comma before exactly three digits groups thousands (English and Indian), one before one or two digits is decimal; a unit word followed by a number is a name; unit-test real label strings (`test_phase6_verification_rules.py`) | Phase 6 verification |
| F-041 | A sheet or dialog component that renders `null` when closed removes the open `<dialog>` from the page instead of calling `close()`, so the browser never returns focus to the button that opened it | keep the `Sheet`/`Dialog` mounted and drive `open`; put per-open state in a keyed child; a keyboard spec asserts the opener is focused after Escape (`phase6-verification.spec.ts`) | Phase 6 verification |
| F-042 | An exception to a scoring rule ("a strong look-alike is still shown") written as "no positive text signal" also lifts a candidate that text speaks against (a different size) | state exceptions by the signals that must be absent, including negative ones; test the exception with a contradicting signal | Phase 6 verification |
