"""Tests run against a real Postgres: `docker compose up -d` first.

They never touch the working database. Each test module receives a fresh
database, so committed facts cannot change the cost or outcome of later
modules.
"""

import hashlib
import os
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from universe.db import database_url
from universe.migrate import migrate

TEST_DATABASE_PREFIX = "universe_test"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "si-mod6-com"


@pytest.fixture(scope="session")
def migrated_database_template():
    database_name = f"{TEST_DATABASE_PREFIX}_template_{os.getpid()}"
    admin_url = make_conninfo(database_url(), dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{database_name}"')
    try:
        template_url = make_conninfo(database_url(), dbname=database_name)
        with psycopg.connect(template_url) as conn:
            applied = migrate(conn)
        yield database_name, applied
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')


@pytest.fixture(scope="module")
def test_database_url(
    request: pytest.FixtureRequest,
    migrated_database_template: tuple[str, list[str]],
):
    suffix = hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:12]
    database_name = f"{TEST_DATABASE_PREFIX}_{os.getpid()}_{suffix}"
    template_name, _ = migrated_database_template
    admin_url = make_conninfo(database_url(), dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
        conn.execute(
            f'CREATE DATABASE "{database_name}" TEMPLATE "{template_name}"'
        )
    try:
        yield make_conninfo(database_url(), dbname=database_name)
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')


@pytest.fixture(scope="session")
def applied_migrations(
    migrated_database_template: tuple[str, list[str]],
) -> list[str]:
    return migrated_database_template[1]


@pytest.fixture(scope="module")
def db(test_database_url: str, applied_migrations: list[str]):
    with psycopg.connect(test_database_url) as conn:
        yield conn
