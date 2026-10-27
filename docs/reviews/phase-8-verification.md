# Phase 8 verification — Polish and motion

Fresh session, 2026-10-28, branch `phase-8-verify`, on the code of `phase8.zip` (`9021b55`). Builder and verifier are the same model family: read sceptically.

## Probe list (written before running anything)
1. Reduced motion everywhere: `document.getAnimations()` empty after load and after actions, no save delivery, final numbers shown at once (score, count).
2. Only `transform`, `opacity` and `stroke-dashoffset` animate, on every screen (dashboard, inventory, item, camera, tasks, savings, notifications, settings), not only the dashboard.
3. No animation blocks input: a click during the entrance, during a row exit and during the delivery takes effect.
4. The entrance plays once per tab session and finishes under 1.4 s.
5. Count-up and ring flare only on a real increase (not on a re-render with the same value, not on a decrease).
6. The truck lane never widens any page at 1024, 1280 and 1536 px.
7. Streak rules D-127: an undone action does not count; quiet days are skipped; local-midnight timezone edges; a reopened reminder; shown only from 2 days; no guilt wording anywhere.
8. Save delivery starts on the road truck when it is on screen, ends at the brand mark, removes itself, and never stacks when two items are saved quickly.
9. Shutter fill ring and coach pill lift under reduced motion (no animation).
10. Light-mode contrast on every screen (contrast spec, both themes).
11. Item page: one action row; History empty state is the real empty state.
12. Storyboard frames 1 to 3 (dashboard at rest, a resolved row and a score change, the delivery) still reproduce with transitions.

## How each probe was tested
(filled in below as the run goes)
