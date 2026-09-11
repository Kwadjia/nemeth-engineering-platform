"""Test fixtures.

The suite runs against a real PostgreSQL (``NEMETH_TEST_DATABASE_URL``, default
``nemeth_test`` on localhost). The schema is dropped and rebuilt from the Alembic
migrations once per session, which doubles as a migration check. Each test runs inside
a transaction that is rolled back afterwards.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.config import get_settings
from nemeth.core.db import get_session
from nemeth.main import create_app
from nemeth.models import Base

from nemeth.__main__ import API_ROOT  # isort: skip

os.environ.setdefault("NEMETH_ENVIRONMENT", "test")
os.environ.setdefault("NEMETH_LOG_LEVEL", "WARNING")


def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin = target.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target.database}
        ).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    return get_settings().test_database_url


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    _ensure_database(database_url)
    engine = create_engine(database_url)

    # Start from nothing, then apply the real migrations.
    with engine.begin() as conn:
        Base.metadata.drop_all(conn)
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    config = AlembicConfig(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def actor() -> Actor:
    return Actor(id="test", display_name="Test User")


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()

    def _override() -> Iterator[Session]:
        yield session
        session.flush()

    app.dependency_overrides[get_session] = _override
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
