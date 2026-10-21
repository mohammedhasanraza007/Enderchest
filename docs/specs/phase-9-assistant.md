# Phase 9 — Assistant (narrow chat over the inventory)

**Read list:** `CLAUDE.md` sections 0, 5, 8 · this file · `API.md` 2.9, 2.16 · `PAGES.md` P-15 · `DATA_MODEL.md` 2.3, 3.2.
**Do not read:** design files beyond reusing existing primitives.
**Owner supplies:** a Gemini key. **Milestone:** E (optional).

## Design (fixed, so no session re-invents it)
Gemini never receives the inventory. It receives the conversation and **four read-only tools**; the backend executes them and returns results:
`search_items(q, category?, location?)`, `items_expiring(days)`, `count_items(filters)`, `get_item(public_id)`. Each tool returns at most 20 rows with names, categories, locations, quantities and expiry words only (no notes, no photos, no prices unless the question needs prices and `assistant_share_item_text` is on).
**Post-check:** every item name or `public_id` in the final answer must appear in that turn's tool results; otherwise the answer is replaced by "I couldn't find that in your inventory." The assistant cannot change data. A privacy line on the page states what is sent. Setting `assistant_share_item_text` (default off) controls whether item text leaves the machine at all; when off the page explains and the assistant is unavailable.

## Gate
1. Questions about real data return correct cited answers ("what expires this week", "do I have a 13 mm spanner").
2. A question about something absent never invents an item (tested with a deliberate trap).
3. Offline and bad-key states degrade with a clear message; no stack trace; no hang.
4. Verification confirms by inspecting the actual request bodies that no more than the tool rows are sent.
5. Verification pass.
