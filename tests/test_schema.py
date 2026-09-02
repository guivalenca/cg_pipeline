from universe.migrate import migrate


def test_migrations_apply_on_a_fresh_database(applied_migrations, db):
    assert applied_migrations == [
        "0001_baseline",
        "0002_lesson_creation",
        "0003_graph_revisions",
    ]
    recorded = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
    assert recorded == set(applied_migrations)


def test_baseline_stops_at_the_source_publication_boundary(db):
    tables = {
        row[0]
        for row in db.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
        ).fetchall()
    }

    assert {
        "source",
        "source_snapshot",
        "artifact",
        "syllabus",
        "syllabus_version",
        "syllabus_lesson",
        "syllabus_source_reference",
        "lesson_build",
        "lesson_build_work",
        "pipeline_lease",
    } <= tables
    assert "vector" not in {
        row[0] for row in db.execute("SELECT extname FROM pg_extension").fetchall()
    }


def test_rerunning_applies_nothing(db):
    assert migrate(db) == []


def test_subject_graph_identity_is_stored_at_the_subject_boundary(db):
    syllabus_columns = {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'syllabus'"
        ).fetchall()
    }
    assert "institution_id" in syllabus_columns
    assert "graph_id" not in syllabus_columns
    assert "display_name" not in syllabus_columns
    assert "institution_slug" not in syllabus_columns

    subject_columns = {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'syllabus_subject'"
        ).fetchall()
    }
    assert {"syllabus_id", "lesson_subject_code", "graph_id"} <= subject_columns

    lesson_columns = {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " AND table_name = 'syllabus_lesson'"
        ).fetchall()
    }
    assert "subjects" in lesson_columns


def test_source_review_binds_validation_to_an_immutable_publication(db):
    columns = {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " AND table_name = 'syllabus_source_review'"
        ).fetchall()
    }

    assert {"validated_artifact_id", "validated_content_hash"} <= columns


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
