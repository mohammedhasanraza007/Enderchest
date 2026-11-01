# Enderchest — project pack (v5.1)

Camera-driven personal inventory and maintenance app. SAP PM/QM-inspired, personal scale. **Laptop app only for now** (Docker + browser on Windows); the website and phone app are locked.

This pack is the rulebook, the full specs (every screen, every endpoint, every table) and the design assets. There is no application code yet: Claude Code builds it phase by phase. v5 adds the zip-in, zip-out workflow (D-067); v5.1 makes a chat start as soon as the zip is pasted (D-071) and checks the visuals every time (D-070); v4 is the reviewed version of v3; `docs/PLAN_REVIEW.md` says what was wrong and what changed.

## Start (zip workflow, D-067, D-071)

1. One-time setup: `docs/OWNER_TASKS.md` (Docker Desktop, Git, Claude Code, and the one-time project instruction). You do not run `git init`; the zip holds the history.
2. Paste the latest zip into a new chat in the Enderchest project. The chat starts by itself; you type nothing else unless you have acceptance results or hand edits to add. For the first chat, the zip is `pack-v5.1.zip`.
3. Claude checks the visuals, resumes from the memory (`docs/logs/handoff.md`), builds the next phase, and ends with a zip (for example `phase0.zip`) and a message.
4. Run `/clear` (or open a new chat in the project) and paste the new zip. Repeat for each phase.
5. Run the acceptance script at the end of each phase on your laptop, from the latest zip (`docs/OWNER_TASKS.md`). Put the result in your next message.
6. Answer the open questions in `docs/DECISIONS.md` section E when convenient. O-010 comes first.

## Map (Claude reads one file at a time; `docs/INDEX.md` routes each question)

```
CLAUDE.md                  rulebook + reading order, loaded every session
.claude/settings.json      blocks destructive Docker commands (Bash and PowerShell)
docs/
  INDEX.md                 task -> file -> section router
  specs/phase-0..9-*.md    the working document of each phase (with Read list and gate)
  DATA_SAFETY.md           how data survives every re-run
  DATA_MODEL.md            tables, rules, derived numbers
  API.md                   every endpoint
  PAGES.md                 every screen and what each control does
  DESIGN.md                tokens, components, motion, logo, storyboard
  ARCHITECTURE.md          environment, layout, scripts, dependencies, security, testing
  PROCESS.md               phases, milestones, gates, verification
  DECISIONS.md             settled decisions + open questions
  PROJECT_PLAN.md          product, theory, SAP mapping
  MISTAKES_TO_AVOID.md     pitfalls by area
  OWNER_TASKS.md           what only you can provide
  PLAN_REVIEW.md           the v4 review (read once if curious)
  design/                  reference-dashboard.jpg, ux-states.png
  logs/  reviews/  history/   memory (handoff, sessions), evidence, verification reports, old audit
assets/logo/               logo SVG, preview, favicon and icon set
tests/fixtures/            expiry test cases; your private photos go in private/
scripts/                   created in Phase 0 (check_docs.py ships now)
```
