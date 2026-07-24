"""Tests run against a real Postgres: `docker compose up -d` first.

They never touch the working database. Everything happens in `universe_test`,
which is dropped and recreated at the start of the session (it is left behind
afterwards so a failure can be inspected).
"""

from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from universe.db import database_url
from universe.migrate import migrate

TEST_DATABASE = "universe_test"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "si-mod6-com"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    admin_url = make_conninfo(database_url(), dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{TEST_DATABASE}"')
    return make_conninfo(database_url(), dbname=TEST_DATABASE)


@pytest.fixture(scope="session")
def applied_migrations(test_database_url: str) -> list[str]:
    with psycopg.connect(test_database_url) as conn:
        return migrate(conn)


@pytest.fixture(scope="session")
def db(test_database_url: str, applied_migrations: list[str]):
    with psycopg.connect(test_database_url) as conn:
        yield conn
