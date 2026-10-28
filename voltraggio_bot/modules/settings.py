"""This module contains the class used to load and save the bot settings."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Settings:
    """Settings of the bot, stored in a JSON file."""

    _path: Path
    _lock: asyncio.Lock
    _settings: dict[str, Any]

    def __init__(self, settings_path: str | Path) -> None:
        """Initialize the settings.

        Args:
            settings_path (str | Path): path to the settings file
        """
        self._path = Path(settings_path)
        self._lock = asyncio.Lock()
        self._settings = {}

    async def load(self) -> None:
        """Load the settings from the file."""
        logger.debug("Loading settings from %s", self._path)
        async with self._lock:
            content = await asyncio.to_thread(self._path.read_text, encoding="utf-8")
            self._settings = json.loads(content)

    async def validate(self, required_keys: list[str]) -> None:
        """Check that all the required keys are in the settings.

        Args:
            required_keys (list[str]): keys that must be in the settings

        Raises:
            KeyError: if a required key is missing
        """
        async with self._lock:
            missing = [key for key in required_keys if key not in self._settings]
        if missing:
            error_msg = f"Missing keys in settings: {', '.join(missing)}"
            raise KeyError(error_msg)

    def _write(self, content: str) -> None:
        """Write the settings file atomically.

        The settings are first written to a temporary file which then replaces
        the old one, so a crash cannot leave a truncated settings file behind.

        Args:
            content (str): content of the settings file
        """
        temp_path = self._path.with_name(f"{self._path.name}.tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        temp_path.replace(self._path)

    async def _saveNoLock(self) -> None:
        """Save the settings to the file without acquiring the lock."""
        content = json.dumps(self._settings, indent=2, ensure_ascii=False)
        await asyncio.to_thread(self._write, content)

    async def save(self) -> None:
        """Save the settings to the file."""
        logger.debug("Saving settings to %s", self._path)
        async with self._lock:
            await self._saveNoLock()

    async def get(self, key: str) -> Any:
        """Get a copy of a setting.

        Args:
            key (str): key of the setting

        Returns:
            Any: value of the setting

        Raises:
            KeyError: if the key is not in the settings
        """
        async with self._lock:
            if key not in self._settings:
                error_msg = f"Key '{key}' not found in settings"
                raise KeyError(error_msg)
            return copy.deepcopy(self._settings[key])

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric setting and save the settings.

        Args:
            key (str): key of the setting
            amount (int): amount to add. Defaults to 1.

        Returns:
            int: the updated value

        Raises:
            KeyError: if the key is not in the settings
        """
        async with self._lock:
            if key not in self._settings:
                error_msg = f"Key '{key}' not found in settings"
                raise KeyError(error_msg)
            self._settings[key] += amount
            await self._saveNoLock()
            return self._settings[key]
