# Phase 9 brief — Assistant (narrow chat over the inventory)

Written 2026-10-28 by the Phase 9 build session (chain step after `phase8v.zip`, D-091). Spec: `docs/specs/phase-9-assistant.md`; look: the owner's reference image (sent in chat 2026-10-28, described in `docs/design/reference-assistant.md`).

## What I will build
1. **Backend.** `POST /api/v1/assistant/chat` (API 2.16). Gemini gets the conversation and four read-only tools; the backend runs them on **active items only** and returns at most 20 rows per call with `public_id`, name, category, location path, quantity and the expiry word (DATA_MODEL 3.2). There are no notes, photos, prices or attributes. Tools: `search_items(q, category?, location?)`, `items_expiring(days)`, `count_items(q?, category?, location?, expiry?)`, `get_item(public_id)`. At most 4 tool rounds, then one call with tools off. The whole turn has a 45 s deadline.
2. **Post-check** (pure module, unit-tested). The answer is replaced by "I couldn't find that in your inventory." when any of these is true:
   - any `ENDR-` id in it is not in this turn's rows;
   - any name of the owner's items (any state, Trash included) appears in it but is not in this turn's rows, unless that word is part of a row's text or of the question;
   - a search or `get_item` ran and the turn found no rows at all.

   Row names in the answer become links (`segments`). `rows_checked` drives the "From your inventory · N items checked" line.
3. **Client.** `integrations/gemini/client.converse`, function calling over REST, the key in the header. The model's content (with any thought signature) goes back verbatim. Errors keep their plain words: offline, bad key, unknown model, limit.
4. **Frontend.** `/assistant` (P-15) as in the reference: an **Assistant** tab after Savings, a centred serif title, the privacy line with a Settings link, one glass card with cream question pills on the right and darker answer bubbles on the left, the item names as underlined links, the foot line, the honest miss, and a pill input "Ask about your things…" with a round cream ↗ send button. It covers every state:
   - unavailable (no key, or the assistant switched off), which explains and links to Settings;
   - empty, sending, the answer, and an error with Retry.

   The conversation lives in `sessionStorage`, so following an item link and coming back keeps it. "Start over" clears it. The Settings → Gemini section gains the "Use the assistant" switch (`assistant_share_item_text`, default off) with notes that say what leaves the laptop.
5. **Tests.**
   - Unit: post-check, row shaping, client parsing.
   - Integration: an in-process **recorded fake** Gemini server that records the real request bodies. It covers the gate questions, the trap, the bad key, offline, read-only and the request bodies.
   - Vitest: the helpers.
   - e2e: unavailable and offline states on the real backend. The conversation rendering uses `page.route` stubs (test code only).
   - The crawler, the contrast test and the shots include `/assistant`.
   - **Probe 28:** a `--network none` container with a recorder as Gemini. Only the tool rows leave, and nothing changes in the database.

## Conflicts and gaps (decided, logged as D-133 to D-136)
1. **Nav entry.** PAGES.md 1 puts "Ask Enderchest" in the name-pill menu. The owner's newer reference shows an **Assistant** tab after Savings. I follow the reference (D-132, D-133); PAGES.md is updated.
2. **Prices.** The spec allows prices "when the question needs them". Tools never send prices: deciding which questions need them would let Gemini choose what leaves the machine (D-134).
3. **Privacy line wording.** The reference says "Questions and the matching item rows are sent to Gemini. Nothing else leaves this laptop." The earlier answers in the chat are sent too, and photo reading (if on) sends other things. I use "This chat and the matching item rows are sent to Gemini. Notes, photos and prices stay on this laptop." (D-135).
4. **Assistant switch and Gemini mode.** The assistant needs a key and `assistant_share_item_text` on. `gemini_mode` keeps governing photo reading only, so its Off note becomes "never called for photos" (D-136).
5. **What the post-check cannot see.** It cannot see a made-up name that matches nothing in the inventory after a search that did find rows. The prompt forbids it, and the trap (a search with no rows) is always caught. Each turn must call its tools again; earlier turns' rows do not count ("that turn's tool results").

## Owner inputs
- **Gemini key:** gate 1 (real answers) and the real bad-key check are BLOCKED until it is set. Tests use a recorded fake only, never the product.
- **Save the reference image** you sent in chat as `docs/design/reference-assistant.png`; it is not on disk.
- Screenshot approval of `/assistant` (dark and light, 1280 and 1024).
