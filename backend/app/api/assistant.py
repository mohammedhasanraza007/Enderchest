"""The assistant (API 2.16, Phase 9): one question in, one checked answer out. Read-only."""

import sqlite3

from fastapi import APIRouter, Depends

from ..boot.manager import BootManager
from ..schemas.assistant import ChatReply, ChatRequest
from ..services import assistant as assistant_service
from .deps import current_user_id, get_db, require_ok

router = APIRouter(prefix="/api/v1")


@router.post("/assistant/chat")
def chat(body: ChatRequest, manager: BootManager = Depends(require_ok),
         conn: sqlite3.Connection = Depends(get_db),
         user_id: int = Depends(current_user_id)) -> ChatReply:
    messages = [message.model_dump() for message in body.messages]
    return ChatReply(**assistant_service.chat(conn, user_id, manager.settings, messages))
