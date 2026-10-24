-- Migration 0003 (Phase 4): tasks, inspections and notifications (DATA_MODEL 2.9, 2.10, 2.12).
-- No rows: notifications are made by the reconcile from real data, never seeded.

-- Maintenance plans and chores in one table (D-040). The per-item maintenance toggle is
-- `enabled` on the item's one live maintenance task.
CREATE TABLE tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    item_id       INTEGER REFERENCES items (id) ON DELETE RESTRICT,
    title         TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('maintenance', 'chore')),
    interval_days INTEGER CHECK (interval_days IS NULL OR interval_days BETWEEN 1 AND 3650),
    schedule_mode TEXT NOT NULL DEFAULT 'from_completion'
                  CHECK (schedule_mode IN ('from_completion', 'fixed')),
    next_due      TEXT NOT NULL,
    last_done     TEXT,
    enabled       INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    source        TEXT NOT NULL DEFAULT 'user' CHECK (source IN ('user', 'gemini')),
    notes         TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    deleted_at    TEXT,
    CHECK (kind <> 'maintenance' OR item_id IS NOT NULL)
);

CREATE UNIQUE INDEX tasks_one_maintenance ON tasks (item_id)
    WHERE kind = 'maintenance' AND deleted_at IS NULL;
CREATE INDEX tasks_due ON tasks (user_id, enabled, next_due);
CREATE INDEX tasks_item ON tasks (user_id, item_id);

-- The QM-flavoured record: each inspection completes the item's maintenance task.
CREATE TABLE inspections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    item_id      INTEGER NOT NULL REFERENCES items (id) ON DELETE RESTRICT,
    task_id      INTEGER REFERENCES tasks (id) ON DELETE RESTRICT,
    performed_at TEXT NOT NULL,
    local_date   TEXT NOT NULL,
    result       TEXT NOT NULL CHECK (result IN ('ok', 'worn', 'defective')),
    note         TEXT NOT NULL DEFAULT '',
    photo_id     TEXT REFERENCES photos (id) ON DELETE RESTRICT
);

CREATE INDEX inspections_item ON inspections (user_id, item_id, id);

-- Reconciled, never fired: the scheduler makes this table match what is due (DATA_MODEL 3.8).
-- `inspection_finding` is the attention row of a worn or defective inspection (D-104).
CREATE TABLE notifications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    kind           TEXT NOT NULL CHECK (kind IN ('expiry_soon', 'expired', 'inspection_due',
                                                 'task_due', 'inspection_finding')),
    item_id        INTEGER REFERENCES items (id) ON DELETE RESTRICT,
    task_id        INTEGER REFERENCES tasks (id) ON DELETE RESTRICT,
    due_date       TEXT NOT NULL,
    dedupe_key     TEXT NOT NULL UNIQUE,
    status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'snoozed', 'resolved')),
    snoozed_until  TEXT,
    read_at        TEXT,
    os_notified_at TEXT,
    created_at     TEXT NOT NULL,
    resolved_at    TEXT,
    resolution     TEXT CHECK (resolution IS NULL OR resolution IN (
                       'used', 'expired_marked', 'discarded', 'done', 'skipped', 'inspected',
                       'dismissed', 'superseded')),
    CHECK ((status = 'resolved') = (resolution IS NOT NULL)),
    CHECK ((status = 'snoozed') = (snoozed_until IS NOT NULL))
);

CREATE INDEX notifications_status ON notifications (user_id, status, due_date);
CREATE INDEX notifications_item ON notifications (item_id);
CREATE INDEX notifications_task ON notifications (task_id);
