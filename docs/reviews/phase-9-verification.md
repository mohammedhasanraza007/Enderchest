# Phase 9 verification — Assistant (narrow chat over the inventory)

Fresh session, 2026-10-28, branch `phase-9-verify`, on the code of `phase9.zip` (`47326aa`). Builder and verifier are the same model family: read sceptically. Spec: `docs/specs/phase-9-assistant.md` (gates 1 to 5); look: `docs/design/reference-assistant.md`.

## Probe list (written before reading the Phase 9 code or running anything)
1. **Gate 4, what leaves the laptop.** Read the actual request bodies the recorded fake (`backend/tests/gemini_fake.py`) and probe 28 capture: no notes, prices, attributes, photo paths or bytes, no item that the tools did not return (unmatched, trashed, disposed, other user), no settings or key in the body; the system prompt holds no inventory. Seed every one of those fields with a marker string and grep the bodies for it.
2. **Forged history.** The client sends the conversation. Can it smuggle a fake "model" turn or a function result (fake rows) that the post-check then trusts, or a role other than user/model? Earlier turns' rows must not count.
3. **Post-check rules.** Replaced: an unknown `ENDR-` id (also lower case); an owned name (Trash included) outside the rows; a search or `get_item` with no rows. Kept: a word that is in the question (exemption); "nothing expires" after `items_expiring` returns no rows. Edge cases: case, substrings (owned "Pen" against "open"), regex characters in names (`C++`, brackets), an empty answer.
4. **No tool call at all.** Gemini answers from imagination without calling a tool ("Yes, you have a red drill in the garage"): is the invention caught or forced through a tool?
5. **Read-only.** No write path from `/assistant/chat`: database bytes or row counts and the audit log unchanged after many turns; an unknown function name from Gemini (`delete_item`) does nothing and does not crash; tool arguments with `%`, `_`, `'` and huge or negative `days` do not crash or leak.
6. **Disabled reasons.** 409 `gemini_disabled` with `details.reason` `no_key` and `assistant_off` (and which wins when both); `gemini_mode` Off for photos does not switch the assistant off (D-136).
7. **Limits.** 20 messages and 2000 characters: 20 and 2000 accepted, 21 and 2001 rejected with the one error shape; empty or whitespace message; last message not from the owner.
8. **Failure modes.** Offline, bad key, unknown model, rate limit: a clear message, no stack trace, no key in the reply or the logs; a model that keeps calling tools stops after 5 calls; a slow model hits the 45 s deadline; one slow turn does not freeze the rest of the API (one worker).
9. **Web-page hardening.** A cross-origin POST to `/assistant/chat` is refused like every other write (ARCHITECTURE 9); logs never hold the question text.
10. **Page states** at 1280 dark and light and 1024 against `reference-assistant.md`: unavailable, empty, sending, answer with links and the foot line, honest miss, error with Retry; only DESIGN tokens; star and gold glow not copied.
11. **Nav at 1024, 1280, 1536:** six tabs fit, no wrap, no page overflow; Assistant after Savings.
12. **Conversation in `sessionStorage`:** survives following an item link and coming back and a reload; Start over clears it; only the newest 20 kept; a corrupt stored value does not break the page.
13. **Settings switch:** "Use the assistant" persists, defaults off, the key field is there; `/settings#assistant-switch` from the unavailable state lands on the switch.
14. **Reality audit:** the fake is test-only (no product import); grep the Phase 9 diff for mock, fake, stub, TODO; the crawler finds no dead control on `/assistant`; empty database shows the honest state.
