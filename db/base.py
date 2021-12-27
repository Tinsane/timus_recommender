import re
from contextlib import contextmanager
from typing import Any, Iterator, Tuple, Type, Union, cast

import sqlalchemy as sa
from sqlalchemy import orm as so
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.pool.events import event

PK_TYPE = sa.Integer()

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


metadata = sa.MetaData(naming_convention=convention)


def classname_to_tablename(name: str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


@as_declarative(metadata=metadata)
class Base:
    @declared_attr
    def __tablename__(cls) -> str:
        return classname_to_tablename(cls.__name__)  # type: ignore

    id = sa.Column(PK_TYPE, primary_key=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    @classmethod
    def __table_cls__(cls, name: str, mtdt: sa.MetaData, *arg: Any, **kw) -> sa.Table:  # type: ignore
        created_at_index = ()

        for obj in arg:
            if isinstance(obj, sa.Column) and obj.primary_key:
                obj.name = f'{name}_id'

            if isinstance(obj, sa.Column) and obj.name == 'created_at':
                created_at_index = (sa.Index(f"{name}_created_at_index", obj, postgresql_using='brin'),)  # type: ignore

        return sa.Table(name, mtdt, *(arg + created_at_index), **kw)


def get_query_cls(
    mapper: Union[Tuple[Type[Base], ...], so.Mapper], session: so.session.Session
) -> so.Query:  # type: ignore
    if mapper:
        m = mapper
        if isinstance(m, tuple):
            m = mapper[0]  # type: ignore
        if isinstance(m, so.Mapper):
            m = m.entity

        try:
            return cast(so.Query, m.__query_cls__(mapper, session))  # type: ignore
        except AttributeError:
            pass

    return so.Query(mapper, session)


Session = so.sessionmaker(query_cls=get_query_cls)


@contextmanager
def create_session() -> Iterator[so.Session]:
    new_session = Session()
    try:
        yield new_session
        new_session.commit()
    except Exception:
        new_session.rollback()
        raise
    finally:
        new_session.close()


@event.listens_for(sa.engine.Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
