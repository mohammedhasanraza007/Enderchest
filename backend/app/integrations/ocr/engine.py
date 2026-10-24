"""The OCR engine: RapidOCR on ONNX Runtime, CPU only, English text (D-063, D-099).

RapidOCR is the provisional engine until the bake-off on the owner's photos (D-099); swapping it
means replacing this module only. Its detection, angle and recognition models ship inside the
`rapidocr` wheel, so the image never downloads anything at run time (D-021). The engine is loaded
on first use and kept: one copy, used only from the heavy worker.
"""

import threading
from dataclasses import dataclass
from importlib.metadata import version

from PIL import Image

_lock = threading.Lock()
_engine = None


@dataclass(frozen=True)
class RawLine:
    text: str
    confidence: float  # 0 to 1, as the engine reports it
    points: tuple[tuple[float, float], ...]  # the four corners of the text box


def label() -> str:
    """Engine name and version, kept with each reading so a later swap is visible."""
    return f"RapidOCR {version('rapidocr')}"


def _load(threads: int):
    global _engine
    with _lock:
        if _engine is None:
            from rapidocr import RapidOCR  # imported late: it loads ONNX Runtime and OpenCV

            _engine = RapidOCR(params={
                "Global.log_level": "error",
                "EngineConfig.onnxruntime.intra_op_num_threads": threads,
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            })
    return _engine


def recognise(image: Image.Image, threads: int) -> list[RawLine]:
    """Every text line the engine finds, in its reading order."""
    output = _load(threads)(image)
    if output.boxes is None:
        return []
    return [RawLine(str(text), float(score), tuple((float(x), float(y)) for x, y in box))
            for box, text, score in zip(output.boxes, output.txts, output.scores, strict=True)]
