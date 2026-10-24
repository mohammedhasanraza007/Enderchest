"""Reading a draft's photos with the local OCR engine (Phase 3 spec, Build 2; D-100, D-101).

A reading is queued in the heavy worker and the request returns at once (202); the confirm
screen polls the draft. A new draft is read as soon as it exists, and Re-read queues another.
The result keeps the lines, the proposals and the notes; the owner's fields are never touched
here (D-100). A reading that was queued when the app stopped shows as interrupted.
"""

import json
import sqlite3
import traceback
from dataclasses import asdict

from .. import clock, heavy
from ..boot.manager import BootManager
from ..db.connection import write_transaction
from ..integrations.ocr import pipeline
from ..logs import log_event
from ..repositories import drafts as drafts_repo
from ..repositories import photos as photos_repo
from . import extraction, inflight
from . import gemini as gemini_service
from . import profile as profile_service

MAX_PHOTOS = 3  # D-100: enough for a front and a printed date, without a long wait
FAILED = "The photo could not be read. Press Re-read, or fill in the fields yourself."
INTERRUPTED = "The reading stopped because the app restarted. Press Re-read."


def queue_local(conn: sqlite3.Connection, manager: BootManager, user_id: int,
                draft_id: str) -> None:
    """Mark the draft `pending` and queue its reading; a second request while queued is a no-op."""
    if not inflight.claim(draft_id, "ocr"):
        return
    try:
        with write_transaction(conn):
            drafts_repo.set_reading(conn, user_id, draft_id, "ocr", "pending", None, clock.stamp())
        heavy.submit(_read, manager, user_id, draft_id)
    except BaseException:
        inflight.release(draft_id, "ocr")
        raise


def _read(manager: BootManager, user_id: int, draft_id: str) -> None:
    """The job, in the heavy worker. Any failure becomes `failed` with a plain message."""
    conn = None
    try:
        conn = manager.open_connection()
        photos = photos_repo.live_for_draft(conn, user_id, draft_id)[:MAX_PHOTOS]
        paths = [manager.settings.photos_dir / photo["path"] for photo in photos]
        reading = pipeline.read_photos(paths, manager.settings.ocr_threads)
        today = profile_service.local_today(conn, user_id)
        result = {"engine": reading.engine, "ms": reading.ms, "photos": len(paths),
                  "lines": [asdict(line) for line in reading.lines],
                  **extraction.propose(reading.lines, today)}
        status = "done"
        log_event("info", "ocr_done", draft_id=draft_id, lines=len(reading.lines),
                  ms=reading.ms, fields=sorted(result["proposed"]))
    except Exception:
        result, status = {"error": FAILED}, "failed"
        log_event("error", "ocr_failed", draft_id=draft_id, trace=traceback.format_exc())
    try:
        if conn is None:
            return
        with write_transaction(conn):
            drafts_repo.set_reading(conn, user_id, draft_id, "ocr", status,
                                    json.dumps(result, ensure_ascii=False), clock.stamp())
        if status == "done":
            gemini_service.after_local_reading(conn, manager, user_id, draft_id, result)
    except Exception:
        log_event("error", "ocr_store_failed", draft_id=draft_id, trace=traceback.format_exc())
    finally:
        inflight.release(draft_id, "ocr")
        if conn is not None:
            conn.close()


def view(row: sqlite3.Row) -> dict:
    """The reading parts of a Draft (API 1, `Draft`): states, proposals, raw text, messages."""
    ocr = json.loads(row["ocr_result"]) if row["ocr_result"] else {}
    gemini = json.loads(row["gemini_result"]) if row["gemini_result"] else {}
    ocr_status, ocr_error = row["ocr_status"], ocr.get("error")
    if ocr_status == "pending" and not inflight.is_queued(row["id"], "ocr"):
        ocr_status, ocr_error = "failed", INTERRUPTED
    gemini_status, gemini_error = row["gemini_status"], gemini.get("error")
    if gemini_status == "pending" and not inflight.is_queued(row["id"], "gemini"):
        gemini_status, gemini_error = "failed", INTERRUPTED
    return {
        "ocr_status": ocr_status, "gemini_status": gemini_status,
        "proposed": combine(ocr.get("proposed", {}), gemini.get("proposed", {})),
        "raw_text": _raw_text(ocr.get("lines")),
        "ocr_error": ocr_error, "gemini_error": gemini_error,
        "read_notes": ocr.get("notes", []),
        "ocr_info": ({"engine": ocr["engine"], "ms": ocr["ms"], "photos": ocr["photos"]}
                     if "engine" in ocr else None),
        "gemini_values": gemini.get("values"),
    }


def combine(local: dict, gemini: dict) -> dict:
    """D-101: Gemini fills a field only where the photo reading has nothing or low confidence."""
    merged = dict(local)
    for field, proposal in gemini.items():
        if field not in merged or merged[field]["confidence"] == "low":
            merged[field] = proposal
    return merged


def _raw_text(lines: list[dict] | None) -> str | None:
    if lines is None:
        return None
    photos: dict[int, list[str]] = {}
    for line in lines:
        photos.setdefault(line["photo"], []).append(line["text"])
    return "\n\n".join("\n".join(texts) for _, texts in sorted(photos.items()))
