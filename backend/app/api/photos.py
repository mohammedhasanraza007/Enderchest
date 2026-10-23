"""Item photos (API 2.6). Uploads are multipart (`security.MULTIPART_PATHS`, D-095)."""

import sqlite3

from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse

from .. import images
from ..boot.manager import BootManager
from ..schemas.items import ItemDetail, PhotoView, PrimaryPhoto
from ..services import photos as photos_service
from .deps import current_user_id, get_db, require_ok

router = APIRouter(prefix="/api/v1")
# Photo files never change once written (DATA_MODEL 2.7), so the browser may keep them.
IMMUTABLE = {"Cache-Control": "private, max-age=31536000, immutable"}


def read_upload(upload: UploadFile) -> bytes:
    """At most one byte over the limit is read, enough to refuse an oversize file."""
    return upload.file.read(images.MAX_UPLOAD_BYTES + 1)


@router.post("/items/{public_id}/photos", status_code=201)
def add_photo(public_id: str, image: UploadFile = File(...),
              manager: BootManager = Depends(require_ok),
              conn: sqlite3.Connection = Depends(get_db),
              user_id: int = Depends(current_user_id)) -> PhotoView:
    view = photos_service.add_item_photo(conn, manager.settings, user_id, public_id,
                                         read_upload(image))
    return PhotoView(**view)


@router.delete("/photos/{photo_id}", status_code=204)
def hide_photo(photo_id: str, conn: sqlite3.Connection = Depends(get_db),
               user_id: int = Depends(current_user_id)) -> Response:
    photos_service.hide_photo(conn, user_id, photo_id)
    return Response(status_code=204)


@router.put("/items/{public_id}/primary-photo")
def set_primary(public_id: str, body: PrimaryPhoto, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> ItemDetail:
    return ItemDetail(**photos_service.set_primary(conn, user_id, public_id, body.photo_id))


@router.get("/photos/{photo_id}/file", response_class=FileResponse)
def photo_file(photo_id: str, manager: BootManager = Depends(require_ok),
               conn: sqlite3.Connection = Depends(get_db),
               user_id: int = Depends(current_user_id)) -> FileResponse:
    path = photos_service.file_for(conn, manager.settings, user_id, photo_id, thumb=False)
    return FileResponse(path, media_type="image/jpeg", headers=IMMUTABLE)


@router.get("/photos/{photo_id}/thumb", response_class=FileResponse)
def photo_thumb(photo_id: str, manager: BootManager = Depends(require_ok),
                conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> FileResponse:
    path = photos_service.file_for(conn, manager.settings, user_id, photo_id, thumb=True)
    return FileResponse(path, media_type="image/jpeg", headers=IMMUTABLE)
