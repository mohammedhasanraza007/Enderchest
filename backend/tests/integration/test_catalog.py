"""Categories and locations (API 2.4; DATA_MODEL 2.4, 2.5; D-094). Gate 5."""

import pytest

from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration


def post(stack: Stack, path: str, body: dict):
    return stack.client.post(f"/api/v1{path}", json=body, headers=HEADERS)


def patch(stack: Stack, path: str, body: dict):
    return stack.client.patch(f"/api/v1{path}", json=body, headers=HEADERS)


def delete(stack: Stack, path: str):
    return stack.client.delete(f"/api/v1{path}", headers=HEADERS)


def item(stack: Stack, **fields) -> dict:
    response = post(stack, "/items", {"name": "Thing", **fields})
    assert response.status_code == 201, response.text
    return response.json()


# ---- categories -------------------------------------------------------------------------------

def test_a_category_is_created_with_its_defaults_and_listed_with_a_count(stack: Stack):
    made = post(stack, "/categories", {"name": " Food and drink ", "expires_default": True,
                                       "label_default": False})
    assert made.status_code == 201
    assert made.json() == {"id": made.json()["id"], "name": "Food and drink",
                           "expires_default": True, "maintenance_default": False,
                           "label_default": False, "item_count": 0}
    item(stack, category_id=made.json()["id"])
    assert stack.client.get("/api/v1/categories").json()[0]["item_count"] == 1


def test_duplicate_category_names_are_refused_case_insensitively(stack: Stack):
    post(stack, "/categories", {"name": "Tools"})
    again = post(stack, "/categories", {"name": "tOOLS"})
    assert again.status_code == 409
    assert again.json()["error"]["details"] == {"reason": "duplicate_name", "field": "name"}
    other = post(stack, "/categories", {"name": "Electronics"}).json()
    assert patch(stack, f"/categories/{other['id']}", {"name": "TOOLS"}).status_code == 409


def test_duplicate_names_are_refused_case_insensitively_beyond_ascii(stack: Stack):
    # Found by the Phase 2 verification: SQLite's NOCASE folds A to Z only.
    post(stack, "/categories", {"name": "Ölfarben"})
    assert post(stack, "/categories", {"name": "ölfarben"}).status_code == 409
    post(stack, "/locations", {"name": "Garáge"})
    assert post(stack, "/locations", {"name": "GARÁGE"}).status_code == 409


def test_renaming_and_toggling_defaults(stack: Stack):
    made = post(stack, "/categories", {"name": "Tools"}).json()
    changed = patch(stack, f"/categories/{made['id']}", {"name": "Hand tools",
                                                         "maintenance_default": True})
    assert (changed.json()["name"], changed.json()["maintenance_default"]) == ("Hand tools", True)
    assert patch(stack, f"/categories/{made['id']}", {"name": None}).status_code == 422
    assert patch(stack, "/categories/999", {"name": "X"}).status_code == 404


def test_a_category_in_use_needs_a_reassign_target_and_trash_items_move_too(stack: Stack):
    tools = post(stack, "/categories", {"name": "Tools"}).json()
    other = post(stack, "/categories", {"name": "Other"}).json()
    kept = item(stack, category_id=tools["id"])
    trashed = item(stack, category_id=tools["id"])
    delete(stack, f"/items/{trashed['public_id']}")

    refused = delete(stack, f"/categories/{tools['id']}")
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "in_use"
    assert refused.json()["error"]["details"]["count"] == 2

    assert delete(stack, f"/categories/{tools['id']}?reassign_to={other['id']}").status_code == 204
    names = [c["name"] for c in stack.client.get("/api/v1/categories").json()]
    assert names == ["Other"]
    for public_id in (kept["public_id"], trashed["public_id"]):
        body = stack.client.get(f"/api/v1/items/{public_id}").json()
        assert body["category"] == {"id": other["id"], "name": "Other"}


def test_reassign_to_none_clears_the_category(stack: Stack):
    tools = post(stack, "/categories", {"name": "Tools"}).json()
    made = item(stack, category_id=tools["id"])
    assert delete(stack, f"/categories/{tools['id']}?reassign_to=none").status_code == 204
    assert stack.client.get(f"/api/v1/items/{made['public_id']}").json()["category"] is None
    # A deleted name may be used again.
    assert post(stack, "/categories", {"name": "Tools"}).status_code == 201


@pytest.mark.parametrize("target", ["self", "999", "abc"])
def test_a_bad_reassign_target_is_refused(stack: Stack, target):
    tools = post(stack, "/categories", {"name": "Tools"}).json()
    item(stack, category_id=tools["id"])
    value = str(tools["id"]) if target == "self" else target
    response = delete(stack, f"/categories/{tools['id']}?reassign_to={value}")
    assert response.status_code in (404, 422)
    assert [c["name"] for c in stack.client.get("/api/v1/categories").json()] == ["Tools"]


# ---- locations --------------------------------------------------------------------------------

def make_chain(stack: Stack, names: list[str]) -> list[dict]:
    made, parent = [], None
    for name in names:
        response = post(stack, "/locations", {"name": name, "parent_id": parent})
        assert response.status_code == 201, response.text
        made.append(response.json())
        parent = made[-1]["id"]
    return made


def test_locations_list_as_a_tree_with_paths(stack: Stack):
    garage, shelf, box = make_chain(stack, ["Garage", "Shelf 2", "Blue box"])
    assert box["path"] == ["Garage", "Shelf 2", "Blue box"]
    make_chain(stack, ["Attic"])
    listed = stack.client.get("/api/v1/locations").json()
    assert [entry["name"] for entry in listed] == ["Attic", "Garage", "Shelf 2", "Blue box"]
    assert listed[3] == {"id": box["id"], "name": "Blue box", "parent_id": shelf["id"],
                         "path": ["Garage", "Shelf 2", "Blue box"], "item_count": 0}


def test_names_are_unique_per_parent_case_insensitively(stack: Stack):
    garage, = make_chain(stack, ["Garage"])
    assert post(stack, "/locations", {"name": "GARAGE"}).status_code == 409
    assert post(stack, "/locations", {"name": "Shelf", "parent_id": garage["id"]}).status_code \
        == 201
    assert post(stack, "/locations", {"name": "shelf", "parent_id": garage["id"]}).status_code \
        == 409
    assert post(stack, "/locations", {"name": "Shelf"}).status_code == 201  # another parent


def test_depth_is_limited_to_five(stack: Stack):
    chain = make_chain(stack, ["L1", "L2", "L3", "L4", "L5"])
    sixth = post(stack, "/locations", {"name": "L6", "parent_id": chain[-1]["id"]})
    assert sixth.status_code == 422
    assert sixth.json()["error"]["details"]["problems"][0]["field"] == "parent_id"
    # Moving a two-level subtree under level 4 would make it six deep.
    other = make_chain(stack, ["A", "B"])
    moved = patch(stack, f"/locations/{other[0]['id']}", {"parent_id": chain[3]["id"]})
    assert moved.status_code == 422


def test_a_move_under_itself_or_a_descendant_is_a_cycle(stack: Stack):
    garage, shelf, box = make_chain(stack, ["Garage", "Shelf", "Box"])
    for target in (garage["id"], box["id"]):
        response = patch(stack, f"/locations/{garage['id']}", {"parent_id": target})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "cycle"


def test_moving_to_the_top_and_renaming(stack: Stack):
    garage, shelf = make_chain(stack, ["Garage", "Shelf"])
    moved = patch(stack, f"/locations/{shelf['id']}", {"parent_id": None, "name": "Top shelf"})
    assert moved.json()["path"] == ["Top shelf"]
    kept = patch(stack, f"/locations/{shelf['id']}", {"name": "Shelf A"})
    assert kept.json()["parent_id"] is None


def test_a_location_with_children_cannot_be_deleted(stack: Stack):
    garage, _ = make_chain(stack, ["Garage", "Shelf"])
    response = delete(stack, f"/locations/{garage['id']}")
    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "has_children"


def test_a_location_in_use_moves_its_items_on_delete(stack: Stack):
    garage, shelf = make_chain(stack, ["Garage", "Shelf"])
    attic, = make_chain(stack, ["Attic"])
    made = item(stack, location_id=shelf["id"])
    assert delete(stack, f"/locations/{shelf['id']}").json()["error"]["code"] == "in_use"
    assert delete(stack, f"/locations/{shelf['id']}?reassign_to={attic['id']}").status_code == 204
    body = stack.client.get(f"/api/v1/items/{made['public_id']}").json()
    assert (body["location"], body["location_path"]) == ({"id": attic["id"], "name": "Attic"},
                                                         ["Attic"])
