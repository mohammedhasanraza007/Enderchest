"""Photos to text lines: resize, read, tidy (Phase 3 spec, Build 2).

Runs in the heavy worker only. The photos are the stored, upright, metadata-free JPEGs; each is
scaled so its long edge is at most `LONG_EDGE` before reading.
"""

import math
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from . import engine

# The bake-off measures 1024 and 1600 (spec Build 1); 1600 keeps small print readable until then.
LONG_EDGE = 1600


@dataclass(frozen=True)
class Line:
    text: str
    confidence: float  # 0 to 1
    box: tuple[int, int, int, int]  # left, top, right, bottom in the resized photo
    height: float  # text height in pixels: the bigger the print, the likelier a name
    photo: int  # which of the draft's photos, from 0


@dataclass(frozen=True)
class Reading:
    lines: list[Line]
    engine: str
    ms: int


def _resized(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    image.thumbnail((LONG_EDGE, LONG_EDGE), Image.Resampling.LANCZOS)
    return image


def _line(raw: engine.RawLine, photo: int) -> Line:
    xs = [x for x, _ in raw.points]
    ys = [y for _, y in raw.points]
    top_left, top_right, bottom_right, bottom_left = raw.points
    # The mean of the two short sides, so a slightly tilted line is not measured too tall.
    height = (math.dist(top_left, bottom_left) + math.dist(top_right, bottom_right)) / 2
    return Line(" ".join(raw.text.split()), round(raw.confidence, 3),
                (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))), round(height, 1), photo)


def read_photos(paths: list[Path], threads: int) -> Reading:
    """Read each photo in turn; lines keep the engine's reading order within a photo."""
    started = time.perf_counter()
    lines: list[Line] = []
    for photo, path in enumerate(paths):
        lines.extend(_line(raw, photo) for raw in engine.recognise(_resized(path), threads)
                     if raw.text.strip())
    return Reading(lines, engine.label(), int((time.perf_counter() - started) * 1000))
