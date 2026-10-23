"""The photo upload pipeline (ARCHITECTURE 6, Uploads).

Every image is checked by its bytes (never its name or the browser's content type), turned
upright from its EXIF orientation, stripped of all metadata, re-encoded as JPEG (quality 92,
long edge at most 2560 px) and given a 320 px thumbnail. Files are named by UUID: the uploaded
name is never used, so it cannot reach the file system. Image work runs one at a time in a
single-worker executor so the API and /health stay responsive.
"""

import hashlib
import io
import os
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .config import Settings
from .fsutil import fsync_dir, fsync_path

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 60_000_000  # a 60 MP photo is plenty; larger is refused, never decompressed
LONG_EDGE = 2560
THUMB_EDGE = 320
JPEG_QUALITY = 92
THUMB_QUALITY = 85

Image.MAX_IMAGE_PIXELS = MAX_PIXELS
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="images")


class ImageRefused(Exception):
    """An upload that cannot become a photo; `code` is the API error code."""

    def __init__(self, code: str, status: int, message: str) -> None:
        super().__init__(message)
        self.code, self.status, self.message = code, status, message


@dataclass(frozen=True)
class Processed:
    jpeg: bytes
    thumb: bytes
    width: int
    height: int
    sha256: str


def sniff(data: bytes) -> str | None:
    """The image type from its first bytes: `jpeg`, `png`, `webp`, `heic`, or None."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"hevc", b"heim", b"heis",
                                                b"mif1", b"msf1", b"avif"):
        return "heic"
    return None


def check_size(data: bytes) -> None:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageRefused("payload_too_large", 413, "That photo is over 12 MB. Use a smaller one.")
    if not data:
        raise ImageRefused("unsupported_media", 415, "That file is empty.")


def _encode(image: Image.Image, edge: int, quality: int) -> bytes:
    copy = image.copy()
    copy.info.clear()  # EXIF, ICC, comments: none of it is carried over
    copy.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    # No `exif=` argument: the new file carries no metadata at all.
    copy.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


def process(data: bytes) -> Processed:
    """Check and re-encode one upload. Raises ImageRefused with the API's code and message."""
    check_size(data)
    kind = sniff(data)
    if kind == "heic":
        raise ImageRefused("unsupported_media", 415,
                           "HEIC photos are not supported. Export the photo as JPEG and try again.")
    if kind is None:
        raise ImageRefused("unsupported_media", 415, "Use a JPEG, PNG or WebP photo.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as opened:
                opened.load()  # a truncated file fails here, before anything is written
                image = ImageOps.exif_transpose(opened)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageRefused("payload_too_large", 413, "That photo has too many pixels.") from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ImageRefused("unsupported_media", 415,
                           "That photo is damaged or incomplete. Try another copy.") from None
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        flat = Image.new("RGB", image.size, (255, 255, 255))  # transparency becomes white
        flat.paste(image, mask=image.getchannel("A"))
        image = flat
    elif image.mode != "RGB":
        image = image.convert("RGB")
    jpeg = _encode(image, LONG_EDGE, JPEG_QUALITY)
    width, height = Image.open(io.BytesIO(jpeg)).size
    return Processed(jpeg, _encode(image, THUMB_EDGE, THUMB_QUALITY), width, height,
                     hashlib.sha256(jpeg).hexdigest())


def process_in_executor(data: bytes) -> Processed:
    return _executor.submit(process, data).result()


def _write_atomic(content: bytes, tmp_dir: Path, final: Path) -> None:
    """Write beside nothing the backup reads, flush, then rename into place (same volume)."""
    partial = tmp_dir / f"{final.name}.partial"
    with partial.open("wb") as handle:
        handle.write(content)
    fsync_path(partial)
    os.replace(partial, final)
    fsync_dir(final.parent)


@dataclass(frozen=True)
class Stored:
    id: str
    path: str  # relative to photos/
    thumb_path: str  # relative to thumbs/


def store(settings: Settings, processed: Processed) -> Stored:
    """Write the photo and its thumbnail. The caller then writes the row (DATA_SAFETY 4)."""
    photo_id = str(uuid.uuid4())
    name = f"{photo_id}.jpg"
    settings.upload_tmp_dir.mkdir(parents=True, exist_ok=True)
    _write_atomic(processed.jpeg, settings.upload_tmp_dir, settings.photos_dir / name)
    _write_atomic(processed.thumb, settings.upload_tmp_dir, settings.thumbs_dir / name)
    return Stored(photo_id, name, name)


def remake_thumb(settings: Settings, original: Path, target: Path) -> None:
    """Make a missing thumbnail again from its photo (after a restore, thumbnails are rebuilt)."""

    def work() -> bytes:
        with Image.open(original) as opened:
            opened.load()
            return _encode(opened.convert("RGB"), THUMB_EDGE, THUMB_QUALITY)

    settings.upload_tmp_dir.mkdir(parents=True, exist_ok=True)
    _write_atomic(_executor.submit(work).result(), settings.upload_tmp_dir, target)


def discard(settings: Settings, stored: Stored) -> None:
    """Remove files whose row was never written (the transaction failed): nothing points at them."""
    (settings.photos_dir / stored.path).unlink(missing_ok=True)
    (settings.thumbs_dir / stored.thumb_path).unlink(missing_ok=True)
