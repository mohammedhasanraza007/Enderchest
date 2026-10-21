# Phase 8 — Polish and motion

**Read list:** `CLAUDE.md` sections 0, 7, 8 · this file · `DESIGN.md` 8, 10, 11, 14, 16, 18.2, 20 · `PAGES.md` P-12 · `DATA_MODEL.md` 3.7.
**Do not read:** back-end material.
**Owner supplies:** approval of light mode and of the truck. **Milestone:** E (optional).

## Build
1. Motion system of `DESIGN.md` 10: ring sweep, count-up, truck travel and "box slides on the truck" on save, row exit, page transitions; CSS first; at most one animation library (`motion`) only if CSS cannot do it. Nothing animates layout properties; nothing blocks input; reduced motion shows final states instantly.
2. Streak (`DATA_MODEL.md` 3.7) and win moments (`DESIGN.md` 10.4, 11): the dashboard's `streak` stops being `null`. No guilt wording.
3. Light theme pass: every screen in light, owner approval or an explicit deferral recorded.
4. Budgets of `ARCHITECTURE.md` 11 and `DESIGN.md` 16 measured and recorded.
5. Full production checklist `DESIGN.md` 18.2.

## Gate
Reduced motion respected; interactions never blocked by an animation; 60 fps measured on the owner's laptop; the three storyboard frames reproduced including transitions; light mode approved or deferred in writing; contrast and dead-control tests green; verification pass.
