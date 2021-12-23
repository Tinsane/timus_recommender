import datetime
from typing import List, Optional

from pydantic import BaseModel

import db
from loader import TimusAPISubmit


class DBUserModel(BaseModel):
    id: int
    telegram_id: int
    timus_id: int

    class Config:
        frozen = True


class DBSubmitModel(BaseModel):
    id: int
    submit_id: int
    timus_user_id: int
    problem_id: int
    date: datetime.datetime
    language: str
    verdict: str
    test: int
    runtime_ms: int
    memory_kb: int

    class Config:
        frozen = True


class UserStorage:
    def create_user(self, user_id: int, timus_id: int) -> DBUserModel:
        with db.create_session() as session:
            user = session.query(db.TelegramUser).filter(db.TelegramUser.user_id == user_id).one_or_none()
            if user is None:
                user = db.TelegramUser(user_id=user_id, timus_id=timus_id)
                session.add(user)
                session.flush()
            user.timus_id = timus_id

            return DBUserModel(telegram_id=user.user_id, id=user.id, timus_id=user.timus_id)

    def get_user(self, user_id: int) -> DBUserModel:
        with db.create_session() as session:
            user = session.query(db.TelegramUser).filter(db.TelegramUser.user_id == user_id).one()

            return DBUserModel(telegram_id=user.user_id, id=user.id, timus_id=user.timus_id)


def convert_submit_api_model_to_db(model: TimusAPISubmit) -> db.Submit:
    return db.Submit(
        timus_submit_id=model.submit_id,
        timus_user_id=model.author_id,
        timus_problem_id=model.problem,
        date=model.date,
        language=model.language,
        verdict=model.verdict,
        test=model.test,
        runtime_ms=model.runtime_ms,
        memory_kb=model.memory_kb,
    )


def convert_db_submit_to_model(submit: db.Submit) -> DBSubmitModel:
    return DBSubmitModel(
        id=submit.id,
        submit_id=submit.timus_submit_id,
        timus_user_id=submit.timus_user_id,
        problem_id=submit.timus_problem_id,
        date=submit.date,
        language=submit.language,
        verdict=submit.verdict,
        test=submit.test,
        runtime_ms=submit.runtime_ms,
        memory_kb=submit.memory_kb,
    )


class SubmitStorage:
    def batch_create(self, submits: List[TimusAPISubmit]) -> List[DBSubmitModel]:
        with db.create_session() as session:
            db_submits = [convert_submit_api_model_to_db(submit) for submit in submits]
            session.add_all(db_submits)
            session.flush()
            return [convert_db_submit_to_model(submit) for submit in db_submits]

    def get_all(self, timus_user_id: int) -> List[DBSubmitModel]:
        with db.create_session() as session:
            submits = session.query(db.Submit).filter(db.Submit.timus_user_id == timus_user_id).all()
            return [convert_db_submit_to_model(submit) for submit in submits]

    def get_last_submit(self, timus_user_id: int, verdict: Optional[str] = None) -> Optional[DBSubmitModel]:
        with db.create_session() as session:
            submit_query = (
                session.query(db.Submit)
                .filter(db.Submit.timus_user_id == timus_user_id)
                .order_by(db.Submit.timus_submit_id.desc())
            )
            if verdict is not None:
                submit_query = submit_query.filter(db.Submit.verdict == verdict)
            submit = submit_query.first()
            if submit is None:
                return None
            return convert_db_submit_to_model(submit)
