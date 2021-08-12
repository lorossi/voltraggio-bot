# Lorenzo Rossi - https://lorenzoros.si
# Somewhere in 2019
# Gotta find an hobby someday

import os
import re
import sys
import ujson
import logging
from datetime import datetime
from telegram import ParseMode, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackContext, \
    Filters, MessageHandler


class Telegram:
    """
    This class contains all the methods and variables needed to control the
    Telegram bot
    """

    def __init__(self):
        self._settings = {}
        self._settings_path = "src/settings.json"
        self._loadSettings()

    def _loadSettings(self):
        """
        loads settings from the settings file
        """

        with open(self._settings_path) as json_file:
            # only keeps settings for Telegram, discarding others
            self._settings = ujson.load(json_file)

    def _saveSettings(self):
        """
        saves settings into file
        """

        with open(self._settings_path) as json_file:
            old_settings = ujson.load(json_file)

        # since settings is a dictionary, we update the settings loaded
        # with the current settings dict
        old_settings.update(self._settings)

        with open(self._settings_path, 'w') as outfile:
            ujson.dump(old_settings, outfile, indent=2)

    # Setters/getters

    @property
    def _admins(self):
        return self._settings["admins"]

    @property
    def _image_path(self):
        return self._settings["image_path"]

    @property
    def _start_date(self):
        return self._settings["start_date"]

    @property
    def _gif_sent(self):
        return self._settings["gif_sent"]

    @_gif_sent.setter
    def _gif_sent(self, value):
        self._settings["gif_sent"] = value
        self._saveSettings()

    @property
    def _trigger_map(self):
        return self._settings["trigger_map"]

    @property
    def _fish_gif_path(self):
        return self._settings["fish_gif_path"]

    def start(self):
        """
        starts the bot
        """

        self._updater = Updater(
            self._settings["token"],
            use_context=True
        )
        self._dispatcher = self._updater.dispatcher
        self._jobqueue = self._updater.job_queue

        self._dispatcher.add_error_handler(self._botError)
        self._jobqueue.run_once(self._botStarted, when=0, name="bot_started")

        self._dispatcher.add_handler(
            CommandHandler('start', self._botStartCommand)
        )
        self._dispatcher.add_handler(
            CommandHandler('gauss', self._botGaussCommand)
        )
        self._dispatcher.add_handler(
            CommandHandler('stop', self._botStopCommand)
        )
        self._dispatcher.add_handler(
            CommandHandler('ping', self._botPingCommand)
        )
        self._dispatcher.add_handler(
            CommandHandler('reset', self._botResetCommand)
        )
        self._dispatcher.add_handler(
            CommandHandler('stats', self._botStatsCommand)
        )
        self._dispatcher.add_handler(
            MessageHandler(Filters.text, self._botTextMessage)
        )

        self._updater.start_polling()
        logging.info("Bot started")
        self._updater.idle()

    def _botStarted(self, context: CallbackContext):
        """
        Function that sends a message to admins whenever the bot is started.
        Callback fired at startup
        """

        message = "*Il bot è stato avviato*"
        for chat_id in self._admins:
            context.bot.send_message(chat_id=chat_id, text=message,
                                     parse_mode=ParseMode.MARKDOWN)

    def _botStartCommand(self, update, context):
        """
        Function that greets user during first start
        Callback fired with command /start
        """

        chat_id = update.effective_chat.id
        message = "_Sono pronto a correggere chiunque dica boiate_"
        context.bot.send_message(chat_id=chat_id, text=message,
                                 parse_mode=ParseMode.MARKDOWN)

    def _botPingCommand(self, update, context):
        """
        Function that simply replies "PONG"
        Callback fired with command /ping for debug purposes
        """

        chat_id = update.effective_chat.id
        message = "🏓 *PONG* 🏓"
        context.bot.send_message(chat_id=chat_id, text=message,
                                 parse_mode=ParseMode.MARKDOWN)

    def _botResetCommand(self, update, context):
        """
        Function that resets the bot 
        Callback fired with command /reset
        """

        chat_id = update.effective_chat.id
        # This works only if the user is an admin
        if chat_id in self._admins:
            message = "_Riavvio in corso..._"
            context.bot.send_message(chat_id=chat_id, text=message,
                                     parse_mode=ParseMode.MARKDOWN)

            logging.warning("Resetting")
            # System command to reload the python script
            os.execl(sys.executable, sys.executable, * sys.argv)
        else:
            message = "*Questo comando è solo per admins*"
            context.bot.send_message(chat_id=chat_id, text=message,
                                     parse_mode=ParseMode.MARKDOWN)

    def _botStopCommand(self, update, context):
        """
        Function that stops the bot
        Callback fired with command  /stop
        """

        chat_id = update.effective_chat.id
        # This works only if the user is an admin
        if chat_id in self._admins:
            message = "_Il bot è stato fermato_"
            context.bot.send_message(chat_id=chat_id, text=message,
                                     parse_mode=ParseMode.MARKDOWN)
            self._saveSettings()
            self._updater.stop()
            logging.warning("Bot stopped")
            os._exit()
        else:
            message = "*Questo comando è solo per admins*"
            context.bot.send_message(chat_id=chat_id, text=message,
                                     parse_mode=ParseMode.MARKDOWN)

    def _botError(self, update, context):
        logging.error(context.error)

        """
        Function that logs in file and admin chat when an error occurs
        Callback fired by errors and handled by telegram module
        """

        # admin message
        for chat_id in self._admins:
            # HECC
            message = "*ERRORE*"
            context.bot.send_message(chat_id=chat_id, text=message,
                                     parse_mode=ParseMode.MARKDOWN)

        error_string = str(context.error).replace(
            "_", "\\_")  # MARKDOWN escape
        time_string = datetime.now().isoformat()

        message = (
            f"Error at time: {time_string}\n"
            f"Error raised: {error_string}\n"
            f"Update: {update}"
        )

        for chat_id in self._admins:
            context.bot.send_message(chat_id=chat_id, text=message)

        # logs to file
        logging.error('Update "%s" caused error "%s"', update, context.error)

    def _botGaussCommand(self, update, context):
        """
        Function that sends a photo of Gauss
        Callback fired with command  /gauss
        """

        chat_id = update.effective_chat.id
        context.bot.send_chat_action(
            chat_id=chat_id, action=ChatAction.TYPING)

        caption = "*Johann Carl Friedrich Gauß*"
        photo = open(self._image_path, "rb")
        context.bot.send_photo(chat_id=chat_id, photo=photo,
                               caption=caption,
                               parse_mode=ParseMode.MARKDOWN)

    def _botStatsCommand(self, update, context):
        """
        Function that return stats about the bot
        Callback fired with command  /stats
        """

        chat_id = update.effective_chat.id
        context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

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
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=message,
                                 parse_mode=ParseMode.MARKDOWN)

    def _botTextMessage(self, update, context):
        """
        Function that sends the gif
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
            if re.search(r'\b' + key + r'\b', user_message):
                context.bot.send_chat_action(
                    chat_id=chat_id, action=ChatAction.TYPING)
                # prepare the message
                message = f"*SI DICE {self._trigger_map[key]}*"
                # send the message
                with open(self._fish_gif_path, "rb") as animation:
                    context.bot.send_animation(
                        chat_id, animation,
                        reply_to_message_id=message_id,
                        caption=message, parse_mode=ParseMode.MARKDOWN
                    )
                # update the number of sent images
                self._gif_sent += 1


# main entry point
def main():
    logging.basicConfig(
        filename=__file__.replace(".py", ".log"),
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        filemode="w+"
    )

    t = Telegram()
    t.start()


if __name__ == '__main__':
    main()
