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
        self.loadSettings()

    def loadSettings(self, path="src/settings.json"):
        """
        loads settings from the settings file
        """

        self._settings_path = path
        with open(self._settings_path) as json_file:
            # only keeps settings for Telegram, discarding others
            self._settings = ujson.load(json_file)

        # Save settings inside variables for easier access
        self._token = self._settings["token"]
        self._admins = self._settings["admins"]
        self._start_date = self._settings["start_date"]
        self._gif_sent = self._settings["gif_sent"]
        self._fish_gif_path = self._settings["fish_gif_path"]
        self._image_path = self._settings["image_path"]
        self._trigger_map = self._settings["trigger_map"]

    def saveSettings(self):
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

    def updateGifSent(self):
        """
        updates number of GIFs sent and saves it to file
        """
        self._gif_sent += 1
        self._settings["gif_sent"] = self._gif_sent
        self.saveSettings()

    # Returns some meaningful informations needed in callbacks
    @ property
    def status(self):
        return {
            "admins": self._admins,
            "fish_gif_path": self._fish_gif_path,
            "start_date": self._start_date,
            "gif_sent": self._gif_sent,
            "image_path": self._image_path,
            "trigger_map": self._trigger_map,
        }

    def start(self):
        """
        starts the bot
        """

        self.updater = Updater(self._token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.jobqueue = self.updater.job_queue

        self.dispatcher.add_error_handler(error)
        self.jobqueue.run_once(bot_started, when=0, name="bot_started")

        self.dispatcher.add_handler(CommandHandler('start', start))
        self.dispatcher.add_handler(CommandHandler('gauss', gauss))
        self.dispatcher.add_handler(CommandHandler('stop', stop))
        self.dispatcher.add_handler(CommandHandler('ping', ping))
        self.dispatcher.add_handler(CommandHandler('reset', reset))
        self.dispatcher.add_handler(CommandHandler('stats', stats))
        self.dispatcher.add_handler(MessageHandler(Filters.text, text_message))

        self.updater.start_polling()
        logging.info("Bot started")
        self.updater.idle()


def bot_started(context: CallbackContext):
    """
    Function that sends a message to admins whenever the bot is started.
    Callback fired at startup
    """

    status = t.status
    for chat_id in status["admins"]:
        message = "*Il bot è stato avviato*"
        context.bot.send_message(chat_id=chat_id, text=message,
                                 parse_mode=ParseMode.MARKDOWN)


def start(update, context):
    """
    Function that greets user during first start
    Callback fired with command /start
    """

    chat_id = update.effective_chat.id
    message = "_Sono pronto a correggere chiunque dica boiate_"
    context.bot.send_message(chat_id=chat_id, text=message,
                             parse_mode=ParseMode.MARKDOWN)


def ping(update, context):
    """
    Function that simply replies "PONG"
    Callback fired with command /ping for debug purposes
    """

    chat_id = update.effective_chat.id
    message = "🏓 *PONG* 🏓"
    context.bot.send_message(chat_id=chat_id, text=message,
                             parse_mode=ParseMode.MARKDOWN)


def reset(update, context):
    """
    Function that resets the bot 
    Callback fired with command /reset
    """

    chat_id = update.effective_chat.id
    # This works only if the user is an admin
    if chat_id in t.status["admins"]:
        message = "_Riavvio in corso..._"
        context.bot.send_message(chat_id=chat_id, text=message,
                                 parse_mode=ParseMode.MARKDOWN)

        logging.warning("Resetting")
        # System command to reload the python script
        os.execl(sys.executable, sys.executable, * sys.argv)
    else:
        message = "*Questo comando è solo per admins*"
        context.bot.send_message(
            chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN)


def stop(update, context):
    """
    Function that stops the bot
    Callback fired with command  /stop
    """

    chat_id = update.effective_chat.id
    # This works only if the user is an admin
    if chat_id in t.status["admins"]:
        message = "_Il bot è stato fermato_"
        context.bot.send_message(
            chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
        t.saveSettings()
        t.updater.stop()
        logging.warning("Bot stopped")
        os._exit()
        exit()
    else:
        message = "*Questo comando è solo per admins*"
        context.bot.send_message(
            chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN)


def error(update, context):
    logging.error(context.error)

    """
    Function that logs in file and admin chat when an error occurs
    Callback fired by errors and handled by telegram module
    """

    # admin message
    for chat_id in t.status["admins"]:
        # HECC
        message = "*ERRORE*"
        context.bot.send_message(chat_id=chat_id, text=message,
                                 parse_mode=ParseMode.MARKDOWN)

    error_string = str(context.error).replace("_", "\\_")  # MARKDOWN escape
    time_string = datetime.now().isoformat()

    message = f"Error at time: {time_string}\n" \
              f"Error raised: {error_string}\n" \
              f"Update: {update}"

    for chat_id in t.status["admins"]:
        context.bot.send_message(chat_id=chat_id, text=message)

    # logs to file
    logging.error('Update "%s" caused error "%s"', update, context.error)


def gauss(update, context):
    """
    Function that sends a photo of Gauss
    Callback fired with command  /gauss
    """

    chat_id = update.effective_chat.id
    context.bot.send_chat_action(
        chat_id=chat_id, action=ChatAction.TYPING)
    caption = "*Johann Carl Friedrich Gauß*"
    status = t.status
    photo = open(status["image_path"], "rb")
    context.bot.send_photo(chat_id=chat_id, photo=photo,
                           caption=caption, parse_mode=ParseMode.MARKDOWN)


def stats(update, context):
    """
    Function that return stats about the bot
    Callback fired with command  /stats
    """

    chat_id = update.effective_chat.id
    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    status = t.status

    # bot started date
    d1 = datetime.fromisoformat(status["start_date"])
    # today's date
    d2 = datetime.now()
    days_between = (d2 - d1).days + 1
    # Average number of gif sent per day
    average = int(status["gif_sent"] / days_between)
    # Create text message
    message = f"Il bot sta funzionando da *{days_between}* giorni.\n" \
              f"Sono state inviate *{status['gif_sent']}* gif, " \
              f"per una media di *{average}* gif al giorno!"
    # Send text message
    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN)


def text_message(update, context):
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
    for key in t.status["trigger_map"]:
        # if key in user_message:
        if re.search(r'\b' + key + r'\b', user_message):
            context.bot.send_chat_action(
                chat_id=chat_id, action=ChatAction.TYPING)
            # prepare the message
            message = f"*SI DICE {t.status['trigger_map'][key]}*"
            animation = open(t.status["fish_gif_path"], "rb")
            context.bot.send_animation(
                chat_id, animation, reply_to_message_id=message_id,
                caption=message, parse_mode=ParseMode.MARKDOWN)
            animation.close()
            # update the number of sent images
            t.updateGifSent()


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
