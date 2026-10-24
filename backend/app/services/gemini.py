"""Gemini, optional and switchable (Phase 3 spec, Build 5; API 2.9; D-101, D-102).

The key lives in `/data/secrets/gemini.key` (mode 0600), outside the database and outside every
backup, and is never returned or logged (DATA_SAFETY 2). Mode `off` never calls; `ask` calls
only when the owner presses Improve with Gemini; `auto` calls after a local reading that found
neither a name nor a model. Photos are sent only when `share_images_with_gemini` is on; otherwise
only the text read on this machine is sent. Every value comes back as a proposal flagged
`unverified`; Gemini never decides anything.
"""

import io
import json
import os
import re
import sqlite3
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from .. import clock
from ..boot.manager import BootManager
from ..config import Settings
from ..db.connection import write_transaction
from ..errors import AppError
from ..fsutil import fsync_dir
from ..integrations.gemini import client
from ..logs import log_event
from ..repositories import categories as categories_repo
from ..repositories import drafts as drafts_repo
from ..repositories import photos as photos_repo
from . import inflight
from . import profile as profile_service
from .expiry_parser import parse_expiry

_KEY_SHAPE = re.compile(r"^[A-Za-z0-9_\-]{20,200}$")
SEND_EDGE = 1024  # photos sent to Gemini are scaled down: enough to read, less to upload
SEND_PHOTOS = 3
NOTHING_TO_SEND = ("There is nothing to send: no text was read from the photo, and sending "
                   "photos to Gemini is off in Settings.")
FAILED = "Gemini could not finish. Try again later."

# Network waits, not CPU work: kept apart from the heavy worker so a slow answer never holds up
# a local reading. One at a time, like everything else here.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gemini")


def key_path(settings: Settings) -> Path:
    return settings.secrets_dir / "gemini.key"


def read_key(settings: Settings) -> str | None:
    try:
        return key_path(settings).read_text(encoding="ascii").strip() or None
    except (FileNotFoundError, UnicodeDecodeError):
        return None


def save_key(settings: Settings, key: str) -> None:
    """Write the key with owner-only permissions, atomically (temporary file, then rename)."""
    key = key.strip()
    if not _KEY_SHAPE.match(key):
        raise AppError("validation_error", 422, "Some values are not valid.",
                       {"problems": [{"field": "key", "problem":
                                      "Paste the whole key: 20 to 200 letters, digits, "
                                      "dashes or underscores."}]})
    settings.secrets_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    final = key_path(settings)
    partial = final.with_name("gemini.key.partial")
    descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii") as handle:
        handle.write(key)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(partial, 0o600)
    os.replace(partial, final)
    fsync_dir(final.parent)


def remove_key(settings: Settings) -> None:
    key_path(settings).unlink(missing_ok=True)


def _config(conn: sqlite3.Connection, user_id: int, settings: Settings) -> dict:
    values = profile_service.get_settings(conn, user_id, settings.gemini_model_default)
    return {"mode": values["gemini_mode"],
            "model": values["gemini_model"] or settings.gemini_model_default,
            "share_images": values["share_images_with_gemini"]}


def status(conn: sqlite3.Connection, user_id: int, settings: Settings) -> dict:
    config = _config(conn, user_id, settings)
    return {"key_set": read_key(settings) is not None, "model": config["model"],
            "mode": config["mode"], "share_images": config["share_images"]}


def _usable(conn: sqlite3.Connection, user_id: int, settings: Settings) -> tuple[dict, str]:
    config = _config(conn, user_id, settings)
    key = read_key(settings)
    if config["mode"] == "off" or key is None:
        raise AppError("gemini_disabled", 409,
                       "Gemini is off or has no key. Turn it on in Settings → Gemini.")
    return config, key


def test_connection(conn: sqlite3.Connection, user_id: int, settings: Settings) -> dict:
    """A real call (API 2.9). Works in every mode except without a key."""
    key = read_key(settings)
    if key is None:
        raise AppError("gemini_disabled", 409, "Set a Gemini key first.")
    model = _config(conn, user_id, settings)["model"]
    try:
        elapsed = client.ping(settings.gemini_url, model, key)
    except client.GeminiError as failed:
        raise AppError("upstream_unavailable", 502, failed.message) from None
    return {"ok": True, "model": model, "latency_ms": elapsed}


def queue(conn: sqlite3.Connection, manager: BootManager, user_id: int, draft_id: str) -> None:
    """Improve with Gemini (P-07), or `auto` after a local reading. 409 when not allowed."""
    _usable(conn, user_id, manager.settings)
    if not inflight.claim(draft_id, "gemini"):
        return
    try:
        with write_transaction(conn):
            drafts_repo.set_reading(conn, user_id, draft_id, "gemini", "pending", None,
                                    clock.stamp())
        _executor.submit(_ask, manager, user_id, draft_id)
    except BaseException:
        inflight.release(draft_id, "gemini")
        raise


def after_local_reading(conn: sqlite3.Connection, manager: BootManager, user_id: int,
                        draft_id: str, result: dict) -> None:
    """`auto` mode: ask only when the photo gave neither a name nor a model (D-101)."""
    config = _config(conn, user_id, manager.settings)
    if config["mode"] != "auto" or read_key(manager.settings) is None:
        return
    if {"name", "model"} & set(result["proposed"]):
        with write_transaction(conn):
            drafts_repo.set_reading(conn, user_id, draft_id, "gemini", "skipped", None,
                                    clock.stamp())
        return
    queue(conn, manager, user_id, draft_id)


def _ask(manager: BootManager, user_id: int, draft_id: str) -> None:
    """The job, in the Gemini worker. Any failure becomes `failed` with a plain message."""
    conn = None
    try:
        conn = manager.open_connection()
        config, key = _usable(conn, user_id, manager.settings)
        row = drafts_repo.get(conn, user_id, draft_id)
        ocr = json.loads(row["ocr_result"]) if row and row["ocr_result"] else {}
        text = "\n".join(line["text"] for line in ocr.get("lines", []))
        photos = _photos(manager.settings, conn, user_id, draft_id) if config["share_images"] \
            else []
        if not text and not photos:
            raise client.GeminiError(NOTHING_TO_SEND)
        values, elapsed = client.extract(manager.settings.gemini_url, config["model"], key,
                                         text, photos)
        result = {"model": config["model"], "ms": elapsed, "sent_photos": len(photos),
                  "values": values.model_dump(),
                  "proposed": proposals(conn, user_id, values)}
        state = "done"
        log_event("info", "gemini_done", draft_id=draft_id, ms=elapsed,
                  photos=len(photos), fields=sorted(result["proposed"]))
    except (client.GeminiError, AppError) as failed:
        result, state = {"error": failed.message}, "failed"
        log_event("warning", "gemini_failed", draft_id=draft_id, reason=failed.message)
    except Exception:
        result, state = {"error": FAILED}, "failed"
        log_event("error", "gemini_failed", draft_id=draft_id, trace=traceback.format_exc())
    try:
        if conn is not None:
            with write_transaction(conn):
                drafts_repo.set_reading(conn, user_id, draft_id, "gemini", state,
                                        json.dumps(result, ensure_ascii=False), clock.stamp())
    except Exception:
        log_event("error", "gemini_store_failed", draft_id=draft_id, trace=traceback.format_exc())
    finally:
        inflight.release(draft_id, "gemini")
        if conn is not None:
            conn.close()


def _photos(settings: Settings, conn: sqlite3.Connection, user_id: int,
            draft_id: str) -> list[bytes]:
    sent = []
    for photo in photos_repo.live_for_draft(conn, user_id, draft_id)[:SEND_PHOTOS]:
        with Image.open(settings.photos_dir / photo["path"]) as opened:
            image = opened.convert("RGB")
        image.thumbnail((SEND_EDGE, SEND_EDGE), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=85)  # a fresh encode: no metadata goes out
        sent.append(buffer.getvalue())
    return sent


def _proposal(value, flags: list[str] | None = None, confidence: str = "medium",
              text: str | None = None) -> dict:
    found = {"value": value, "source": "gemini", "confidence": confidence,
             "flags": ["unverified", *(flags or [])]}
    if text is not None:
        found["text"] = text
    return found


def proposals(conn: sqlite3.Connection, user_id: int, values: client.GeminiValues) -> dict:
    """Gemini's answer as proposals (D-101): never `high`, always `unverified`."""
    found: dict[str, dict] = {}
    for field in ("name", "brand", "model", "size"):
        value = " ".join((getattr(values, field) or "").split())
        if value:
            found[field] = _proposal(value[:120])
    if values.category:
        wanted = values.category.strip().casefold()
        for row in categories_repo.list_all(conn, user_id):
            if row["name"].casefold() == wanted:
                found["category_id"] = _proposal(row["id"], text=values.category)
                break
    if values.expiry_text:
        reading = parse_expiry(values.expiry_text,
                               profile_service.local_today(conn, user_id))
        if reading.date is not None:
            flags = list(reading.flags)
            low = {"ambiguous", "unlabelled", "far_past", "far_future"} & set(flags)
            found["expiry_date"] = _proposal(reading.date.isoformat(), flags,
                                             "low" if low else "medium", values.expiry_text)
            if reading.alternatives:
                found["expiry_date"]["alternatives"] = [d.isoformat()
                                                        for d in reading.alternatives]
    if values.inspection_interval_days:
        found["inspection_interval_days"] = _proposal(values.inspection_interval_days,
                                                      ["suggested"])
    return found
