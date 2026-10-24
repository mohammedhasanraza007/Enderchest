"""Image embeddings for saved photos (Phase 6 spec, Build 1; D-115).

Every live photo gets a vector from the current model; a photo with none, or with one from an
older model, is picked up by the background job (`scheduler/embeddings.py`), so new photos,
the backfill of older ones and a model change are the same work. Vectors are derived data: a
missing one only means the photo cannot add "looks similar" candidates yet.
"""

import sqlite3
from pathlib import Path

from PIL import Image

from .. import heavy
from ..config import Settings
from ..db.connection import write_transaction
from ..integrations.embedding import model as embedding
from ..logs import log_event
from ..repositories import photos as photos_repo

BATCH = 4  # photos per tick: small, so OCR jobs queued meanwhile wait only a moment


def _vector(path: Path, model_path: Path) -> bytes:
    with Image.open(path) as image:
        return embedding.to_blob(embedding.embed(image, model_path))


def fill(conn: sqlite3.Connection, settings: Settings, user_id: int, limit: int = BATCH) -> int:
    """Embed up to `limit` photos that need it; returns how many were written."""
    if not embedding.available(settings.embedding_model):
        return 0
    written = 0
    for row in photos_repo.needing_embedding(conn, user_id, embedding.MODEL_NAME, limit):
        path = settings.photos_dir / row["path"]
        try:
            blob = heavy.run(_vector, path, settings.embedding_model)
        except (OSError, ValueError) as exc:
            # An unreadable file keeps an empty marker so the job does not retry it every tick.
            log_event("warning", "embedding_failed", photo_id=row["id"], error=type(exc).__name__)
            blob = b""
        with write_transaction(conn):
            photos_repo.set_embedding(conn, user_id, row["id"], blob, embedding.MODEL_NAME)
        written += 1
    return written
