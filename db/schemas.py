import sqlalchemy as sa

from db.base import Base


class TelegramUser(Base):
    user_id = sa.Column(sa.BigInteger, unique=True, nullable=False)
    timus_id = sa.Column(sa.Integer, index=True, nullable=False)


class Problem(Base):
    number = sa.Column(sa.Integer, index=True, nullable=False, unique=True)
    title = sa.Column(sa.Text, nullable=False)
    difficulty = sa.Column(sa.Integer, nullable=False)
    solutions = sa.Column(sa.Integer, nullable=False)
    limits = sa.Column(sa.Text, nullable=False)
    text = sa.Column(sa.Text, nullable=False)


class Submit(Base):
    timus_submit_id = sa.Column(sa.BigInteger, unique=True, nullable=False)
    timus_user_id = sa.Column(sa.Integer, index=True, nullable=False)
    timus_problem_id = sa.Column(sa.Integer, nullable=False)
    date = sa.Column(sa.DateTime(timezone=True), nullable=False)
    language = sa.Column(sa.Text, nullable=False)
    verdict = sa.Column(sa.Text, nullable=False)
    test = sa.Column(sa.Integer, nullable=False)
    runtime_ms = sa.Column(sa.Integer, nullable=False)
    memory_kb = sa.Column(sa.Integer, nullable=False)
