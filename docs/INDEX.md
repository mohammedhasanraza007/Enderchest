# INDEX.md — Which single file answers which question

Do not read the whole pack. Find your task, open that file, open only that section (`grep -n "^## " <file>`, then view the range). Maximum three documents open per step.

| I am about to… | Open | Section |
|---|---|---|
| start a session | `CLAUDE.md`, then `docs/logs/handoff.md` | 0 |
| start a phase | `docs/specs/phase-N-*.md` (its Read list tells the rest) | all |
| write or run Docker, scripts, backups, restore | `docs/DATA_SAFETY.md` | 3, 4, 7, 9, 11, 12 |
| add a table, query, or any number on the dashboard | `docs/DATA_MODEL.md` | 2.x, 3.x |
| write or call an endpoint | `docs/API.md` | 1, then the area (2.x) |
| build or verify a screen | `docs/PAGES.md` | the page (P-xx) |
| style anything (colour, glass, pill, type, motion) | `docs/DESIGN.md` | 4, 5, 6 |
| build the dashboard look | `docs/DESIGN.md` | 6 (+ `docs/design/reference-dashboard.jpg`) |
| install a dependency, add a script, set up tests | `docs/ARCHITECTURE.md` | 6, 8, 10 |
| decide something that feels ambiguous | `docs/DECISIONS.md` | search the topic first |
| avoid a known trap | `docs/MISTAKES_TO_AVOID.md` | the letter for your area |
| run or write a verification | `docs/PROCESS.md` | 4, 5 |
| understand why the product exists or how it maps to SAP | `docs/PROJECT_PLAN.md` | the section named in the spec |
| know what the owner must provide | `docs/OWNER_TASKS.md` | the phase |
| understand what v4 changed and why | `docs/PLAN_REVIEW.md` | summary |
