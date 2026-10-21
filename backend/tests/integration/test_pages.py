"""The home page and the app files: boot page unless the state is `ok`, else the built frontend."""

from pathlib import Path

import pytest

from app.config import Settings
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

BOOT_MARK = "Checking your data"  # a sentence of the boot page


def test_the_home_page_is_the_app_shell_when_the_state_is_ok(stack: Stack):
    response = stack.client.get("/")
    assert response.status_code == 200
    assert 'id="root"' in response.text
    assert response.headers["cache-control"] == "no-store"  # same URL, different page by state
    assert 'data-theme-pref="system"' in response.text


@pytest.mark.parametrize("path", ["/settings", "/welcome", "/anything/the/router/handles",
                                  "/index.html"])
def test_any_app_route_gets_the_shell_with_the_stored_theme(stack: Stack, path: str):
    stack.client.put("/api/v1/profile", headers=HEADERS,
                     json={"name": "Mo", "timezone": "UTC", "theme": "dark"})
    response = stack.client.get(path)
    assert response.status_code == 200
    assert 'data-theme-pref="dark"' in response.text  # written by the server, no flash


def test_every_other_state_gets_the_boot_page_for_every_route(settings: Settings):
    with Stack(settings, is_mount=lambda p: False) as locked:
        for path in ("/", "/settings", "/welcome"):
            response = locked.client.get(path)
            assert response.status_code == 200 and BOOT_MARK in response.text
            assert response.headers["cache-control"] == "no-store"


def test_built_files_are_served_with_the_right_cache_rules(stack: Stack):
    assets = stack.settings.frontend_dir / "assets"
    assets.mkdir()
    (assets / "app-3f2a1b.js").write_text("console.log(1)")
    (stack.settings.frontend_dir / "tokens.css").write_text(":root{--bg-base:#16110D}")
    hashed = stack.client.get("/assets/app-3f2a1b.js")
    assert hashed.status_code == 200 and "javascript" in hashed.headers["content-type"]
    assert hashed.headers["cache-control"] == "public, max-age=31536000, immutable"
    shared = stack.client.get("/tokens.css")
    assert shared.status_code == 200 and shared.headers["cache-control"] == "no-cache"
    assert shared.headers["x-content-type-options"] == "nosniff"


def test_the_boot_pages_can_still_load_their_styles_when_the_state_is_not_ok(settings: Settings):
    (settings.frontend_dir / "tokens.css").write_text(":root{--bg-base:#16110D}")
    with Stack(settings, is_mount=lambda p: False) as locked:
        assert locked.client.get("/tokens.css").status_code == 200


def test_a_missing_file_is_a_404_in_the_one_error_shape_never_the_shell(stack: Stack):
    for path in ("/assets/gone.js", "/favicon.ico", "/api", "/api/v1/nothing"):
        response = stack.client.get(path)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("path", [
    "/..%2fsecret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt", "/%00",
    "/..%5csecret.txt",
])
def test_a_path_cannot_climb_out_of_the_app_folder(stack: Stack, path: str):
    (stack.settings.frontend_dir.parent / "secret.txt").write_text("do not serve me")
    response = stack.client.get(path)
    assert "do not serve me" not in response.text
    assert response.status_code in (200, 404, 400)


def test_a_build_without_app_files_says_so_plainly(stack: Stack):
    (stack.settings.frontend_dir / "index.html").unlink()
    response = stack.client.get("/settings")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "build.bat" in response.json()["error"]["message"]


def test_the_api_still_wins_over_the_catch_all(stack: Stack):
    assert stack.client.get("/health").json()["status"] == "ok"
    assert stack.client.get("/api/v1/profile").json()["timezone"] == "UTC"
    assert isinstance(Path(stack.settings.frontend_dir), Path)
