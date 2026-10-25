"""Camera coach frame answer (API 2.15). Boxes are fractions of the frame (D-121)."""

from typing import Literal

from pydantic import BaseModel


class FrameBox(BaseModel):
    x: float
    y: float
    w: float
    h: float
    conf: float
    kind: Literal["text", "model", "date"]


class FrameFields(BaseModel):
    model: str | None = None
    date: str | None = None  # ISO date, only when read with medium or high confidence


class FrameResult(BaseModel):
    text_found: bool
    confidence: float
    boxes: list[FrameBox]
    fields: FrameFields
