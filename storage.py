from typing import List, Optional, Tuple

from pydantic import BaseModel

import db


class UserModel(BaseModel):
    id: int
    telegram_id: int
    timus_id: int

    class Config:
        frozen = True


class SubmitModel(BaseModel):
    id: int
    submit_id: int
    timus_user_id: int
    problem_id: int

    class Config:
        frozen = True


class UserStorage:
    def create_user(self, user_id: int, timus_id: int) -> UserModel:
        with db.create_session() as session:
            user = session.query(db.TelegramUser).filter(db.TelegramUser.user_id == user_id).one_or_none()
            if user is None:
                user = db.TelegramUser(user_id=user_id, timus_id=timus_id)
                session.add(user)
                session.flush()
            user.timus_id = timus_id

            return UserModel(telegram_id=user.user_id, id=user.id, timus_id=user.timus_id)

    def get_user(self, user_id: int) -> UserModel:
        with db.create_session() as session:
            user = session.query(db.TelegramUser).filter(db.TelegramUser.user_id == user_id).one()

            return UserModel(telegram_id=user.user_id, id=user.id, timus_id=user.timus_id)


class SubmitStorage:
    def batch_create(self, submits: List[Tuple[int, int, int]]) -> List[SubmitModel]:
        with db.create_session() as session:
            db_submits = [
                db.Submit(timus_submit_id=submit_id, timus_user_id=timus_user_id, problem_id=problem_id)
                for (submit_id, timus_user_id, problem_id) in submits
            ]
            session.add_all(db_submits)
            session.flush()
            return [
                SubmitModel(
                    id=submit.id,
                    submit_id=submit.timus_submit_id,
                    timus_user_id=submit.timus_user_id,
                    problem_id=submit.problem_id,
                )
                for submit in db_submits
            ]

    def get_all(self, timus_user_id: int) -> List[SubmitModel]:
        with db.create_session() as session:
            submits = session.query(db.Submit).filter(db.Submit.timus_user_id == timus_user_id).all()
            return [
                SubmitModel(
                    id=submit.id,
                    submit_id=submit.timus_submit_id,
                    timus_user_id=submit.timus_user_id,
                    problem_id=submit.problem_id,
                )
                for submit in submits
            ]

    def create_submit(self, submit_id: int, timus_user_id: int, problem_id: int) -> SubmitModel:
        with db.create_session() as session:
            submit = session.query(db.Submit).filter(db.Submit.timus_submit_id == submit_id).one_or_none()
            if submit is None:
                submit = db.Submit(timus_submit_id=submit_id, timus_user_id=timus_user_id, problem_id=problem_id)
                session.add(submit)
                session.flush()
                return SubmitModel(
                    id=submit.id,
                    submit_id=submit.timus_submit_id,
                    timus_user_id=submit.timus_user_id,
                    problem_id=submit.problem_id,
                )
            else:
                raise AssertionError("I fucked your mother")

    def get_last_submit(self, timus_user_id: int) -> Optional[SubmitModel]:
        with db.create_session() as session:
            submit = (
                session.query(db.Submit)
                .filter(db.Submit.timus_user_id == timus_user_id)
                .order_by(db.Submit.timus_submit_id.desc())
                .first()
            )
            if submit is None:
                return None
            return SubmitModel(
                id=submit.id,
                submit_id=submit.timus_submit_id,
                timus_user_id=submit.timus_user_id,
                problem_id=submit.problem_id,
            )
