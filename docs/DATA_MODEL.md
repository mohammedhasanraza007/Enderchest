# DATA_MODEL.md — Tables, Rules and Derived Values

The single source for the database. Read before any schema, repository, API or dashboard-number work. If another file disagrees, this file wins for data shapes (decision D-036). No ORM: stdlib `sqlite3`, plain SQL, forward-only numbered migrations (`ARCHITECTURE.md` section 6).

> **Read when:** schema, repositories, API payloads, or any number on the dashboard. **Do not read when:** doing Docker, scripts or pure styling.
> **Sections:** 1 Conventions · 2 Tables (2.1 meta … 2.15 backup_log) · 3 Derived values (3.2 expiry status, 3.4 rings, 3.5 score, 3.8 scheduler) · 4 Migration plan · 5 Invariants. Open only the table or section your phase spec names.

---

## 1. Conventions

- **Types:** `INTEGER`, `TEXT`, `BLOB` only. Booleans are `INTEGER` 0/1 with a `CHECK`.
- **Dates (no timezone):** `TEXT` `YYYY-MM-DD` (expiry, due, `local_date`). **Moments:** `TEXT` ISO-8601 UTC with `Z` (`2026-10-16T07:49:12Z`). **Money:** `INTEGER` paise.
- **Ids:** `INTEGER PRIMARY KEY AUTOINCREMENT`, except `photos.id` and `drafts.id` (UUID v4 text) and `items.public_id` (the QR value, section 2.6). The API addresses items by `public_id`, never by the integer id.
- **`user_id`:** every user-owned table has `user_id INTEGER NOT NULL REFERENCES users(id)`. Instance-level tables (`meta`, `scheduler_state`, `backup_log`) have none. Every repository query filters by `user_id` even though there is one user. The single user row (id 1) is created together with a brand-new database; `name` stays `NULL` until first run completes.
- **Soft delete:** `deleted_at TEXT NULL`. Default queries add `deleted_at IS NULL`. Permanent delete is a separate, confirmed action (`API.md` 2.5).
- **Foreign keys on, `ON DELETE RESTRICT`.** Nothing cascades silently.
- **Connection pragmas:** `journal_mode=WAL`, `synchronous=FULL`, `foreign_keys=ON`, `busy_timeout=5000`. One connection per request thread; writes use `BEGIN IMMEDIATE` (D-052).
- **Text:** names trimmed, 1 to 120 characters; notes up to 2000; no control characters.

---

## 2. Tables

### 2.1 `meta` (migration 0001)
| Column | Type | Notes |
|---|---|---|
| `key` | TEXT PK | `schema_version`, `created_at`, `env_marker`, `instance_id` |
| `value` | TEXT NOT NULL | `env_marker` is `live` or `test`, written once when the database is created (D-054) |

### 2.2 `users` (0001)
`id`, `name` TEXT NULL, `timezone` TEXT NOT NULL (IANA, for example `Asia/Kolkata`), `theme` TEXT NOT NULL DEFAULT `system` CHECK in (`system`,`light`,`dark`), `created_at`, `updated_at`.

### 2.3 `settings` (0001)
`user_id`, `key` TEXT, `value` TEXT (JSON), `updated_at`; PK (`user_id`,`key`). Allowed keys are validated in code:

| Key | Type / range | Default |
|---|---|---|
| `lead_days` | int 1 to 14 | 3 |
| `coach_enabled` | bool | true |
| `gemini_mode` | `off` / `ask` / `auto` | `off` |
| `gemini_model` | string | from env `ENDERCHEST_GEMINI_MODEL` |
| `share_images_with_gemini` | bool | false |
| `assistant_share_item_text` | bool | false |
| `first_run_step` | `categories` or `done` (Phase 2, D-093) | not stored until the first name is saved; read through `GET /profile`, never returned by `GET /settings` |

The Gemini API key is **not** here (`DATA_SAFETY.md` section 2).

### 2.4 `categories` (0002)
`id`, `user_id`, `name`, `expires_default` 0/1, `maintenance_default` 0/1, `label_default` 0/1, `created_at`, `deleted_at`. Unique index on (`user_id`, `name` COLLATE NOCASE) where `deleted_at IS NULL`.
Defaults drive the add form: a new item in a category with `expires_default=1` starts with `expiry_mode='date'` (date required); `0` starts it as `none`. `label_default=0` starts the item with `no_label_needed=1`. `maintenance_default=1` pre-opens the maintenance toggle (never auto-enables it).
Starter set offered at first run (created by the user's tick, never seeded): Tools (0,1,1), Electronics (0,1,1), Food and drink (1,0,0), Cosmetics (1,0,0), Household (0,0,1), Other (0,0,1) in the order (expires, maintenance, label).

### 2.5 `locations` (0002)
`id`, `user_id`, `name`, `parent_id` INTEGER NULL REFERENCES locations(id), `created_at`, `deleted_at`. Unique index on (`user_id`, `COALESCE(parent_id,0)`, `name` COLLATE NOCASE) where `deleted_at IS NULL` (the `COALESCE` is needed because SQLite treats NULLs as distinct). Maximum depth 5; moving a location under itself or its descendants is refused (`cycle`). The path shown in the UI is the chain of names, for example `Garage › Shelf 2 › Blue box`.

### 2.6 `items` (0002)
| Column | Type | Rule |
|---|---|---|
| `id` | INTEGER PK | internal only |
| `user_id` | INTEGER | |
| `public_id` | TEXT NOT NULL UNIQUE | `ENDR-` + 8 characters from `0123456789ABCDEFGHJKMNPQRSTVWXYZ`, generated with `secrets`, retried on collision, never changed, never reused: generation also checks `item_purged` events, which keep the id after a permanent delete |
| `name` | TEXT NOT NULL | |
| `category_id` | INTEGER NULL | |
| `location_id` | INTEGER NULL | |
| `quantity` | INTEGER NOT NULL DEFAULT 1 | `CHECK (quantity >= 0)`; identical units that share one expiry date. Different expiry dates are different items |
| `state` | TEXT NOT NULL DEFAULT `active` | `CHECK` in (`active`,`used`,`expired`,`discarded`) |
| `expiry_mode` | TEXT NOT NULL DEFAULT `unknown` | `CHECK` in (`unknown`,`none`,`date`) |
| `expiry_date` | TEXT NULL | `CHECK ((expiry_mode = 'date') = (expiry_date IS NOT NULL))` |
| `price_paise` | INTEGER NULL | `CHECK (price_paise IS NULL OR price_paise >= 0)`; price of one unit |
| `attributes` | TEXT NOT NULL DEFAULT `{}` | JSON object. Keys lower snake case (`size`, `model`, `part_no`, `brand`, `colour`, `voltage`); values string, number, or list of strings or numbers. At most 40 keys, 500 characters per value. A wrench set stores `{"sizes": [8,10,12,13]}` (D-041) |
| `notes` | TEXT NOT NULL DEFAULT `` | |
| `no_label_needed` | INTEGER NOT NULL DEFAULT 0 | 0/1 |
| `label_printed_at` | TEXT NULL | set only when the user confirms the print (D-045) |
| `primary_photo_id` | TEXT NULL | `photos.id` |
| `created_at`, `updated_at`, `state_changed_at`, `deleted_at` | TEXT | |
Indexes: (`user_id`,`state`,`deleted_at`), (`user_id`,`expiry_date`), (`user_id`,`category_id`), (`user_id`,`location_id`). `public_id` unique.

### 2.7 `photos` (0002)
`id` TEXT PK (UUID), `user_id`, `item_id` INTEGER NULL, `draft_id` TEXT NULL, `path` TEXT (relative to `/data/photos`), `thumb_path` TEXT (relative to `/data/thumbs`), `width`, `height`, `bytes`, `sha256`, `mime` (`image/jpeg` after re-encode), `created_at`, `deleted_at`, `embedding` BLOB NULL (float32 vector), `embedding_model` TEXT NULL. `CHECK (item_id IS NOT NULL OR draft_id IS NOT NULL)`. A draft photo gets `item_id` set and `draft_id` cleared on commit. Files are immutable; "deleting" a photo sets `deleted_at` only. Maximum 12 live photos per item.

### 2.8 `drafts` (0002)
`id` TEXT PK (UUID), `user_id`, `status` (`open`,`committed`,`discarded`), `fields` TEXT (JSON, keys as in `POST /api/v1/items` plus `expiry_confirmed` bool), `ocr_status` (`none`,`pending`,`done`,`failed`), `ocr_result` TEXT NULL (JSON), `gemini_status` (`none`,`pending`,`done`,`failed`,`skipped`), `gemini_result` TEXT NULL (JSON), `created_at`, `updated_at`, `committed_item_id` INTEGER NULL. A draft is not an item: it is excluded from every count, ring and search (D-049).

### 2.9 `tasks` (0003) — maintenance plans and chores in one table (D-040)
| Column | Rule |
|---|---|
| `id`, `user_id` | |
| `item_id` INTEGER NULL | required when `kind='maintenance'` (`CHECK (kind <> 'maintenance' OR item_id IS NOT NULL)`) |
| `title` TEXT NOT NULL | for maintenance defaults to `Inspect <item name>` |
| `kind` | `maintenance` or `chore` |
| `interval_days` INTEGER NULL | 1 to 3650; `NULL` means one-off |
| `schedule_mode` | `from_completion` (default) or `fixed` (D-048) |
| `next_due` TEXT NOT NULL | date |
| `last_done` TEXT NULL | date |
| `enabled` | 0/1. The per-item maintenance toggle is this flag on the item's maintenance task |
| `source` | `user` or `gemini` (a `gemini` task is shown as "suggested, unverified" until the user edits or confirms it) |
| `notes`, `created_at`, `updated_at`, `deleted_at` | |
At most one live maintenance task per item (unique index on `item_id` where `kind='maintenance' AND deleted_at IS NULL`).
**Completion rule:** `done` on date D sets `last_done=D`; recurring: `next_due = D + interval_days` when `from_completion`, or the next date of the original series strictly after D when `fixed` (add `interval_days` to the old `next_due` at least once, then repeatedly until it is after D: the occurrence just done is satisfied even when done early; Phase 4 verification N3). `skip` behaves like `done` for scheduling but records `task_skipped` and does not count towards streaks. One-off tasks set `enabled=0` after done or skipped.

### 2.10 `inspections` (0003) — the QM-flavoured record
`id`, `user_id`, `item_id`, `task_id` NULL, `performed_at`, `local_date`, `result` (`ok`,`worn`,`defective`), `note`, `photo_id` NULL. An inspection also completes the item's maintenance task (same rule as `done`). `worn` and `defective` leave the item `active`, add an attention row worded "inspection suggested: worn" or "inspection suggested: defective" (never "replacement required"), and offer "Mark discarded".

### 2.11 `events` (0002, extended in later phases without schema change)
Append-only. `id`, `user_id`, `item_id` NULL, `task_id` NULL, `kind`, `payload` TEXT (JSON), `at`, `local_date`. Kinds: `item_created`, `item_updated`, `item_deleted`, `item_restored`, `item_purged` (kept after permanent delete; holds name and `public_id` only), `item_used`, `item_expired_marked`, `item_discarded`, `item_reactivated`, `label_printed`, `photo_added`, `photo_removed`, `draft_committed`, `task_created`, `task_updated`, `task_deleted`, `task_done`, `task_skipped`, `inspection_done`, `notification_resolved`, `savings_added`, `savings_removed`. Reversible kinds store `payload.before` (the changed fields' old values); `POST /api/v1/events/{id}/undo` applies it.

### 2.12 `notifications` (0003)
`id`, `user_id`, `kind` (`expiry_soon`,`expired`,`inspection_due`,`task_due`,`inspection_finding` (D-104)), `item_id` NULL, `task_id` NULL, `due_date` TEXT, `dedupe_key` TEXT NOT NULL UNIQUE, `status` (`open`,`snoozed`,`resolved`), `snoozed_until` TEXT NULL (date), `read_at` NULL, `os_notified_at` NULL, `created_at`, `resolved_at` NULL, `resolution` TEXT NULL (`used`,`expired_marked`,`discarded`,`done`,`skipped`,`inspected`,`dismissed`,`superseded`).
`dedupe_key = kind|item_id-or-dash|task_id-or-dash|due_date` (D-022). The scheduler **reconciles**; it does not fire events (section 3.8). An `inspection_finding` row belongs to an active item whose latest inspection is `worn` or `defective` (due date = that inspection's local date). Lifecycle actions resolve the item's rows with their own resolution (D-105).

### 2.13 `savings` (0004)
`id`, `user_id`, `item_id` NULL, `item_name` TEXT NOT NULL (snapshot), `price_paise` INTEGER NOT NULL CHECK (> 0), `confirmed_at`, `local_date`, `note`, `deleted_at`.

### 2.14 `scheduler_state` (0001, instance-level)
`key` TEXT PK, `value` TEXT. Keys: `last_reconcile_at`, `last_local_date` (written only beside a reconcile that changed rows; the timing itself is kept in memory, D-108).

### 2.15 `backup_log` (0001, instance-level)
`id`, `kind` (`auto`,`manual`,`pre-migration`,`safety`,`restore`), `name`, `started_at`, `finished_at`, `ok` 0/1, `error` TEXT NULL, `bytes`, `item_count` NULL, `verified` 0/1.

---

## 3. Derived values (computed in the backend, one place, unit-tested)

### 3.1 Today
`today` = the current date in the user's `timezone` (from the test clock when `ENDERCHEST_ENV=test`). Every comparison with an expiry or due date uses `today`, never UTC (D-019).

### 3.2 Expiry status (per item)
`days_left = expiry_date - today` when `expiry_mode='date'`.
| Condition | `status` | Word shown |
|---|---|---|
| `expiry_mode='none'` | `no_expiry` | "no expiry" |
| `expiry_mode='unknown'` | `unknown` | "date not set" |
| `days_left < 0` | `expired` | "expired" |
| `days_left = 0` | `today` | "expires today" |
| `days_left = 1` | `soon` | "1 day left" |
| `2 ≤ days_left ≤ lead_days` | `soon` | "N days left" |
| `days_left > lead_days` | `ok` | "N days left" (shown on the item page only) |
The reference image's word "expiring" is retired; "expires today" replaces it.

### 3.3 Active items
"Active items" means `state='active' AND deleted_at IS NULL`. Used, expired, discarded, deleted items and drafts never count in any ring or total.

### 3.4 Health rings (each value 0 to 100, or not applicable)
| Ring | Numerator (active items that…) | Denominator | Not applicable when |
|---|---|---|---|
| Documented | have at least one live photo **and** (`label_printed_at` set **or** `no_label_needed=1`) | active items | no active items |
| Located | have a `location_id` | active items | no active items |
| Fresh | have `expiry_mode='none'`, or `expiry_mode='date'` and `expiry_date >= today` | active items | no active items |
| On time | n/a, see below | enabled tasks | no enabled tasks |
**On time** = 100 × (enabled live tasks with `next_due >= today`) / (enabled live tasks). An item with `unknown` expiry counts as not fresh until the user picks "no expiry" or a date, so the category default (section 2.4) matters.
`value = round(100 × numerator / denominator)`. A ring that is not applicable is **excluded from the score** and drawn as an empty track with the words "no tasks yet" (On time) or an em dash (D-044).

### 3.5 Score
`score = round(Σ(weight × value) / Σ(weight))` over applicable rings only. Default weights Documented 25, Located 20, Fresh 35, On time 20 (O-004). With no active items the score is `null` and the UI shows an em dash.

### 3.6 Road (next 14 days)
Window = `today` through `today + 13`. Events: active items with `expiry_mode='date'` and `expiry_date` in the window; enabled tasks with `next_due` in the window. Overdue things are not on the road; they are in Needs attention. Several events on one date collapse to a count. **Truck date** = the earliest task (chore or maintenance) due after `today` in the window; with none, the earliest event after `today`; else `today` (D-110: what is due today is already in Needs attention).

### 3.7 Streak
A local day counts when at least one event of kind `item_used`, `item_expired_marked`, `item_discarded`, `task_done`, `inspection_done` or `notification_resolved` (resolution not `superseded`) happened on that `local_date`. Days on which nothing was due are skipped (they neither extend nor break the streak). The streak is the number of consecutive counting days ending today or yesterday. No copy ever shames a broken streak.

### 3.8 Scheduler reconcile (Phase 4)
Run at start-up, every 15 minutes, when the local date changes, and before `GET /api/v1/dashboard` if the last run is over 60 seconds old. It computes the *desired* set of notifications from current data and makes the table match; it is idempotent, so downtime, restarts and double runs create no duplicates and lose nothing.
1. For each active item with `expiry_mode='date'`: `0 ≤ days_left ≤ lead_days` → ensure `expiry_soon` (due = `expiry_date`); `days_left < 0` → ensure `expired` and resolve any `expiry_soon` for that item as `superseded`.
2. For each enabled task with `next_due <= today` → ensure `inspection_due` (maintenance) or `task_due` (chore), due = `next_due`.
3. Re-open `snoozed` rows whose `snoozed_until <= today`.
4. Resolve as `superseded` any open row whose item is not active or is deleted, or whose task is disabled or deleted; in general any open or snoozed row that is no longer desired (a date edited, a task moved) (D-104).
5. A resolved row whose key is desired again (undo, restore, reactivate) reopens unless the owner dismissed it, and keeps `os_notified_at` (D-104). The reconcile also runs after every write that changes what is due, and before notification reads when the date moved (D-107).
Snooze options: `tomorrow`, `3days`, `week`, always capped at the due date for `expiry_soon` (a snooze cannot hide an item past its date) (D-047).

---

## 4. Migration plan

| Migration | Phase | Creates |
|---|---|---|
| 0001 | 0 | `meta`, `users`, `settings`, `scheduler_state`, `backup_log` |
| 0002 | 2 | `categories`, `locations`, `items`, `photos`, `drafts`, `events` and their indexes |
| 0003 | 4 | `tasks`, `inspections`, `notifications` |
| 0004 | 6 | `savings` |
Every migration is a numbered `.sql` file applied in one transaction by the runner, after a verified pre-migration backup, and has a test that migrates a realistic database from the previous version (`DATA_SAFETY.md` section 6). Adding a column later is a new migration, never an edit.

## 5. Invariants every phase's tests assert
- `quantity >= 0`; the `expiry_mode`/`expiry_date` pairing `CHECK`; `public_id` unique and matching `^ENDR-[0-9A-HJKMNP-TV-Z]{8}$`.
- Every repository query includes `user_id`.
- A committed draft never leaves an item without its photos; a failed commit leaves the draft open and creates no item.
- `notifications.dedupe_key` is unique; running the reconcile twice changes nothing.
- Ring values equal their breakdown lists; counts equal list lengths; no negative money.
