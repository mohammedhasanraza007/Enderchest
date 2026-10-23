"""QR labels and lookup (API 2.7). The QR holds only the public id, never a URL (CLAUDE.md 6)."""

import io
import sqlite3

import segno
from fastapi import APIRouter, Depends, Response

from ..schemas.items import ItemSummary, LabelPrinted, LabelPrintedDone
from ..services import items as items_service
from .deps import current_user_id, get_db
from .photos import IMMUTABLE

router = APIRouter(prefix="/api/v1")


def qr_svg(public_id: str) -> str:
    """Black on white, medium error correction, the quiet zone included. The SVG has a viewBox
    and no fixed size, so the label sheet sizes it in millimetres."""
    out = io.BytesIO()
    segno.make_qr(public_id, error="m").save(
        out, kind="svg", scale=1, border=4, dark="#000", light="#fff", xmldecl=False,
        omitsize=True, title=public_id)
    return out.getvalue().decode()


@router.get("/items/{public_id}/qr.svg", response_class=Response)
def qr(public_id: str, conn: sqlite3.Connection = Depends(get_db),
       user_id: int = Depends(current_user_id)) -> Response:
    row = items_service.item_row(conn, user_id, public_id)
    return Response(qr_svg(row["public_id"]), media_type="image/svg+xml", headers=IMMUTABLE)


@router.post("/items/label-printed")
def label_printed(body: LabelPrinted, conn: sqlite3.Connection = Depends(get_db),
                  user_id: int = Depends(current_user_id)) -> LabelPrintedDone:
    return LabelPrintedDone(updated=items_service.mark_labels_printed(conn, user_id,
                                                                      body.public_ids))


@router.get("/lookup/{code}")
def lookup(code: str, conn: sqlite3.Connection = Depends(get_db),
           user_id: int = Depends(current_user_id)) -> ItemSummary:
    return ItemSummary(**items_service.lookup(conn, user_id, code))
