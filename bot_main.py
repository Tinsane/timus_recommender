#!/usr/local/bin/python3
import datetime
import logging
import pathlib
from typing import Any

import telebot
import turicreate as tc

from src.config import DBSettings, Settings
from src.handlers import HelpHandler, RecommendHandler, StartHandler
from src.loader import TimusAPIClient, TimusClientSettings
from src.storage import SubmitStorage, UserStorage

logger = logging.getLogger(__name__)


class AmazingExceptionHandler:
    def handle(self, exc: Exception) -> None:
        logger.exception("Есть пробитие!\n %s", exc)


def setup_logging() -> None:
    log_directory = pathlib.Path(__file__).parent / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_file = "log-{:%Y-%m-%d:%H:%M:%ST%z}.log".format(datetime.datetime.now(datetime.timezone.utc))
    log_path = log_directory / log_file

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_path, 'w', 'utf-8')
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s (%(filename)s:%(lineno)d %(threadName)s) %(levelname)s - %(name)s: "%(message)s"'
        )
    )
    root_logger.addHandler(handler)
    root_logger.addHandler(logging.StreamHandler())


class _MockModel:
    def recommend_from_interactions(self, frame: tc.SFrame) -> Any:
        return {'problemid': [1, 2, 3, 4, 5]}


class ModelLoader:
    def __init__(self, settings: Settings):
        self._settings = settings

    def load(self) -> Any:
        if self._settings.use_mock_model:
            return _MockModel()
        return tc.load_model(str(self._settings.model_path))


def main() -> None:
    DBSettings().setup_db()

    settings = Settings()
    user_storage = UserStorage()
    submit_storage = SubmitStorage()
    timus_client = TimusAPIClient.from_settings(TimusClientSettings())
    model = ModelLoader(settings).load()

    setup_logging()

    logger.info("Started")
    bot = telebot.TeleBot(settings.token, exception_handler=AmazingExceptionHandler())
    bot.message_handler(commands=['help'])(HelpHandler(bot))
    bot.message_handler(commands=['start'])(
        StartHandler(bot, user_storage=user_storage, submit_storage=submit_storage, timus_client=timus_client)
    )
    bot.message_handler(commands=['recommend'])(
        RecommendHandler(
            bot, user_storage=user_storage, submit_storage=submit_storage, timus_client=timus_client, model=model
        )
    )

    if True:
        try:
            bot.polling(timeout=1, long_polling_timeout=1)
        # TGBot wraps this exception :(
        # except KeyboardInterrupt:  # noqa : E800
        #     break  # noqa : E800
        except Exception:
            logger.exception("Exception caught by global try/except")


if __name__ == '__main__':
    main()
