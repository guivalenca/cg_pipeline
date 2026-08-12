from universe.migrate import migrate


def test_migrations_apply_on_a_fresh_database(applied_migrations, db):
    assert "0001_ingestion_chain" in applied_migrations
    recorded = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
    assert recorded == set(applied_migrations)


def test_rerunning_applies_nothing(db):
    assert migrate(db) == []


def test_source_asset_accepts_the_complete_preservable_mime_union(db):
    source_id = "source-schema-preservable-mimes"
    job_id = "acq-schema-preservable-mimes"
    expected = [
        (1, "application/pdf", "pdf"),
        (2, "image/png", "article_image"),
        (3, "image/jpeg", "article_image"),
        (4, "image/webp", "article_image"),
        (5, "image/avif", "article_image"),
        (6, "image/svg+xml", "article_image"),
        (7, "image/gif", "article_image"),
    ]
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{}', 'MIME schema probe', 'article')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO acquisition_job (id, source_id, provider) VALUES (%s, %s, %s)",
        (job_id, source_id, "schema-test/v1"),
    )
    for ordinal, mime_type, kind in expected:
        sha256 = f"{ordinal:064x}"
        db.execute(
            "INSERT INTO source_asset"
            " (id, acquisition_job_id, source_id, ordinal, kind, filename,"
            "  mime_type, sha256, byte_size, storage_key)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)",
            (
                f"asset-schema-mime-{ordinal}",
                job_id,
                source_id,
                ordinal,
                kind,
                f"probe-{ordinal}",
                mime_type,
                sha256,
                f"sha256/{sha256[:2]}/{sha256}",
            ),
        )
    db.commit()

    actual = db.execute(
        "SELECT ordinal, mime_type, kind FROM source_asset"
        " WHERE acquisition_job_id = %s ORDER BY ordinal",
        (job_id,),
    ).fetchall()

    assert actual == expected


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
