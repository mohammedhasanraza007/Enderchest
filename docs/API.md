# API.md — HTTP Contract

> **Read when:** writing or calling any endpoint. **Do not read when:** doing Docker, styling or design-token work.
> **Sections:** 1 Conventions · 2.1 Boot/health · 2.2 Profile/settings · 2.3 Backups · 2.4 Categories/locations · 2.5 Items · 2.6 Photos · 2.7 Labels/lookup · 2.8 Drafts · 2.9 Gemini · 2.10 Lifecycle · 2.11 Tasks/inspections · 2.12 Notifications · 2.13 Dashboard · 2.14 Ownership/savings · 2.15 Capture coach · 2.16 Assistant · 2.17 Test-only. Open only the area your phase spec names.

Data shapes live in `DATA_MODEL.md`. Page behaviour lives in `PAGES.md`. Every endpoint below is used by at least one page or spec (checked by `scripts/check_docs.py`); do not add an endpoint nobody calls.

---

## 1. Conventions

- **Base:** `/api/v1`. The only exception is `GET /health`. JSON everywhere except uploads (`multipart/form-data`) and file/SVG responses.
- **Safety header:** every non-GET/HEAD request must send `X-Enderchest: 1`, and the `Host` must be `localhost`, `127.0.0.1` or `[::1]` with the app port. No CORS headers are ever sent (D-050, `ARCHITECTURE.md` section 9).
- **Dates and money:** dates `YYYY-MM-DD`; moments ISO UTC `Z`; money integer paise; items addressed by `public_id`.
- **Errors:** `{"error":{"code":"<code>","message":"<one human sentence>","details":{}}}`.

| Code | HTTP | Meaning |
|---|---|---|
| `validation_error` | 422 | `details` lists `{field, problem}` |
| `not_found` | 404 | |
| `conflict` | 409 | generic state conflict (`details.reason`) |
| `in_use` | 409 | category/location still has items; retry with `reassign_to` |
| `cycle` | 409 | location move would create a loop |
| `not_deleted` | 409 | permanent delete needs the item in Trash first |
| `backup_required` | 409 | permanent delete needs a good backup under 24 h old |
| `limit_reached` | 409 | for example 12 photos per item |
| `expiry_unconfirmed` | 422 | draft commit with an unconfirmed parsed date |
| `undo_expired` | 409 | undo window (60 s server-side) has passed |
| `payload_too_large` | 413 | upload over 12 MB |
| `unsupported_media` | 415 | not JPEG/PNG/WebP (HEIC gets a specific message) |
| `rate_limited` | 429 | |
| `busy` | 409 | coach frame still processing |
| `forbidden_host` | 403 | Host/Origin/header check failed |
| `locked` | 503 | boot state is not `ok` (`details.state`) |
| `gemini_disabled` | 409 | no key or mode off |
| `upstream_unavailable` | 502 | Gemini unreachable or errored |
| `backup_unavailable` | 503 | backup folder not mounted |
| `internal_error` | 500 | never leaks a stack trace |

- **Pagination:** `limit` 1 to 200 (default 100), opaque `cursor`; responses `{items:[…], next_cursor: string|null}`.
- **Idempotency:** `POST /items`, `POST /drafts/{id}/commit`, `POST /tasks`, `POST /savings` accept `Idempotency-Key`; a repeat within 10 minutes returns the first result (in-memory, single worker).
- **Shared shapes.**
  - `ItemSummary`: `{public_id, name, category_name|null, location_path:[string], quantity, state, expiry:{mode, date|null, status, days_left|null, word}, primary_photo_id|null, has_photo, deleted_at|null}`.
  - `ItemDetail`: `ItemSummary` plus `{category:{id,name}|null, location:{id,name}|null, price_paise|null, notes, attributes, label:{printed_at|null, no_label_needed}, photos:[{id, is_primary, width, height}], maintenance:{task_id, enabled, interval_days|null, next_due, last_done|null, source}|null, created_at, updated_at}`.
  - `NotificationView`: `{id, kind, item:{public_id,name,primary_photo_id}|null, task:{id,title}|null, due_date, word, urgency, status, snoozed_until|null, read_at|null, actions:[{key,label,primary}]}`.
  - `Draft`: `{id, status, fields, photos:[{id,width,height}], ocr_status, gemini_status, proposed:{<field>:{value, source:'ocr'|'gemini', confidence:'high'|'medium'|'low', flags:[…]}}, raw_text|null, created_at}`.

Tables below: columns are Phase, Method, Path (relative to `/api/v1` unless it starts with `/health`), Request, Success, Errors.

---

## 2. Endpoints

### 2.1 Boot and health
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 0 | GET | /health | none | `{status:'starting'\|'ok'\|'recovery'\|'locked'\|'failed', reason\|null, app_version, schema_found\|null, schema_supported, env, build_date}` always 200 when the process answers; `build_date` is `YYYY-MM-DD` set by `build.bat`, or `null` when not recorded (D-085) | none |
| 0 | GET | /boot | none | `{state, reason, message\|null, data_mounted, backups_mounted, schema_found, schema_supported, backups:[{name,kind,at,bytes,item_count\|null,ok}], warnings:[string]}` available in every state (`message` is the plain sentence the boot page shows; D-075) | none |
| 0 | POST | /boot/restore | `{name, confirm:'RESTORE'}` (recovery state only) | `{restored:name, items, photos_missing:n}` | `validation_error`, `conflict` |
| 0 | POST | /boot/start-empty | `{confirm:'START EMPTY'}` (recovery state only; first makes a safety backup of whatever is on disk) | `{state:'ok'}` | `conflict` |

### 2.2 Profile and settings
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 1 | GET | /profile | none | `{name\|null, timezone, theme, first_run_complete, first_run_step}`; `first_run_step` is `name`, `categories` or `done`, and `first_run_complete` is true only at `done` (D-084, D-093) | `locked` |
| 1 | PUT | /profile | `{name, timezone, theme?}`; name 1 to 40 characters after trimming, no control characters; timezone from the IANA list; a theme left out stays as it is (D-085) | profile | `validation_error` |
| 1 | GET | /settings | none | all keys of `DATA_MODEL.md` 2.3 with defaults filled | |
| 1 | PATCH | /settings | partial settings; from Phase 2 also `first_run_step: "done"` (P-01 step 2 finished; the only value a client may write, never returned by `GET /settings`, D-093) | settings | `validation_error` |

### 2.3 Backups
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 0 | GET | /backups | none | `{status:'ok'\|'stale'\|'failing'\|'unavailable', last_good:{name,at,bytes}\|null, warnings:[string], items:[{name,kind,at,bytes,item_count\|null,ok}], folder_hint}`; `folder_hint` is the host folder, shown on the Settings page (D-085) | |
| 0 | POST | /backups | none | 201 `{name, bytes, verified:true, folder_hint}` | `backup_unavailable`, `internal_error` |

### 2.4 Categories and locations
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 2 | GET | /categories | none | `[{id,name,expires_default,maintenance_default,label_default,item_count}]` | |
| 2 | POST | /categories | `{name, expires_default?, maintenance_default?, label_default?}` | 201 category | `validation_error`, `conflict` |
| 2 | PATCH | /categories/{id} | partial | category | `not_found`, `conflict` |
| 2 | DELETE | /categories/{id} | query `reassign_to?` | 204 | `in_use`, `not_found` |
| 2 | GET | /locations | none | flat `[{id,name,parent_id,path:[string],item_count}]` | |
| 2 | POST | /locations | `{name, parent_id?}` | 201 location | `validation_error`, `conflict` |
| 2 | PATCH | /locations/{id} | `{name?, parent_id?}` | location | `cycle`, `conflict`, `not_found` |
| 2 | DELETE | /locations/{id} | query `reassign_to?` | 204 | `in_use`, `not_found` |

### 2.5 Items
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 2 | GET | /items | query `q`, `category_id`, `location_id` (includes descendants), `state` (`active` default, `used`, `expired`, `discarded`, `all`), `expiry` (`soon`,`today`,`past`,`none`,`unknown`,`any`), `has_photo`, `sort` (`created_desc` default, `name_asc`, `expiry_asc`), `deleted` (`exclude` default, `only`), `limit`, `cursor` | `{items:[ItemSummary], next_cursor, total}` | |
| 2 | POST | /items | `{name*, category_id?, location_id?, quantity?, expiry_mode?, expiry_date?, price_paise?, notes?, attributes?, no_label_needed?}` | 201 ItemDetail | `validation_error`, `not_found` |
| 2 | GET | /items/{public_id} | none | ItemDetail | `not_found` |
| 2 | PATCH | /items/{public_id} | any editable field above (never `state`) | ItemDetail | `validation_error`, `not_found` |
| 2 | DELETE | /items/{public_id} | none | `{event_id}` (soft delete, undoable) | `not_found` |
| 2 | POST | /items/{public_id}/restore | none | ItemDetail | `not_found` |
| 2 | DELETE | /items/{public_id}/permanent | `{confirm:'DELETE'}` | 204 | `not_deleted`, `backup_required`, `validation_error` |
| 2 | GET | /items/{public_id}/events | `limit`, `cursor` | `{items:[{kind,payload,at,local_date}], next_cursor}` | `not_found` |

### 2.6 Photos
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 2 | POST | /items/{public_id}/photos | multipart `image` | 201 `{id,is_primary,width,height}` | `payload_too_large`, `unsupported_media`, `limit_reached` |
| 2 | DELETE | /photos/{id} | none | 204 (sets `deleted_at`; file kept) | `not_found` |
| 2 | PUT | /items/{public_id}/primary-photo | `{photo_id}` | ItemDetail | `not_found` |
| 2 | GET | /photos/{id}/file | none | image bytes, `Cache-Control: private, max-age=31536000, immutable` | `not_found` |
| 2 | GET | /photos/{id}/thumb | none | JPEG 320 px long edge, same caching | `not_found` |

### 2.7 Labels and lookup
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 2 | GET | /items/{public_id}/qr.svg | none | `image/svg+xml` QR of the `public_id` only | `not_found` |
| 2 | POST | /items/label-printed | `{public_ids:[…]}` | `{updated:n}` | `validation_error` |
| 2 | GET | /lookup/{code} | none | ItemSummary; `code` accepts typed forms (lowercase, `I`/`L` as 1, `O` as 0, with or without the dash) | `not_found` |

### 2.8 Drafts (the add flow, D-049)
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 2 | POST | /drafts | multipart `images[]` (1 to 20); one draft per image | 201 `{drafts:[Draft]}` | `payload_too_large`, `unsupported_media` |
| 2 | GET | /drafts | query `status` (default `open`) | `{items:[Draft]}` | |
| 2 | GET | /drafts/{id} | none | Draft | `not_found` |
| 2 | PATCH | /drafts/{id} | `{fields:{…partial…}}` | Draft | `validation_error` |
| 2 | POST | /drafts/{id}/photos | multipart `image` | Draft | `limit_reached`, `unsupported_media` |
| 2 | POST | /drafts/{id}/commit | none | 201 ItemDetail | `validation_error`, `expiry_unconfirmed` |
| 2 | DELETE | /drafts/{id} | none | 204 (status `discarded`, photos untouched) | `not_found` |
| 3 | POST | /drafts/{id}/extract | `{engine:'local'\|'gemini'}` | 202 `{ocr_status\|gemini_status:'pending'}`; the client polls `GET /drafts/{id}` | `gemini_disabled`, `upstream_unavailable` |

### 2.9 Gemini settings
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 3 | GET | /gemini | none | `{key_set, model, mode, share_images}` (never the key) | |
| 3 | PUT | /gemini/key | `{key}` | `{key_set:true}` | `validation_error` |
| 3 | DELETE | /gemini/key | none | 204 | |
| 3 | POST | /gemini/test | none | `{ok:true, model, latency_ms}` (a real call) | `gemini_disabled`, `upstream_unavailable` |

### 2.10 Lifecycle
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 4 | POST | /items/{public_id}/use | `{amount?:1}` (quantity minus amount; at 0 the state becomes `used`) | `{item:ItemDetail, event_id}` | `conflict`, `not_found` |
| 4 | POST | /items/{public_id}/mark-expired | none | `{item, event_id}` | `conflict` |
| 4 | POST | /items/{public_id}/discard | none | `{item, event_id}` | `conflict` |
| 4 | POST | /items/{public_id}/reactivate | `{quantity?:1}` | ItemDetail | `conflict` |
| 2 | POST | /events/{id}/undo | none; Phase 2 undoes `item_deleted`, later phases add their kinds (D-092) | `{ok:true}` | `undo_expired`, `not_found` |

### 2.11 Tasks, maintenance and inspections
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 4 | GET | /tasks | query `scope` (`open` default, `due`, `all`), `item` (public_id) | `{items:[{id,title,kind,item:{public_id,name}\|null,interval_days,schedule_mode,next_due,last_done,enabled,source,word}]}` | |
| 4 | POST | /tasks | `{title*, item_public_id?, kind?, interval_days?, schedule_mode?, first_due*, notes?, enabled?}` | 201 task | `validation_error` |
| 4 | PATCH | /tasks/{id} | partial | task | `not_found` |
| 4 | DELETE | /tasks/{id} | none | `{event_id}` | `not_found` |
| 4 | POST | /tasks/{id}/done | none | `{task, event_id}` | `not_found` |
| 4 | POST | /tasks/{id}/skip | none | `{task, event_id}` | `not_found` |
| 4 | PUT | /items/{public_id}/maintenance | `{enabled, interval_days?, first_due?, source?}` (creates or updates the item's maintenance task) | task | `validation_error` |
| 4 | POST | /items/{public_id}/inspections | `{result:'ok'\|'worn'\|'defective', note?, photo_id?}` | `{inspection, task\|null, event_id}` | `validation_error` |
| 4 | GET | /items/{public_id}/inspections | none | `{items:[inspection]}` | `not_found` |

### 2.12 Notifications
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 4 | GET | /notifications | query `status` (`open` default, `snoozed`, `resolved`, `all`), `limit`, `cursor` | `{items:[NotificationView], next_cursor}` | |
| 4 | GET | /notifications/count | none | `{open, unread}` | |
| 4 | POST | /notifications/{id}/read | none | 204 | `not_found` |
| 4 | POST | /notifications/read-all | none | `{updated:n}` | |
| 4 | POST | /notifications/{id}/snooze | `{option:'tomorrow'\|'3days'\|'week'}` | NotificationView | `not_found` |
| 4 | POST | /notifications/{id}/shown | none | 204 (records `os_notified_at` so a browser alert shows once) | `not_found` |

### 2.13 Dashboard
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 5 | GET | /dashboard | none | `{today, greeting:{part:'morning'\|'afternoon'\|'evening'\|'night', name}, subtitle, item_count, score\|null, rings:{documented,located,fresh,on_time}, attention:{rows:[NotificationView], total}, road:{start,end,events:[{date,kind,label,count}], truck_date}, savings:{month_paise, pill_date\|null}\|null, streak:{days}\|null}`; each ring `{value\|null, num, den}`. `savings` is `null` until Phase 6 data exists | |
| 5 | GET | /dashboard/rings/{ring} | `ring` is `documented`, `located`, `fresh` or `on_time` | `{ring, value, num, den, qualifying:[ItemSummary\|task], failing:[ItemSummary\|task]}` (up to 200 each) | `not_found` |

### 2.14 Ownership and savings
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 6 | POST | /ownership/check | multipart: `image?` and form `text?` (at least one) | `{query:{lines:[string], fields:{}}, candidates:[{public_id,name,primary_photo_id,location_path,quantity,score,level:'high'\|'medium'\|'low',reasons:[string]}], engine:{ocr, gemini_used}}` (max 5, never certain) | `validation_error`, `unsupported_media` |
| 6 | POST | /savings | `{item_public_id?, item_name?, price_paise*, note?}` | 201 `{id, event_id}` | `validation_error` |
| 6 | GET | /savings | query `period` (`month` default, `all`), `limit`, `cursor` | `{total_paise, month_paise, items:[{id,item_name,item_public_id\|null,price_paise,local_date,note}], next_cursor}` | |
| 6 | DELETE | /savings/{id} | none | `{event_id}` | `not_found` |

### 2.15 Camera coach
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 7 | POST | /capture/frame | multipart `image` (JPEG up to 200 KB) | `{text_found, confidence, boxes:[{x,y,w,h,conf,kind:'text'\|'model'\|'date'}], fields:{model?, date?}}` | `busy`, `rate_limited` |

### 2.16 Assistant
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 9 | POST | /assistant/chat | `{messages:[{role:'user'\|'assistant', content}]}` | `{reply, cited:[{public_id,name}], tools_used:[string]}` | `gemini_disabled`, `upstream_unavailable` |

### 2.17 Test-only (exist only when `ENDERCHEST_ENV=test` **and** `meta.env_marker='test'`; otherwise 404)
| Ph | Method | Path | Request | Success | Errors |
|---|---|---|---|---|---|
| 0 | POST | /test/reset | none | wipes the test database and files, re-initialises | `forbidden_host` |
| 0 | POST | /test/delete-db | none | deletes only the test database file (probe 8) | |
| 0 | POST | /test/write-loop | `{seconds}` | starts a background loop of marked writes (probe 6) | |
| 0 | GET | /test/write-loop | none | `{running, rows, counter, consistent, quick_check}`: the loop's records must be 1..N with the counter equal to N (probes 1 to 6, 8, 11; D-075) | |
| 0 | GET | /test/clock | none | `{now, local_date}` | |
| 0 | POST | /test/clock | `{now?, advance_seconds?, local_date?}` | `{now, local_date}` | |
| 2 | POST | /test/fixtures/{name} | none | loads a named fixture set into the **test** database: `items-1000` from Phase 2 (D-092), `storyboard-1` in Phase 5 | `not_found` |
