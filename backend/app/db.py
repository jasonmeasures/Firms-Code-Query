from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base, ExtractCounter, User

ADMIN_ID = 'admin'
OPERATOR_ID = 'operator'


def _database_url() -> str:
    configured = get_settings().database_url
    if configured:
        return configured
    db_path = Path(__file__).resolve().parent.parent / 'extract.db'
    return f'sqlite:///{db_path}'


DATABASE_URL = _database_url()
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if session.get(User, ADMIN_ID) is None:
            session.add(User(id=ADMIN_ID, display_name='Extract Admin', role='ADMIN'))
        if session.get(User, OPERATOR_ID) is None:
            session.add(User(id=OPERATOR_ID, display_name='Extract Operator', role='OPERATOR'))
        if session.get(ExtractCounter, 'kn') is None:
            session.add(ExtractCounter(name='kn', last_value=0))
        session.commit()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def next_kn_sequence(session: Session) -> int:
    row = session.get(ExtractCounter, 'kn')
    if row is None:
        row = ExtractCounter(name='kn', last_value=0)
        session.add(row)
    row.last_value += 1
    session.flush()
    return row.last_value


def user_by_id(session: Session, user_id: str) -> User | None:
    return session.scalar(select(User).where(User.id == user_id))
