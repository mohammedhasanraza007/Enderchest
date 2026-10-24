"""Phase 2 verification probes V2 to V8, V10 (API part) and V11 (docs/reviews/phase-2-verification.md).

Runs INSIDE the test app container (enderchest-test-app-1) against the TEST stack only:
    docker cp probes_v.py enderchest-test-app-1:/tmp/ && docker exec enderchest-test-app-1 python /tmp/probes_v.py V2
It reads the test database read-only and lists /data folders to check that nothing is half-written.
"""

import hashlib
import io
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

from PIL import Image

assert os.environ.get("ENDERCHEST_ENV") == "test", "test stack only"
HOST = "127.0.0.1:" + os.environ["ENDERCHEST_PORT"]
API = "http://127.0.0.1:8470/api/v1"
DB = "/data/db/enderchest.sqlite3"
RESULTS: list[tuple[str, bool, str]] = []


def call(method, path, body=None, headers=None, raw=None, ctype=None, timeout=120):
    h = {"Host": HOST, "X-Enderchest": "1"}
    data = None
    if raw is not None:
        data, h["Content-Type"] = raw, ctype
    elif body is not None:
        data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
    if headers:
        h.update(headers)
    h = {k: v for k, v in h.items() if v is not None}
    req = urllib.request.Request(API + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            status, hdrs = r.status, r.headers
    except urllib.error.HTTPError as e:
        payload, status, hdrs = e.read(), e.code, e.headers
    if hdrs.get_content_type() == "application/json" and payload:
        return status, json.loads(payload), hdrs
    return status, payload, hdrs


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def code_of(body):
    return body.get("error", {}).get("code") if isinstance(body, dict) else None


def multipart(files):
    boundary = uuid.uuid4().hex
    out = []
    for field, name, data, ctype in files:
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
                   f'filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + data + b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def jpeg(w=640, h=480, colour=(120, 80, 40), quality=90):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def noisy_jpeg(w, h):
    buf = io.BytesIO()
    Image.frombytes("RGB", (w, h), os.urandom(w * h * 3)).save(buf, "JPEG", quality=100)
    return buf.getvalue()


def ro():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def snapshot():
    con = ro()
    rows = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("items", "photos", "drafts", "events")}
    con.close()
    files = {d: len(os.listdir(f"/data/{d}")) for d in ("photos", "thumbs", "upload-tmp")}
    return rows, files


def reset(name="Mohammed", tz="Asia/Kolkata"):
    s, b, _ = call("POST", "/test/reset")
    assert s == 200, (s, b)
    for _ in range(60):
        s, b, _ = call("GET", "/profile")
        if s == 200:
            break
        time.sleep(0.5)
    s, b, _ = call("PUT", "/profile", {"name": name, "timezone": tz})
    assert s == 200, (s, b)


def new_item(name="Probe item", **extra):
    s, b, _ = call("POST", "/items", {"name": name, **extra})
    assert s == 201, (s, b)
    return b["public_id"]


def upload(public_id, data, name="p.jpg", ctype="image/jpeg"):
    raw, ct = multipart([("image", name, data, ctype)])
    return call("POST", f"/items/{public_id}/photos", raw=raw, ctype=ct)


def parallel(n, fn):
    out, threads = [None] * n, []
    barrier = threading.Barrier(n)

    def run(i):
        barrier.wait()
        out[i] = fn(i)

    for i in range(n):
        threads.append(threading.Thread(target=run, args=(i,)))
        threads[-1].start()
    for t in threads:
        t.join()
    return out


# ---- V2: hostile uploads leave nothing half-written -------------------------------------------

def v2():
    reset()
    pid = new_item("Upload target")
    good = jpeg()
    s, b, _ = upload(pid, good)
    check("V2 a good JPEG is accepted", s == 201, f"{s}")
    base = snapshot()
    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 2000
    big = noisy_jpeg(2600, 1700)
    big = big + b"\x00" * (12 * 1024 * 1024 + 1 - len(big)) if len(big) <= 12 * 1024 * 1024 else big
    cases = [
        ("HEIC by bytes, named .jpg", heic, "photo.jpg", "image/jpeg"),
        ("PDF named .jpg", b"%PDF-1.7\n" + b"0" * 4000, "scan.jpg", "image/jpeg"),
        ("SVG named .png", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', "x.png", "image/png"),
        ("12 MB + 1 byte", big, "big.jpg", "image/jpeg"),
        ("truncated JPEG", good[: len(good) // 2], "half.jpg", "image/jpeg"),
        ("zero bytes", b"", "empty.jpg", "image/jpeg"),
        ("GIF", b"GIF89a" + b"\x00" * 100, "a.gif", "image/gif"),
    ]
    s, b, _ = upload(pid, good, "IMG_0001.HEIC", "image/heic")
    check("V2 JPEG bytes named .HEIC are judged by their bytes (stored as JPEG)", s == 201, f"{s}")
    for label, data, name, ctype in cases:
        base = snapshot()
        s, b, _ = upload(pid, data, name, ctype)
        snap = snapshot()
        check(f"V2 {label} refused, nothing written", s >= 400 and snap == base,
              f"{s} {code_of(b)} {b.get('error', {}).get('message') if isinstance(b, dict) else ''}"
              + ("" if snap == base else f" CHANGED {snap} vs {base}"))
    # Hostile file names on a good image: stored under a UUID, never the given name.
    for name in ("../../db/x.jpg", "..\\..\\x.jpg", "a" * 300 + ".jpg", "x.jpg\r\nX-Evil: 1"):
        s, b, _ = upload(pid, good, name)
        files = os.listdir("/data/photos")
        bad = [f for f in files if not f.endswith(".jpg") or len(f) != 40]
        escaped = os.path.exists("/data/db/x.jpg") or os.path.exists("/data/x.jpg")
        check(f"V2 name {name[:20]!r} stored as a UUID", s in (201, 400, 422) and not bad and not escaped,
              f"{s} odd files {bad[:2]}")
    # The 13th photo.
    con = ro()
    live = con.execute("SELECT COUNT(*) FROM photos p JOIN items i ON i.id = p.item_id "
                       "WHERE i.public_id = ? AND p.deleted_at IS NULL", (pid,)).fetchone()[0]
    con.close()
    for _ in range(12 - live):
        upload(pid, jpeg(colour=(10, 200, 30)))
    before = snapshot()
    s, b, _ = upload(pid, good)
    check("V2 the 13th photo is refused (limit_reached), nothing written",
          s == 409 and code_of(b) == "limit_reached" and snapshot() == before, f"{s} {code_of(b)}")
    # Drafts: 21 files, then 19 good + 1 bad.
    before = snapshot()
    raw, ct = multipart([("images[]", f"d{i}.jpg", good, "image/jpeg") for i in range(21)])
    s, b, _ = call("POST", "/drafts", raw=raw, ctype=ct)
    check("V2 21 files to POST /drafts refused, nothing written", s >= 400 and snapshot() == before,
          f"{s} {code_of(b)}")
    raw, ct = multipart([("images[]", f"d{i}.jpg", good, "image/jpeg") for i in range(19)]
                        + [("images[]", "bad.jpg", b"%PDF-1.7 nope", "image/jpeg")])
    s, b, _ = call("POST", "/drafts", raw=raw, ctype=ct)
    check("V2 19 good + 1 bad to POST /drafts refused whole, nothing written",
          s >= 400 and snapshot() == before, f"{s} {code_of(b)}")
    raw, ct = multipart([("images[]", f"d{i}.jpg", jpeg(colour=(i * 10, 50, 50)), "image/jpeg")
                         for i in range(20)])
    s, b, _ = call("POST", "/drafts", raw=raw, ctype=ct)
    check("V2 20 good files make 20 drafts", s == 201 and len(b["drafts"]) == 20, f"{s}")
    # EXIF and metadata: an image with EXIF GPS is stored without it.
    img = Image.new("RGB", (800, 600), (200, 10, 10))
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90
    exif[0x010F] = "SecretCam"
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes())
    pid2 = new_item("Exif item")
    s, b, _ = upload(pid2, buf.getvalue())
    con = ro()
    path = con.execute("SELECT path FROM photos WHERE id = ?", (b["id"],)).fetchone()[0]
    con.close()
    stored = open(f"/data/photos/{path}", "rb").read()
    with Image.open(io.BytesIO(stored)) as im:
        check("V2 EXIF applied (upright 600x800) and stripped",
              im.size == (600, 800) and not im.getexif() and b"SecretCam" not in stored,
              f"size {im.size} exif keys {list(im.getexif().keys())}")
    left = os.listdir("/data/upload-tmp")
    check("V2 upload-tmp is empty at the end", not left, f"{left[:3]}")


# ---- V3: double submit and concurrency --------------------------------------------------------

def v3():
    reset()
    key = str(uuid.uuid4())
    res = parallel(10, lambda i: call("POST", "/items", {"name": "Twin"},
                                      headers={"Idempotency-Key": key}))
    ids = {b["public_id"] for s, b, _ in res if s == 201}
    con = ro()
    rows = con.execute("SELECT COUNT(*) FROM items WHERE name = 'Twin'").fetchone()[0]
    con.close()
    check("V3 10 parallel POST /items with one key make one item",
          all(s == 201 for s, _, _ in res) and len(ids) == 1 and rows == 1,
          f"statuses {sorted({s for s, _, _ in res})} ids {len(ids)} rows {rows}")
    raw, ct = multipart([("images[]", "a.jpg", jpeg(), "image/jpeg"),
                         ("images[]", "b.jpg", jpeg(colour=(1, 2, 3)), "image/jpeg")])
    s, b, _ = call("POST", "/drafts", raw=raw, ctype=ct)
    d1, d2 = b["drafts"][0]["id"], b["drafts"][1]["id"]
    for d in (d1, d2):
        call("PATCH", f"/drafts/{d}", {"fields": {"name": f"Draft {d[:4]}", "expiry_mode": "none"}})
    key = str(uuid.uuid4())
    res = parallel(10, lambda i: call("POST", f"/drafts/{d1}/commit", headers={"Idempotency-Key": key}))
    ids = {b["public_id"] for s, b, _ in res if s == 201}
    check("V3 10 parallel commits with one key make one item",
          all(s == 201 for s, _, _ in res) and len(ids) == 1, f"{sorted({s for s, _, _ in res})} {len(ids)}")
    res = parallel(10, lambda i: call("POST", f"/drafts/{d2}/commit"))
    ok = [b for s, b, _ in res if s == 201]
    con = ro()
    made = con.execute("SELECT COUNT(*) FROM items WHERE name = ?", (f"Draft {d2[:4]}",)).fetchone()[0]
    photos = con.execute("SELECT COUNT(*) FROM photos WHERE item_id = (SELECT id FROM items "
                         "WHERE name = ?)", (f"Draft {d2[:4]}",)).fetchone()[0]
    con.close()
    check("V3 10 parallel commits without a key: exactly one item, the rest conflict",
          len(ok) == 1 and made == 1 and photos == 1
          and all(code_of(b) == "conflict" for s, b, _ in res if s != 201),
          f"{sorted(s for s, _, _ in res)} items {made} photos {photos}")
    pid = new_item("Racer")
    res = parallel(10, lambda i: call("PATCH", f"/items/{pid}", {"name": f"Racer {i}"}))
    s, b, _ = call("GET", f"/items/{pid}")
    con = ro()
    ev = con.execute("SELECT COUNT(*) FROM events WHERE kind = 'item_updated' AND item_id = "
                     "(SELECT id FROM items WHERE public_id = ?)", (pid,)).fetchone()[0]
    con.close()
    check("V3 10 parallel PATCH on one item: all 200, 10 events, a final name",
          all(s == 200 for s, _, _ in res) and ev == 10 and b["name"].startswith("Racer "),
          f"{sorted({s for s, _, _ in res})} events {ev}")
    pid = new_item("Photo racer")
    for _ in range(9):
        upload(pid, jpeg())
    res = parallel(6, lambda i: upload(pid, jpeg(colour=(i, i, i))))
    con = ro()
    live = con.execute("SELECT COUNT(*) FROM photos p JOIN items i ON i.id = p.item_id WHERE "
                       "i.public_id = ? AND p.deleted_at IS NULL", (pid,)).fetchone()[0]
    con.close()
    rows, files = snapshot()
    check("V3 6 parallel uploads onto 9 photos: 12 live, 3 refused, files equal rows",
          live == 12 and sum(s == 201 for s, _, _ in res) == 3 and files["photos"] == rows["photos"]
          and files["upload-tmp"] == 0,
          f"live {live} statuses {sorted(s for s, _, _ in res)} files {files} rows {rows}")
    con = ro()
    check("V3 integrity_check ok", con.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    con.close()


# ---- V4: permanent delete ---------------------------------------------------------------------

def v4():
    reset()
    pid = new_item("Doomed")
    s, b, _ = upload(pid, jpeg())
    photo = b["id"]
    con = ro()
    path, thumb = con.execute("SELECT path, thumb_path FROM photos WHERE id = ?", (photo,)).fetchone()
    con.close()
    s, b, _ = call("DELETE", f"/items/{pid}/permanent", {"confirm": "DELETE"})
    check("V4 an item not in Trash is refused (not_deleted)", s == 409 and code_of(b) == "not_deleted",
          f"{s} {code_of(b)}")
    call("DELETE", f"/items/{pid}")
    for bad in ({"confirm": "delete"}, {"confirm": "DELETE "}, {}, {"confirm": "DELETE", "x": 1}):
        s, b, _ = call("DELETE", f"/items/{pid}/permanent", bad)
        check(f"V4 confirm {bad} refused", s == 422 and code_of(b) == "validation_error", f"{s} {code_of(b)}")
    s, b, _ = call("GET", "/backups")
    good = [x for x in (b if isinstance(b, list) else b.get("items", b.get("backups", [])))]
    s, b, _ = call("POST", "/test/clock", {"advance_seconds": 25 * 3600})
    s, b, _ = call("DELETE", f"/items/{pid}/permanent", {"confirm": "DELETE"})
    check("V4 no good backup under 24 h (clock +25 h): backup_required",
          s == 409 and code_of(b) == "backup_required", f"{s} {code_of(b)} backups listed {len(good)}")
    # Backup log times use the real clock (clock.py), so move the test clock back first.
    call("POST", "/test/clock", {"advance_seconds": -25 * 3600})
    s, b, _ = call("POST", "/backups")
    check("V4 Back up now works on the test stack", s == 201, f"{s} {code_of(b)}")
    s, b, _ = call("DELETE", f"/items/{pid}/permanent", {"confirm": "DELETE"})
    gone = not os.path.exists(f"/data/photos/{path}") and not os.path.exists(f"/data/thumbs/{thumb}")
    con = ro()
    row = con.execute("SELECT COUNT(*) FROM items WHERE public_id = ?", (pid,)).fetchone()[0]
    prow = con.execute("SELECT COUNT(*) FROM photos WHERE id = ?", (photo,)).fetchone()[0]
    ev = con.execute("SELECT payload, item_id FROM events WHERE kind = 'item_purged'").fetchall()
    con.close()
    payload = json.loads(ev[0]["payload"]) if ev else {}
    check("V4 permanent delete: 204, row, photo row and files gone, item_purged keeps name and id only",
          s == 204 and gone and row == 0 and prow == 0 and len(ev) == 1
          and set(payload) == {"name", "public_id"} and payload["public_id"] == pid,
          f"{s} files gone {gone} rows {row}/{prow} event {payload}")
    s1, _, _ = call("GET", f"/items/{pid}")
    s2, _, _ = call("GET", f"/lookup/{pid}")
    s3, b3, _ = call("DELETE", f"/items/{pid}/permanent", {"confirm": "DELETE"})
    check("V4 a purged id: item 404, lookup 404, second purge 404", (s1, s2, s3) == (404, 404, 404),
          f"{s1} {s2} {s3} {code_of(b3)}")
    in_backup = any(pid.encode() in open(os.path.join(dp, f), "rb").read()
                    for dp, _, fs in os.walk("/backups") for f in fs if f.endswith(".sqlite3"))
    check("V4 older backups still hold the item (what the dialog says)", in_backup)


# ---- V5: undo window and photo hide -----------------------------------------------------------

def v5():
    reset()
    pid = new_item("Undo me")
    s, b, _ = call("DELETE", f"/items/{pid}")
    ev1 = b["event_id"]
    call("POST", "/test/clock", {"advance_seconds": 59})
    s, b, _ = call("POST", f"/events/{ev1}/undo")
    s2, item, _ = call("GET", f"/items/{pid}")
    check("V5 undo at 59 s restores the item", s == 200 and item["deleted_at"] is None, f"{s} {code_of(b)}")
    s, b, _ = call("POST", f"/events/{ev1}/undo")
    check("V5 the same undo twice is refused", s == 409, f"{s} {code_of(b)}")
    s, b, _ = call("DELETE", f"/items/{pid}")
    ev2 = b["event_id"]
    call("POST", "/test/clock", {"advance_seconds": 61})
    s, b, _ = call("POST", f"/events/{ev2}/undo")
    s2, item, _ = call("GET", f"/items/{pid}")
    check("V5 undo at 61 s is refused (undo_expired), item stays in Trash",
          s == 409 and code_of(b) == "undo_expired" and item["deleted_at"] is not None, f"{s} {code_of(b)}")
    con = ro()
    created = con.execute("SELECT id FROM events WHERE kind = 'item_created'").fetchone()[0]
    con.close()
    s, b, _ = call("POST", f"/events/{created}/undo")
    check("V5 undo of item_created is refused", s in (409, 422), f"{s} {code_of(b)}")
    s, b, _ = call("POST", "/events/999999/undo")
    check("V5 undo of an unknown event is 404", s == 404, f"{s} {code_of(b)}")
    s, b, _ = call("POST", f"/items/{pid}/restore")
    check("V5 restore from Trash after the window", s == 200 and b["deleted_at"] is None, f"{s}")
    s, b, _ = call("DELETE", f"/items/{pid}")
    ev3 = b["event_id"]
    call("POST", f"/items/{pid}/restore")
    s, b, _ = call("POST", f"/events/{ev3}/undo")
    s2, item, _ = call("GET", f"/items/{pid}")
    check("V5 undo after a manual restore does nothing harmful", item["deleted_at"] is None,
          f"undo {s} {code_of(b)}")
    s, b, _ = upload(pid, jpeg())
    s, b2, _ = upload(pid, jpeg(colour=(9, 9, 9)))
    photo = b["id"]
    con = ro()
    path = con.execute("SELECT path FROM photos WHERE id = ?", (photo,)).fetchone()[0]
    con.close()
    s, b, _ = call("DELETE", f"/photos/{photo}")
    s2, item, _ = call("GET", f"/items/{pid}")
    check("V5 Delete photo: 204, file still on disk, photo gone from the item, primary moves",
          s == 204 and os.path.exists(f"/data/photos/{path}")
          and photo not in [p["id"] for p in item["photos"]] and item["primary_photo_id"] == b2["id"],
          f"{s} primary {item['primary_photo_id']}")
    s, b, _ = call("GET", f"/photos/{photo}/file")
    check("V5 a hidden photo's file is no longer served", s == 404, f"{s}")
    call("POST", "/test/clock", {"advance_seconds": -120})


# ---- V6: search and filters on items-1000 -----------------------------------------------------

def walk(params):
    seen, cursor, pages, total = [], None, 0, None
    while True:
        q = dict(params, limit=37)
        if cursor:
            q["cursor"] = cursor
        s, b, _ = call("GET", "/items?" + urllib.parse.urlencode(q))
        assert s == 200, (s, b, q)
        total = b["total"] if total is None else total
        seen += [x["public_id"] for x in b["items"]]
        pages += 1
        cursor = b["next_cursor"]
        if not cursor or pages > 60:
            return seen, total


def v6():
    import urllib.parse  # noqa: F401  (used by walk)
    reset()
    s, b, _ = call("POST", "/test/fixtures/items-1000")
    check("V6 fixture loads", s == 200, f"{s} {b}")
    s, clk, _ = call("GET", "/test/clock")
    today = clk["local_date"]
    s, st, _ = call("GET", "/settings")
    lead = st.get("lead_days", 3) if isinstance(st, dict) else 3
    import datetime as dt
    soon_until = (dt.date.fromisoformat(today) + dt.timedelta(days=lead)).isoformat()
    con = ro()
    items = [dict(r) for r in con.execute("SELECT * FROM items")]
    locs = {r["id"]: r["parent_id"] for r in con.execute("SELECT id, parent_id FROM locations")}
    cats = [r["id"] for r in con.execute("SELECT id FROM categories")]
    con.close()

    def under(loc, root):
        while loc is not None:
            if loc == root:
                return True
            loc = locs[loc]
        return False

    def expect(state="active", deleted="exclude", category=None, location=None, expiry="any",
               has_photo=None, q=""):
        out = []
        for it in items:
            if (it["deleted_at"] is None) != (deleted == "exclude"):
                continue
            if state != "all" and it["state"] != state:
                continue
            if category is not None and it["category_id"] != category:
                continue
            if location is not None and not under(it["location_id"], location):
                continue
            if has_photo is not None and (it["primary_photo_id"] is not None) != has_photo:
                continue
            d, m = it["expiry_date"], it["expiry_mode"]
            if expiry == "soon" and not (m == "date" and today < d <= soon_until):
                continue
            if expiry == "today" and not (m == "date" and d == today):
                continue
            if expiry == "past" and not (m == "date" and d < today):
                continue
            if expiry in ("none", "unknown") and m != expiry:
                continue
            hay = (it["name"] + " " + it["public_id"]).lower()
            if any(w not in hay for w in q.lower().split()):
                continue
            out.append(it["public_id"])
        return out

    cases = [{}]
    cases += [{"state": s} for s in ("used", "expired", "discarded", "all")]
    cases += [{"deleted": "only", "state": "all"}]
    cases += [{"category_id": c} for c in cats]
    cases += [{"location_id": loc} for loc in locs]
    cases += [{"expiry": e} for e in ("soon", "today", "past", "none", "unknown")]
    cases += [{"has_photo": "true"}, {"has_photo": "false"}]
    cases += [{"q": w} for w in ("spanner", "SPANNER", "blue drill", "7", "zz-nothing", "%", "_")]
    cases += [{"location_id": list(locs)[0], "expiry": "past", "state": "all"}]
    bad = []
    for case in cases:
        mapped = {"category": case.get("category_id"), "location": case.get("location_id"),
                  "state": case.get("state", "active"), "deleted": case.get("deleted", "exclude"),
                  "expiry": case.get("expiry", "any"), "q": case.get("q", ""),
                  "has_photo": None if "has_photo" not in case else case["has_photo"] == "true"}
        want = expect(**mapped)
        got, total = walk(case)
        if sorted(got) != sorted(want) or total != len(want) or len(got) != len(set(got)):
            bad.append(f"{case}: api {len(got)} (total {total}) vs expected {len(want)}")
    check(f"V6 {len(cases)} filter cases equal an independent filter over the table", not bad,
          "; ".join(bad[:6]))
    # A public id typed in the search pill.
    pid = items[10]["public_id"]
    got, _ = walk({"q": pid.lower(), "state": "all"})
    check("V6 a public id in the search finds that item", got == [pid], f"{got[:3]}")
    # Attribute JSON keys must not match: 'size' is a key in every 7th item, never a value.
    got, total = walk({"q": "size"})
    check("V6 searching 'size' (an attribute KEY) does not match every item that has the key",
          total == len(expect(q="size")), f"api {total} vs names containing 'size' {len(expect(q='size'))}")
    # Sort orders: paging returns every item once, in the documented order.
    for sort, keyf in (("name_asc", lambda it: (it["name"].lower(), it["id"])),
                       ("created_desc", lambda it: (it["created_at"], it["id"]))):
        got, _ = walk({"sort": sort, "state": "all"})
        live = [it for it in items if it["deleted_at"] is None]
        want = [it["public_id"] for it in sorted(live, key=keyf, reverse=(sort == "created_desc"))]
        check(f"V6 sort {sort}: paging returns every item once in order", got == want,
              f"{len(got)} vs {len(want)}")
    t = []
    for _ in range(5):
        start = time.perf_counter()
        call("GET", "/items?limit=100")
        t.append((time.perf_counter() - start) * 1000)
    check("V6 first page of 100 within 150 ms", max(t) < 150, f"ms {[round(x) for x in t]}")


# ---- V7: category and location rules ----------------------------------------------------------

def v7():
    reset()
    s, c1, _ = call("POST", "/categories", {"name": "Tools"})
    for name in ("tools", "TOOLS", "  Tools  ", "Tools "):
        s, b, _ = call("POST", "/categories", {"name": name})
        check(f"V7 duplicate category {name!r} refused", s == 409 and code_of(b) == "conflict",
              f"{s} {code_of(b)}")
    s, a, _ = call("POST", "/categories", {"name": "Ölfarben"})
    s, b, _ = call("POST", "/categories", {"name": "ölfarben"})
    check("V7 non-ASCII duplicate 'ölfarben' vs 'Ölfarben' refused", s == 409, f"{s} {code_of(b)}")
    s, l1, _ = call("POST", "/locations", {"name": "Garage"})
    s, l2, _ = call("POST", "/locations", {"name": "Shelf", "parent_id": l1["id"]})
    s, l3, _ = call("POST", "/locations", {"name": "Box", "parent_id": l2["id"]})
    s, b, _ = call("POST", "/locations", {"name": "shelf", "parent_id": l1["id"]})
    check("V7 duplicate sibling location refused", s == 409, f"{s} {code_of(b)}")
    s, b, _ = call("POST", "/locations", {"name": "Shelf"})
    check("V7 the same name under another parent is allowed", s == 201, f"{s} {code_of(b)}")
    s, b, _ = call("POST", "/locations", {"name": "shelf"})
    check("V7 duplicate top-level location refused (NULL parent)", s == 409, f"{s} {code_of(b)}")
    s, b, _ = call("PATCH", f"/locations/{l1['id']}", {"parent_id": l3["id"]})
    check("V7 moving Garage under its grandchild is a cycle", s == 409 and code_of(b) == "cycle",
          f"{s} {code_of(b)}")
    s, b, _ = call("PATCH", f"/locations/{l1['id']}", {"parent_id": l1["id"]})
    check("V7 moving Garage under itself is a cycle", s == 409 and code_of(b) == "cycle", f"{s} {code_of(b)}")
    parent, chain, level_ids = None, [], {}
    for depth in range(1, 7):
        s, b, _ = call("POST", "/locations", {"name": f"Level {depth}", "parent_id": parent})
        chain.append((depth, s, code_of(b)))
        level_ids[depth] = b.get("id") if s == 201 else None
        parent = b.get("id", parent) if s == 201 else parent
    check("V7 depth 5 allowed, depth 6 refused", [x[1] for x in chain] == [201] * 5 + [422]
          or (chain[5][1] >= 400 and all(x[1] == 201 for x in chain[:5])), f"{chain}")
    s, top, _ = call("POST", "/locations", {"name": "Top"})
    s, b, _ = call("PATCH", f"/locations/{top['id']}", {"parent_id": parent})
    check("V7 moving a location below depth 5 is refused", s >= 400, f"{s} {code_of(b)}")
    s, sub, _ = call("POST", "/locations", {"name": "Sub", "parent_id": top["id"]})
    # Top under Level 4 is depth 5, but its child Sub would be depth 6.
    s, b, _ = call("PATCH", f"/locations/{top['id']}", {"parent_id": level_ids[4]})
    check("V7 moving a location whose child would land at depth 6 is refused", s >= 400,
          f"{s} {code_of(b)}")
    # Reassign on delete, including an item in Trash.
    s, c2, _ = call("POST", "/categories", {"name": "Spare"})
    live = new_item("Live hammer", category_id=c1["id"], location_id=l3["id"])
    trashed = new_item("Trashed hammer", category_id=c1["id"], location_id=l3["id"])
    call("DELETE", f"/items/{trashed}")
    s, b, _ = call("DELETE", f"/categories/{c1['id']}")
    check("V7 deleting a used category without reassign_to is in_use", s == 409 and code_of(b) == "in_use",
          f"{s} {code_of(b)} {b.get('error', {}).get('details') if isinstance(b, dict) else ''}")
    s, b, _ = call("DELETE", f"/categories/{c1['id']}?reassign_to={c2['id']}")
    s1, i1, _ = call("GET", f"/items/{live}")
    s2, i2, _ = call("POST", f"/items/{trashed}/restore")
    check("V7 category delete reassigns live and trashed items",
          s == 204 and i1["category"]["id"] == c2["id"] and i2["category"]["id"] == c2["id"],
          f"{s} {i1.get('category')} {i2.get('category')}")
    s, b, _ = call("DELETE", f"/locations/{l1['id']}")
    check("V7 a location with children cannot be deleted (has_children)",
          s == 409 and (b["error"]["details"] or {}).get("reason") == "has_children", f"{s} {b}")
    s, b, _ = call("DELETE", f"/locations/{l3['id']}?reassign_to=none")
    s1, i1, _ = call("GET", f"/items/{live}")
    check("V7 location delete with reassign_to=none leaves no location",
          s == 204 and i1["location"] is None, f"{s} {i1.get('location')}")
    s, b, _ = call("DELETE", f"/categories/{c2['id']}?reassign_to={c2['id']}")
    check("V7 reassigning a category to itself is refused", s >= 400, f"{s} {code_of(b)}")
    s, b, _ = call("POST", "/categories", {"name": "Tools"})
    check("V7 a deleted category's name can be used again", s == 201, f"{s} {code_of(b)}")


# ---- V8: lookup and ids -----------------------------------------------------------------------

def v8():
    reset()
    pid = new_item("Label me")
    body = pid[5:]
    typed = {
        "lowercase with dash": pid.lower(),
        "no dash": pid.replace("-", ""),
        "lowercase no dash": pid.replace("-", "").lower(),
        "spaces around": f"  {pid}  ",
        "O for 0, I and L for 1": "ENDR-" + body.replace("0", "O").replace("1", "I"),
        "only the 8 characters": body,
    }
    for label, code in typed.items():
        s, b, _ = call("GET", "/lookup/" + urllib.parse.quote(code))
        check(f"V8 lookup {label} ({code!r})", s == 200 and b.get("public_id") == pid, f"{s} {code_of(b)}")
    for label, code in {"unknown valid id": "ENDR-00000000", "wrong length": pid + "X",
                        "garbage": "hello", "a URL": "https://x.test/" + pid}.items():
        s, b, _ = call("GET", "/lookup/" + urllib.parse.quote(code, safe=""))
        check(f"V8 lookup {label} is a clean 404", s == 404 and code_of(b) == "not_found", f"{s} {code_of(b)}")
    call("PATCH", f"/items/{pid}", {"name": "Renamed", "notes": "x"})
    s, b, _ = call("GET", f"/lookup/{pid}")
    check("V8 the id survives an edit", s == 200 and b["name"] == "Renamed", f"{s}")
    call("DELETE", f"/items/{pid}")
    s, b, _ = call("GET", f"/lookup/{pid}")
    check("V8 lookup of a trashed item answers it with deleted_at set (the item page shows In Trash)",
          s == 200 and b["deleted_at"] is not None, f"{s} {code_of(b)}")
    call("POST", f"/items/{pid}/restore")
    s, svg, h = call("GET", f"/items/{pid}/qr.svg")
    check("V8 qr.svg is image/svg+xml and carries no item data in text",
          s == 200 and h.get_content_type() == "image/svg+xml" and b"Renamed" not in svg, f"{s}")
    open("/tmp/qr.svg", "wb").write(svg)
    s, b, _ = call("POST", "/items/label-printed", {"public_ids": [pid, "ENDR-00000000"]})
    s2, item, _ = call("GET", f"/items/{pid}")
    check("V8 label-printed with one unknown id", s in (200, 404, 422), f"{s} {b} printed_at "
          f"{item['label']['printed_at']}")
    s, b, _ = call("POST", "/items/label-printed", {"public_ids": []})
    check("V8 label-printed with an empty list", s in (200, 422), f"{s} {b}")


# ---- V10 (API part) and V11 -------------------------------------------------------------------

def v10():
    reset()
    pid = new_item("Guarded")
    s, b, _ = call("DELETE", f"/items/{pid}", headers={"X-Enderchest": None})
    check("V10 DELETE /items without X-Enderchest is 403", s == 403, f"{s} {code_of(b)}")
    raw, ct = multipart([("image", "p.jpg", jpeg(), "image/jpeg")])
    s, b, _ = call("POST", f"/items/{pid}/photos", raw=raw, ctype=ct,
                   headers={"Origin": "http://evil.test"})
    check("V10 upload with a foreign Origin is 403", s == 403, f"{s} {code_of(b)}")
    s, b, _ = call("POST", "/items", raw=raw, ctype=ct)
    check("V10 multipart on a JSON route is refused", s in (415, 422), f"{s} {code_of(b)}")
    s, b, _ = call("PATCH", f"/items/{pid}", raw=b'{"notes":"' + b"x" * (1024 * 1024) + b'"}',
                   ctype="application/json")
    check("V10 a JSON body over 1 MB is 413", s == 413 and code_of(b) == "payload_too_large", f"{s} {code_of(b)}")
    for path in ("/photos/..%2F..%2Fdb%2Fenderchest.sqlite3/file", "/photos/../../etc/passwd/file",
                 "/photos/%2e%2e/thumb", f"/photos/{uuid.uuid4()}/file"):
        s, b, _ = call("GET", path)
        check(f"V10 {path[:40]} is 404 and not a file", s == 404 and not (isinstance(b, bytes) and b),
              f"{s}")
    s, b, h = call("GET", "/items/ENDR-ZZZZZZZZ")
    check("V10 unknown item is a JSON 404", s == 404 and code_of(b) == "not_found", f"{s}")
    s, up, _ = upload(pid, jpeg())
    s, b, h = call("GET", f"/photos/{up['id']}/thumb")
    check("V10 thumb cache header is private, immutable", "immutable" in h.get("Cache-Control", "")
          and "private" in h.get("Cache-Control", "") and "Access-Control-Allow-Origin" not in h, f"{h.get('Cache-Control')}")


def v11():
    reset(tz="Asia/Kolkata")
    call("POST", "/test/clock", {"now": "2026-10-24T20:00:00Z"})
    s, clk, _ = call("GET", "/test/clock")
    a = new_item("Expired yesterday locally", expiry_mode="date", expiry_date="2026-10-24")
    b_ = new_item("Expires today locally", expiry_mode="date", expiry_date="2026-10-25")
    _, ia, _ = call("GET", f"/items/{a}")
    _, ib, _ = call("GET", f"/items/{b_}")
    check("V11 local date is 25 Oct in India at 20:00 UTC on 24 Oct", clk["local_date"] == "2026-10-25",
          f"{clk}")
    check("V11 an item expiring 24 Oct is expired; one expiring 25 Oct expires today",
          ia["expiry"]["status"] == "expired" and ib["expiry"]["status"] == "today"
          and ib["expiry"]["word"] == "expires today", f"{ia['expiry']} {ib['expiry']}")
    s, lst, _ = call("GET", "/items?expiry=today")
    check("V11 the 'today' filter uses the local date", [x["public_id"] for x in lst["items"]] == [b_],
          f"{[x['name'] for x in lst['items']]}")
    s, b, _ = call("POST", "/items", {"name": "Bad", "expiry_mode": "date"})
    s2, b2, _ = call("POST", "/items", {"name": "Bad", "expiry_mode": "none", "expiry_date": "2026-01-01"})
    s3, b3, _ = call("POST", "/items", {"name": "Bad", "expiry_mode": "date", "expiry_date": "2026-02-30"})
    check("V11 expiry mode and date must agree; 30 Feb refused", (s, s2, s3) == (422, 422, 422),
          f"{s} {s2} {s3}")
    call("POST", "/test/clock", {"now": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})


# ---- V12: survival (setup prints a manifest; check compares it after a restart) ----------------

def manifest():
    con = ro()
    items = sorted(r[0] for r in con.execute("SELECT public_id FROM items"))
    drafts = sorted(r[0] for r in con.execute("SELECT id FROM drafts WHERE status = 'open'"))
    photos = {r["id"]: r["sha256"] for r in con.execute("SELECT id, sha256, path FROM photos")}
    files = {r["id"]: hashlib.sha256(open(f"/data/photos/{r['path']}", "rb").read()).hexdigest()
             for r in con.execute("SELECT id, path FROM photos")}
    quick = con.execute("PRAGMA quick_check").fetchone()[0]
    con.close()
    return {"items": items, "drafts": drafts, "photos": photos, "files": files, "quick_check": quick}


def v12_setup():
    reset()
    for n in range(3):
        pid = new_item(f"Keeper {n}", quantity=n + 1)
        upload(pid, noisy_jpeg(900, 700))
    raw, ct = multipart([("images[]", f"d{i}.jpg", noisy_jpeg(500, 400), "image/jpeg") for i in range(2)])
    call("POST", "/drafts", raw=raw, ctype=ct)
    m = manifest()
    check("V12 setup: 3 items, 5 photos, 2 open drafts, every file matches its stored SHA-256",
          len(m["items"]) == 3 and len(m["photos"]) == 5 and len(m["drafts"]) == 2
          and m["photos"] == m["files"], f"{len(m['items'])} {len(m['photos'])} {len(m['drafts'])}")
    open("/data/v12-manifest.json", "w").write(json.dumps(m))
    print("MANIFEST " + json.dumps(m))


def v12_check():
    before = json.load(open("/data/v12-manifest.json"))
    now = manifest()
    check("V12 after the restart: same items, drafts, photo rows and file hashes; quick_check ok",
          now == before and now["quick_check"] == "ok",
          "" if now == before else f"before {before} now {now}")


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    which = sys.argv[1:] or ["V2", "V3", "V4", "V5", "V6", "V7", "V8", "V10", "V11"]
    for name in which:
        try:
            globals()[name.lower()]()
        except Exception as exc:  # a crash is a FAIL with its message, never a silent skip
            import traceback
            traceback.print_exc()
            check(f"{name} crashed", False, repr(exc))
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)
