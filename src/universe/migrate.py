"""Apply pending SQL migrations.

    python -m universe.migrate

Migrations are numbered plain-SQL files in `migrations/`, applied in filename
order, each recorded in `schema_migrations`. There are no down-migrations: a
correction is a new migration.
"""

from pathlib import Path

import psycopg

from universe.db import connect, database_url

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def migrate(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every migration not yet recorded. Returns the versions applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY,"
        " applied_at timestamptz NOT NULL DEFAULT now())"
    )
    conn.commit()
    done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}

    applied = []
    for path in sorted(directory.glob("*.sql")):
        if path.stem in done:
            continue
        conn.execute(path.read_text())
        conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
        conn.commit()
        applied.append(path.stem)
    return applied


def main() -> None:
    with connect() as conn:
        applied = migrate(conn)
    if applied:
        print(f"applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("up to date, nothing to apply")
    print(f"database: {database_url()}")


if __name__ == "__main__":
    main()
