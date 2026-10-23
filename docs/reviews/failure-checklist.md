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
