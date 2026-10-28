"""This module contains unit tests for the telegram module."""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from voltraggio_bot.modules.telegram import (
    FISH_PATH,
    GAUSS_PATH,
    Telegram,
    findCorrections,
)

TRIGGER_MAP = {
    "voltaggio": "TENSIONE",
    "amperaggio": "CORRENTE",
    "tension": "VOLTAGE",
}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("il voltaggio è alto", ["TENSIONE"]),
        ("VOLTAGGIO!", ["TENSIONE"]),
        ("amperaggio e voltaggio", ["CORRENTE", "TENSIONE"]),
        ("voltaggioso non conta", []),
        ("high tension", ["VOLTAGE"]),
        ("tensione", []),
        ("niente da correggere", []),
    ],
)
def test_find_corrections(text: str, expected: list[str]) -> None:
    """Only whole words are corrected, in order of appearance."""
    assert findCorrections(text, TRIGGER_MAP) == expected


def test_find_corrections_escapes_words() -> None:
    """Trigger words are matched literally, not as regular expressions."""
    assert findCorrections("a.c", {"a.c": "X"}) == ["X"]
    assert findCorrections("abc", {"a.c": "X"}) == []


def test_assets_exist() -> None:
    """The assets are shipped with the package."""
    assert GAUSS_PATH.is_file()
    assert FISH_PATH.is_file()


@pytest.fixture
async def bot(tmp_path: Path) -> Telegram:
    """Create a bot with loaded settings and a mocked application.

    Returns:
        Telegram: the bot
    """
    path = tmp_path / "settings.json"
    shutil.copy("tests/data/settings.json", path)
    t = Telegram(settings_path=str(path))
    await t._settings.load()
    t._application = MagicMock()
    t._application.bot.send_message = AsyncMock()
    return t


def makeUpdate(user_id: int, text: str = "") -> MagicMock:
    """Create a fake update.

    Returns:
        MagicMock: the update
    """
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.send_message = AsyncMock()
    update.message.text = text
    update.message.chat.send_chat_action = AsyncMock()
    update.message.reply_animation = AsyncMock()
    update.message.reply_animation.return_value.animation.file_id = "fish-id"
    return update


async def test_text_message_sends_fish(bot: Telegram) -> None:
    """A wrong word is corrected and the counter is incremented."""
    update = makeUpdate(1, "che voltaggio")
    await bot._botTextMessage(update, MagicMock())
    kwargs = update.message.reply_animation.call_args.kwargs
    assert kwargs["animation"] == FISH_PATH
    assert kwargs["caption"] == "*SI DICE TENSIONE*"
    assert await bot._settings.get("gif_sent") == 1

    # the second time, the already uploaded fish is reused
    await bot._botTextMessage(update, MagicMock())
    kwargs = update.message.reply_animation.call_args.kwargs
    assert kwargs["animation"] == "fish-id"
    assert await bot._settings.get("gif_sent") == 2


async def test_text_message_ignores_correct_text(bot: Telegram) -> None:
    """Nothing is sent when there is nothing to correct."""
    update = makeUpdate(1, "la tensione è alta")
    await bot._botTextMessage(update, MagicMock())
    update.message.reply_animation.assert_not_called()
    assert await bot._settings.get("gif_sent") == 0


async def test_stop_requires_admin(bot: Telegram) -> None:
    """Only admins can stop the bot."""
    await bot._botStopCommand(makeUpdate(1), MagicMock())
    assert not bot._stop_event.is_set()

    await bot._botStopCommand(makeUpdate(123456789), MagicMock())
    assert bot._stop_event.is_set()
    assert not bot.restart_requested


async def test_reset_requires_admin(bot: Telegram) -> None:
    """Only admins can restart the bot."""
    await bot._botResetCommand(makeUpdate(1), MagicMock())
    assert not bot._stop_event.is_set()

    await bot._botResetCommand(makeUpdate(123456789), MagicMock())
    assert bot._stop_event.is_set()
    assert bot.restart_requested


async def test_stats(bot: Telegram) -> None:
    """The stats are sent."""
    update = makeUpdate(1)
    await bot._botStatsCommand(update, MagicMock())
    text = update.effective_chat.send_message.call_args.kwargs["text"]
    assert "*0* gif" in text


async def test_error_notifies_admins(bot: Telegram) -> None:
    """Errors are sent to the admins as plain text."""
    context = MagicMock()
    context.error = ValueError("boom")
    await bot._botError(None, context)
    calls = bot._application.bot.send_message.call_args_list
    assert len(calls) == 2
    assert "ValueError: boom" in calls[1].kwargs["text"]
    assert calls[1].kwargs["parse_mode"] is None
