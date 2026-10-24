"""The notification centre (API 2.12, PAGES P-11, D-104, D-107)."""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from ..schemas.lifecycle import (
    NotificationCount,
    NotificationPage,
    NotificationView,
    ReadAllDone,
    ShownResult,
    SnoozeBody,
)
from ..services import notifications as notifications_service
from .deps import current_user_id, get_db

router = APIRouter(prefix="/api/v1/notifications")


@router.get("")
def list_notifications(status: Literal["open", "snoozed", "resolved", "all"] = "open",
                       limit: int = Query(default=100, ge=1, le=200),
                       cursor: str | None = Query(default=None, max_length=100),
                       conn: sqlite3.Connection = Depends(get_db),
                       user_id: int = Depends(current_user_id)) -> NotificationPage:
    return NotificationPage(**notifications_service.list_notifications(
        conn, user_id, status, limit, cursor))


@router.get("/count")
def count(conn: sqlite3.Connection = Depends(get_db),
          user_id: int = Depends(current_user_id)) -> NotificationCount:
    return NotificationCount(**notifications_service.count(conn, user_id))


@router.post("/read-all")
def read_all(conn: sqlite3.Connection = Depends(get_db),
             user_id: int = Depends(current_user_id)) -> ReadAllDone:
    return ReadAllDone(updated=notifications_service.mark_all_read(conn, user_id))


@router.post("/{notification_id}/read", status_code=204)
def read(notification_id: int, conn: sqlite3.Connection = Depends(get_db),
         user_id: int = Depends(current_user_id)) -> Response:
    notifications_service.mark_read(conn, user_id, notification_id)
    return Response(status_code=204)


@router.post("/{notification_id}/snooze")
def snooze(notification_id: int, body: SnoozeBody, conn: sqlite3.Connection = Depends(get_db),
           user_id: int = Depends(current_user_id)) -> NotificationView:
    return NotificationView(**notifications_service.snooze(conn, user_id, notification_id,
                                                           body.option))


@router.post("/{notification_id}/dismiss")
def dismiss(notification_id: int, conn: sqlite3.Connection = Depends(get_db),
            user_id: int = Depends(current_user_id)) -> NotificationView:
    return NotificationView(**notifications_service.dismiss(conn, user_id, notification_id))


@router.post("/{notification_id}/shown")
def shown(notification_id: int, conn: sqlite3.Connection = Depends(get_db),
          user_id: int = Depends(current_user_id)) -> ShownResult:
    return ShownResult(claimed=notifications_service.claim_shown(conn, user_id, notification_id))
