"""Lifecycle, tasks, maintenance and inspections (API 2.10, 2.11).

Every write is followed by a reconcile, so the bell and the notification centre show the change
at once (D-107).
"""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query

from ..idempotency import IdempotencyStore
from ..schemas.items import ItemDetail
from ..schemas.lifecycle import (
    InspectionCreate,
    InspectionDone,
    InspectionList,
    LifecycleDone,
    MaintenanceBody,
    ReactivateBody,
    TaskCreate,
    TaskDeleted,
    TaskDone,
    TaskList,
    TaskPatch,
    TaskView,
    UseBody,
)
from ..services import lifecycle as lifecycle_service
from ..services import notifications as notifications_service
from ..services import tasks as tasks_service
from .deps import current_user_id, get_db
from .items import get_idempotency

router = APIRouter(prefix="/api/v1")


# ---- lifecycle (2.10) -------------------------------------------------------------------------

@router.post("/items/{public_id}/use")
def use_item(public_id: str, body: UseBody | None = None,
             conn: sqlite3.Connection = Depends(get_db),
             user_id: int = Depends(current_user_id)) -> LifecycleDone:
    result = lifecycle_service.use(conn, user_id, public_id, (body or UseBody()).amount)
    notifications_service.after_write(conn, user_id)
    return LifecycleDone(**result)


@router.post("/items/{public_id}/mark-expired")
def mark_expired(public_id: str, conn: sqlite3.Connection = Depends(get_db),
                 user_id: int = Depends(current_user_id)) -> LifecycleDone:
    result = lifecycle_service.leave(conn, user_id, public_id, "expired")
    notifications_service.after_write(conn, user_id)
    return LifecycleDone(**result)


@router.post("/items/{public_id}/discard")
def discard_item(public_id: str, conn: sqlite3.Connection = Depends(get_db),
                 user_id: int = Depends(current_user_id)) -> LifecycleDone:
    result = lifecycle_service.leave(conn, user_id, public_id, "discarded")
    notifications_service.after_write(conn, user_id)
    return LifecycleDone(**result)


@router.post("/items/{public_id}/reactivate")
def reactivate_item(public_id: str, body: ReactivateBody | None = None,
                    conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> ItemDetail:
    item = lifecycle_service.reactivate(conn, user_id, public_id,
                                        (body or ReactivateBody()).quantity)
    notifications_service.after_write(conn, user_id)
    return ItemDetail(**item)


# ---- tasks (2.11) -----------------------------------------------------------------------------

@router.get("/tasks")
def list_tasks(scope: Literal["open", "due", "all", "done"] = "open",
               item: str | None = Query(default=None, max_length=40),
               conn: sqlite3.Connection = Depends(get_db),
               user_id: int = Depends(current_user_id)) -> TaskList:
    return TaskList(**tasks_service.list_tasks(conn, user_id, scope, item))


@router.post("/tasks", status_code=201)
def create_task(body: TaskCreate, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id),
                store: IdempotencyStore = Depends(get_idempotency),
                idempotency_key: str | None = Header(default=None)) -> TaskView:
    def work() -> TaskView:
        task = TaskView(**tasks_service.create_task(conn, user_id, body.model_dump()))
        notifications_service.after_write(conn, user_id)
        return task
    return store.run("POST /tasks", idempotency_key, work)


@router.patch("/tasks/{task_id}")
def change_task(task_id: int, body: TaskPatch, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> TaskView:
    task = tasks_service.change_task(conn, user_id, task_id, body.model_dump(exclude_unset=True))
    notifications_service.after_write(conn, user_id)
    return TaskView(**task)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> TaskDeleted:
    event_id = tasks_service.delete_task(conn, user_id, task_id)
    notifications_service.after_write(conn, user_id)
    return TaskDeleted(event_id=event_id)


@router.post("/tasks/{task_id}/done")
def task_done(task_id: int, conn: sqlite3.Connection = Depends(get_db),
              user_id: int = Depends(current_user_id)) -> TaskDone:
    result = tasks_service.complete_task(conn, user_id, task_id, "done")
    notifications_service.after_write(conn, user_id)
    return TaskDone(**result)


@router.post("/tasks/{task_id}/skip")
def task_skip(task_id: int, conn: sqlite3.Connection = Depends(get_db),
              user_id: int = Depends(current_user_id)) -> TaskDone:
    result = tasks_service.complete_task(conn, user_id, task_id, "skip")
    notifications_service.after_write(conn, user_id)
    return TaskDone(**result)


# ---- maintenance and inspections (2.11) -------------------------------------------------------

@router.put("/items/{public_id}/maintenance")
def put_maintenance(public_id: str, body: MaintenanceBody,
                    conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> TaskView:
    task = tasks_service.put_maintenance(conn, user_id, public_id,
                                         body.model_dump(exclude_unset=True))
    notifications_service.after_write(conn, user_id)
    return TaskView(**task)


@router.post("/items/{public_id}/inspections", status_code=201)
def add_inspection(public_id: str, body: InspectionCreate,
                   conn: sqlite3.Connection = Depends(get_db),
                   user_id: int = Depends(current_user_id)) -> InspectionDone:
    result = tasks_service.add_inspection(conn, user_id, public_id, body.model_dump())
    notifications_service.after_write(conn, user_id)
    return InspectionDone(**result)


@router.get("/items/{public_id}/inspections")
def list_inspections(public_id: str, conn: sqlite3.Connection = Depends(get_db),
                     user_id: int = Depends(current_user_id)) -> InspectionList:
    return InspectionList(**tasks_service.list_inspections(conn, user_id, public_id))
