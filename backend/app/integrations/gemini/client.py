"""The Gemini REST call (`models/{model}:generateContent`), through `httpx` (D-102).

The key travels in the `x-goog-api-key` header, never in the URL, and is never logged. The label
answer must be the strict JSON the schema asks for; it is validated here, and anything else is an
error with a plain message. The assistant (Phase 9) uses `converse`, one function-calling step at
a time. Every failure is a `GeminiError`; nothing here raises anything else.
"""

import base64
import json
import time

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

TIMEOUT_SECONDS = 20.0

PROMPT = (
    "You read product labels for a personal home inventory. From the photo(s) and the text read "
    "from them, give: the product name as a shopper would say it; the brand; the model or part "
    "number exactly as printed; the size or net quantity with its unit; a one- or two-word "
    "category; the expiry text exactly as printed, including its label word (for example "
    "'EXP 14/03/2027' or 'Best before 6 months from MFG 03/2025'), never a manufacture or "
    "packing date; and, only for things that need upkeep (tools, appliances, electronics, "
    "safety gear), a sensible inspection interval in days. Use null for anything not visible. "
    "Never guess an expiry date.")

_TEXT = {"type": "STRING", "nullable": True}
SCHEMA = {
    "type": "OBJECT",
    "properties": {"name": _TEXT, "brand": _TEXT, "model": _TEXT, "size": _TEXT,
                   "category": _TEXT, "expiry_text": _TEXT,
                   "inspection_interval_days": {"type": "INTEGER", "nullable": True}},
    "required": ["name", "brand", "model", "size", "category", "expiry_text",
                 "inspection_interval_days"],
}


class GeminiValues(BaseModel):
    """What Gemini may answer; anything else is ignored, anything malformed refused."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=60)
    expiry_text: str | None = Field(default=None, max_length=200)
    inspection_interval_days: int | None = Field(default=None, ge=1, le=3650)


class GeminiError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _post(base_url: str, model: str, key: str, body: dict,
          transport: httpx.BaseTransport | None,
          timeout: float = TIMEOUT_SECONDS) -> tuple[dict, int]:
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(f"{base_url.rstrip('/')}/models/{model}:generateContent",
                                   headers={"x-goog-api-key": key}, json=body)
    except httpx.TimeoutException:
        raise GeminiError(f"Gemini did not answer within {round(timeout)} seconds. "
                          "Try again later.") from None
    except httpx.HTTPError:
        raise GeminiError("Gemini could not be reached. Check the internet connection; "
                          "everything else keeps working without it.") from None
    elapsed = int((time.perf_counter() - started) * 1000)
    if response.status_code != 200:
        raise GeminiError(_refusal(response, model))
    try:
        return response.json(), elapsed
    except ValueError:
        raise GeminiError("Gemini sent an answer that is not JSON.") from None


def _refusal(response: httpx.Response, model: str) -> str:
    status = response.status_code
    if status in (401, 403):
        return "Gemini did not accept the key. Check it in Settings."
    if status == 404:
        return f'Gemini does not know the model "{model}". Check the model name in Settings.'
    if status == 429:
        return "Gemini's limit for this key is used up for now. Try again later."
    if status >= 500:
        return "Gemini had a problem on its side. Try again later."
    try:
        detail = str(response.json()["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError):
        detail = f"HTTP {status}"
    if "API key" in detail:
        return "Gemini did not accept the key. Check it in Settings."
    return f"Gemini refused the request: {detail}"


def _answer_text(data: dict) -> str:
    block = (data.get("promptFeedback") or {}).get("blockReason")
    if block:
        raise GeminiError(f"Gemini declined to answer ({block}).")
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError):
        raise GeminiError("Gemini sent an empty answer.") from None


def extract(base_url: str, model: str, key: str, text: str, images: list[bytes],
            transport: httpx.BaseTransport | None = None) -> tuple[GeminiValues, int]:
    """Ask for the label's fields; `images` are JPEG bytes and may be empty (text only)."""
    parts: list[dict] = [{"text": f"{PROMPT}\n\nText read from the photo:\n{text or '(none)'}"}]
    parts += [{"inline_data": {"mime_type": "image/jpeg",
                               "data": base64.b64encode(image).decode("ascii")}}
              for image in images]
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json",
                                 "responseSchema": SCHEMA, "temperature": 0}}
    data, elapsed = _post(base_url, model, key, body, transport)
    try:
        return GeminiValues.model_validate(json.loads(_answer_text(data))), elapsed
    except (ValueError, ValidationError):
        raise GeminiError("Gemini's answer did not have the expected fields.") from None


def converse(base_url: str, model: str, key: str, *, system: str, contents: list[dict],
             tools: list[dict], calling: str = "AUTO", timeout: float = TIMEOUT_SECONDS,
             transport: httpx.BaseTransport | None = None) -> dict:
    """One step of a function-calling conversation (the assistant, Phase 9).

    Returns the model's content exactly as sent (`role` and `parts`), so it can go back in the
    next step unchanged: newer models attach a thought signature to their calls and refuse a
    conversation that drops it. `calling` is "AUTO" (tools allowed) or "NONE" (answer now).
    """
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "tools": [{"functionDeclarations": tools}],
            "toolConfig": {"functionCallingConfig": {"mode": calling}}}
    data, _ = _post(base_url, model, key, body, transport, timeout)
    block = (data.get("promptFeedback") or {}).get("blockReason")
    if block:
        raise GeminiError(f"Gemini declined to answer ({block}).")
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        raise GeminiError("Gemini sent an empty answer.") from None
    if not isinstance(parts, list) or not all(isinstance(part, dict) for part in parts):
        raise GeminiError("Gemini sent an answer in an unexpected shape.")
    return {"role": "model", "parts": parts}


def function_calls(content: dict) -> list[dict]:
    """The tool calls in a model content, as `{name, args, id}` (id only when Gemini sent one)."""
    calls = []
    for part in content["parts"]:
        call = part.get("functionCall")
        if isinstance(call, dict) and isinstance(call.get("name"), str):
            args = call.get("args")
            calls.append({"name": call["name"], "args": args if isinstance(args, dict) else {},
                          "id": call.get("id") if isinstance(call.get("id"), str) else None})
    return calls


def answer_text(content: dict) -> str:
    """The visible answer: the text parts, without any thought summaries."""
    return "".join(part["text"] for part in content["parts"]
                   if isinstance(part.get("text"), str) and not part.get("thought"))


def ping(base_url: str, model: str, key: str,
         transport: httpx.BaseTransport | None = None) -> int:
    """A real, tiny call for "Test connection"; returns the time it took in milliseconds."""
    body = {"contents": [{"role": "user", "parts": [{"text": "Reply with the word OK."}]}],
            "generationConfig": {"temperature": 0}}
    data, elapsed = _post(base_url, model, key, body, transport)
    _answer_text(data)
    return elapsed
