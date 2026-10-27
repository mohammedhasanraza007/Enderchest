# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase9.zip`, unzipped into `D:\Projects\Enderchest-phase-9v\Enderchest` on branch `phase-9-verify` (made from `phase-9`). Never unzip over an existing folder (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** verify Phase 9 next, then the final merge on `main`. Keep `D:\Projects\enderchest-chain-state.txt` current. If `start_session` is refused, message the top session "Enderchest phase 0 foundation" (local_c7445ab0-a8d2-4c45-8f9f-39bd2b0ce33f).
- Last built phase: **Phase 9** (the narrow Gemini assistant), build closed. **Verification: pending for phase 9.**
- Resume check: `git log --oneline -3` shows `pack: phase 9 build (phase9 zip): ...` on top.
- Brief: `docs/reviews/phase-9-brief.md`; decisions D-133 to D-136 are in `DECISIONS.md`.

## What Phase 9 is (for the verifier)
- Backend: `POST /api/v1/assistant/chat` (API 2.16). `services/assistant.py` (at most 5 Gemini calls, the last with tools off, 45 s), `assistant_tools.py` (4 read-only tools, active items, 20 rows, `row_view` = public_id, name, category, location, quantity, expiry word), `assistant_check.py` (post-check rules 1 to 3, `link` into `segments`), `integrations/gemini/client.converse`. 409 `gemini_disabled` with `details.reason` `no_key` or `assistant_off`.
- Frontend: `screens/Assistant.tsx` (P-15 per `docs/design/reference-assistant.md`), `lib/assistant.ts` (sessionStorage conversation, newest 20 messages), NavCapsule "Assistant" tab after Savings (D-133; tighter tabs under 1100 px), Settings → Gemini "Use the assistant" switch (`#assistant-switch`; Settings scrolls to a hash), photo-mode Off note "never called for photos" (D-136).
- Tests: unit `test_assistant_rules.py`, integration `test_assistant.py` with `backend/tests/gemini_fake.py` (recorded stand-in), vitest `assistant.test.ts`, e2e `assistant.spec.ts` and `phase9-shots.spec.ts`, `/assistant` in the crawler and routes-contrast, probe 28 (`assistant_probe.py`, `probe28.ps1`), `tests/live/test_assistant_live.py` (real Gemini, owner-run).

## Results of the build (`docs/logs/raw/phase-9/`)
- lint clean; unit 291 + vitest 119; integration 346; e2e 168 + 3; probes 1 to 28 (one log each, `probe-N.log`).
- Fixed while building: a crash on send (an effect returned `scrollIntoView`'s Promise), the nav overflow at 1024 px with six tabs.
- Looked at `test-results/shots-phase-9/` at 1280 dark and light and 1024: matches the reference description.

## Next steps (Phase 9 verification, fresh session)
1. Follow `D:\Projects\phase9v-next-prompt.txt`: probe list first in `docs/reviews/phase-9-verification.md`, then own probes, then re-run every suite into `docs/logs/raw/phase-9v/`.
2. Gate 4: inspect the actual request bodies (fake Gemini recordings and probe 28) for notes, prices, attributes, photos, unmatched items.
3. Verdict; then hand off to the final merge on `main`.

## Owner runs next
1. **Real Gemini check (you asked to test the real API):** put your key in Settings → Gemini or set `GEMINI_API_KEY` in your shell, then run:
   `docker run --rm -e GEMINI_API_KEY -v <folder>\Enderchest\backend:/app -w /app enderchest-tools:latest pytest -q -s tests/live`
   Phase 9 gates 1 and 3 (real answers) and the real bad-key message stay BLOCKED until then.
2. In the app: Settings → Gemini → paste the key, switch on **Use the assistant**, then open **Assistant** and ask "What's expiring this week?" and "Do I have a drill?".
3. Save the assistant reference image you sent in chat (2026-10-28) as `docs/design/reference-assistant.png`.
4. Screenshot approval of `/assistant` (`test-results/shots-phase-9/`, dark and light, 1280 and 1024).
5. Still open from earlier phases: `build.bat` then `run.bat`; Phase 8: 60 fps, light mode and truck approval; Phase 7 and 6 gates; screenshot approval for Phases 1 to 8; acceptance runs; `backup.bat`/`restore.bat` once; `test.bat bakeoff`.

## How to work on this laptop
- Ryzen 5 5500, 16 GB, RX 6600 LE: small CPU models only. Never touch the live stack (127.0.0.1:8470) except read-only GETs; the test stack is 8471.
- Quick backend loop: `MSYS_NO_PATHCONV=1 docker run --rm -v <repo>/backend:/app -w /app enderchest-tools:latest pytest …`.
- Run `test.bat` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`; one probe per `-Only`. A targeted e2e: `docker compose -f compose.test.yaml --profile e2e run --rm e2e npx playwright test <spec names>` after building `app` and `e2e`.
- Edit with the editor tools, never shell here-documents (F-035). Prettier for tests: pass `--config frontend/.prettierrc.json` only to new files (older specs use a wider style).
