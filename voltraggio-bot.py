"""
Lorenzo Rossi - https://lorenzoros.si - 2024.

Somewhere in year 2019 - Updated at home in year 2024
Gotta find an hobby someday
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime

import ujson
from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


class Telegram:
    """This class contains all the methods and variables needed to control the Telegram bot."""

    def __init__(self) -> Telegram:
        """Instantiate the Telegram class."""
        self._settings = {}
        self._settings_path = "src/settings.json"
        self._loadSettings()

    def _loadSettings(self) -> None:
        """Load settings from the settings file."""
        with open(self._settings_path) as json_file:
            # only keeps settings for Telegram, discarding others
            self._settings = ujson.load(json_file)

    def _saveSettings(self) -> None:
        """Save settings into file."""
        with open(self._settings_path) as json_file:
            old_settings = ujson.load(json_file)

        # since settings is a dictionary, we update the settings loaded
        # with the current settings dict
        old_settings.update(self._settings)

        with open(self._settings_path, "w") as outfile:
            ujson.dump(old_settings, outfile, indent=2)

    # Setters/getters

    @property
    def _admins(self) -> list[str]:
        return self._settings["admins"]

    @property
    def _image_path(self) -> str:
        return self._settings["image_path"]

    @property
    def _start_date(self) -> str:
        return self._settings["start_date"]

    @property
    def _gif_sent(self) -> int:
        return self._settings["gif_sent"]

    @_gif_sent.setter
    def _gif_sent(self, value: int) -> None:
        self._settings["gif_sent"] = value
        self._saveSettings()

    @property
    def _trigger_map(self) -> dict[str, str]:
        return self._settings["trigger_map"]

    @property
    def _fish_gif_path(self) -> str:
        return self._settings["fish_gif_path"]

    def start(self) -> None:
        """Start the bot."""
        self._application = Application.builder().token(self._settings["token"]).build()
        self._jobqueue = self._application.job_queue

        self._jobqueue.run_once(self._botStarted, when=0, name="bot_started")

        self._application.add_error_handler(self._botError)

        self._application.add_handler(CommandHandler("start", self._botStartCommand))
        self._application.add_handler(CommandHandler("gauss", self._botGaussCommand))
        self._application.add_handler(CommandHandler("stop", self._botStopCommand))
        self._application.add_handler(CommandHandler("ping", self._botPingCommand))
        self._application.add_handler(CommandHandler("reset", self._botResetCommand))
        self._application.add_handler(CommandHandler("stats", self._botStatsCommand))
        self._application.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), self._botTextMessage)
        )

        self._application.run_polling()
        logging.info("Bot started")

    async def _botStarted(self, context: ContextTypes) -> None:
        """
        Send a message to admins whenever the bot is started.

        Callback fired at startup
        """
        message = "*Il bot è stato avviato*"
        for chat_id in self._admins:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN,
            )

    async def _botStartCommand(self, update: Update, context: ContextTypes) -> None:
        """
        Greet user during first start.

        Callback fired with command /start
        """
        chat_id = update.effective_chat.id
        message = "_Sono pronto a correggere chiunque dica boiate_"
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    async def _botPingCommand(self, update: Update, context: ContextTypes) -> None:
        """
        Simply replies "PONG".

        Callback fired with command /ping for debug purposes
        """
        chat_id = update.effective_chat.id
        message = "🏓 *PONG* 🏓"
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    async def _botResetCommand(self, update: Update, context: ContextTypes) -> None:
        """
        Reset the bot.

        Callback fired with command /reset
        """
        chat_id = update.effective_chat.id
        # This works only if the user is an admin
        if chat_id in self._admins:
            message = "_Riavvio in corso..._"
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN,
            )

            logging.warning("Resetting")
            # System command to reload the python script
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            message = "*Questo comando è solo per admins*"
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN,
            )

    async def _botStopCommand(self, update: Update, context: ContextTypes) -> None:
        """
        Stop the bot.

        Callback fired with command  /stop
        """
        chat_id = update.effective_chat.id
        # This works only if the user is an admin
        if chat_id in self._admins:
            message = "_Il bot è stato fermato_"
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN,
            )
            self._saveSettings()
            self._updater.stop()
            logging.warning("Bot stopped")
            os._exit()
        else:
            message = "*Questo comando è solo per admins*"
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN,
            )

    async def _botError(self, update: Update, context: ContextTypes) -> None:
        logging.error(context.error)

        """
        Function that logs in file and admin chat when an error occurs
        Callback fired by errors and handled by telegram module
        """

        # admin message
        for chat_id in self._admins:
            # HECC
            message = "*ERRORE*"
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN,
            )

        error_string = str(context.error)
        time_string = datetime.now().isoformat()

        message = (
            f"Error at time: {time_string}\n"
            f"Error raised: {error_string}\n"
            f"Update: {update}"
        )

        for chat_id in self._admins:
            await context.bot.send_message(chat_id=chat_id, text=message)

        # logs to file
        logging.error('Update "%s" caused error "%s"', update, context.error)

    async def _botGaussCommand(self, update: Update, context: ContextTypes) -> None:
        """
        Send a photo of Gauss.

        Callback fired with command /gauss
        """
        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=constants.ChatAction.TYPING,
        )

        caption = "*Johann Carl Friedrich Gauß*"
        photo = open(self._image_path, "rb")
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    async def _botStatsCommand(self, update: Update, context: ContextTypes) -> None:
        """
        Return stats about the bot.

        Callback fired with command  /stats
        """
        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(
            chat_id=chat_id, action=constants.ChatAction.TYPING
        )

        # bot started date
        d1 = datetime.fromisoformat(self._start_date)
        # today's date
        d2 = datetime.now()
        days_between = (d2 - d1).days + 1
        # Average number of gif sent per day
        average = int(self._gif_sent / days_between)
        # Create text message
        message = (
            f"Il bot sta funzionando da *{days_between}* giorni.\n"
            f"Sono state inviate *{self._gif_sent}* gif, "
            f"per una media di *{average}* gif al giorno!"
        )
        # Send text message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    async def _botTextMessage(self, update: Update, context: ContextTypes) -> None:
        """
        Send the gif.

        Callback fired with text message
        """
        # skips invalid messages
        if not update.message:
            return

        chat_id = update.effective_chat.id
        user_message = update.message.text.lower()
        message_id = update.message.message_id

        # trigger_map = list of words that trigger the bot
        for key in self._trigger_map:
            # if key in user_message:
            if re.search(r"\b" + key + r"\b", user_message):
                await context.bot.send_chat_action(
                    chat_id=chat_id,
                    action=constants.ChatAction.TYPING,
                )
                # prepare the message
                message = f"*SI DICE {self._trigger_map[key]}*"
                # send the message
                with open(self._fish_gif_path, "rb") as animation:
                    await context.bot.send_animation(
                        chat_id,
                        animation,
                        reply_to_message_id=message_id,
                        caption=message,
                        parse_mode=constants.ParseMode.MARKDOWN,
                    )
                # update the number of sent images
                self._gif_sent += 1


# main entry point
def main() -> None:
    """Script entry point."""
    logging.basicConfig(
        filename=__file__.replace(".py", ".log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        filemode="w+",
    )

    t = Telegram()
    t.start()


if __name__ == "__main__":
    main()
