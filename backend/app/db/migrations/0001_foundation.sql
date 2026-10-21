-- Migration 0001 (Phase 0): instance tables and the user table.
-- Rows (the single user, meta values) are written by the first-run creation code,
-- never here, so a migration never seeds data (DATA_SAFETY 6).

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT,
    timezone   TEXT NOT NULL,
    theme      TEXT NOT NULL DEFAULT 'system' CHECK (theme IN ('system', 'light', 'dark')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE settings (
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    key        TEXT NOT NULL,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE scheduler_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE backup_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL CHECK (kind IN ('auto', 'manual', 'pre-migration', 'safety', 'restore')),
    name        TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    ok          INTEGER NOT NULL CHECK (ok IN (0, 1)),
    error       TEXT,
    bytes       INTEGER NOT NULL DEFAULT 0,
    item_count  INTEGER,
    verified    INTEGER NOT NULL CHECK (verified IN (0, 1))
);

CREATE INDEX backup_log_started ON backup_log (started_at);
