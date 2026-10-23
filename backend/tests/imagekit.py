"""Images made in memory for upload tests. Regression tools only, never gate evidence (D-056)."""

import io

from PIL import Image

ORIENTATION = 0x0112
GPS_INFO = 0x8825
ARTIST = 0x013B


def jpeg(width: int = 640, height: int = 480, *, rotated: bool = False,
         colour: tuple[int, int, int] = (180, 120, 60)) -> bytes:
    """A JPEG with metadata that the pipeline must drop; `rotated` sets EXIF orientation 6."""
    image = Image.new("RGB", (width, height), colour)
    exif = Image.Exif()
    exif[ARTIST] = "Owner Name"
    exif[GPS_INFO] = {1: "N", 2: (12.0, 58.0, 0.0)}
    if rotated:
        exif[ORIENTATION] = 6  # "rotate 90° clockwise to display"
    out = io.BytesIO()
    image.save(out, format="JPEG", exif=exif, comment=b"private note")
    return out.getvalue()


def png_with_alpha(width: int = 200, height: int = 100) -> bytes:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def webp(width: int = 300, height: int = 300) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (20, 90, 40)).save(out, format="WEBP")
    return out.getvalue()


def heic_header() -> bytes:
    """The first bytes of an iPhone HEIC file; enough for the type check to recognise it."""
    return b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 64


def truncated_jpeg() -> bytes:
    data = jpeg(1200, 900)
    return data[: len(data) // 2]
