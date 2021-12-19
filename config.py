from typing import Callable, Iterator, Set

import sqlalchemy as sa
from pydantic import BaseSettings, Field
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.pool import StaticPool


class Settings(BaseSettings):
    token: str
    log: str = Field("")
    create_database: bool = True

    class Config:
        env_prefix = 'TIMUS_RECOMMENDER_BOT_'
        frozen = True


class SAUrl(URL):
    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[str], URL]]:
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> URL:
        try:
            return make_url(v)
        except ArgumentError as e:
            raise ValueError from e


class DBSettings(BaseSettings):
    url: SAUrl = SAUrl.validate('sqlite:///my-data.sqlite')  # type: ignore

    def setup_db(self) -> None:
        from db import metadata

        engine = sa.engine_from_config(
            {'url': self.url, "connect_args": {'check_same_thread': False}, 'poolclass': StaticPool}, prefix="",
        )
        metadata.bind = engine

    def create_database(self) -> None:
        from db.base import metadata

        metadata.create_all()

    class Config:
        env_prefix = 'DB_'
