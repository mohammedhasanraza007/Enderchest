"""The dashboard (API 2.13, PAGES P-12, D-113)."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from ..schemas.dashboard import Dashboard, RingBreakdown, Road
from ..services import dashboard as dashboard_service
from .deps import current_user_id, get_db

router = APIRouter(prefix="/api/v1/dashboard")


@router.get("")
def dashboard(conn: sqlite3.Connection = Depends(get_db),
              user_id: int = Depends(current_user_id)) -> Dashboard:
    return Dashboard(**dashboard_service.dashboard(conn, user_id))


@router.get("/rings/{ring}")
def ring_breakdown(ring: str, conn: sqlite3.Connection = Depends(get_db),
                   user_id: int = Depends(current_user_id)) -> RingBreakdown:
    return RingBreakdown(**dashboard_service.ring_breakdown(conn, user_id, ring))


@router.get("/road")
def road(days: int = Query(default=14, ge=1, le=30), conn: sqlite3.Connection = Depends(get_db),
         user_id: int = Depends(current_user_id)) -> Road:
    return Road(**dashboard_service.road_for(conn, user_id, days))
