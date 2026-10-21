"""Probe 12 at the unit level: every rejection rule of the localhost hardening."""

import pytest

from app.api.security import check_request

PORT = 8470
GOOD = {"host": "127.0.0.1:8470", "x-enderchest": "1"}


def check(method="GET", path="/api/v1/backups", **headers):
    merged = {**GOOD, **headers} if method != "GET" else {"host": "127.0.0.1:8470", **headers}
    return check_request(method, path, merged, PORT)


@pytest.mark.parametrize("host", ["localhost:8470", "127.0.0.1:8470", "[::1]:8470"])
def test_local_hosts_with_the_app_port_pass(host):
    assert check_request("GET", "/", {"host": host}, PORT) is None


@pytest.mark.parametrize("host", ["evil.example:8470", "127.0.0.1:9999", "127.0.0.1",
                                  "localhost.evil.com:8470", ""])
def test_wrong_host_is_refused_for_every_method(host):
    refusal = check_request("GET", "/", {"host": host}, PORT)
    assert refusal is not None and refusal[0] == "forbidden_host" and refusal[1] == 403


def test_published_test_port_is_accepted_alongside_the_internal_port():
    assert check_request("GET", "/", {"host": "127.0.0.1:8471"}, 8471) is None
    assert check_request("GET", "/", {"host": "127.0.0.1:8470"}, 8471) is None


def test_writes_without_the_safety_header_are_refused():
    refusal = check_request("POST", "/api/v1/backups", {"host": "127.0.0.1:8470"}, PORT)
    assert refusal is not None and refusal[0] == "forbidden_host"


def test_writes_with_the_header_pass():
    assert check("POST") is None
    assert check("DELETE") is None


def test_a_foreign_origin_on_a_write_is_refused():
    refusal = check("POST", origin="http://evil.example")
    assert refusal is not None and refusal[0] == "forbidden_host"


def test_the_apps_own_origin_on_a_write_passes():
    assert check("POST", origin="http://127.0.0.1:8470") is None


@pytest.mark.parametrize("content_type", ["text/plain", "text/plain;charset=UTF-8",
                                          "application/x-www-form-urlencoded",
                                          "multipart/form-data; boundary=x"])
def test_non_json_bodies_are_refused_with_validation_error(content_type):
    refusal = check("POST", **{"content-type": content_type, "content-length": "5"})
    assert refusal is not None and refusal[0] == "validation_error" and refusal[1] == 422


def test_json_bodies_pass():
    assert check("POST", **{"content-type": "application/json; charset=utf-8",
                            "content-length": "5"}) is None


def test_a_body_without_a_content_type_is_refused():
    refusal = check("POST", **{"content-length": "5"})
    assert refusal is not None and refusal[0] == "validation_error"


def test_a_bodyless_post_passes():
    assert check("POST") is None
