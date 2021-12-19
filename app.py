import logging

import telebot

from rpg_bot.config import DBSettings, Settings
from utils import filter_user_by_message


def create_bot(settings: Settings) -> telebot.TeleBot:
    from rpg_bot.factory import CallbackHandler, CommonHandler, create_container

    bot = telebot.TeleBot(settings.token)
    container = create_container(bot)

    bot.message_handler(func=filter_user_by_message(settings))(container.resolve(CommonHandler))
    bot.callback_query_handler(func=filter_user_by_message(settings))(container.resolve(CallbackHandler))

    return bot


def main(bot: telebot.TeleBot) -> None:
    log = logging.getLogger("main")

    log.info("Started")

    if True:
        try:
            bot.polling()
        except Exception:
            log.exception("Exception cought by global try/except")


def init_database(settings: Settings) -> None:
    db_settings = DBSettings()
    db_settings.setup_db()
    if settings.create_database:
        db_settings.create_database()


if __name__ == '__main__':
    settings = Settings()
    init_database(settings)
    main(create_bot(settings))
