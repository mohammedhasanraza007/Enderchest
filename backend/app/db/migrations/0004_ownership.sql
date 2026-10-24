-- Migration 0004 (Phase 6): confirmed savings (DATA_MODEL 2.13) and the embedding lookup index.
-- No rows: a saving exists only after the owner confirms "I didn't buy it" and types the price.
-- `photos.embedding` and `photos.embedding_model` already exist since 0002 (DATA_MODEL 2.7).

CREATE TABLE savings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    item_id      INTEGER REFERENCES items (id) ON DELETE SET NULL,
    item_name    TEXT NOT NULL,
    price_paise  INTEGER NOT NULL CHECK (price_paise > 0),
    confirmed_at TEXT NOT NULL,
    local_date   TEXT NOT NULL,
    note         TEXT NOT NULL DEFAULT '',
    deleted_at   TEXT
);

CREATE INDEX savings_by_date ON savings (user_id, local_date, id);

-- The embedding job looks for live photos with no vector, or one from another model.
CREATE INDEX photos_embedding_todo ON photos (embedding_model) WHERE deleted_at IS NULL;
