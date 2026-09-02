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
from adalove_workbook import activity, stable_uuid, write_adalove_workbook

TEST_DATABASE_PREFIX = "universe_test"


@pytest.fixture
def adalove_workbook():
    """One Class with its Self-study, as the Adalove Observer Exporter writes it.

    The Class UUID derives from its title so a renamed Class looks like a new
    activity and exercises the text-based identity matcher; pass a fixed
    ``activity_uuid`` to model the exporter preserving it across a rename.
    """

    def build(
        path: Path,
        *,
        lesson_title: str = "Programação e Desenvolvimento de Banco de Dados",
        lesson_description: str = "Criação e manipulação de bancos relacionais.",
        lesson_axis: str = "Computação",
        activity_uuid: str | None = None,
        include_course_events: bool = False,
    ) -> Path:
        lesson = activity(
            week=2,
            order=1,
            kind="Class",
            title=lesson_title,
            description=lesson_description,
            subject=lesson_axis,
            subjects=["Banco de dados relacional", "SQL Básico"],
            activity_uuid=activity_uuid or stable_uuid("activity", lesson_title),
        )
        rows = [
            lesson,
            activity(
                week=2,
                order=2,
                kind="Self-study",
                title="Tutorial MySQL",
                parent_uuid=lesson["Activity UUID"],
                parent_title=lesson_title,
                subject=None,
                url="https://example.com/mysql",
            ),
        ]
        if include_course_events:
            for order, title, kind in (
                (3, "Sprint Planning", "Orientation"),
                (4, "Entrega do artefato", "Deliverable"),
                (5, "Avaliação geral", "Evaluation"),
            ):
                rows.append(
                    activity(week=2, order=order, kind=kind, title=title, subject=None)
                )
        return write_adalove_workbook(path, rows, project="GRAD CC07")

    return build


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
