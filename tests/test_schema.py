from universe.migrate import migrate


def test_migrations_apply_on_a_fresh_database(applied_migrations, db):
    assert "0001_ingestion_chain" in applied_migrations
    recorded = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
    assert recorded == set(applied_migrations)


def test_rerunning_applies_nothing(db):
    assert migrate(db) == []


def test_pgvector_is_usable(db):
    db.execute("CREATE TEMP TABLE embedding_probe (id TEXT PRIMARY KEY, vec vector(3))")
    db.execute(
        "INSERT INTO embedding_probe VALUES ('a', '[1,0,0]'), ('b', '[0,1,0]'), ('c', '[0.9,0.1,0]')"
    )
    nearest = db.execute(
        "SELECT id FROM embedding_probe ORDER BY vec <-> '[1,0,0]' LIMIT 2"
    ).fetchall()
    assert [row[0] for row in nearest] == ["a", "c"]
    db.execute("DROP TABLE embedding_probe")
    db.commit()
