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

(none yet)
