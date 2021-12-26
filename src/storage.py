import datetime
from typing import List, Optional

from pydantic import BaseModel

import db
from src.loader import ProblemModel, TimusAPISubmit


class DBUser(BaseModel):
    id: int
    telegram_id: int
    timus_id: int

    class Config:
        frozen = True


class DBSubmit(BaseModel):
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


class DBProblem(BaseModel):
    id: int
    number: int
    title: str
    difficulty: int
    solutions: int
    limits: str
    text: str

    class Config:
        frozen = True


class UserStorage:
    def create_or_update(self, user_id: int, timus_id: int) -> DBUser:
        with db.create_session() as session:
            user = session.query(db.TelegramUser).filter(db.TelegramUser.user_id == user_id).one_or_none()
            if user is None:
                user = db.TelegramUser(user_id=user_id, timus_id=timus_id)
                session.add(user)
                session.flush()
            user.timus_id = timus_id

            return self._convert_db_to_model(user)

    def get_user(self, user_id: int) -> DBUser:
        with db.create_session() as session:
            user = session.query(db.TelegramUser).filter(db.TelegramUser.user_id == user_id).one()

            return self._convert_db_to_model(user)

    def _convert_db_to_model(self, user: db.TelegramUser) -> DBUser:
        return DBUser(telegram_id=user.user_id, id=user.id, timus_id=user.timus_id)


class SubmitStorage:
    def batch_create(self, submits: List[TimusAPISubmit]) -> List[DBSubmit]:
        with db.create_session() as session:
            timus_submit_ids = {submit.submit_id for submit in submits}

            already_created = {
                submit.timus_submit_id
                for submit in session.query(db.Submit).filter(db.Submit.timus_submit_id.in_(timus_submit_ids)).all()
            }
            db_submits = [
                self._convert_api_model_to_db(submit) for submit in submits if submit.submit_id not in already_created
            ]
            session.add_all(db_submits)
            session.flush()
            return [self._convert_db_to_model(submit) for submit in db_submits]

    def get_all_by_author(self, timus_user_id: int) -> List[DBSubmit]:
        with db.create_session() as session:
            submits = session.query(db.Submit).filter(db.Submit.timus_user_id == timus_user_id).all()
            return [self._convert_db_to_model(submit) for submit in submits]

    def get_all(self) -> List[DBSubmit]:
        with db.create_session() as session:
            return [self._convert_db_to_model(submit) for submit in session.query(db.Submit).all()]

    def get_last_or_none(
        self, timus_user_id: Optional[int] = None, verdict: Optional[str] = None
    ) -> Optional[DBSubmit]:
        with db.create_session() as session:
            submit_query = session.query(db.Submit).order_by(db.Submit.timus_submit_id.desc())
            if timus_user_id is not None:
                submit_query = submit_query.filter(db.Submit.timus_user_id == timus_user_id)
            if verdict is not None:
                submit_query = submit_query.filter(db.Submit.verdict == verdict)
            submit = submit_query.first()
            if submit is None:
                return None
            return self._convert_db_to_model(submit)

    def _convert_api_model_to_db(self, model: TimusAPISubmit) -> db.Submit:
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

    def _convert_db_to_model(self, submit: db.Submit) -> DBSubmit:
        return DBSubmit(
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


class ProblemStorage:
    def create_or_update(self, problem: ProblemModel) -> DBProblem:
        with db.create_session() as session:
            db_problem = session.query(db.Problem).filter(db.Problem.number == problem.number).one_or_none()
            if db_problem is None:
                db_problem = db.Problem(
                    number=problem.number,
                    title=problem.title,
                    difficulty=problem.difficulty,
                    solutions=problem.solutions,
                    limits=problem.limits,
                    text=problem.text,
                )
                session.add(db_problem)
                session.flush()

            return self._convert_db_to_model(db_problem)

    def get_by_number_or_none(self, number: int) -> Optional[DBProblem]:
        with db.create_session() as session:
            db_problem = session.query(db.Problem).filter(db.Problem.number == number).one_or_none()
            if db_problem is None:
                return None

            return self._convert_db_to_model(db_problem)

    def _convert_db_to_model(self, problem: db.Problem) -> DBProblem:
        return DBProblem(
            id=problem.id,
            number=problem.number,
            title=problem.title,
            difficulty=problem.difficulty,
            solutions=problem.solutions,
            limits=problem.limits,
            text=problem.text,
        )
