#!/usr/local/bin/python3
import datetime
import logging
import os
import pathlib
import time
from html.parser import HTMLParser
from typing import Any, List, Optional, Tuple

import requests
import telebot
import turicreate as tc

from config import DBSettings, Settings
from storage import SubmitModel, SubmitStorage, UserModel, UserStorage

logger = logging.getLogger(__name__)


class AmazingExceptionHandler:
    def handle(self, exc: Exception) -> None:
        logger.exception("Есть пробитие!\n %s", exc)


TOKEN = os.environ.get('TIMUS_RECOMMENDER_BOT_TOKEN', default='')
bot = telebot.TeleBot(TOKEN, exception_handler=AmazingExceptionHandler())
user_storage = UserStorage()
submit_storage = SubmitStorage()
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


class SubmitsParser(HTMLParser):
    def __init__(self, authorid: int):
        self._authorid = authorid
        self.submits: List[Tuple[int, int, int]] = []
        self.start_parsing = False
        self.submit_row = False
        self.parse_id = False
        self.id: Optional[int] = None
        self.parse_problem = False
        super().__init__()

    def handle_starttag(self, tag: str, attrs: Any) -> None:  # noqa : C901
        if tag == 'table':
            dattrs = dict(attrs)
            if dattrs.get('class', '') == 'status':
                self.start_parsing = True
        elif not self.start_parsing:
            return

        if tag == 'tr':
            dattrs = dict(attrs)
            if dattrs.get('class', '') in {'even', 'odd'}:
                self.submit_row = True
        elif not self.submit_row:
            return

        if tag == 'td':
            dattrs = dict(attrs)
            if dattrs.get('class', '') == 'id':
                self.parse_id = True
            elif dattrs.get('class', '') == 'problem':
                self.parse_problem = True

    def handle_endtag(self, tag: str) -> None:
        if tag == 'table' and self.start_parsing:
            self.start_parsing = False
        if tag == 'tr' and self.submit_row:
            self.submit_row = False

    def handle_data(self, data: str) -> None:
        if self.parse_id:
            self.id = int(data)
            self.parse_id = False
            return
        if self.parse_problem:
            problem = int(data)
            if self.id is None:
                raise AssertionError()
            self.submits.append((self.id, self._authorid, problem))
            self.parse_problem = False
            return


def fetch_submits(user: UserModel) -> None:
    last_submit = submit_storage.get_last_submit(user.timus_id)
    fetch_to = last_submit.submit_id if last_submit is not None else 0
    pagination_token: Optional[int] = None
    submits = []
    while True:
        if pagination_token is None:
            url = f'https://timus.online/status.aspx?author={user.timus_id}&status=accepted&count=100'
        else:
            url = f'https://timus.online/status.aspx?author={user.timus_id}&status=accepted&count=100&from={pagination_token}'  # noqa : E501
        page = requests.get(url)
        parser = SubmitsParser(user.timus_id)
        parser.feed(page.text)
        if len(parser.submits) == 0:
            break
        finished_fetching = False
        for submit in parser.submits:
            submit_id, _, _ = submit
            if submit_id == fetch_to:
                finished_fetching = True
                break
            submits.append(submit)
        if finished_fetching:
            break
        pagination_token = submits[-1][0] - 1
    submit_storage.batch_create(submits)


def to_unique_submits_df(submits: List[SubmitModel]) -> tc.SFrame:
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
