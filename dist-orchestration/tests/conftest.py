"""Pytest fixtures: a session bound to a rolled-back transaction.

Requires a reachable Postgres with the migration applied (see README).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import database_url


@pytest.fixture(scope="session")
def engine():
    return create_engine(database_url())


@pytest.fixture()
def session(engine):
    conn = engine.connect()
    trans = conn.begin()
    sess = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield sess
    finally:
        sess.close()
        trans.rollback()
        conn.close()
