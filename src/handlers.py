import abc
import logging
import time
from typing import Any, List, Optional

import telebot
import turicreate as tc

from src.loader import TimusAPIClient, Verdict
from src.storage import DBSubmit, DBUser, SubmitStorage, UserStorage

logger = logging.getLogger(__name__)


class IBotHandler(abc.ABC):
    @abc.abstractmethod
    def __call__(self, message: telebot.types.Message) -> None:
        pass


class HelpHandler(IBotHandler):
    def __init__(self, bot: telebot.TeleBot):
        self._bot = bot

    def __call__(self, message: telebot.types.Message) -> None:
        self._bot.reply_to(message, 'Help is on the way!')


class StartHandler(IBotHandler):
    def __init__(
        self,
        bot: telebot.TeleBot,
        user_storage: UserStorage,
        submit_storage: SubmitStorage,
        timus_client: TimusAPIClient,
    ):
        self._bot = bot
        self._user_storage = user_storage
        self._submit_storage = submit_storage
        self._timus_client = timus_client

    def __call__(self, message: telebot.types.Message) -> None:
        msg = self._bot.reply_to(
            message,
            f'Привет, {message.from_user.username}!\nНам нужен твой judge id без букв. Например,'
            f' если твой judge id - это 248409ex, то нужно ввести 248409.',
        )
        self._bot.register_next_step_handler(msg, self._register_user)

    def _register_user(self, message: telebot.types.Message) -> None:
        try:
            user = self._user_storage.create_or_update(message.from_user.id, int(message.text))
        except Exception:
            logger.exception("User could not be created")
            self._bot.send_message(message.from_user.id, 'Какое-то палево, напиши @tinsane')
        else:
            self._bot.send_message(message.from_user.id, 'Молодец, возьми с полки пирожок.')
            fetch_submits(user, self._submit_storage, self._timus_client)


class RecommendHandler(IBotHandler):
    def __init__(
        self,
        bot: telebot.TeleBot,
        user_storage: UserStorage,
        submit_storage: SubmitStorage,
        timus_client: TimusAPIClient,
        model: Any,
    ):
        self._bot = bot
        self._user_storage = user_storage
        self._submit_storage = submit_storage
        self._timus_client = timus_client
        self._model = model

    def __call__(self, message: telebot.types.Message) -> None:
        logger.info("Started at: %s", time.time())
        user = self._user_storage.get_user(int(message.from_user.id))
        fetch_submits(user, self._submit_storage, self._timus_client)
        ac_submits = [
            submit
            for submit in self._submit_storage.get_all_by_author(user.timus_id)
            if submit.verdict == Verdict.ACCEPTED
        ]
        logger.info("Loaded submissions at: %s", time.time())
        sub_df = to_unique_submits_df(ac_submits)
        # TODO : fails with zero submits :(
        # print(model.recommend(users=[248409]))  # noqa=E800
        recommendation = self._model.recommend_from_interactions(sub_df)
        logger.info("Computed recommendations at: %s", time.time())
        self._bot.send_message(
            message.from_user.id,
            "Попробуй решить эти задачи:\n%s" % '\n'.join(map(str, recommendation['problemid'])),
        )


def fetch_submits(user: DBUser, submit_storage: SubmitStorage, client: TimusAPIClient) -> None:
    last_submit = submit_storage.get_last_or_none(user.timus_id)
    fetch_to = last_submit.submit_id if last_submit is not None else 0
    from_submit_id: Optional[int] = None
    count = 100
    submits = []
    while True:
        current_submits = client.get_submits(author_id=user.timus_id, count=count, from_submit_id=from_submit_id)
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


def to_unique_submits_df(submits: List[DBSubmit]) -> tc.SFrame:
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
