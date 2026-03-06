"""Shared pytest fixtures for kanAPI tests."""

import sys
from pathlib import Path

# Ensure the project root is in sys.path so `from src.api.*` imports resolve
# correctly regardless of how pytest is invoked (e.g. PYTHONPATH=src in Makefile).
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.api.db.database import Base  # noqa: E402
from src.api.v1.case.models import CaseDB  # noqa: E402, F401
from src.api.v1.company.models import CompanyDB  # noqa: E402, F401
from src.api.v1.user.models import UserDB  # noqa: E402, F401

SQLITE_URL = 'sqlite:///:memory:'


@pytest.fixture(scope='session')
def test_engine():
    """Single in-memory SQLite engine for the whole test session."""
    engine = create_engine(SQLITE_URL, connect_args={'check_same_thread': False})
    # Enable FK enforcement in SQLite (off by default)
    event.listen(engine, 'connect', lambda c, _: c.execute('PRAGMA foreign_keys=ON'))
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(test_engine):
    """Function-scoped DB session that rolls back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
