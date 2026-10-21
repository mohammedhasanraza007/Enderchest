# DESIGN.md — Enderchest Front-End Design Spec (v4, Style Lock)

> **Read when:** any front-end work. **Do not read when:** backend, Docker, data work. **Open only the sections your phase spec lists.**
> **Sections:** 2 Style lock · 3 Hard rules · 4 Tokens (4.3 glass, 4.5 status colours, 4.6 type) · 5 Shape · 6 Components (6.2 nav … 6.11 road) · 7 Other screens · 9 Camera coach · 10 Motion · 12 Voice · 13 States · 14 Accessibility · 16 Performance · 18 Reference gate and checklist · 20 Storyboard.

Scope: front end only (React), **laptop app** (owner decision D-011). Process, models and phase gates live in `PROCESS.md`; the rulebook in `../CLAUDE.md`; product theory in `PROJECT_PLAN.md`; data rules in `DATA_SAFETY.md`; what not to do in `MISTAKES_TO_AVOID.md`; settled decisions in `DECISIONS.md`.

Authority for anything visual or about UX: the owner's latest instruction, then this file. If this file conflicts with `CLAUDE.md` on process, `CLAUDE.md` wins. If something is unclear, ask one question.

**Phone and tablet layouts, the bottom tab bar and anything about HTTPS or sign-in are deferred to Phase 10 (locked).** Their specs are kept in section 21 so nothing is lost, but they are not built now.

---

## 0. How to use this file

- **Open the visuals first** (`CLAUDE.md` section 0): `docs/design/reference-dashboard.jpg`, `docs/design/ux-states.png`, and `assets/logo/enderchest-logo-preview.png`.
  - `reference-dashboard.jpg` (1376 × 768) is **the reference**: every measurement below was taken from it. It defines the look.
  - `ux-states.png` (768 × 1376, three stacked frames) is **the storyboard**: it shows how one dashboard changes as the user resolves things. It defines the behaviour (section 20). Its pixel sizes are not measurements; it is a scaled-down render.
  - The logo is specified in section 4.9.
  - Where the two images disagree, section 2.3 says which wins.
- Read this file before any front-end work. Phase 1 builds the tokens, theme switch, primitives and nav shell (sections 4, 5, 6.1 to 6.7, 6.10, 6.12). Phase 5 builds the dashboard and runs the reference-match gate (section 18). Phase 8 adds motion and the light-mode pass. **Screen behaviour lives in `PAGES.md`; this file is look and feel.** Read only the sections your phase spec names.
- Design process for each screen: (1) a short plan with tokens, an ASCII wireframe, and alignment; (2) review the plan against this file and revise anything that looks like a generic default; (3) build; (4) screenshot in both themes and critique; (5) fix.
- **Skills.** The owner named these front-end skills: UI UX Pro Max, Taste, Interface, Anthropic frontend-design, Bencium, Vercel web interface guidelines, ClaudeKit, Designer, UX Expert. If any are installed, use them for front-end work only, never for backend code. Check what is actually installed and say which were used; never claim one that was not available. Where a skill's defaults conflict with this file (palette, shapes, gradients, copy), this file wins.

---

## 1. Experience goal: the user is always in the loop

The user always knows what the app sees, what it is doing, what is due, and what just changed.

1. **The camera talks.** It reacts to what it actually sees.
2. **Every action answers** within 100 ms, even if the work takes longer.
3. **The app shows what is next.** Due dates and tasks live on the 14-day road.
4. **Progress is visible.** Health rings, streak, and money saved are one glance away.
5. **Nothing is left unexplained.** Loading, empty, error, offline, and permission states all say what is happening and what to do.

Feeling words: warm, tidy, alive, proud, trustworthy. Not: corporate, neon, sci-fi, cartoonish.

---

## 2. Style Lock: the reference images

The owner approved the reference as the visual style for the **entire** front end. It is a warm, dark, frosted-glass interface: a floating navigation capsule, a glowing set of concentric health rings, a frosted "Needs attention" card with cream pill actions, and a 14-day road with a clay delivery truck.

**Everything in the product is derived from the reference's components, colours, glass behaviour, type, and shapes.** New screens are built from the same primitives (section 7). No screen may introduce a new visual language.

### 2.1 The opacity rule (owner request)
Glass in the reference is a little too see-through. Every translucent fill is raised by **10 percentage points of opacity** relative to the reference (more frosted, less see-through). Borders and text are not changed.

Important: simply adding 10 points of cream makes the glass lighter and breaks text contrast. So the spec uses a slightly warmer, darker **taupe tint** (`#C9B8A8`) at the higher opacity. The resulting glass colours stay close to the reference (within a few percent in lightness) and keep text readable. The composite colours and contrast ratios are listed in section 4.3. If the owner meant a different reading of "10 percent more", change the alpha values in 4.3 only.

### 2.2 Things in the reference that must NOT be built
- The four-point star at the bottom right of the reference is an image-generator watermark. It is not part of the design. No sparkle or star icons anywhere.
- The sample data (names, items, numbers, dates) is illustrative. The real UI shows real data only.
- The "₹1,240 saved" pill sits on a future date (24 Oct, when today is 16 Oct) in the reference and in **all three** storyboard frames. In the product it must never sit on a future date (see 6.11).
- The storyboard's third frame also contains a second, cropped star-like triangle above the road. Same rule: no stars or sparkles.
- Title Case labels in the images ("Inventory Health", "Next 14 Days", and "142 Items" in the first storyboard frame) conflict with the sentence-case rule in section 4.6. The written rule wins: "Inventory health", "Next 14 days", "142 items" (decision D-033).
- The reference's subtitle "Here is your household overview." is a static slogan. Section 6.7 forbids that; the real subtitle states one real fact.

### 2.3 When the two images disagree

| Topic | `reference-dashboard.jpg` | `ux-states.png` | Rule |
|---|---|---|---|
| Corner glow | Subtle brown (sampled `#4F3C2E` at the top-right corner; token `#4C392B`) | Strong gold (sampled `#835D30` to `#C69143`) | Use the JPG token. Define `--bg-glow-corner-strong` (`#8D6532`) as an alternative the owner can switch to. **Open question O-001** |
| Card height | Fixed height with three rows | Shrinks to fit its rows (frame 3 has one row) | Fit the rows (decision D-027) |
| Item count | 143 | 142, 142, 141 | Illustrative; real data only |
| Layout, rings, nav, card, road, truck | Measured | Same components, same arrangement | No conflict |

### 2.4 Reference frame
All pixel values below are measured or estimated at the reference size of 1376 × 768 and describe the desktop layout. In code, scale them with `rem` and `clamp()`; do not hard-code them. "Approximately" means measured by eye or by pixel sampling and must be confirmed by overlay (section 18).

---

## 3. Hard rules

### 3.1 No purple, no gradient clichés
- No purple, indigo, violet, or lavender in the **interface**, in any theme. The logo is exempt from this section (4.9, decision D-012).
- No blue-to-purple, neon, rainbow, or "aurora" gradients. No gradient text.
- Gradients are allowed only as warm tonal depth: the background glow, the top-lit glass, the ring glow. They are never the main feature.

### 3.2 No AI slop
Do not produce any of these:
- A generic hero with a big number, small label and gradient accent as a lazy default. (The health rings are a specific, data-driven element, not a default.)
- Identical rounded cards in a uniform grid with one radius, one shadow, and no hierarchy.
- Floating blurry blobs or orbs, sparkle or star icons, emoji used as icons, 3D blob art.
- Fade-and-slide-up on every section; hover lift on every card.
- Tracked-out all-caps eyebrow labels above headings, "A · B · C" meta strings, arrows appended to every link or button, numbered markers on content that is not a sequence.
- Fake testimonials, fake metrics, lorem ipsum, placeholder names, filler greetings.
- Glass stacked on glass on glass. (One nested level is allowed, see 4.3.)
- Glow with no meaning. Glow is allowed only on the health rings, the active nav item, the LIVE badge, and the truck's destination.
- Decorative charts with invented data.

Spend boldness in two places only: the health rings and the road with the truck. Everything else stays quiet.

### 3.3 No logic failure
- The UI never shows fake or hard-coded data. Every number, date, list, and status comes from real data.
- Every control is wired to a real action or does not exist. No dead buttons. **The navigation shows only screens that are built**: until Camera, Tasks and Savings exist, their items are absent, not disabled (decision D-025). The reference shows all five because it is a finished-product picture.
- Counts equal list lengths. The ring values equal their computed breakdown. No negative or impossible values. Dates are right in the user's local time zone.
- Every screen has all of its states (section 13). No dead ends.
- Destructive actions are confirmed or undoable. Double taps do not double-submit. Disabled controls say why.
- No layout shift, overlap, or clipped text.
- The LIVE badge appears only while a camera stream is actually running.
- The greeting follows the user's local time of day.

---

## 4. Design tokens

All values are defined once as CSS variables in a single tokens file. No hard-coded colours, radii, or durations elsewhere. Theme is set by a `data-theme` attribute applied before first paint (no flash).

### 4.1 Dark theme (the reference) — colour tokens

Measured from the reference by sampling pixels.

| Token | Value | Source |
|---|---|---|
| `--bg-base` | `#16110D` | Page background (left and bottom areas) |
| `--bg-glow-corner` | `#4C392B` | Warm glow peak at the top-right corner |
| `--bg-halo-ring` | `#35271E` | Warm halo behind the health rings |
| `--bg-mid` | `#231C16` | Transitional warm brown between glows |
| `--text` | `#FFFAF0` | All primary text (warm white) |
| `--text-muted-page` | `#AEA6A0` | Secondary text directly on the page background only |
| `--text-muted-halo` | `#CDC4BB` | Secondary text inside the ring (on the halo) |
| `--text-muted-glass` | `#E3DACF` | Secondary text on any glass surface |
| `--cream-fill` | `#FDECDA` | Primary pill fill and tooltip fill (reference: `#FDECDA`, `#FFF1DD`) |
| `--on-cream` | `#2A1A12` | Text on cream fills (14.5:1) |
| `--clay-badge` | `#9C5E43` | LIVE badge fill (reference was `#AC785E`; darkened for contrast, see below) |
| `--on-clay` | `#FAF0E4` | Text on the clay badge (4.6:1) |
| `--truck-body` | `#C98A6E` | Truck body (reference measured `#C08469` to `#CA8A6E`) |
| `--truck-cab` | `#915E4B` | Truck cab |
| `--truck-ink` | `#1B120D` | Wheels, outlines |
| `--ring-arc` | `#FFF1DD` | Progress arc fill |
| `--hairline` | `rgba(255, 243, 226, 0.38)` | Nav and ring hairlines (estimated) |
| `--bg-glow-corner-strong` | `#8D6532` | Optional stronger corner glow sampled from `ux-states.png`; unused unless the owner chooses it (O-001) |

Deviation to note: the reference LIVE badge (`#AC785E` with cream text) is only 3.3:1, which fails for small text. The spec darkens the fill to `#9C5E43` (4.6:1). If the owner prefers the lighter look, use dark text (`#1B120D`) on `#AC785E` instead.

### 4.2 Background recipe (dark)
Build the background in layers, back to front:
1. Solid `--bg-base`.
2. A large radial glow anchored at the top-right corner (about 100% x, 10% y), radius about 70% of the viewport width, from `--bg-glow-corner` to transparent.
3. A soft radial halo centred on the health rings (about 50% x, 50% y of the ring area), radius about 330 px at the reference size, from `--bg-halo-ring` to transparent.
4. Optional very fine static grain at about 3% opacity. Never animated.

The right edge in the reference falls back to a slightly reddish dark (`#1D1311`); the glow fades out before the edge.

### 4.3 Glass system (dark) — the opacity rule applied

**Implementation rule (D-059): build every text-bearing glass surface as an OPAQUE fill using the hex in the "Resulting colour" column, as CSS variables (`--surface-nav`, `--surface-nav-glow`, `--surface-card-top`, `--surface-card-bottom`, `--surface-panel`, `--surface-pill`, `--surface-road`).** The nav is a left-to-right gradient from `#52473F` to `#635448` (its two measured values, base and corner glow). `--glass-tint: #C9B8A8` (warm taupe) and the "spec fill" alphas are *design intent only*. Do **not** implement them as `rgba` tints: recomputed on 2026-10-17, the stated alphas do not produce the listed colours (taupe at 29% over base is `#4A413A`, not `#52473F`), and over the corner glow where the card sits the inner panel would be `#877566` (text 4.23:1) and the Snooze pill `#907E6F` (3.74:1), both failing AA. Backdrop blur stays as a cosmetic layer over the opaque fill. Translucent glass is allowed only over live camera video, where a dark scrim `rgba(22,17,13,0.62)` sits behind the text.

| Surface | Reference (approx.) | Spec fill | Resulting colour | Text contrast (`--text`) | Muted-on-glass contrast |
|---|---|---|---|---|---|
| Nav capsule | about 18% cream | taupe at 29% | `#52473F` (over base) / `#635448` (over glow) | 8.7 / 7.0 | 6.5 / 5.3 |
| Active nav tab | +15% over nav | taupe +18% over nav | `#675B52` | 6.3 | 4.8 |
| User name pill | +14% over nav | taupe +18% over nav | `#756659` | 5.3 | not used |
| Card, top edge | about 24% | taupe at 34% | `#6B5B4F` | 6.2 | 4.7 |
| Card, bottom edge | about 12% | taupe at 22% | `#4E4138` | 9.4 | 7.1 |
| Inner panel (on card) | about +17% over card | taupe +20% over card | `#67594E` | 6.5 | 4.9 |
| Secondary pill ("Snooze") | about +9% over panel | taupe +14% over panel | `#75665B` | 5.3 | not used |
| Road bar | about 12% | taupe at 22% | `#3D362F` | 11.4 | 8.6 |

How the card works: the card fill is a **top-lit vertical gradient** from the "top edge" value to the "bottom edge" value. The nested inner panel is a flat fill.

Contrast rules that follow from this table:
- `--text` is allowed on every glass surface.
- `--text-muted-glass` is allowed on the nav, card, inner panel, and road. It is **not** allowed inside pills (the name pill and secondary pill use `--text`).
- `--text-muted-page` is allowed only directly on the page background, never on glass.
- Re-verify every pair with a contrast tool when real content is in place. Minimum 4.5:1 for text below 24 px.
- **Audit check (2026-10-16, by calculation, hex values only; corrected 2026-10-17 by the rule above):** every ratio in the table above matches to within 0.05 *for the listed hex colours*. Two pairs pass with almost no margin and must be re-measured on the real composited pixels: `--on-clay` on `--clay-badge` is 4.55:1 (12 px text), and `--text-muted-page` on the corner glow `#4C392B` is 4.55:1 (so muted page text must not be placed over the corner glow). Light-mode muted text on cream is 5.6:1, not 5.7.

Glass details:
- Border: 1 px hairline, cream. Nav `rgba(255, 243, 226, 0.38)`; card `0.30`; inner panel `0.18`; secondary pill `0.22`. (Estimated from the reference; confirm by overlay.)
- Top inner highlight: 1 px inset line at the top edge of nav and card, cream at 20%.
- Backdrop blur: nav 18 px, card 22 px, both with `saturate(140%)`. The inner panel has **no** backdrop blur, only a fill and a hairline (this is the one allowed nested glass level, and it avoids stacked blur cost).
- Shadows: nav `0 12px 32px rgba(0, 0, 0, 0.30)`; card `0 24px 60px rgba(0, 0, 0, 0.35)`. Nothing else casts shadows in dark mode.
- Fallbacks: if `backdrop-filter` is unsupported, or the user prefers reduced transparency (where supported) or high contrast, the opaque colours are already the default (rule above); there is nothing to fall back to.

### 4.4 Light theme tokens (the same style, translated)
Light mode keeps the exact layout, components, rings, and road. Only materials change.

| Token | Value |
|---|---|
| `--bg-base` | `#F4F1EA` |
| `--bg-glow-corner` | `rgba(185, 121, 90, 0.22)` at the top-right, same placement as dark |
| `--bg-halo-ring` | `rgba(185, 121, 90, 0.12)` behind the rings |
| `--glass-tint` | `#FFFDF9` |
| Nav, card, panels | tint at 62% / 62% top-lit to 52% / inner panel 50% |
| Glass hairline | `rgba(59, 38, 25, 0.14)` |
| `--text` | `#1E1510` |
| `--text-muted` | `#6B5D52` (5.7:1 on cream) |
| Primary pill | fill `#9C5E43`, text `#FAF8F3` (about 4.8:1), hover `#874F37` |
| Secondary pill | cocoa at 6%, hairline cocoa at 16%, text `--text` |
| Ring tracks | `#E9E2D5` with cocoa hairlines; arcs `#3B2619` with a faint clay glow |
| Road bar | `#E9E2D5`, dashes cocoa at 35% |
| Savings pill | fill `#3B2619`, text `#FAF8F3` |
| Truck | same colours as dark mode |
| Focus ring | 2 px `#2A1A12`, 2 px offset |

Light-mode glass needs a worthwhile backdrop to blur (the warm glow and item photos); if it sits on flat colour, use solid surfaces.

### 4.5 Semantic colours (no purple, no blue-violet)

| Role | Light | Dark |
|---|---|---|
| Success (sage) | `#5C7F4D` | `#8FB27E` |
| Warning (amber) | `#B07A1F` | `#E0A94A` |
| Danger (brick) | `#B5463A` | `#E07A6C` |
| Info (slate teal) | `#3F6F7A` | `#7FB0BC` |

Status is never colour alone: always an icon and a word as well.

**Where these colours may be used (verified 2026-10-17 by calculation).** The dark values reach 6.4 to 8.9:1 on the page background but only **2.3 to 3.2:1 on glass surfaces** (danger on the inner panel is 2.30:1). So on glass, the status *word* stays `--text` and the colour appears only on a **StatusChip**: a pill filled `#241B16` holding an icon and the word in the semantic colour (success 7.11, warning 8.00, danger 5.77, info 7.11 on that fill; `--text` on it 16.2). Light theme: `#5C7F4D` and `#B07A1F` are only 4.05:1 and 3.30:1 on `#F4F1EA`; use the **text variants** success `#4A6B3C` (5.38:1) and warning `#8A5F12` (5.00:1); danger `#B5463A` (4.77) and info `#3F6F7A` (4.94) pass as they are. The lighter originals remain for icons and fills (3:1). The Phase 1 contrast test re-measures these on rendered pixels.

### 4.6 Typography

Reference reading: a refined, text-weight serif for the wordmark, greeting, and score; a clean humanist sans for everything else.

- **Display serif:** Newsreader (variable, optical size axis), weight 400 to 500. Used for the wordmark, the greeting, the score number, and large headings only. Closest free match to the reference; compare against the reference and adjust within the same classification if needed.
- **UI sans:** DM Sans, weights 400, 500, 600. All interface text.
- **Data and IDs:** JetBrains Mono, only for QR identifiers and part numbers.
- Self-host subsetted woff2 files. The app works offline, so no font CDN. At most three families and about five files.
- Numbers use tabular lining figures wherever they update or align (dates, counts, ₹).

Sizes measured from the reference (at 1376 wide), with a desktop to mobile scale:

| Element | Desktop (reference) | Mobile |
|---|---|---|
| Wordmark "Enderchest" | about 26 px serif | 22 px |
| Greeting (two lines) | about 56 px / 60 px line height serif | 36 / 40 |
| Subtitle under greeting | about 17 px sans, `--text-muted-page` | 15 |
| Score "82" | about 88 px serif | 64 |
| "Inventory health" | about 17 px sans | 15 |
| "143 items" | about 16 px sans, `--text-muted-halo` | 14 |
| Nav items | about 17 px sans | 15 |
| Card title "Needs attention" | about 19 px sans | 18 |
| Row title (item name and status) | about 16 px sans | 15 |
| Button labels | about 17 px sans | 16 |
| "Next 14 days" | about 21 px sans | 18 |
| Date ticks | about 17 px sans, tabular | 14 |
| Event label under a date | about 14 px sans, `--text-muted-page` | 12 |
| LIVE badge | about 12 px sans, medium weight | 11 |

Sentence case everywhere. The only all-caps text allowed is the single word in the LIVE badge. Body line length under 75 characters.

### 4.7 Spacing and geometry (reference frame)

| Item | Measurement |
|---|---|
| Nav capsule | x 70 to 1305 (width about 1235), y 50 to 110 (height 60), full pill. Outer page margin about 70 px (5.1% of width) |
| Content inset | Hero content starts at x 87, which is the nav's left edge plus 17 px |
| Hero left block | Greeting top at about y 188; subtitle at about y 332 |
| Ring centre | (688, 382), about 50% of width |
| Needs attention card | x 965 to 1288 (323 wide), y 182 to 566 (384 tall), radius about 24 px |
| Inner panel | x 982 to 1270, y 243 to 548; inset 17 px left and right, about 18 px bottom; radius about 18 px |
| Row pitch | About 102 px between item rows; hairline divider between rows |
| Pill buttons in rows | About 126 × 38 px each, 12 px apart, left edge aligned with row text (x 994) |
| Road bar | Full bleed edge to edge, y 647 to 674 (27 px tall) |
| Road dashes | Centre line at y 660; short dashes, cream at about 50% |
| Date ticks | Pitch about 89.6 px between days; labels about 42 px below the bar |
| Truck | About 75 × 42 px, sitting on top of the road bar |
| Spacing scale | 4, 8, 12, 16, 24, 32, 48, 64, 96 px |
| Touch targets | Minimum 44 × 44 px (pill buttons add invisible padding on mobile) |
| Container | Max width 1240 px for content on very wide screens; the road may stay full bleed |

### 4.8 Motion tokens

| Token | Value |
|---|---|
| `--dur-instant` | 100 ms |
| `--dur-fast` | 160 ms |
| `--dur-base` | 240 ms |
| `--dur-slow` | 400 ms |
| `--dur-ring` | 900 ms (ring sweep on first view) |
| `--dur-scene` | 700 ms (truck moments) |
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` |
| `--ease-inout` | `cubic-bezier(0.65, 0, 0.35, 1)` |

Animate only `transform` and `opacity` (and `stroke-dashoffset` on the ring arcs). Never animate width, height, top, left, or large blur values.

---

### 4.9 Logo and brand mark

The logo is part of the product (decision D-012). Files in `assets/logo/`:

| File | Use |
|---|---|
| `enderchest-logo.svg` | Source of truth: 64 × 64 viewBox, a dark rounded tile holding a bead-pattern letter shape in teal and green with a single white bead |
| `enderchest-logo-preview.png` | 512 px render, for Claude to look at (`CLAUDE.md` section 0) |
| `favicon.ico` (16, 32, 48) and `icon-16/32/48/180/192/512.png` | Pre-rendered icons for the browser tab and the app shell. `icon-180` and `icon-192/512` are kept for Phase 10; not wired now |
| `enderchest-logo.original.svg` | The file as supplied. The working copy differs in two ways only: the outline rectangle is inset by half a stroke (the original outline was clipped at the viewBox edge) and the root has a fixed 64 × 64 size instead of 100% |

Rules:
- **Use it exactly as supplied.** No recolouring, tinting, CSS filters, outline, drop shadow, glow, rotation or animation. Do not sample UI colours from it, and do not tint the UI to match it.
- **Exempt from the palette rules** (3.1, 4.5), whatever its exact hue. Measured fills are teal and green with near-neutral dark greys; the exemption exists so nobody "corrects" it.
- It is already a tile, so it sits directly on the page or nav. Never place it inside a glass fill, a pill or a second tile.
- Placement:
  - Nav capsule: 32 px mark at the left, 12 px gap, then the serif wordmark (6.2). 28 px in the compact nav state.
  - Browser tab: `favicon.ico`; page title `Enderchest`.
  - First-run screen: 72 px above the greeting.
  - Settings, About: 96 px.
  - Nowhere else. It is not a bullet, a list icon or a repeated decoration.
- Minimum size 16 px. Clear space around it: a quarter of its width.
- Accessibility: `alt=""` when next to the wordmark (decorative); `alt="Enderchest"` when alone.
- The teal and green tile against the warm brown UI is intentional contrast. The tile reads as an app icon, not as part of the palette.
- Delivered in Phase 1 (nav mark and favicon). Component name: `BrandMark`.

---

## 5. Shape language

### 5.1 Dark mode (as in the reference)
- Navigation capsule, nav tabs, buttons, badges, the name pill, chips, toggles, the savings pill, and inputs under 56 px tall: full pills (`border-radius: 9999px`).
- Frosted cards: radius about 24 px. Inner panels: about 18 px.
- Photos in frames: radius 20 px; thumbnails circular.

### 5.2 Light mode: everything is a pill (owner rule)
- Every button, input, search field, select, tab, chip, badge, toggle, tooltip, toast, nav bar, list row, progress bar, and tile with a height up to about 120 px is a full pill.
- Containers taller than about 120 px would become ellipses with a full radius. They use a 48 to 56 px "soft capsule" radius, and **everything inside them is a pill**. The Needs attention card is a 52 px soft capsule; its inner panel is a 40 px soft capsule.
- No square corners and no small radii (4 to 12 px) anywhere in light mode.
- Text that can wrap to more than one line never sits in a full pill: use the soft capsule radius with at least 24 px padding.
- Horizontal padding in pills is at least 20 px. Focus rings follow the shape.
- Test with long text, large text sizes, and narrow widths.

### 5.3 Theme switching
Options: system (default), light, dark. Stored per user. Applied before first paint. Colours crossfade over 160 ms; no crossfade under reduced motion.

---

## 6. Component specifications (from the reference)

Each component lists anatomy, material, states, and data binding. All states exist in both themes.

### 6.1 Page background
See 4.2. The corner glow and ring halo are fixed to the layout, not to the scroll position. On pages without rings, keep the corner glow and drop the halo.

### 6.2 Navigation capsule
- Floating full pill, 60 px tall, 70 px from the left, right, and top edges. Glass per 4.3 (blur 18 px, hairline, top highlight, shadow).
- Left: the logo mark (4.9, 32 px) followed by the wordmark "Enderchest" in the display serif, cream. The wordmark is plain type with no gradient; the mark is the supplied logo.
- Centre: Dashboard, Inventory, Camera, Tasks, Savings, **only those that exist in the current phase** (3.3). 17 px sans, `--text`.
- Right: bell icon, then the user name pill.
- Sticky. On scroll it compacts slightly (height 60 to 52 px) with transform and opacity only.
- Narrow laptop windows (down to 1024 px): the capsule keeps its layout; the user name pill truncates first. A phone tab bar is deferred (section 21).

### 6.3 Nav item and active tab
- Inactive: text only, no fill. Hover: text to full `--text`, fill taupe at 8%, 160 ms. Pressed: fill 14%.
- Active: pill with glass fill (4.3) and a 1 px hairline, text `--text`. Exactly one active item.
- Focus: 2 px cream ring with 2 px offset that follows the pill.
- Each item is at least 44 px tall including padding.

### 6.4 LIVE badge
- Small pill on the Camera nav item: leading 6 px dot, then "LIVE". Fill `--clay-badge`, text `--on-clay`, 12 px medium.
- Visible only while a camera stream is actually running. Dot pulses at most once per second, and not at all under reduced motion.

### 6.5 Bell
- Thin-stroke bell icon (1.5 px stroke), 22 px, 44 px hit area. A count badge (clay pill) appears only when there are unresolved notifications and shows the real count. It opens the notification centre.

### 6.6 User name pill
- Glass pill with the user's chosen name in `--text`. Opens a menu: Settings, Theme, Backup, Sign out (sign out only in the website phase).
- Long names truncate with an ellipsis; full name in the menu.

### 6.7 Greeting block
- Left of the hero. Two lines of display serif, cream: "Good evening," then the user's name. The greeting word follows the local hour (morning, afternoon, evening, night).
- A muted one-line subtitle below, `--text-muted-page` (so it must sit on the plain page, never over the corner glow). It states one real fact about today (for example "3 items need attention today."). If nothing needs attention, say so plainly. Never a static slogan.
- Left aligned to the content inset (87 px at the reference width).

### 6.8 Health rings (the dominant element)
Anatomy (reference frame, centre (688, 382)):
- **Halo:** soft warm radial glow behind everything (4.2).
- **Outer hairline ring:** radius about 200 px, 1 px cream hairline, a faint glass fill outside the tracks.
- **Four progress rings** (outer to inner), pitch about 16 px, stroke about 12 px, round caps, at radii of approximately 180, 164, 148, and 132 px. Each ring has a **track** (glass tube: faint taupe fill at about 10% with two hairlines) and a bright **arc** (`--ring-arc`) with a soft cream glow (blur about 10 px at 25%).
- **Inner hairline circle:** radius about 112 px, 1 px cream hairline.
- **Centre text:** score in display serif (about 88 px), "Inventory health" below, "• 143 items" below that in muted text.

What each ring means (outer to inner), always computed from real data:
1. **Documented:** share of active items with a photo **and** a label marked printed. (A QR exists for every item automatically, so "has a QR" would always be true.)
2. **Located:** share of active items with a location.
3. **Fresh:** share of active items not past their expiry date; no date counts only if the user marked "no expiry"; unknown does not count.
4. **On time:** share of due tasks and prompts that are not overdue. With no tasks yet the ring is empty and the breakdown says "no tasks yet"; never 100%.

The score is a weighted average of the four values. Default weights 25 / 20 / 35 / 20 (open question O-004). Exact formulas, the exclusion of rings with no denominator, and the score rounding are in `DATA_MODEL.md` 3.4 and 3.5, which win over the one-line definitions above. The ring arc length equals each value exactly. The label reads "Inventory health" and "N items" in sentence case (D-033).

Behaviour:
- Arcs start at 12 o'clock and run clockwise. On first view they sweep from 0 to their value (`--dur-ring`, `--ease-out`, staggered 80 ms outer to inner), once per page visit. Re-render only animates the change in value.
- Tapping or pressing Enter on the rings opens a breakdown sheet (the four values with the exact items behind each).
- Hover or focus on one ring highlights it and dims the others to 60%.
- Accessible name: "Inventory health 82 out of 100. Documented 90, Located 75, Fresh 80, On time 85" with real values.
- Empty state (no items yet): empty tracks, score shows an em dash, and the label reads "Add your first item".

### 6.9 "Needs attention" card
- Frosted card per 4.3 (top-lit gradient, hairline, top highlight, blur 22 px, shadow). Title "Needs attention" in 19 px sans.
- Inside, a flat inner panel holds rows separated by hairline dividers.
- Row: item name followed by its status in parentheses, for example "Oat Milk (expires today)", "Greek Yogurt (2 days left)", "Baby Spinach (inspect)". The reference's vague "(expiring)" is retired. The words come from the server (`DATA_MODEL.md` 3.2 and `PAGES.md` P-11): expires today, 1 day left, N days left, expired, inspect, due today, N days overdue. Task rows ("Clean PC (due today)") use the same layout with **Mark done / Snooze**; the pill labels per kind are in `PAGES.md` P-11. Below the text, two pills side by side.
- Show at most three rows. If more exist, the last row becomes "View all 7" (a secondary pill) opening the notification centre. Sorted by urgency, soonest first.
- **Height fits the rows** (storyboard frame 3 shows a one-row card; decision D-027). The card keeps its top edge and its position; only its bottom edge moves. Row removal animates with opacity and a short transform; the card height change is the one allowed exception to "never animate height", done as a crossfade of the old and new card, not a live height tween.
- Empty state: "Nothing needs attention." with a small calm line below; the card keeps a one-row minimum height so the layout does not jump.
- A row leaves the card when the user acts on it. A snoozed row leaves until its snooze ends (confirmed: until `snoozed_until`, `DATA_MODEL.md` 3.8).

### 6.10 Pills and buttons
- **Primary pill:** fill `--cream-fill`, text `--on-cream`, 38 px tall, 17 px label, horizontal padding 24 px. Hover: fill lightens to `#FFF3E4`. Pressed: fill `#F2DFC9` and scale 0.98. Disabled: 40% opacity with a visible reason. Focus: 2 px cream ring with 2 px offset.
- **Secondary pill:** glass fill (4.3), hairline, text `--text`. Hover: fill +6%. Pressed: scale 0.98.
- **Row actions:** state-aware. Expiring item: "Use it" and "Snooze". Inspection task: "Inspect now" and "Snooze". Other actions (Mark expired, Discard, Edit) live in an overflow pill labelled "More" and on the item page.
- Labels say exactly what happens and stay consistent through the flow. Sentence case.
- Loading: the label stays, a small progress dot appears inside, the button is not disabled for more than the action takes. Failure restores the button and shows an inline reason.
- Light mode: primary pill becomes clay (`#9C5E43`) with cream text; secondary becomes a cocoa-tinted pill.

### 6.11 The road (14-day timeline)
- Full-bleed bar (27 px tall) per 4.3 with a dashed cream centre line. Above it on the left: "Next 14 days" (21 px, `--text`).
- Date ticks below the bar: day numbers, with the month shown on the first date ("16 Oct"). The first date is **today**, marked with a small filled dot. Weekend days are not specially coloured.
- Events: a notch on the bar at the event's date and a muted label beneath the date number (for example "Pantry Refill" below 18). Several events on one day collapse to a count chip ("2 tasks"); tapping opens the day.
- **Truck:** a flat SVG delivery truck, about 75 × 42 px, body `--truck-body`, cab `--truck-cab`, cream window, dark wheels. It rides on the bar and **parks at the next due event** (in the reference: at 18, "Pantry Refill"). Its position is computed from real dates. It never loops. **When the user resolves the event it is parked at, the truck drives to the next due event** (storyboard: Pantry Refill on the 18th, then Clean PC on the 21st, then Blade check on the 26th), wheels turning only while moving, within `--dur-scene`. If nothing is due in the window it parks at today's dot.
- **Savings pill:** a cream pill with the confirmed total saved this month, anchored to today's tick with a thin stem to the road. It must **never** appear on a future date. If it would overlap the truck (less than about 110 px apart) it shifts left or above to avoid overlap.
- Hover or focus on an event shows its details in a small glass tooltip; keyboard users can step through events.
- The road scrolls horizontally on mobile with snap to day.
- Empty state: the road still renders with today's dot and the text "No tasks or expiries in the next 14 days."

### 6.12 Other primitives (same language)
Build every other control from the same recipes so nothing feels foreign:
- **Inputs and search:** full pill (dark) with glass fill at the secondary-pill level, 1 px hairline, 44 px tall, label above in muted text, placeholder `--text-muted-glass`. Focus: hairline becomes cream at 70% plus 2 px ring. Error: brick border, icon, and message beneath.
- **Chips and filters:** pills at the secondary-pill level; selected chip uses the active-tab fill.
- **Toggles:** pill track with a cream thumb; on state uses the clay badge colour; off uses glass.
- **Sheets and modals:** frosted card material, radius 24 px (dark) or 52 px soft capsule (light), scrim of base colour at 60%.
- **Toasts:** glass pills at the bottom centre; one at a time; auto-dismiss after 5 seconds, longer if there is an Undo action.
- **Progress and skeletons:** pill-shaped bars and skeletons that match the final shape.
- **Icons:** one set, thin 1.5 px stroke (Lucide), 20 or 22 px, `--text`. No emoji, no filled blobs.

---

## 7. Applying the style to every screen

Every screen reuses the dashboard's grammar: the floating nav capsule at the top, a hero zone with serif type on the left, one dominant element, a frosted card for the secondary content, and (where time matters) the road at the bottom. One dominant element per screen.

| Screen | Dominant element | Built from |
|---|---|---|
| Dashboard | Health rings | Section 6 as specified |
| Camera and capture | Full-screen live view | Coach and detection chips as glass pills; shutter as a ring in `--ring-arc`; extracted-fields review as a frosted card with an inner panel of editable rows |
| Item detail | Large item photo in a frame | Frosted card with attribute rows, lifecycle pills, QR label preview, event timeline as a vertical road with the truck marking "now" |
| Inventory | Search pill and the item grid | Item tiles as frosted cards with a health dot; filter chips; virtualised list |
| Do I own this? | Ranked candidate stack | Candidate rows as inner-panel rows with a confidence pill and the stored photo; "Yes, I own it" primary pill, "Not the same" secondary pill |
| Notification centre | List in a frosted card | Rows identical to Needs attention rows, with the same state-aware pills |
| Tasks and maintenance | The road, larger, showing 30 days | Task rows as inner-panel rows, per-item maintenance toggle |
| Savings | Rupee total in the display serif | A frosted card list of confirmed savings; no estimates |
| Settings | Section cards | Pill inputs and toggles; theme selector as three pills |
| Trash, Labels, Review queue, Scan, Assistant, boot and not-found pages | One frosted card or list; the dominant element is the first thing the page exists for | Behaviour and layout in `PAGES.md` (P-07 to P-09, P-15 to P-17); built only from the same primitives and tokens; no new visual language |
| First run | Greeting and a single field | Serif headline, one pill input for the name, then a calm empty state inviting the first item |

Rules:
- Serif is used for hero type and large numbers only. Interface text is sans.
- Glass appears on the nav, one main card, and sheets. It does not appear on every element.
- The truck appears on the dashboard, the item timeline, the tasks road, and the save moment (10.3). It does not appear elsewhere.

---

## 8. Light mode: the same product, translated

Everything in sections 6 and 7 applies. Changes are materials only (4.4) and the pill rule (5.2). Specific translations:
- The nav capsule is a frosted cream pill on a cream page with the warm clay glow at the top-right.
- The rings become cocoa arcs over sand tracks with a very faint clay glow. Score in cocoa serif.
- The Needs attention card is a 52 px frosted cream capsule; the inner panel is a 40 px capsule; the action buttons are pills.
- Primary pills are clay with cream text; the road bar is sand with cocoa dashes; the savings pill is cocoa with cream text.
- Check contrast again for every pair; light mode has its own numbers.

---

## 9. Camera coach

One message at a time, driven only by real measurements (blur, brightness, glare, text found, text confidence, fields found). Never a static list of rules. Shown in a frosted pill near the bottom of the camera view, same material as the nav capsule.

| State | Trigger | Example message |
|---|---|---|
| No text found | OCR finds nothing | "I can't see a label yet. Try the side with printing." |
| Blurry | Sharpness below threshold | "Hold steady." |
| Too far | Text is too small | "Move a little closer to the label." |
| Glare | Large saturated highlight area | "Tilt it slightly to lose the glare." |
| Too dark | Low brightness | "It's dark here. Find some light." |
| Low confidence | Text found, confidence low | "Almost. Hold it still for a second." |
| Model found | Model or part number detected | "Got the model number. Show me the date." |
| Date found | Date detected | "Date spotted: 14 Mar 2027. Is that right?" |
| Complete | Fields captured | "Captured. 5 fields filled." |

Rules: 12 words or fewer; each message stays at least 1.2 seconds; changes are debounced; quiet when all is well; announced through a polite live region; can be turned off in settings. Detection chips (for example "Model number") appear as small glass pills on the image where the text was found. The shutter is a ring in `--ring-arc` that fills as the capture completes.

---

## 10. Motion system

### 10.1 Principles
Motion shows what changed or what is happening. It is fast, interruptible, and never blocks input. Below 60 fps on a modest laptop is a defect. Respect reduced motion everywhere.

### 10.2 Page and scroll
- **One orchestrated entrance** per screen on first view: nav capsule settles, hero text arrives, the rings sweep, the card arrives, then the truck rolls to its stop. Total under 1.4 seconds, skippable by any input. Not a fade-up on every section.
- **Scroll-linked road:** on long pages a slim road runs along the edge and the truck's position follows real scroll progress.
- **Nav compaction** on scroll (transform and opacity only).
- **Parallax:** only the background glow, with a tiny range (about 6%).
- **Counters** animate only when their real value changes.
- No scroll-jacking, no pinned sections, no infinite animation.
- Implementation: CSS scroll-driven animations where supported, with an IntersectionObserver fallback. At most one animation library (Motion, formerly Framer Motion), only where CSS cannot do it. About a dozen simultaneously animated elements at most.

### 10.3 The truck
Flat custom SVG, palette tokens only. Not an emoji, not stock art.

| Where | Behaviour |
|---|---|
| Dashboard road | Parks at the next due event; position from real data; never loops |
| Page load | Rolls in once per session, at most 700 ms |
| Saving a new item | A box slides onto the truck, the truck drives to the logo mark and wordmark in the nav, and the item count ticks up. Under 1.2 s, skippable, never blocks input |
| Scrolling | On long pages the edge-road truck tracks scroll progress |
| Idle | Still. Wheels turn only while it moves |
| Reduced motion | Static at its real position; changes crossfade |

### 10.4 Rings and win moments
- Ring sweep (6.8). When a value improves, the arc extends smoothly and a single soft glow pulse plays on that ring.
- Win moments (an expiring item used in time, a task completed, a milestone): the ring ticks up, one pulse, and on milestones the truck makes a short delivery. Understated. No confetti, no emoji, no guilt when something is missed.

### 10.5 Loading and feedback
Shape-matched skeletons. Optimistic updates with a visible rollback and reason on failure. Any wait over 300 ms gets explanatory text, not a bare spinner.

---

## 11. Engagement design

- The health rings, streak, and rupee savings are the hooks.
- Savings (for example "₹1,240 saved") count only after the user confirms they skipped the purchase and confirms the price. Never inflate or estimate silently.
- Add-item speed matters more than any visual reward. Target under 10 seconds for a typical item.
- No fake leaderboards, no manufactured urgency, no guilt copy.

---

## 12. Content and voice

- Warm, short, specific. Sentence case. Active voice. One job per piece of text.
- Buttons say exactly what happens: "Use it", "Snooze", "Save item", "Print label". The same name carries through the flow (button "Save item", toast "Item saved").
- Row format: "Item name (status)". Statuses are short and real: "expiring", "2 days left", "inspect".
- Errors say what happened and what to do, without apologising. Empty states invite the next action.
- Indian context: ₹, Indian digit grouping (₹1,24,500), dates like "16 Oct" and "14 Mar 2027", the user's local time zone.
- No exclamation marks as filler, no jokes in errors.

---

## 13. States and logic integrity

Every screen implements and is checked for:

| State | Required behaviour |
|---|---|
| Loading | Shape-matched skeleton; text if over 300 ms |
| Empty | Explains and offers the next action |
| Error | What happened, what to do, retry |
| Offline | App still works locally; Gemini features hidden or marked unavailable |
| Camera denied | Explains why, shows how to allow it, offers file upload and manual entry |
| Notifications denied | Explains the effect; the in-app notification centre keeps working |
| Partial data | Shows what exists; missing fields marked clearly |
| Very long text | Ellipsis in lists; full text on detail |
| 1,000 or more items | Virtualised and responsive |
| No search results | Says so, offers to clear filters |
| Slow network or slow OCR | Progress text and a cancel option |
| Unsaved changes | Guard before leaving |
| Mark used or expired | Undo for 10 seconds |

Integrity checks (automate them):
- Every on-screen number traces to data. Ring values equal their breakdown; the score equals the weighted average.
- Counts match list lengths. The notification bell count equals the unresolved notifications.
- Road positions come from real dates; the savings pill never sits on a future date; the first road date is today.
- The LIVE badge matches the real stream state. The greeting matches local time.
- Date maths is correct across time zones and daylight saving. Rupee formatting is correct and never negative.
- Double-submit is ignored. Back navigation never loses data silently.

---

## 14. Accessibility (WCAG 2.2 AA minimum)

- Text contrast 4.5:1 (3:1 for large text and UI boundaries) in both themes. Because glass is more opaque than the reference, re-check every pair against the composite colours in 4.3 and against real content.
- Visible keyboard focus everywhere, following each element's shape. Logical focus order.
- Everything reachable by keyboard. Touch targets at least 44 × 44 px.
- Respect reduced motion, reduced transparency (where supported), and forced-colours or high-contrast modes.
- Status is never colour alone.
- The rings expose their values as text; the road is also available as a list of upcoming events for screen readers.
- The camera coach uses a polite live region. Manual entry and file upload are always an alternative to the camera.
- Meaningful alt text for item photos; decorative elements hidden from assistive tech.

---

## 15. Responsive behaviour (laptop scope)

- Supported window width: **1024 px and up**, fluid between 1024 and wide screens. Below 1024 px nothing is promised in this phase; show the content without breaking, and do not build a phone layout.
- Reference layout from 1280 px: greeting left, rings centre, card right, road at the bottom.
- 1024 to 1279 px: the card moves below the rings at full content width; the road stays full bleed.
- Rings are an SVG with a fixed `viewBox` and scale smoothly; text inside scales with `clamp()`.
- Check both themes at 1024, 1280 and 1536 widths, including the light-mode pill rule: pills never clip text. Respect browser zoom up to 200%.

## 16. Performance budgets

- Initial route JavaScript at or under about 250 KB gzipped. Camera and heavy modules lazy-load.
- Interaction response under 100 ms. Animation at a steady 60 fps on a modest laptop.
- `backdrop-filter` is used only on the nav, the main card, and sheets. Never on list rows or the inner panel. Reduce blur radius on low-power devices.
- Thumbnails in lists, never full-size images.
- No runtime requests to third parties from the browser. Fonts and icons are bundled; Gemini calls go through the backend.

---

## 17. Implementation guidelines

- React functional components, small and commented, readable by someone with limited React experience.
- One tokens file; theme via `data-theme`; no hard-coded colours, radii, or durations in components.
- One icon set (Lucide). No emoji as icons.
- Structure: primitives (Pill, Button, Input, Toggle, Chip, Sheet, Toast, GlassCard, InnerPanel), patterns (BrandMark, NavCapsule, NavItem, LiveBadge, HealthRings, NeedsAttentionCard, Road, Truck, SavingsPill, CoachPill, ItemTile, QrLabel), screens.
- The rings and the truck are SVG components driven by real data props; no animation library is needed for them.
- Keep CSS specificity flat so section styles do not cancel each other.
- Test both themes and all breakpoints with screenshots before calling a screen done.

---

## 18. Reference-match gate and production checklist

### 18.1 Reference-match gate (Phase 5; a first pass of the shell in Phase 1)
With sample data matching the reference, render the dashboard at 1376 × 768 in dark mode and compare it to `docs/design/reference-dashboard.jpg` by overlay or side by side:
- Layout positions within about 12 px for the nav, rings, card, and road.
- Colours match the tokens in 4.1 and 4.3; glass reads about 10 points more opaque than the reference, with text contrast verified.
- Ring radii, arc style, and glow match; the truck matches in size and colour.
- Type styles match 4.6.
- The star watermark is absent. The savings pill is not on a future date.
- The logo is present in the nav and the tab, unmodified.
- The storyboard sequence (section 20) reproduces with test data: score, item count, card rows, truck position.
Record screenshots and measured differences in the evidence log.

### 18.2 Production checklist
A screen is done only when all of these are true:
- [ ] Looks right in dark mode (reference style) and light mode (all pills, no clipped text). Light mode stays marked "unapproved" until the owner approves a screenshot (O-005).
- [ ] No purple, no gradient clichés, none of the slop in 3.2.
- [ ] All states in section 13 exist and were checked.
- [ ] All numbers, dates, and positions trace to real data and are tested.
- [ ] Contrast verified with a tool in both themes, including muted text on glass.
- [ ] Keyboard-only run-through passes; focus is visible.
- [ ] Reduced motion and reduced transparency behave correctly.
- [ ] 60 fps on the owner's laptop within the performance budgets (the PC is a later check, D-011).
- [ ] Works offline and with Gemini disabled.
- [ ] Automated overflow and contrast checks at 1024, 1280 and 1536 px in both themes; the reviewer looks at 1280 px dark and light for each new or changed screen (`PROCESS.md` 4).
- [ ] No console errors or warnings.

Tie-in with phases: Phase 1 delivers tokens, theme switch, glass and pill primitives, nav capsule and the first reference check. Phase 5 runs the dashboard reference gate; Phase 8 runs the full pass. The Phase Verification Gate in `docs/PROCESS.md` applies to every phase that touches the interface.

---

## 19. Open decisions

See `DECISIONS.md` section E: O-001 corner glow strength, O-002 meaning of "10% more opaque", O-003 truck illustration approval, O-004 health score weights, O-005 light-mode approval, O-006 auto-start with Docker Desktop. Also open: whether the edge road shows on every long page or only on the dashboard.

---

## 20. UX storyboard (`docs/design/ux-states.png`)

Three frames of the same evening (the first date on the road is `16 Oct` in all three). Read as a sequence, they show what the product does when the user resolves things.

| | Frame 1 | Frame 2 | Frame 3 |
|---|---|---|---|
| Score | 82 | 86 | 91 |
| Item count | 142 | 142 | 141 |
| Needs attention rows | 3 | 3 | 1 (Baby Spinach) |
| Truck parked at | 18, "Pantry Refill" | 21, "Clean PC" | 26, "Blade check" |
| Savings pill | on 24 | on 24 | on 24 |

Behaviours the build must reproduce (with real data, in Phase 5):

1. **Completing a task** (Pantry Refill → Clean PC) raises the score through the "On time" ring and moves the truck to the next due event. The item count does not change.
2. **Using or closing items** (frame 2 → 3) lowers the item count, shrinks the Needs attention card to its remaining rows, raises the score again, and moves the truck on.
3. The score counts up and the arcs extend smoothly; one soft glow pulse per improved ring (10.4). No confetti.
4. The road window does not change within the same day; it rolls forward at local midnight with today as the first tick.

Defects in the storyboard that must **not** be copied: the pill on a future date in every frame, the star and the stray triangle, Title Case labels, and the differing item counts as hard-coded values. Frames 1 to 3 are drawn at slightly different scales (frame 3 is larger); the pixel sizes in section 4.7 come from the JPG only.

For tests, build these three states as fixtures in the test volume, so the reference-match gate can render each and compare.

---

## 21. Deferred to Phase 10 (locked, not built now)

Kept from v2 so nothing is lost:
- Tablet (768 to 1279 px): greeting on top, rings centred beneath, card below at full width, road below.
- Phone (under 768 px): bottom pill tab bar with a central camera button; greeting, rings (about 80% of screen width), card stacked, road as a horizontal snap-scroll strip; full-screen camera; safe-area insets; breakpoints 360 and 768; mobile type sizes in 4.6; road snap-to-day scrolling; invisible padding on pills for 44 px touch targets.
- Sign out entry in the user menu.
