# Delivery video comparison (final merge, 2026-10-28)

Owner's request (2026-10-28): compare the owner's Gemini delivery video with the built save delivery and fix the gaps, after the Phase 9 verification. Source: the frame study `delivery-video-study.md` and its timed frame sheets (shared notes folder; the video stays out of git). Built: `frontend/src/patterns/Delivery.tsx`, `Road.tsx` (Truck), `lib/motion.ts`, `patterns.css` "save delivery".

## Gap list (before this session)
| # | Video beat | Built before | Gap | Done |
|---|---|---|---|---|
| G1 | The box drops from just under the nav onto the truck before it moves | The box dropped 56 px | Yes | Box falls from under the nav (D-138) |
| G2 | The truck stands, then turns on the spot (a yaw) to face the logo | It flipped (`scaleX(-1)`) mid-climb | Yes | Yaw before lift-off: narrows to an edge, opens facing the mark |
| G3 | A thin dashed trail behind the climb; a small four-point star at the lift-off point | None | Yes | Dashed trail (dash offset creeps toward the mark) and a lift-off star |
| G4 | It shrinks down into the logo mark | Shrank to 0.4 and faded | Yes | Shrinks to 0.05 while fading |
| G5 | "Item saved." after the arrival | Toast at once, with the save | Kept | Not copied, see below |
| G6 | Beats land on their times | One easing over the whole animation warped every offset: the box landed late, the climb ended early | Bug | Easing per keyframe segment |
| G7 | Off the dashboard the truck starts at the bottom centre | The lookup found the flying copy's own `.road__truck` (top left of the window) on every page without a road | Bug | The copy is skipped |

## Not copied (rules)
- The 10 s length: the beats are compressed to 1.15 s (under 1.2 s, D-130); any input finishes it.
- The logo glow (CLAUDE.md 7.3), the nav morphing and the made-up truck label.
- The arrowhead creeping up the trail: the creeping dashes carry the same idea without another shape.
- The trail staying on screen: it fades with the trip; nothing stays behind (never stacks).
- G5: the toast stays immediate. It is the save confirmation; under reduced motion there is no trip to wait for, and the form closes and the screen can change at once.

## Checks
- Only transform, opacity and stroke-dashoffset animate; pointer-events none; nothing under reduced motion; never stacks; a click lands and finishes it: `motion.spec.ts` (new test D-138) and `phase8-verification.spec.ts` V1 to V4, green (`docs/logs/raw/final/e2e-delivery-targeted.log`).
- Frames looked at: `delivery-shots.spec.ts` pauses the trip at seven beats on the dashboard, dark and light, 1280 px (`docs/logs/raw/final/shots-delivery/`): the box falls past the greeting, the truck turns to an edge on the road, climbs with the trail and star behind it, and shrinks into the brand mark. Owner approval of the look stays BLOCKED (owner's judgement).
