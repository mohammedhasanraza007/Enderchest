"""Photos and drafts: the upload pipeline, limits, serving, the add flow (API 2.6, 2.8;
ARCHITECTURE 6 Uploads; D-095). Gates 1 (API half), 3 (photo kept) and 6."""

import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from tests import imagekit
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration


def create(stack: Stack, **fields) -> dict:
    response = stack.client.post("/api/v1/items", json={"name": "Thing", **fields},
                                 headers=HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def upload(stack: Stack, public_id: str, data: bytes, name: str = "photo.jpg"):
    return stack.client.post(f"/api/v1/items/{public_id}/photos", headers=HEADERS,
                             files={"image": (name, data, "image/jpeg")})


def make_drafts(stack: Stack, images: list[bytes]):
    files = [("images[]", (f"p{n}.jpg", data, "image/jpeg")) for n, data in enumerate(images)]
    return stack.client.post("/api/v1/drafts", headers=HEADERS, files=files)


def files_in(folder) -> set[str]:
    return {p.name for p in folder.iterdir()} if folder.is_dir() else set()


def opened(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


# ---- the pipeline -----------------------------------------------------------------------------

def test_a_photo_is_upright_stripped_reencoded_and_thumbnailed(stack: Stack):
    item = create(stack)
    response = upload(stack, item["public_id"], imagekit.jpeg(640, 480, rotated=True),
                      name="../../etc/passwd.jpg")
    assert response.status_code == 201, response.text
    photo = response.json()
    assert (photo["is_primary"], photo["width"], photo["height"]) == (True, 480, 640)

    original = stack.client.get(f"/api/v1/photos/{photo['id']}/file")
    assert original.headers["content-type"] == "image/jpeg"
    assert original.headers["cache-control"] == "private, max-age=31536000, immutable"
    image = opened(original.content)
    assert image.size == (480, 640)
    assert dict(image.getexif()) == {} and "comment" not in image.info

    thumb = opened(stack.client.get(f"/api/v1/photos/{photo['id']}/thumb").content)
    assert max(thumb.size) == 320
    # Files are named by UUID, never by the uploaded name.
    assert files_in(stack.settings.photos_dir) == {f"{photo['id']}.jpg"}
    assert files_in(stack.settings.upload_tmp_dir) == set()


def test_png_with_transparency_and_webp_are_accepted(stack: Stack):
    item = create(stack)
    png = upload(stack, item["public_id"], imagekit.png_with_alpha(), "a.png")
    assert png.status_code == 201
    pixel = opened(stack.client.get(f"/api/v1/photos/{png.json()['id']}/file").content
                   ).getpixel((5, 5))
    assert min(pixel) > 240  # transparency became white, not black
    assert upload(stack, item["public_id"], imagekit.webp(), "b.webp").status_code == 201


def test_a_large_photo_is_capped_at_2560_on_its_long_edge(stack: Stack):
    item = create(stack)
    photo = upload(stack, item["public_id"], imagekit.jpeg(4000, 3000)).json()
    assert (photo["width"], photo["height"]) == (2560, 1920)


@pytest.mark.parametrize("data, code, words", [
    (imagekit.heic_header(), "unsupported_media", "HEIC"),
    (b"%PDF-1.7 not an image", "unsupported_media", "JPEG, PNG or WebP"),
    (imagekit.truncated_jpeg(), "unsupported_media", "damaged"),
    (b"", "unsupported_media", "empty"),
])
def test_refused_uploads_leave_nothing_behind(stack: Stack, data, code, words):
    item = create(stack)
    response = upload(stack, item["public_id"], data)
    error = response.json()["error"]
    assert (error["code"], words in error["message"]) == (code, True)
    assert files_in(stack.settings.photos_dir) == files_in(stack.settings.thumbs_dir) == set()
    assert stack.client.get(f"/api/v1/items/{item['public_id']}").json()["photos"] == []


def test_an_oversize_upload_is_refused_before_it_is_read(stack: Stack):
    item = create(stack)
    big = b"\xff\xd8\xff" + b"0" * (13 * 1024 * 1024)
    response = upload(stack, item["public_id"], big)
    assert (response.status_code, response.json()["error"]["code"]) == (413, "payload_too_large")
    assert files_in(stack.settings.photos_dir) == set()


def test_a_file_just_over_12_mb_inside_the_framing_allowance_is_refused_too(stack: Stack):
    item = create(stack)
    response = upload(stack, item["public_id"], b"\xff\xd8\xff" + b"0" * (12 * 1024 * 1024))
    assert response.json()["error"]["code"] == "payload_too_large"


def test_multipart_is_refused_on_paths_that_take_json(stack: Stack):
    response = stack.client.post("/api/v1/items", headers=HEADERS,
                                 files={"image": ("a.jpg", imagekit.jpeg(), "image/jpeg")})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Requests must be JSON."


def test_a_json_body_over_1_mb_is_refused(stack: Stack):
    response = stack.client.post("/api/v1/items", headers=HEADERS,
                                 json={"name": "A", "notes": "x" * (1024 * 1024)})
    assert response.status_code == 413


def test_twelve_photos_per_item_then_limit_reached(stack: Stack):
    item = create(stack)
    small = imagekit.jpeg(64, 48)
    for _ in range(12):
        assert upload(stack, item["public_id"], small).status_code == 201
    refused = upload(stack, item["public_id"], small)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "limit_reached")
    assert len(files_in(stack.settings.photos_dir)) == 12


def test_concurrent_double_submit_leaves_whole_photos_only(stack: Stack):
    item = create(stack)
    data = imagekit.jpeg(800, 600)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: upload(stack, item["public_id"], data), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    detail = stack.client.get(f"/api/v1/items/{item['public_id']}").json()
    ids = {p["id"] for p in detail["photos"]}
    assert len(ids) == 2 and sum(p["is_primary"] for p in detail["photos"]) == 1
    assert files_in(stack.settings.photos_dir) == {f"{i}.jpg" for i in ids}
    assert files_in(stack.settings.upload_tmp_dir) == set()


# ---- primary, hide, serving ------------------------------------------------------------------

def test_primary_and_hide_keep_the_file_on_disk(stack: Stack):
    item = create(stack)
    first = upload(stack, item["public_id"], imagekit.jpeg()).json()
    second = upload(stack, item["public_id"], imagekit.jpeg(colour=(1, 2, 3))).json()
    assert second["is_primary"] is False
    made_primary = stack.client.put(f"/api/v1/items/{item['public_id']}/primary-photo",
                                    json={"photo_id": second["id"]}, headers=HEADERS).json()
    assert made_primary["primary_photo_id"] == second["id"]

    assert stack.client.delete(f"/api/v1/photos/{second['id']}",
                               headers=HEADERS).status_code == 204
    detail = stack.client.get(f"/api/v1/items/{item['public_id']}").json()
    assert detail["primary_photo_id"] == first["id"]  # the next photo takes over
    assert [p["id"] for p in detail["photos"]] == [first["id"]]
    assert f"{second['id']}.jpg" in files_in(stack.settings.photos_dir)  # file kept (gate 3)
    assert stack.client.delete(f"/api/v1/photos/{second['id']}",
                               headers=HEADERS).status_code == 404

    stack.client.delete(f"/api/v1/photos/{first['id']}", headers=HEADERS)
    assert stack.client.get("/api/v1/items?has_photo=false").json()["total"] == 1


def test_a_photo_of_another_item_cannot_become_primary(stack: Stack):
    one, two = create(stack), create(stack)
    photo = upload(stack, one["public_id"], imagekit.jpeg()).json()
    response = stack.client.put(f"/api/v1/items/{two['public_id']}/primary-photo",
                                json={"photo_id": photo["id"]}, headers=HEADERS)
    assert response.status_code == 404


def test_a_missing_thumbnail_is_made_again(stack: Stack):
    item = create(stack)
    photo = upload(stack, item["public_id"], imagekit.jpeg()).json()
    (stack.settings.thumbs_dir / f"{photo['id']}.jpg").unlink()
    response = stack.client.get(f"/api/v1/photos/{photo['id']}/thumb")
    assert response.status_code == 200 and max(opened(response.content).size) == 320


def test_unknown_photos_are_not_found(stack: Stack):
    for path in ("/api/v1/photos/nope/file", "/api/v1/photos/..%2F..%2Fdb/thumb"):
        assert stack.client.get(path).status_code == 404


def test_photos_survive_a_restart(settings):
    with Stack(settings) as stack:
        item = create(stack)
        photo = upload(stack, item["public_id"], imagekit.jpeg()).json()
        before = stack.client.get(f"/api/v1/photos/{photo['id']}/file").content
    with Stack(settings) as stack:
        assert stack.client.get(f"/api/v1/photos/{photo['id']}/file").content == before
        assert stack.client.get(f"/api/v1/items/{item['public_id']}").json()["photos"][0]["id"] \
            == photo["id"]


# ---- drafts -----------------------------------------------------------------------------------

def test_many_images_make_one_draft_each_and_count_nowhere(stack: Stack):
    response = make_drafts(stack, [imagekit.jpeg(colour=(n, n, n)) for n in range(3)])
    assert response.status_code == 201, response.text
    drafts = response.json()["drafts"]
    assert len(drafts) == 3 and all(len(d["photos"]) == 1 for d in drafts)
    assert drafts[0]["fields"] == {} and drafts[0]["status"] == "open"
    assert stack.client.get("/api/v1/items").json()["total"] == 0
    assert len(stack.client.get("/api/v1/drafts").json()["items"]) == 3


def test_one_bad_image_in_a_batch_adds_nothing(stack: Stack):
    response = make_drafts(stack, [imagekit.jpeg(), imagekit.heic_header(), imagekit.jpeg()])
    assert response.status_code == 415
    assert response.json()["error"]["message"].startswith("Photo 2:")
    assert stack.client.get("/api/v1/drafts").json()["items"] == []
    assert files_in(stack.settings.photos_dir) == set()


def test_more_than_twenty_images_are_refused(stack: Stack):
    small = imagekit.jpeg(32, 32)
    assert make_drafts(stack, [small] * 21).status_code == 422
    assert stack.client.get("/api/v1/drafts").json()["items"] == []


def test_a_draft_is_edited_then_committed_with_its_photos(stack: Stack):
    draft = make_drafts(stack, [imagekit.jpeg()]).json()["drafts"][0]
    path = f"/api/v1/drafts/{draft['id']}"
    stack.client.post(f"{path}/photos", headers=HEADERS,
                      files={"image": ("b.jpg", imagekit.jpeg(colour=(9, 9, 9)), "image/jpeg")})
    edited = stack.client.patch(path, json={"fields": {"name": "Spirit level", "quantity": 2}},
                                headers=HEADERS).json()
    assert edited["fields"] == {"name": "Spirit level", "quantity": 2}
    stack.client.patch(path, json={"fields": {"expiry_mode": "none"}}, headers=HEADERS)

    committed = stack.client.post(f"{path}/commit", headers={**HEADERS, "Idempotency-Key": "c1"})
    assert committed.status_code == 201, committed.text
    item = committed.json()
    assert (item["name"], item["quantity"], item["expiry"]["mode"]) == ("Spirit level", 2, "none")
    assert len(item["photos"]) == 2 and item["photos"][0]["is_primary"]
    repeat = stack.client.post(f"{path}/commit", headers={**HEADERS, "Idempotency-Key": "c1"})
    assert repeat.json()["public_id"] == item["public_id"]
    again = stack.client.post(f"{path}/commit", headers=HEADERS)
    assert (again.status_code, again.json()["error"]["details"]["reason"]) == (409, "committed")
    assert stack.client.get("/api/v1/drafts").json()["items"] == []
    events = stack.client.get(f"/api/v1/items/{item['public_id']}/events").json()["items"]
    assert [e["kind"] for e in events] == ["draft_committed", "item_created"]


def test_a_draft_needs_a_name_and_a_confirmed_date_to_commit(stack: Stack):
    draft = make_drafts(stack, [imagekit.jpeg()]).json()["drafts"][0]
    path = f"/api/v1/drafts/{draft['id']}"
    no_name = stack.client.post(f"{path}/commit", headers=HEADERS)
    assert no_name.json()["error"]["details"]["problems"][0]["field"] == "name"
    stack.client.patch(path, json={"fields": {"name": "Milk", "expiry_date": "2026-11-01",
                                              "expiry_confirmed": False}}, headers=HEADERS)
    unconfirmed = stack.client.post(f"{path}/commit", headers=HEADERS)
    assert unconfirmed.json()["error"]["code"] == "expiry_unconfirmed"
    stack.client.patch(path, json={"fields": {"expiry_confirmed": True}}, headers=HEADERS)
    assert stack.client.post(f"{path}/commit", headers=HEADERS).status_code == 201


def test_a_discarded_draft_keeps_its_photo_rows_and_files(stack: Stack):
    draft = make_drafts(stack, [imagekit.jpeg()]).json()["drafts"][0]
    assert stack.client.delete(f"/api/v1/drafts/{draft['id']}", headers=HEADERS).status_code \
        == 204
    assert stack.client.get(f"/api/v1/drafts/{draft['id']}").json()["status"] == "discarded"
    assert len(files_in(stack.settings.photos_dir)) == 1
    assert stack.client.patch(f"/api/v1/drafts/{draft['id']}", json={"fields": {"name": "x"}},
                              headers=HEADERS).status_code == 409


def test_draft_field_types_are_checked(stack: Stack):
    draft = make_drafts(stack, [imagekit.jpeg()]).json()["drafts"][0]
    for fields in ({"quantity": "two"}, {"unknown": 1}, {"expiry_date": "tomorrow"}):
        response = stack.client.patch(f"/api/v1/drafts/{draft['id']}", json={"fields": fields},
                                      headers=HEADERS)
        assert response.status_code == 422, fields


# ---- backups carry photos; restore reports what is missing -----------------------------------

def test_a_backup_counts_items_and_mirrors_photos(stack: Stack):
    item = create(stack)
    photo = upload(stack, item["public_id"], imagekit.jpeg()).json()
    assert stack.client.post("/api/v1/backups", headers=HEADERS).status_code == 201
    listed = stack.client.get("/api/v1/backups").json()["items"][0]
    assert listed["item_count"] == 1
    assert f"{photo['id']}.jpg" in files_in(stack.settings.backup_photos_dir)
