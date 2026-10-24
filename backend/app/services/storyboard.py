"""The storyboard fixtures `storyboard-1`, `-2`, `-3` (Phase 5 spec item 5, DESIGN 20, D-109,
D-111). Test stack only: `POST /test/fixtures/{name}` is the one caller.

Real rows, built so the *computed* numbers are the frames' numbers: 142 active items (112
documented, 124 located, 136 fresh) and nine tasks. Frames 2 and 3 are frame 1 plus the actions
the owner would take, run through the same services the buttons call.
"""

import io
import sqlite3
from datetime import date, timedelta

from PIL import Image

from .. import clock, ids, images
from ..config import Settings
from ..db.connection import write_transaction
from ..repositories import items as items_repo
from . import lifecycle as lifecycle_service
from . import notifications as notifications_service
from . import profile as profile_service
from . import tasks as tasks_service
from .photos import store_row

ITEMS = 142
DOCUMENTED, LOCATED, FRESH = 112, 124, 136
# Household things, the reference's three foods first; the first 20 are food.
_NAMES = (
    "Oat Milk", "Greek Yogurt", "Baby Spinach", "Lawn trimmer", "Bread flour", "Paneer",
    "Basmati rice", "Toor dal", "Olive oil", "Green tea", "Honey", "Peanut butter", "Rolled oats",
    "Coffee beans", "Ghee", "Turmeric", "Cumin seeds", "Garam masala", "Salt", "Sugar",
    "AA batteries", "AAA batteries", "USB-C cable", "HDMI cable", "Laptop charger",
    "Wireless mouse", "Keyboard", "Webcam", "Power strip", "Extension cord", "Torch",
    "Screwdriver set", "Allen keys", "Spanner set", "Hammer", "Measuring tape", "Spirit level",
    "Drill", "Drill bits", "Sandpaper", "WD-40", "Duct tape", "Cable ties", "Super glue",
    "Vernier caliper", "Multimeter", "Soldering iron", "Solder wire", "Safety goggles",
    "Work gloves", "First aid kit", "Paracetamol", "Band-aids", "Antiseptic cream",
    "Thermometer", "Toothpaste", "Shampoo", "Conditioner", "Body wash", "Sunscreen",
    "Moisturiser", "Razor blades", "Shaving foam", "Deodorant", "Hand wash", "Dish soap",
    "Laundry detergent", "Fabric softener", "Floor cleaner", "Glass cleaner", "Sponges",
    "Trash bags", "Paper towels", "Tissues", "Light bulbs", "Fuse wire", "Bicycle pump",
    "Bike lights", "Helmet", "Umbrella", "Raincoat", "Backpack", "Water bottle", "Lunch box",
    "Notebooks", "Graph paper", "Pencils", "Erasers", "Scientific calculator", "Drawing set",
    "Stapler", "Staples", "Sticky notes", "Highlighters", "Printer paper", "Ink cartridge",
    "Desk lamp", "Phone stand", "Power bank", "Earphones", "SD card", "USB drive",
    "External SSD", "Router", "Ethernet cable", "Mosquito repellent", "Candles", "Matches",
    "Sewing kit", "Safety pins", "Shoe polish", "Shoe brush", "Iron", "Ironing board",
    "Hangers", "Bedsheets", "Pillow covers", "Blanket", "Towels", "Yoga mat", "Dumbbells",
    "Skipping rope", "Football", "Badminton racket", "Shuttlecocks", "Pressure cooker",
    "Kadai", "Tawa", "Chef's knife", "Cutting board", "Measuring cups", "Mixer jar",
    "Kettle", "Toaster", "Rice cooker", "Water filter", "Filter cartridge", "Ladder",
    "Toolbox", "Paint brushes", "Wall plugs", "Spare keys",
)
_PLACES = (("Kitchen", None), ("Fridge", "Kitchen"), ("Pantry", "Kitchen"), ("Garage", None),
           ("Study", None), ("Bedroom", None), ("Bathroom", None))
# Chores due after today (days from today, title, repeat every N days).
_CHORES = ((2, "Pantry Refill", 30), (5, "Clean PC", 90), (40, "Service bicycle", 180))
# Overdue chores whose reminders the owner snoozed, so the card shows the frame's rows (D-111).
_SNOOZED = ((-1, "Water the plants"), (-2, "Change bedsheets"), (-3, "Descale kettle"),
            (-4, "Clean the fridge"))


def _photo_bytes() -> bytes:
    """One small plain photo; every documented item gets its own stored copy of it."""
    buffer = io.BytesIO()
    Image.new("RGB", (96, 72), (120, 92, 70)).save(buffer, "JPEG", quality=85)
    return buffer.getvalue()


def _expiry(index: int, today: date) -> tuple[str, str | None]:
    """Oat Milk today, Greek Yogurt in 2 days, a few later dates, six unknown, the rest none."""
    fixed = {0: 0, 1: 2, 2: 6, 4: 8, 5: 11, 6: 45, 7: 120}
    if index in fixed:
        return "date", (today + timedelta(days=fixed[index])).isoformat()
    if index >= ITEMS - (ITEMS - FRESH):
        return "unknown", None
    return "none", None


def _items(conn: sqlite3.Connection, settings: Settings, user_id: int, today: date) -> dict:
    now = clock.stamp()
    processed = images.process(_photo_bytes())
    with write_transaction(conn):
        place_ids: dict[str, int] = {}
        for name, parent in _PLACES:
            place_ids[name] = conn.execute(
                "INSERT INTO locations (user_id, name, parent_id, created_at) VALUES (?, ?, ?, ?)",
                (user_id, name, place_ids.get(parent) if parent else None, now)).lastrowid
        rooms = [place_ids[name] for name in ("Garage", "Study", "Bedroom", "Bathroom")]
        public_ids: dict[str, str] = {}
        for index in range(ITEMS):
            name = _NAMES[index]
            if index == 3:  # the lawn trimmer
                place = place_ids["Garage"]
            elif index < 20:
                place = place_ids["Fridge"] if index < 6 else place_ids["Pantry"]
            else:
                place = rooms[index % len(rooms)]
            mode, expiry = _expiry(index, today)
            public_id = ids.new_public_id()
            item_id = items_repo.insert(conn, user_id, public_id, {
                "name": name, "location_id": place if index < LOCATED else None,
                "quantity": 1, "expiry_mode": mode, "expiry_date": expiry, "attributes": "{}",
                "notes": "", "no_label_needed": int(index % 4 == 3)}, now)
            if index < DOCUMENTED:  # the last 30 lack a photo, so they are not documented
                stored = images.store(settings, processed)
                store_row(conn, user_id, stored, processed, item_id=item_id, now=now)
                conn.execute("UPDATE items SET primary_photo_id = ?, label_printed_at = ? "
                             "WHERE id = ?", (stored.id, None if index % 4 == 3 else now, item_id))
            public_ids[name] = public_id
    return public_ids


def _tasks(conn: sqlite3.Connection, user_id: int, today: date, public_ids: dict) -> dict:
    def create(title: str, due: int, every: int | None, item: str | None = None) -> int:
        return tasks_service.create_task(conn, user_id, {
            "title": title, "kind": "maintenance" if item else "chore",
            "item_public_id": public_ids[item] if item else None, "interval_days": every,
            "schedule_mode": "from_completion", "first_due": (today + timedelta(days=due))
            .isoformat(), "enabled": True, "notes": ""})["id"]

    task_ids = {title: create(title, due, every) for due, title, every in _CHORES}
    task_ids["Inspect baby spinach"] = create("Inspect baby spinach", 0, 7, "Baby Spinach")
    task_ids["Blade check"] = create("Blade check", 10, 60, "Lawn trimmer")
    for due, title in _SNOOZED:
        task_ids[title] = create(title, due, 14)
    notifications_service.reconcile(conn, user_id)
    for _due, title in _SNOOZED:
        row_id = _row_for(conn, user_id, task_id=task_ids[title])
        notifications_service.snooze(conn, user_id, row_id, "tomorrow")
    return task_ids


def _row_for(conn: sqlite3.Connection, user_id: int, *, task_id: int | None = None,
             item_id: int | None = None) -> int:
    column, value = ("task_id", task_id) if task_id is not None else ("item_id", item_id)
    return conn.execute(f"SELECT id FROM notifications WHERE user_id = ? AND {column} = ? "
                        "AND status = 'open'", (user_id, value)).fetchone()["id"]


def _done(conn: sqlite3.Connection, user_id: int, task_ids: dict, *titles: str) -> None:
    for title in titles:
        tasks_service.complete_task(conn, user_id, task_ids[title], "done")


def build(conn: sqlite3.Connection, settings: Settings, stage: int, user_id: int = 1) -> dict:
    """Frame 1, then the owner's actions up to `stage` (D-111)."""
    today = profile_service.local_today(conn, user_id)
    public_ids = _items(conn, settings, user_id, today)
    task_ids = _tasks(conn, user_id, today, public_ids)
    if stage >= 2:  # frame 2: the truck moves on to Clean PC; On time rises
        _done(conn, user_id, task_ids, "Pantry Refill", "Water the plants", "Change bedsheets")
    if stage >= 3:  # frame 3: Oat Milk used, Greek Yogurt snoozed, Clean PC and the rest done
        lifecycle_service.use(conn, user_id, public_ids["Oat Milk"], 1)
        yogurt = items_repo.get(conn, user_id, public_ids["Greek Yogurt"])
        notifications_service.snooze(conn, user_id, _row_for(conn, user_id, item_id=yogurt["id"]),
                                     "tomorrow")
        _done(conn, user_id, task_ids, "Clean PC", "Descale kettle", "Clean the fridge")
    notifications_service.after_write(conn, user_id)
    return {"fixture": f"storyboard-{stage}", "items": ITEMS, "tasks": len(task_ids),
            "public_ids": {name: public_ids[name] for name in
                           ("Oat Milk", "Greek Yogurt", "Baby Spinach", "Lawn trimmer")},
            "task_ids": task_ids}
