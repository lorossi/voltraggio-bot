"""Voltraggio BOT.

LE PAROLE SONO IMPORTANTI!
Corrects anyone who says "voltaggio" instead of "tensione" with a fish.

Somewhere in year 2019 - Updated at home in year 2024 - and again in 2026.
Gotta find an hobby someday.

CC BY-NC 4.0 - Lorenzo Rossi - https://lorenzoros.si
"""

from __future__ import annotations

import asyncio
import logging
import re
import traceback
from datetime import datetime
from pathlib import Path

from telegram import Update, constants
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from voltraggio_bot.modules.settings import Settings

logger = logging.getLogger(__name__)

Context = ContextTypes.DEFAULT_TYPE

ASSETS_DIR = Path(__file__).parent.parent / "assets"
GAUSS_PATH = ASSETS_DIR / "gauss.jpg"
FISH_PATH = ASSETS_DIR / "pesce.mp4"

REQUIRED_SETTINGS = ["token", "admins", "start_date", "gif_sent", "trigger_map"]

# maximum length of a message sent to the admins when an error occurs
MAX_ERROR_LENGTH = 4000


def findCorrections(text: str, trigger_map: dict[str, str]) -> list[str]:
    """Find the corrections for the wrong words in a text.

    Args:
        text (str): text to check
        trigger_map (dict[str, str]): wrong words mapped to their correction

    Returns:
        list[str]: corrections of the wrong words found, in order of appearance
    """
    text = text.lower()
    found: list[tuple[int, str]] = []
    for word, correction in trigger_map.items():
        match = re.search(rf"\b{re.escape(word.lower())}\b", text)
        if match:
            found.append((match.start(), correction))
    return [correction for _, correction in sorted(found)]


class Telegram:
    """This class contains all the logic for the Telegram bot."""

    _application: Application
    _settings: Settings
    _stop_event: asyncio.Event
    _restart_requested: bool
    _fish_file_id: str | None

    def __init__(self, settings_path: str = "settings.json") -> None:
        """Initialize the Telegram bot.

        Args:
            settings_path (str): path to the settings file
        """
        self._settings = Settings(settings_path)
        # set when the bot is asked to stop (or restart)
        self._stop_event = asyncio.Event()
        self._restart_requested = False
        # once uploaded, the fish is re-sent by id instead of being uploaded again
        self._fish_file_id = None

    # Lifecycle

    async def start(self) -> None:
        """Start the bot.

        Raises:
            RuntimeError: if the application has no updater
        """
        logger.info("Starting bot...")
        await self._settings.load()
        await self._settings.validate(REQUIRED_SETTINGS)

        token = await self._settings.get("token")
        self._application = Application.builder().token(token).build()
        self._setupHandlers()

        await self._application.initialize()
        if self._application.updater is None:
            error_msg = "Updater not available"
            raise RuntimeError(error_msg)
        await self._application.updater.start_polling()
        await self._application.start()
        logger.info("Bot started as @%s", self._application.bot.username)

        await self._notifyAdmins("*Il bot è stato avviato*")

    async def stop(self) -> None:
        """Stop the bot."""
        logger.info("Stopping bot...")
        # stopping the updater also marks the received updates as read,
        #   so they are not delivered again after a restart
        if self._application.updater is not None:
            await self._application.updater.stop()
        await self._application.stop()
        await self._application.shutdown()
        await self._settings.save()
        logger.info("Bot stopped")

    def requestStop(self, *, restart: bool = False) -> None:
        """Ask the bot to stop, letting the owner of the bot perform the shutdown.

        Args:
            restart (bool): whether the bot should be restarted after stopping
        """
        self._restart_requested = self._restart_requested or restart
        self._stop_event.set()

    async def waitForStopRequest(self) -> None:
        """Wait until the bot is asked to stop."""
        await self._stop_event.wait()

    @property
    def restart_requested(self) -> bool:
        """Whether the bot should be restarted after stopping."""
        return self._restart_requested

    def _setupHandlers(self) -> None:
        """Register the handlers of the bot."""
        self._application.add_error_handler(self._botError)
        self._application.add_handlers(
            [
                CommandHandler("start", self._botStartCommand),
                CommandHandler("gauss", self._botGaussCommand),
                CommandHandler("stop", self._botStopCommand),
                CommandHandler("ping", self._botPingCommand),
                CommandHandler("reset", self._botResetCommand),
                CommandHandler("stats", self._botStatsCommand),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE,
                    self._botTextMessage,
                ),
            ]
        )

    # Helpers

    async def _isAdmin(self, update: Update) -> bool:
        """Check whether the sender of an update is an admin.

        Args:
            update (Update): incoming update

        Returns:
            bool: True if the sender is an admin
        """
        user = update.effective_user
        if user is None:
            return False
        return user.id in await self._settings.get("admins")

    async def _notifyAdmins(
        self,
        message: str,
        parse_mode: str | None = constants.ParseMode.MARKDOWN,
    ) -> None:
        """Send a message to all the admins.

        A failure to reach an admin (e.g. if they blocked the bot) is logged
        and does not prevent the other admins from being notified.

        Args:
            message (str): text of the message
            parse_mode (str | None): parse mode of the message.
                Defaults to markdown.
        """
        for chat_id in await self._settings.get("admins"):
            try:
                await self._application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode,
                )
            except TelegramError as e:
                logger.warning("Cannot notify admin %d: %s", chat_id, e)

    @staticmethod
    async def _reply(update: Update, message: str) -> None:
        """Reply to an update with a markdown message.

        Args:
            update (Update): incoming update
            message (str): text of the message
        """
        if update.effective_chat is None:
            return
        await update.effective_chat.send_message(
            text=message,
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    # Callbacks

    async def _botStartCommand(self, update: Update, _context: Context) -> None:
        """Greet the user.

        Callback fired with command /start
        """
        await self._reply(update, "_Sono pronto a correggere chiunque dica boiate_")

    async def _botPingCommand(self, update: Update, _context: Context) -> None:
        """Reply "PONG".

        Callback fired with command /ping for debug purposes
        """
        await self._reply(update, "🏓 *PONG* 🏓")

    async def _botResetCommand(self, update: Update, _context: Context) -> None:
        """Restart the bot.

        Callback fired with command /reset
        """
        if not await self._isAdmin(update):
            await self._reply(update, "*Questo comando è solo per admins*")
            return

        await self._reply(update, "_Riavvio in corso..._")
        logger.warning("Restart requested")
        # the bot cannot be stopped from inside a handler, as stopping
        #   waits for all the handlers to finish
        self.requestStop(restart=True)

    async def _botStopCommand(self, update: Update, _context: Context) -> None:
        """Stop the bot.

        Callback fired with command /stop
        """
        if not await self._isAdmin(update):
            await self._reply(update, "*Questo comando è solo per admins*")
            return

        await self._reply(update, "_Il bot è stato fermato_")
        logger.warning("Stop requested")
        self.requestStop()

    @staticmethod
    async def _botGaussCommand(update: Update, _context: Context) -> None:
        """Send a photo of Gauss.

        Callback fired with command /gauss
        """
        chat = update.effective_chat
        if chat is None:
            return

        await chat.send_chat_action(constants.ChatAction.UPLOAD_PHOTO)
        await chat.send_photo(
            photo=GAUSS_PATH,
            caption="*Johann Carl Friedrich Gauß*",
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    async def _botStatsCommand(self, update: Update, _context: Context) -> None:
        """Send the stats of the bot.

        Callback fired with command /stats
        """
        start_date = datetime.fromisoformat(await self._settings.get("start_date"))
        gif_sent = await self._settings.get("gif_sent")

        days_between = (datetime.now() - start_date).days + 1  # ruff: ignore[call-datetime-now-without-tzinfo]
        average = gif_sent / days_between
        message = (
            f"Il bot sta funzionando da *{days_between}* giorni.\n"
            f"Sono state inviate *{gif_sent}* gif, "
            f"per una media di *{average:.2f}* gif al giorno!"
        )
        await self._reply(update, message)

    async def _botTextMessage(self, update: Update, _context: Context) -> None:
        """Correct the wrong words with a fish.

        Callback fired with text messages
        """
        message = update.message
        if message is None or message.text is None:
            return

        corrections = findCorrections(
            message.text, await self._settings.get("trigger_map")
        )
        if not corrections:
            return

        caption = "\n".join(f"*SI DICE {c}*" for c in corrections)
        await message.chat.send_chat_action(constants.ChatAction.UPLOAD_VIDEO)
        sent = await message.reply_animation(
            animation=self._fish_file_id or FISH_PATH,
            caption=caption,
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        if sent.animation is not None:
            self._fish_file_id = sent.animation.file_id

        await self._settings.increment("gif_sent")

    async def _botError(self, update: object, context: Context) -> None:
        """Log errors and notify the admins.

        Callback fired by errors and handled by the telegram module
        """
        logger.error("Update %s caused error", update, exc_info=context.error)

        error = context.error
        error_trace = (
            "".join(traceback.format_exception(error)) if error else "Unknown error"
        )
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"Error at time: {datetime.now().isoformat()}\n"  # ruff: ignore[call-datetime-now-without-tzinfo]
            f"Update: {update_str}\n"
            f"{error_trace}"
        )
        # the traceback is sent as plain text, as it could break the markdown
        await self._notifyAdmins("*ERRORE*")
        await self._notifyAdmins(message[-MAX_ERROR_LENGTH:], parse_mode=None)
