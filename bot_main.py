#!/usr/local/bin/python3
import datetime
import logging
import os
import pathlib
import time
from typing import List, Optional

import telebot
import turicreate as tc

from config import DBSettings, Settings
from loader import TimusLoader, TimusLoaderSettings
from storage import DBSubmitModel, DBUserModel, SubmitStorage, UserStorage

logger = logging.getLogger(__name__)


class AmazingExceptionHandler:
    def handle(self, exc: Exception) -> None:
        logger.exception("Есть пробитие!\n %s", exc)


TOKEN = os.environ.get('TIMUS_RECOMMENDER_BOT_TOKEN', default='')
bot = telebot.TeleBot(TOKEN, exception_handler=AmazingExceptionHandler())
user_storage = UserStorage()
submit_storage = SubmitStorage()
loader = TimusLoader(TimusLoaderSettings())
model = tc.load_model('prod_model')


@bot.message_handler(commands=['help'])
def help_handler(message: telebot.types.Message) -> None:
    bot.reply_to(message, 'Help is on the way!')


@bot.message_handler(commands=['start'])
def start_handler(message: telebot.types.Message) -> None:
    msg = bot.reply_to(
        message,
        f'Привет, {message.from_user.username}!\nНам нужен твой judge id без букв. Например,'
        f' если твой judge id - это 248409ex, то нужно ввести 248409.',
    )
    bot.register_next_step_handler(msg, register_user)


def register_user(message: telebot.types.Message) -> None:
    try:
        user = user_storage.create_user(message.from_user.id, int(message.text))
    except Exception:
        logger.exception("User could not be created")
        bot.send_message(message.from_user.id, 'Какое-то палево, напиши @tinsane')
    else:
        bot.send_message(message.from_user.id, 'Молодец, возьми с полки пирожок.')
        fetch_submits(user)


@bot.message_handler(commands=['recommend'])
def recommend_handler(message: telebot.types.Message) -> None:
    logger.info("Started at: %s", time.time())
    user = user_storage.get_user(int(message.from_user.id))
    fetch_submits(user)
    submits = submit_storage.get_all(user.timus_id)
    logger.info("Loaded submissions at: %s", time.time())
    sub_df = to_unique_submits_df(submits)
    # TODO : fails with zero submits :(
    # print(model.recommend(users=[248409]))  # noqa=E800
    recommendation = model.recommend_from_interactions(sub_df)
    logger.info("Computed recommendations at: %s", time.time())
    bot.send_message(
        message.from_user.id,
        "Попробуй решить эти задачи:\n%s" % '\n'.join(map(str, recommendation['problemid'])),
    )


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


def init_database(settings: Settings) -> None:
    db_settings = DBSettings()
    db_settings.setup_db()
    if settings.create_database:
        db_settings.create_database()


def fetch_submits(user: DBUserModel) -> None:
    last_submit = submit_storage.get_last_submit(user.timus_id)
    fetch_to = last_submit.submit_id if last_submit is not None else 0
    from_submit_id: Optional[int] = None
    count = 100
    submits = []
    while True:
        current_submits = loader.get_submits(author_id=user.timus_id, count=count, from_submit_id=from_submit_id)
        finished_fetching = False
        for submit in current_submits:
            if submit.submit_id == fetch_to:
                finished_fetching = True
                break
            submits.append(submit)
        if finished_fetching:
            break
        from_submit_id = submits[-1].submit_id - 1
    submit_storage.batch_create(submits)


def to_unique_submits_df(submits: List[DBSubmitModel]) -> tc.SFrame:
    problems = {}
    for submit in submits[::-1]:
        problems[submit.problem_id] = (submit.submit_id, submit.timus_user_id)
    sub_col = []
    prob_col = []
    auth_col = []
    for problem in problems:
        sub_id, author_id = problems[problem]
        sub_col.append(sub_id)
        prob_col.append(problem)
        auth_col.append(author_id)
    return tc.SFrame({'submitid': sub_col, 'authorid': auth_col, 'problemid': prob_col})


def main() -> None:
    settings = Settings()
    init_database(settings)
    setup_logging()
    log = logging.getLogger("main")

    log.info("Started")

    if True:
        try:
            bot.polling(timeout=1, long_polling_timeout=1)
        # TGBot wraps this exception :(
        # except KeyboardInterrupt:  # noqa : E800
        #     break  # noqa : E800
        except Exception:
            log.exception("Exception caught by global try/except")


if __name__ == '__main__':
    main()
