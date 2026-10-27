"""Request and response shapes for the assistant (API 2.16, Phase 9)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from .text import _has_control

MESSAGE_MAX = 2000
MESSAGES_MAX = 20


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def _content(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= MESSAGE_MAX:
            raise PydanticCustomError("message_length",
                                      "Write a question of 1 to 2000 characters.")
        if _has_control(value, allowed="\n\t\r"):
            raise PydanticCustomError("message_chars",
                                      "A question cannot contain control characters.")
        return value


class ChatRequest(BaseModel):
    """The conversation so far (the page keeps it); the server keeps nothing between turns."""

    model_config = ConfigDict(extra="forbid", strict=True)

    messages: list[ChatMessage] = Field(min_length=1, max_length=MESSAGES_MAX)

    @model_validator(mode="after")
    def _owner_first_and_last(self) -> "ChatRequest":
        if self.messages[0].role != "user" or self.messages[-1].role != "user":
            raise PydanticCustomError("messages_order",
                                      "The conversation must start and end with a question.")
        return self


class Segment(BaseModel):
    text: str
    public_id: str | None  # set when this piece is the name of an item the tools returned


class Cited(BaseModel):
    public_id: str
    name: str


class ChatReply(BaseModel):
    reply: str
    segments: list[Segment]
    cited: list[Cited]
    tools_used: list[str]
    rows_checked: int
