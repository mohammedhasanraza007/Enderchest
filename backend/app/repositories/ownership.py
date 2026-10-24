"""SQL for the ownership check (Phase 6): the active items it may propose. Reads only."""

import sqlite3


def active_items(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """Active items outside Trash with what scoring needs (only these qualify, spec Build 3)."""
    return conn.execute(
        "SELECT i.id, i.public_id, i.name, i.quantity, i.location_id, i.primary_photo_id, "
        "i.attributes, i.price_paise, c.name AS category_name FROM items i "
        "LEFT JOIN categories c ON c.id = i.category_id "
        "WHERE i.user_id = ? AND i.state = 'active' AND i.deleted_at IS NULL",
        (user_id,)).fetchall()
