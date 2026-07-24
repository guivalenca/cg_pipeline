"""Database access. One connection helper, no pool, no ORM."""

import os

import psycopg

DEFAULT_DATABASE_URL = "postgresql://universe:universe@localhost:5433/universe"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or database_url())
