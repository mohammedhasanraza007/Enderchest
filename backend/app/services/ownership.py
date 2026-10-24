"""The desk-side "Do I own this?" check (Phase 6 spec, Build 2; API 2.14; P-13).

A photo and/or typed words become a query: the photo is read by the Phase 3 OCR pipeline and
embedded by the local model; the words give a name, a model number and a size. Every active item
is scored (`ownership_rules`) and at most five are proposed with a level and reasons. The check
writes nothing and keeps nothing: the query photo exists only in a temporary file for the
reading. Nothing leaves the machine; Gemini is not called (D-117) and never sees the inventory.
"""

import io
import json
import sqlite3
import uuid
from datetime import date

import numpy as np
from PIL import Image

from .. import heavy
from ..config import Settings
from ..integrations.embedding import model as embedding
from ..integrations.ocr.pipeline import Line, read_photos
from ..repositories import ownership as ownership_repo
from ..repositories import photos as photos_repo
from . import catalog, extraction, profile
from . import ownership_rules as rules
from .items import problem
from .photos import prepare

TEXT_MAX = 200


def _typed_lines(text: str) -> list[Line]:
    return [Line(" ".join(text.split()), 1.0, (0, 0, 0, 0), 1.0, 0)]


def _value(proposed: dict, field: str) -> str:
    found = proposed.get(field)
    return str(found["value"]) if found else ""


def _read(settings: Settings, jpeg: bytes) -> tuple[list[Line], str, np.ndarray | None]:
    """OCR lines, the engine label and the query vector. Runs in the heavy worker."""
    path = settings.upload_tmp_dir / f"check-{uuid.uuid4().hex}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(jpeg)
        reading = read_photos([path], settings.ocr_threads)
    finally:
        path.unlink(missing_ok=True)
    vector = None
    if embedding.available(settings.embedding_model):
        with Image.open(io.BytesIO(jpeg)) as image:
            vector = embedding.embed(image, settings.embedding_model)
    return reading.lines, reading.engine, vector


def _similarities(conn: sqlite3.Connection, user_id: int, vector: np.ndarray) -> dict[int, float]:
    """The best cosine per active item over its live photos' vectors."""
    best: dict[int, float] = {}
    for row in photos_repo.active_item_embeddings(conn, user_id, embedding.MODEL_NAME):
        cosine = float(np.dot(vector, embedding.from_blob(row["embedding"])))
        best[row["item_id"]] = max(cosine, best.get(row["item_id"], -1.0))
    return best


def build_query(lines: list[Line], text: str, today: date) -> tuple[rules.Query, dict]:
    """The query from read lines and typed words; typed words win where both give a field."""
    read = extraction.propose(lines, today)["proposed"] if lines else {}
    typed = extraction.propose(_typed_lines(text), today)["proposed"] if text else {}
    fields = {field: _value(typed, field) or _value(read, field)
              for field in ("name", "model", "size")}
    name = text or fields["name"]
    size_text = " ".join(filter(None, [fields["size"], text]))
    query = rules.Query(name=name, model=fields["model"], sizes=rules.sizes_in(size_text))
    return query, {field: value for field, value in fields.items() if value}


def check(conn: sqlite3.Connection, settings: Settings, user_id: int, image: bytes | None,
          text: str | None) -> dict:
    """POST /ownership/check."""
    text = " ".join((text or "").split())
    if len(text) > TEXT_MAX:
        raise problem("text", f"Keep the words to {TEXT_MAX} characters.")
    if not image and not text:
        raise problem("text", "Add a photo or type what you are looking for.")
    lines, engine, vector = [], None, None
    if image:
        processed = prepare(image)  # the same checks as every upload; nothing is stored
        lines, engine, vector = heavy.run(_read, settings, processed.jpeg)
    query, fields = build_query(lines, text, profile.local_today(conn, user_id))
    if vector is not None:
        query = rules.Query(query.name, query.model, query.sizes,
                            _similarities(conn, user_id, vector))
    rows = {row["id"]: row for row in ownership_repo.active_items(conn, user_id)}
    scored = [rules.score(query, {"id": row["id"], "name": row["name"],
                                  "attributes": json.loads(row["attributes"])},
                          row["category_name"]) for row in rows.values()]
    paths = catalog.location_paths(conn, user_id)
    candidates = [_view(rows[found.item_id], found, paths) for found in rules.rank(scored)]
    return {"query": {"lines": [line.text for line in lines], "fields": fields},
            "candidates": candidates, "engine": {"ocr": engine, "gemini_used": False}}


def _view(row: sqlite3.Row, found: rules.Candidate, paths: dict[int, list[str]]) -> dict:
    return {"public_id": row["public_id"], "name": row["name"],
            "primary_photo_id": row["primary_photo_id"],
            "location_path": paths.get(row["location_id"], []) if row["location_id"] else [],
            "quantity": row["quantity"], "price_paise": row["price_paise"],
            "score": found.score, "level": found.level, "reasons": found.reasons}


