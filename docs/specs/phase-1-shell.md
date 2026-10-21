# Phase 1 — App shell and design system

**Read list:** `CLAUDE.md` sections 0, 6, 7, 8 · this file · `DESIGN.md` 2, 3, 4, 5, 6.1–6.7, 6.10, 6.12, 12, 14, 17, 18.1 · `PAGES.md` 1, 2, P-01, P-02, P-16, P-17 · `API.md` 1, 2.2 · `ARCHITECTURE.md` 7, 8, 10 · open the three images (`CLAUDE.md` 0).
**Do not read:** `DATA_MODEL.md` (except 2.2–2.3), `PROJECT_PLAN.md`, other phase specs.
**Owner supplies:** approval of the shell screenshot. **Milestone:** A.

## Goal
The calm, correct skeleton every later screen sits in: tokens, themes, primitives, navigation, first run, settings, error and boot pages. It must already match the reference for the parts that exist.

## Build
1. Frontend scaffold (`ARCHITECTURE.md` 2, 7, 8); `scripts/export_openapi.py` and the generated API types; `client.ts`.
2. Tokens exactly as `DESIGN.md` 4: **text-bearing surfaces are opaque tokens (4.3), status colours appear only on dark status chips on glass (4.5)**; dark theme first, light theme tokens in place; fonts via Fontsource; no-flash theme application.
3. Primitives (`DESIGN.md` 6.10, 6.12): Pill/Button (primary, secondary, ghost), Input, Select, Toggle, Chip, StatusChip, GlassCard, InnerPanel, Sheet, Dialog, Toast (with Undo), Skeleton, BrandMark. The `LiveBadge` component exists but is unused until Phase 2.
4. NavCapsule (`DESIGN.md` 6.2–6.6) showing only what exists after this phase (`PAGES.md` 1): brand and name pill with its menu (Settings, theme pills, backup status line). Bell not yet.
5. Routing, error boundary, P-17, global backup banner (`DATA_SAFETY.md` 7 statuses), redirect `/` → `/settings`.
6. P-01 (steps 1 and 3; step 2 appears in Phase 2), P-02 sections Profile, Appearance, Backup, About.
7. Boot pages from Phase 0 restyled with the same tokens CSS (still plain HTML).
8. Favicon set and brand mark generated from `assets/logo/` (`DESIGN.md` 4.9).
9. Tests: contrast test, dead-control crawler (first version), theme persistence test, a render test of every primitive in both themes.

## Gate
1. Shell reference check (`DESIGN.md` 18.1) with the numbers recorded; owner approves the screenshot.
2. Contrast test passes in both themes against the opaque tokens and chips; the recorded ratios match the tables in `DESIGN.md` 4.
3. Dead-control crawler: zero dead controls on `/welcome`, `/settings`, 404.
4. First run: closing the tab after the name step and reopening resumes correctly; the name survives `stop.bat` then `run.bat`.
5. Back up now creates a real file; the banner appears when the backup folder is made unavailable in the test stack.
6. Theme switch persists across reload with no flash; reduced-motion honoured.
7. Generated API types are current; `₹` rendering checked and recorded.
8. Verification pass.

## Owner acceptance (3 minutes)
Complete the welcome screen, switch the three themes, press Back up now and see the file, approve the screenshot.
