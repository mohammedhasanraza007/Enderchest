"""The assistant: a narrow chat over the inventory (Phase 9 spec; API 2.16; P-15).

Gemini gets the conversation and four read-only tools (`assistant_tools`), never the inventory.
Each turn: ask Gemini; while it calls tools, run them here and send back only their rows; the
first round must call a tool (an answer that never looked cannot be checked, D-137), at most four
rounds may call tools, the fifth must answer (tools off); the whole turn has 45 seconds.
Then the post-check (`assistant_check`) keeps the answer only if it names nothing the turn's tools
did not return. The assistant needs a key and the owner's "Use the assistant" switch
(`assistant_share_item_text`, default off; D-136). It cannot change data: nothing here writes.
"""

import sqlite3
import time

from ..config import Settings
from ..errors import AppError
from ..integrations.gemini import client
from ..logs import log_event
from ..repositories import items as items_repo
from . import assistant_check, assistant_tools
from . import gemini as gemini_service
from . import profile as profile_service

MAX_ROUNDS = 5  # round 1 must call a tool; rounds 2 to 4 may; round 5 has tools off and answers
TURN_SECONDS = 45.0
SYSTEM = (
    "You are the assistant inside Enderchest, the owner's personal home inventory. You answer "
    "questions about the owner's own things, and only from what the tools return in this turn. "
    "Rules: call a tool before every answer about items, even a follow-up, because earlier "
    "answers may be out of date. Never mention an item, id or detail the tools did not return "
    "in this turn, and write item names exactly as the tools give them. If the tools find "
    "nothing that answers the question, reply exactly: " + assistant_check.MISS + " "
    "You cannot change anything (add, edit, use up or delete items); say so if asked. Keep "
    "answers short and plain: one sentence, or a short list with one item per line such as "
    "'Oat Milk — expires today'. Do not show item ids. Do not give buying, safety or health "
    "advice.")


def _ready(conn: sqlite3.Connection, user_id: int, settings: Settings) -> tuple[str, str]:
    """The key and the model, or `gemini_disabled` with the reason the page explains."""
    key = gemini_service.read_key(settings)
    if key is None:
        raise AppError("gemini_disabled", 409,
                       "The assistant needs a Gemini key. Add one in Settings → Gemini.",
                       {"reason": "no_key"})
    values = profile_service.get_settings(conn, user_id, settings.gemini_model_default)
    if not values["assistant_share_item_text"]:
        raise AppError("gemini_disabled", 409,
                       'The assistant is off. Turn on "Use the assistant" in Settings → Gemini.',
                       {"reason": "assistant_off"})
    return key, values["gemini_model"] or settings.gemini_model_default


def _contents(messages: list[dict]) -> list[dict]:
    return [{"role": "user" if message["role"] == "user" else "model",
             "parts": [{"text": message["content"]}]} for message in messages]


def _response(call: dict, result: dict) -> dict:
    answer = {"name": call["name"], "response": result}
    if call["id"]:
        answer["id"] = call["id"]
    return {"functionResponse": answer}


def _calling(round_number: int) -> str:
    """Gemini's function-calling mode for a round: look first, then free, then answer."""
    if round_number == 1:
        return "ANY"
    return "NONE" if round_number == MAX_ROUNDS else "AUTO"


def _converse(settings: Settings, model: str, key: str, box: assistant_tools.Toolbox,
              messages: list[dict]) -> tuple[str, int]:
    """Run the tool rounds; returns Gemini's final text and the number of calls made."""
    system = f"{SYSTEM} Today is {box.today:%A %d %B %Y}."
    contents = _contents(messages)
    started = time.monotonic()
    for round_number in range(1, MAX_ROUNDS + 1):
        remaining = TURN_SECONDS - (time.monotonic() - started)
        if remaining < 1:
            break
        content = client.converse(settings.gemini_url, model, key, system=system,
                                  contents=contents, tools=assistant_tools.DECLARATIONS,
                                  calling=_calling(round_number),
                                  timeout=min(client.TIMEOUT_SECONDS, remaining))
        calls = client.function_calls(content)
        if not calls:
            text = client.answer_text(content)
            if not text.strip():
                raise client.GeminiError("Gemini sent an empty answer. Try again.")
            return text, round_number
        contents.append(content)
        contents.append({"role": "user",
                         "parts": [_response(call, box.run(call["name"], call["args"]))
                                   for call in calls]})
    raise client.GeminiError("Gemini did not finish its answer in time. Try a shorter "
                             "question, or try again later.")


def chat(conn: sqlite3.Connection, user_id: int, settings: Settings,
         messages: list[dict]) -> dict:
    """POST /assistant/chat. `messages` start and end with the owner's question (checked)."""
    key, model = _ready(conn, user_id, settings)
    box = assistant_tools.Toolbox(conn, user_id)
    started = time.perf_counter()
    try:
        text, rounds = _converse(settings, model, key, box, messages)
    except client.GeminiError as failed:
        log_event("warning", "assistant_failed", tools=box.found.tools,
                  rows=len(box.found.rows), reason=failed.message)
        raise AppError("upstream_unavailable", 502, failed.message) from None
    checked = assistant_check.check(text, box.found.rows, box.found.searched,
                                    items_repo.names(conn, user_id), messages[-1]["content"],
                                    looked=bool(box.found.tools))
    log_event("info", "assistant_answered", tools=box.found.tools, rows=len(box.found.rows),
              rounds=rounds, ms=int((time.perf_counter() - started) * 1000),
              replaced=checked.replaced)
    return {"reply": checked.reply, "segments": checked.segments, "cited": checked.cited,
            "tools_used": box.found.tools, "rows_checked": len(box.found.rows)}
