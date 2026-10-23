-- Migration 0002 (Phase 2): the inventory tables (DATA_MODEL 2.4 to 2.8 and 2.11).
-- No rows: starter categories are created by the owner's tick at first run, never seeded.

CREATE TABLE categories (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    name                TEXT NOT NULL,
    expires_default     INTEGER NOT NULL DEFAULT 0 CHECK (expires_default IN (0, 1)),
    maintenance_default INTEGER NOT NULL DEFAULT 0 CHECK (maintenance_default IN (0, 1)),
    label_default       INTEGER NOT NULL DEFAULT 1 CHECK (label_default IN (0, 1)),
    created_at          TEXT NOT NULL,
    deleted_at          TEXT
);

CREATE UNIQUE INDEX categories_name ON categories (user_id, name COLLATE NOCASE)
    WHERE deleted_at IS NULL;

CREATE TABLE locations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    name       TEXT NOT NULL,
    parent_id  INTEGER REFERENCES locations (id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

-- COALESCE: SQLite treats NULLs as distinct, so two top-level "Garage" rows would both pass.
CREATE UNIQUE INDEX locations_name ON locations (user_id, COALESCE(parent_id, 0), name COLLATE NOCASE)
    WHERE deleted_at IS NULL;

CREATE TABLE items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    public_id        TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    category_id      INTEGER REFERENCES categories (id) ON DELETE RESTRICT,
    location_id      INTEGER REFERENCES locations (id) ON DELETE RESTRICT,
    quantity         INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    state            TEXT NOT NULL DEFAULT 'active'
                     CHECK (state IN ('active', 'used', 'expired', 'discarded')),
    expiry_mode      TEXT NOT NULL DEFAULT 'unknown' CHECK (expiry_mode IN ('unknown', 'none', 'date')),
    expiry_date      TEXT,
    price_paise      INTEGER CHECK (price_paise IS NULL OR price_paise >= 0),
    attributes       TEXT NOT NULL DEFAULT '{}',
    notes            TEXT NOT NULL DEFAULT '',
    no_label_needed  INTEGER NOT NULL DEFAULT 0 CHECK (no_label_needed IN (0, 1)),
    label_printed_at TEXT,
    primary_photo_id TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    state_changed_at TEXT NOT NULL,
    deleted_at       TEXT,
    CHECK ((expiry_mode = 'date') = (expiry_date IS NOT NULL))
);

CREATE INDEX items_state ON items (user_id, state, deleted_at);
CREATE INDEX items_expiry ON items (user_id, expiry_date);
CREATE INDEX items_category ON items (user_id, category_id);
CREATE INDEX items_location ON items (user_id, location_id);

CREATE TABLE drafts (
    id                TEXT PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    status            TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'committed', 'discarded')),
    fields            TEXT NOT NULL DEFAULT '{}',
    ocr_status        TEXT NOT NULL DEFAULT 'none'
                      CHECK (ocr_status IN ('none', 'pending', 'done', 'failed')),
    ocr_result        TEXT,
    gemini_status     TEXT NOT NULL DEFAULT 'none'
                      CHECK (gemini_status IN ('none', 'pending', 'done', 'failed', 'skipped')),
    gemini_result     TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    committed_item_id INTEGER REFERENCES items (id) ON DELETE RESTRICT
);

CREATE INDEX drafts_status ON drafts (user_id, status, created_at);

CREATE TABLE photos (
    id              TEXT PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    item_id         INTEGER REFERENCES items (id) ON DELETE RESTRICT,
    draft_id        TEXT REFERENCES drafts (id) ON DELETE RESTRICT,
    path            TEXT NOT NULL,
    thumb_path      TEXT NOT NULL,
    width           INTEGER NOT NULL,
    height          INTEGER NOT NULL,
    bytes           INTEGER NOT NULL,
    sha256          TEXT NOT NULL,
    mime            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    deleted_at      TEXT,
    embedding       BLOB,
    embedding_model TEXT,
    CHECK (item_id IS NOT NULL OR draft_id IS NOT NULL)
);

CREATE INDEX photos_item ON photos (item_id, deleted_at);
CREATE INDEX photos_draft ON photos (draft_id);

-- Append-only. item_id has no foreign key: an `item_purged` event outlives its item and keeps
-- the public id so it is never reused (DATA_MODEL 2.6, 2.11).
CREATE TABLE events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    item_id    INTEGER,
    task_id    INTEGER,
    kind       TEXT NOT NULL,
    payload    TEXT NOT NULL DEFAULT '{}',
    at         TEXT NOT NULL,
    local_date TEXT NOT NULL
);

CREATE INDEX events_item ON events (user_id, item_id, id);
CREATE INDEX events_kind ON events (user_id, kind);
