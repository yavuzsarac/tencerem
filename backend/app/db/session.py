from collections.abc import Generator
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.core.config import Settings


def make_engine(settings: Settings):
    if settings.database_url is None:
        return None
    url = settings.database_url.get_secret_value()
    if url.startswith("sqlite"):
        if settings.environment != "test" or not settings.allow_test_sqlite:
            raise ValueError("SQLite is restricted to explicitly isolated test environments")
        engine = create_engine(url, connect_args={"check_same_thread": False})
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
        return engine
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("Use postgresql+psycopg for persistence")
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})


def get_db(request: Request) -> Generator[Session, None, None]:
    engine = request.app.state.engine
    if engine is None:
        raise HTTPException(503, "Hesap servisi için PostgreSQL yapılandırılmalı. Misafir olarak devam edebilirsiniz.")
    with Session(engine) as session:
        yield session
