"""Shared fixtures: every test gets its own temporary data and backup folders."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.boot.manager import Status
from app.config import Settings
from app.db.connection import connect
from app.db.create import create_database
from app.main import create_app

PORT = 8470
HEADERS = {"X-Enderchest": "1"}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data, backups = tmp_path / "data", tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Settings(env="test", port=PORT, data_dir=data, backups_dir=backups,
                    backup_dir_hint="the backup folder")


def make_database(settings: Settings) -> None:
    """A real database in the given settings' folders, built the same way the app builds it."""
    for folder in (settings.db_path.parent, settings.photos_dir, settings.staging_dir):
        folder.mkdir(parents=True, exist_ok=True)
    create_database(settings)


def put_marker_row(settings: Settings, key: str, value: str = "1") -> None:
    conn = connect(settings.db_path)
    conn.execute("INSERT OR REPLACE INTO scheduler_state (key, value) VALUES (?, ?)", (key, value))
    conn.close()


def state_keys(settings: Settings) -> set[str]:
    conn = connect(settings.db_path)
    try:
        return {r["key"] for r in conn.execute("SELECT key FROM scheduler_state")}
    finally:
        conn.close()


def wait_for_state(manager, *, timeout: float = 15.0) -> Status:
    """Boot checks run in a thread; wait until they settle."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if manager.state.status is not Status.STARTING:
            return manager.state.status
        time.sleep(0.02)
    raise AssertionError("boot checks did not settle")


class Stack:
    """A running app on temporary folders, with a client that speaks like the browser."""

    def __init__(self, settings: Settings, *, is_mount=lambda _path: True) -> None:
        self.settings = settings
        self.app = create_app(settings, is_mount=is_mount, start_scheduler=False)
        self.client = TestClient(self.app, base_url=f"http://127.0.0.1:{settings.port}",
                                 raise_server_exceptions=False)

    def __enter__(self) -> "Stack":
        self.client.__enter__()
        wait_for_state(self.app.state.manager)
        return self

    def __exit__(self, *exc) -> None:
        self.client.__exit__(*exc)

    @property
    def manager(self):
        return self.app.state.manager

    def post(self, path: str, json=None):
        return self.client.post(path, json=json, headers=HEADERS)


@pytest.fixture
def stack(settings: Settings):
    with Stack(settings) as running:
        yield running
