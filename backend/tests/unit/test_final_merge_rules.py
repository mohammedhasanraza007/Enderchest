"""Final merge fixes.

- The embedding loop survives an error it did not expect (Phase 6 verification N4). Before the
  fix, an ONNX Runtime or other unexpected error escaped `tick`, ended `run` and stopped
  embeddings until the app restarted.
- A pasted Gemini key is accepted in any shape Google could issue (D-139, owner's UX test): the
  old rule allowed only letters, digits, dashes and underscores and refused the owner's key.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.boot.manager import Status
from app.errors import AppError
from app.scheduler import embeddings as loop
from app.services import gemini

KEY = "AIzaSyA1b2C3d4E5f6G7h8I9j0K-L_mNoPqRsTu"


@pytest.mark.parametrize("pasted", [
    KEY,
    f"  {KEY}\n",
    f"​{KEY}﻿",
    f'"{KEY}"',
    f"GEMINI_API_KEY={KEY}",
    f"google_api_key: '{KEY}'",
])
def test_what_copying_adds_is_removed(pasted):
    assert gemini.clean_key(pasted) == KEY


def test_a_key_with_dots_is_accepted(tmp_path):
    settings = SimpleNamespace(secrets_dir=tmp_path / "secrets")
    dotted = "AQ.Ab8RN6Lq0vX2yZ.w4kT9-mP_s7dQe1uV3"
    gemini.save_key(settings, f" {dotted} ")
    assert (tmp_path / "secrets" / "gemini.key").read_text(encoding="ascii") == dotted


@pytest.mark.parametrize(("pasted", "says"), [
    ("short", "20 to 400 characters"),
    ("AIzaSyA1b2C3d4E5 f6G7h8I9j0K-L_mNoPqRsTu", "space or line break"),
    ("AIzaSyA1b2C3d4E5\nf6G7h8I9j0K-L_mNoPqRsTu", "space or line break"),
    ("AIzaSyA1b2C3d4E5f6G7h8I9j0K-L_mNoPqRsTü", "20 to 400 characters"),
])
def test_a_key_that_cannot_work_is_refused_in_plain_words(tmp_path, pasted, says):
    settings = SimpleNamespace(secrets_dir=tmp_path / "secrets")
    with pytest.raises(AppError) as refused:
        gemini.save_key(settings, pasted)
    assert says in refused.value.details["problems"][0]["problem"]
    assert not (tmp_path / "secrets" / "gemini.key").exists()


class _Manager:
    state = SimpleNamespace(status=Status.OK)

    @property
    def settings(self):
        raise RuntimeError("onnxruntime failed")


def test_tick_returns_zero_on_an_unexpected_error():
    assert loop.Embedder(_Manager()).tick() == 0


def test_run_keeps_ticking_after_an_unexpected_error(monkeypatch):
    monkeypatch.setattr(loop, "TICK_SECONDS", 0.01)
    embedder = loop.Embedder(_Manager())
    ticks = []
    real = embedder.tick

    def counted() -> int:
        ticks.append(1)
        return real()

    embedder.tick = counted

    async def main() -> None:
        task = asyncio.create_task(embedder.run())
        await asyncio.sleep(0.2)
        await embedder.stop()
        await asyncio.wait_for(task, 1)

    asyncio.run(main())
    assert len(ticks) >= 2
