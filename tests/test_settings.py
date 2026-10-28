"""This module contains unit tests for the settings module."""

import json
import shutil
from pathlib import Path

import pytest

from voltraggio_bot.modules.settings import Settings


@pytest.fixture
def settings_path(tmp_path: Path) -> Path:
    """Copy the test settings to a temporary folder.

    Returns:
        Path: path to the copied settings
    """
    path = tmp_path / "settings.json"
    shutil.copy("tests/data/settings.json", path)
    return path


async def test_load_and_get(settings_path: Path) -> None:
    """The settings are loaded from the file."""
    settings = Settings(settings_path)
    await settings.load()
    assert await settings.get("gif_sent") == 0
    assert await settings.get("admins") == [123456789]


async def test_get_returns_copy(settings_path: Path) -> None:
    """Changing a returned value does not change the settings."""
    settings = Settings(settings_path)
    await settings.load()
    admins = await settings.get("admins")
    admins.append(1)
    assert await settings.get("admins") == [123456789]


async def test_missing_key(settings_path: Path) -> None:
    """Missing keys raise KeyError."""
    settings = Settings(settings_path)
    await settings.load()
    with pytest.raises(KeyError):
        await settings.get("nope")
    with pytest.raises(KeyError):
        await settings.increment("nope")
    with pytest.raises(KeyError, match="nope"):
        await settings.validate(["token", "nope"])
    await settings.validate(["token", "admins"])


async def test_increment_saves(settings_path: Path) -> None:
    """Incrementing a value saves it to the file."""
    settings = Settings(settings_path)
    await settings.load()
    assert await settings.increment("gif_sent") == 1
    assert await settings.increment("gif_sent", 2) == 3
    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert saved["gif_sent"] == 3
    assert not settings_path.with_name("settings.json.tmp").exists()
