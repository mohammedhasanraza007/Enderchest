"""The image-embedding model: DINOv2-small on ONNX Runtime, CPU only (D-115).

An embedding is one vector per photo; photos of the same object point the same way, so the
cosine of two vectors says how alike two photos look. It only proposes candidates for the
ownership check and never decides (CLAUDE.md 6). DINOv2-small is provisional until the
measurement on the owner's photos; another model means replacing this module only. The model
file is baked into the image, loaded on first use and kept; it runs only in the heavy worker.
"""

import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

MODEL_NAME = "dinov2-small-fp32"  # stored in photos.embedding_model
SIZE = 224  # the crop the model was trained on
_RESIZE = 256  # shortest edge before the centre crop (the model's own preprocessing)
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)  # ImageNet statistics
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
THREADS = 2  # leaves the other cores to the API and the browser

_lock = threading.Lock()
_sessions: dict[Path, object] = {}


def _session(model_path: Path):
    with _lock:
        if model_path not in _sessions:
            import onnxruntime  # imported late: loading it costs memory the app may never need

            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = THREADS
            options.inter_op_num_threads = 1
            _sessions[model_path] = onnxruntime.InferenceSession(
                str(model_path), options, providers=["CPUExecutionProvider"])
        return _sessions[model_path]


def available(model_path: Path) -> bool:
    return model_path.is_file()


def pixels(image: Image.Image) -> np.ndarray:
    """The model's input: shortest edge 256, centre 224 crop, normalised, shape (1, 3, 224, 224)."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    scale = _RESIZE / min(image.size)
    image = image.resize((max(SIZE, round(image.width * scale)),
                          max(SIZE, round(image.height * scale))), Image.Resampling.BICUBIC)
    left, top = (image.width - SIZE) // 2, (image.height - SIZE) // 2
    image = image.crop((left, top, left + SIZE, top + SIZE))
    array = (np.asarray(image, dtype=np.float32) / 255.0 - _MEAN) / _STD
    return array.transpose(2, 0, 1)[np.newaxis]


def embed(image: Image.Image, model_path: Path) -> np.ndarray:
    """A unit-length float32 vector for one photo (the class token of the last layer)."""
    session = _session(model_path)
    outputs = session.run(None, {session.get_inputs()[0].name: pixels(image)})
    names = [output.name for output in session.get_outputs()]
    if "pooler_output" in names:
        vector = outputs[names.index("pooler_output")][0]
    else:
        vector = outputs[0][0, 0]  # last_hidden_state: the class token comes first
    return unit(np.asarray(vector, dtype=np.float32))


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


def to_blob(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype="<f4").tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype="<f4")
