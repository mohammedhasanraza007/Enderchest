"""Probe 12 over real HTTP: refusals, the error shape, and no CORS headers anywhere."""

import pytest

from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration


def code(response) -> str:
    return response.json()["error"]["code"]


def test_wrong_host_is_forbidden_even_on_health(stack: Stack):
    for path in ("/health", "/api/v1/boot", "/api/v1/backups", "/"):
        response = stack.client.get(path, headers={"Host": "evil.example:8470"})
        assert (response.status_code, code(response)) == (403, "forbidden_host")


def test_write_without_the_safety_header_is_forbidden(stack: Stack):
    response = stack.client.post("/api/v1/backups")
    assert (response.status_code, code(response)) == (403, "forbidden_host")
    assert not list(stack.settings.backups_dir.glob("*.sqlite3"))  # nothing was made


def test_foreign_origin_is_forbidden(stack: Stack):
    response = stack.client.post("/api/v1/backups", headers={**HEADERS, "Origin": "http://evil.example"})
    assert (response.status_code, code(response)) == (403, "forbidden_host")


def test_own_origin_is_accepted(stack: Stack):
    response = stack.client.post("/api/v1/backups",
                                 headers={**HEADERS, "Origin": "http://127.0.0.1:8470"})
    assert response.status_code == 201


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded"])
def test_text_plain_and_form_bodies_are_refused(stack: Stack, content_type):
    response = stack.client.post("/api/v1/boot/start-empty", content=b'{"confirm":"START EMPTY"}',
                                 headers={**HEADERS, "Content-Type": content_type})
    assert (response.status_code, code(response)) == (422, "validation_error")


def test_no_cors_headers_on_any_response(stack: Stack):
    responses = [
        stack.client.get("/health"),
        stack.client.get("/api/v1/boot"),
        stack.client.get("/api/v1/backups"),
        stack.client.get("/"),
        stack.client.get("/health", headers={"Origin": "http://evil.example"}),
        stack.client.options("/api/v1/backups", headers={
            "Origin": "http://evil.example", "Access-Control-Request-Method": "POST"}),
        stack.client.post("/api/v1/backups"),  # refused
        stack.client.get("/nope", headers={"Origin": "http://evil.example"}),
    ]
    for response in responses:
        assert not [h for h in response.headers if h.lower().startswith("access-control-")]


def test_errors_use_the_one_error_shape_and_never_leak_a_traceback(stack: Stack):
    missing = stack.client.get("/api/v1/nothing-here")
    assert missing.status_code == 404
    assert set(missing.json()["error"]) == {"code", "message", "details"}
    assert code(missing) == "not_found"

    invalid = stack.post("/api/v1/boot/restore", {"name": 5})
    assert invalid.status_code == 422 and code(invalid) == "validation_error"
    assert "problems" in invalid.json()["error"]["details"]
    assert "Traceback" not in invalid.text


def test_unexpected_exceptions_become_internal_error(stack: Stack, monkeypatch):
    from app.api import backups

    def boom(*args, **kwargs):
        raise RuntimeError("secret detail that must not leak")

    monkeypatch.setattr(backups, "create_backup", boom)
    response = stack.post("/api/v1/backups")
    assert (response.status_code, code(response)) == (500, "internal_error")
    assert "secret detail" not in response.text and "Traceback" not in response.text


