import sqlalchemy as sa

from db.base import Base


class TelegramUser(Base):
    user_id = sa.Column(sa.BigInteger, unique=True, nullable=False)
    timus_id = sa.Column(sa.Integer, nullable=False)


class Submit(Base):
    timus_submit_id = sa.Column(sa.BigInteger, unique=True, nullable=False)
    timus_user_id = sa.Column(sa.Integer, nullable=False)
    problem_id = sa.Column(sa.Integer, nullable=False)
