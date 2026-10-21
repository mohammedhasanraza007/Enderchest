# Enderchest — project pack (v4)

Camera-driven personal inventory and maintenance app. SAP PM/QM-inspired, personal scale. **Laptop app only for now** (Docker + browser on Windows); the website and phone app are locked.

This pack is the rulebook, the full specs (every screen, every endpoint, every table) and the design assets. There is no application code yet: Claude Code builds it phase by phase. v4 is the reviewed version of v3; `docs/PLAN_REVIEW.md` says what was wrong and what changed.

## Start

1. Do the one-time setup in `docs/OWNER_TASKS.md` (Docker Desktop, Git, Claude Code).
2. Unzip, open a terminal in this folder, `git init`, `git add -A`, `git commit -m "Enderchest pack v4"`.
3. Start Claude Code here (`claude`). It loads `CLAUDE.md` automatically. Run `/permissions` and `/model` (Sonnet 5.5).
4. First message: *"Start the session per CLAUDE.md section 0, then give me the Phase 0 brief."* Claude opens the three images, reads `docs/logs/handoff.md`, then **only** the Phase 0 spec and the sections it lists.
5. Reply "go" (or your changes). Do the short acceptance script at the end of each phase.
6. Answer the open questions in `docs/DECISIONS.md` section E when convenient (defaults apply until you do).

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
  logs/  reviews/  history/   memory, evidence, verification reports, old audit
assets/logo/               logo SVG, preview, favicon and icon set
tests/fixtures/            expiry test cases; your private photos go in private/
scripts/                   created in Phase 0 (check_docs.py ships now)
```
