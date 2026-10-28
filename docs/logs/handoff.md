# handoff.md — The memory between chats

Read by every new chat right after `CLAUDE.md` section 0. Rewrite it at the end of every chat; keep it under 60 lines. The chat's own entry goes in `sessions.md`.

## Resume here
- Zip: `phase9v.zip`, unzipped into `D:\Projects\Enderchest-final\Enderchest` on branch `main` (created from `phase-9-verify`, which carries every phase). Never unzip over an existing folder (D-067).
- **Chain of sessions, no human in the loop (D-091, D-097):** the next and last step is the **final merge on `main`**: the delivery-video comparison (owner, 2026-10-28), rebuild, every suite, bug sweep, then "status: done". Keep `D:\Projects\enderchest-chain-state.txt` current. If `start_session` is refused, message the top session "Enderchest phase 0 foundation" (local_c7445ab0-a8d2-4c45-8f9f-39bd2b0ce33f).
- Last built phase: **Phase 9** (the narrow Gemini assistant). **Verification: done for phase 9, PASS WITH NOTES** (`docs/reviews/phase-9-verification.md`).
- Resume check: `git log --oneline -3` shows `pack: phase 9 verification (phase9v zip): ...` on top.

## What the Phase 9 verification changed
- D-137: the first Gemini step of a turn must call a tool (`ANY`); the post-check replaces an answer from a turn with no tool call (`no_tool`). `services/assistant.py`, `services/assistant_check.py`.
- `integrations/gemini/client.converse` refuses content that cannot go back as strict JSON (NaN, Infinity): 502 in plain words, not a 500.
- `frontend/src/lib/assistant.ts`: a damaged stored conversation starts empty instead of crashing the page.
- New tests: `backend/tests/unit/test_phase9_verification_rules.py`, `backend/tests/integration/test_phase9_verification.py`, `tests/e2e/phase9-verification.spec.ts`. Failure kinds F-043 to F-045.
- Notes left (minor): N1 lexical post-check limit; N2 privacy line wording (owner's call, D-135); N3 word search matches attribute values; N4 bare 8-character ids not checked; N5 selected tab is the shell's pill, not cream.

## Results (`docs/logs/raw/phase-9v/`)
- lint clean; unit 296 + vitest 120; integration 359; e2e 179 + 3; probes 1 to 28 (one log each, all PASS). Shots looked at: `raw/phase-9v/shots/`.

## Next steps (final merge, fresh session)
1. Follow `D:\Projects\final-next-prompt.txt`.
2. Delivery video: the study and frame sheets are in the shared notes folder (`delivery-video-study.md`, `delivery-video/`); compare with `Delivery.tsx`, fix the gaps with D-lines and tests.
3. Rebuild, every suite into `docs/logs/raw/final/`, bug sweep of the verification notes, zip `final.zip`, chain "done", delete the keeper task, ask the owner to run /design-sync.

## Owner runs next
1. **Real Gemini check (you asked to test the real API):** put your key in Settings → Gemini or set `GEMINI_API_KEY` in your shell, then run:
   `docker run --rm -e GEMINI_API_KEY -v <folder>\Enderchest\backend:/app -w /app enderchest-tools:latest pytest -q -s tests/live`
   Phase 9 gates 1 to 3 with real answers and the real bad-key message stay BLOCKED until then.
2. In the app: Settings → Gemini → paste the key, switch on **Use the assistant**, then open **Assistant** and ask "What's expiring this week?" and "Do I have a drill?".
3. Save the assistant reference image you sent in chat (2026-10-28) as `docs/design/reference-assistant.png`.
4. Screenshot approval of `/assistant` (`docs/logs/raw/phase-9v/shots/`, dark and light, 1280 and 1024).
5. Decide the privacy line (note N2): keep "Notes, photos and prices stay on this laptop." or use "The assistant never sends notes, photos or prices."
6. Still open from earlier phases: `build.bat` then `run.bat`; Phase 8: 60 fps, light mode and truck approval; Phase 7 and 6 gates; screenshot approval for Phases 1 to 8; acceptance runs; `backup.bat`/`restore.bat` once; `test.bat bakeoff`.

## How to work on this laptop
- Ryzen 5 5500, 16 GB, RX 6600 LE: small CPU models only. Never touch the live stack (127.0.0.1:8470) except read-only GETs; the test stack is 8471.
- Quick backend loop: `docker run --rm -v <repo>/backend:/app -w /app enderchest-tools:latest pytest …` (from PowerShell; add `MSYS_NO_PATHCONV=1` from Git Bash).
- Run `test.bat` through `cmd /c "<full path>\test.bat <what> > <full path>\file 2>&1"`; one probe per `-Only`. Run a loop of suites inline in PowerShell: a script started with `-ExecutionPolicy Bypass` is refused by the permission classifier. A targeted e2e: `docker compose -f compose.test.yaml --profile e2e run --rm e2e npx playwright test <spec names>` after building `app` and `e2e` (specs are baked into the e2e image).
- Edit with the editor tools, never shell here-documents (F-035). Prettier for tests: pass `--config /repo/frontend/.prettierrc.json` only to new files (older specs use a wider style).
