# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase9-2.zip`, unzipped into `D:\Projects\Enderchest-phase-9-2\Enderchest` on branch `phase-9` (D-091). This is a **checkpoint of the Phase 9 build, part 1 done**: continue it and do not restart it. Never unzip over an existing folder (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** build Phase 9, a fresh session verifies it, then the final merge on `main`. Keep `D:\Projects\enderchest-chain-state.txt` current. If `start_session` is refused, message the top session "Enderchest phase 0 foundation" (local_c7445ab0-a8d2-4c45-8f9f-39bd2b0ce33f).
- Last built phase: **Phase 8**, verified PASS WITH NOTES. Phase 9 build: **in progress**.
- Resume check: `git log --oneline -3` shows `pack: phase 9 build checkpoint (phase9-2 zip)` on top.
- Brief: `docs/reviews/phase-9-brief.md` (decisions D-133 to D-136 are described there; they are **not yet written into DECISIONS.md**).

## Done in part 1 (commits 85dd516, c08150c, 33eec3f)
- Backend complete:
  - `services/assistant.py` (loop: at most 5 rounds, the last with tools off, 45 s per turn);
  - `assistant_tools.py` (4 read-only tools, active items only, 20 rows, row = public_id, name, category, location, quantity, expiry word);
  - `assistant_check.py` (post-check rules 1 to 3, `link` into segments);
  - `integrations/gemini/client.converse`, `function_calls`, `answer_text`;
  - `schemas/assistant.py`; `api/assistant.py` (router in `main.py`); `items_repo.names` and the `ItemQuery` expiry `within`.
- The response adds `segments` and `rows_checked` to API 2.16. A 409 `gemini_disabled` carries `details.reason` `no_key` or `assistant_off`.
- Tests: `backend/tests/gemini_fake.py` (recorded stand-in that records request bodies) and `tests/integration/test_assistant.py` (13 tests, green). `tests/live/test_assistant_live.py` runs the real Gemini, owner-run, and skips without `GEMINI_API_KEY`.

## Next steps (part 2), in this order
1. Unit tests: `backend/tests/unit/test_assistant_rules.py` (check and link rules, the substring and question exemptions, `row_view`, `converse` and parsing with `httpx.MockTransport`).
2. `test.bat types`; commit `openapi.json` and `schema.d.ts`; add `api.assistantChat` to `endpoints.ts`.
3. Frontend:
   - `screens/Assistant.tsx` (P-15) per the owner's reference: centred serif title; privacy line "This chat and the matching item rows are sent to Gemini. Notes, photos and prices stay on this laptop." with a Settings link; one glass card with cream right-aligned question pills and darker left answer bubbles (16 px radius), segments with `public_id` as underlined links to `/items/:id`, `white-space: pre-line`; "From your inventory · N items checked" when `rows_checked > 0`; a pill input "Ask about your things…" with a round cream ↗ send button.
   - States: unavailable (no key, or switch off: explain and link to Settings, no input), empty, sending (input disabled), error with Retry.
   - The conversation lives in `sessionStorage` (`lib/assistant.ts`, try/catch) with "Start over"; send the last 20 messages, starting with a question.
   - Route `/assistant`; NavCapsule "Assistant" after Savings (check 1024 px).
   - GeminiSection: Toggle "Use the assistant" (`assistant_share_item_text`) with on/off notes; the mode Off note becomes "never called for photos".
   - Vitest for `lib/assistant.ts`.
4. e2e `tests/e2e/assistant.spec.ts`: unavailable states and offline with Retry on the real backend; the conversation through `page.route` stubs (links, foot line, miss, keyboard).
5. Add `/assistant` to the crawler, contrast and shots specs.
6. Probe 28 (`assistant_probe.py` plus `probe28.ps1`, like probe 24: `--network none`, a recorder scripting a function call; only the rows leave; the database is unchanged). Then `run-probes` 1..28.
7. Docs:
   - D-133 to D-136 into DECISIONS.md;
   - API.md 2.16 (`segments`, `rows_checked`, the reasons);
   - PAGES.md 1 and P-15 (the nav tab);
   - CODE_MAP;
   - the evidence log.
8. Run all the suites into `docs/logs/raw/phase-9/`, look at the shots (1280 dark and light, 1024), close the build, zip `phase9.zip`, then hand off the verification (prompt step 9).

## Owner runs next
1. **Real Gemini check (owner asked to test the real API):** set `GEMINI_API_KEY` in your shell, then run:
   `docker run --rm -e GEMINI_API_KEY -v D:\Projects\Enderchest-phase-9-2\Enderchest\backend:/app -w /app enderchest-tools:latest pytest -q -s tests/live`
   Phase 9 gates 1 and 3 (real) stay BLOCKED until then.
2. Save the assistant reference image you sent in chat (2026-10-28) as `docs/design/reference-assistant.png`.
3. Still open from earlier phases: `build.bat` then `run.bat`; Phase 8: 60 fps, light mode and truck approval; Phase 7 and 6 gates; screenshot approval for Phases 1 to 8; acceptance runs; `backup.bat`/`restore.bat` once; `test.bat bakeoff`.

## How to work on this laptop
- Ryzen 5 5500, 16 GB, RX 6600 LE: small CPU models only. Never touch the live stack (127.0.0.1:8470) except read-only GETs; the test stack is 8471.
- Quick backend loop: `MSYS_NO_PATHCONV=1 docker run --rm -v <repo>/backend:/app -w /app enderchest-tools:latest pytest …`.
- Run `test.bat` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`; one probe per `-Only`.
- Edit with the editor tools, never shell here-documents (F-035).
