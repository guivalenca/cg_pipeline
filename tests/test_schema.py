import shutil
import uuid

import psycopg
from psycopg.conninfo import make_conninfo

from universe.db import database_url
from universe.migrate import MIGRATIONS_DIR, migrate


def test_migrations_apply_on_a_fresh_database(applied_migrations, db):
    assert "0001_ingestion_chain" in applied_migrations
    recorded = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
    assert recorded == set(applied_migrations)


def test_rerunning_applies_nothing(db):
    assert migrate(db) == []


def test_syllabus_metadata_schema_stores_only_the_export_identity(db):
    columns = {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'syllabus'"
        ).fetchall()
    }
    assert {"institution_id", "graph_id"} <= columns
    assert "display_name" not in columns
    assert "institution_slug" not in columns
    assert db.execute(
        "SELECT to_regclass('syllabus_legacy_graph_metadata'),"
        " to_regclass('lesson_subject'), to_regclass('syllabus_lesson_subject')"
    ).fetchone() == (
        "syllabus_legacy_graph_metadata",
        None,
        None,
    )


def test_0061_preserves_versions_and_archives_conflicting_graph_metadata(tmp_path):
    database_name = f"universe_test_upgrade_{uuid.uuid4().hex[:12]}"
    admin_url = make_conninfo(database_url(), dbname="postgres")
    database_connection = make_conninfo(database_url(), dbname=database_name)
    pre_upgrade = tmp_path / "pre-upgrade"
    pre_upgrade.mkdir()
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name >= "0061_syllabus_institution_lesson_subjects.sql":
            continue
        shutil.copy(path, pre_upgrade / path.name)

    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{database_name}"')
    try:
        with psycopg.connect(database_connection) as conn:
            migrate(conn, pre_upgrade)
            conn.execute(
                "INSERT INTO institution (id, name) VALUES"
                " ('upgrade-inteli', 'Upgrade Inteli'),"
                " ('upgrade-other', 'Upgrade Other')"
            )
            conn.execute(
                "INSERT INTO study_group (id, institution_id, name)"
                " VALUES ('g-upgrade-inteli', 'upgrade-inteli', 'Upgrade Group')"
            )
            conn.execute(
                "INSERT INTO syllabus"
                " (id, title, group_id, graph_id, display_name, institution_slug)"
                " VALUES"
                " ('upgrade-match', 'Módulo 7', 'g-upgrade-inteli',"
                "  'old-graph-match', 'Computação', 'upgrade-inteli'),"
                " ('upgrade-conflict', 'Conflito', 'g-upgrade-inteli',"
                "  'old-graph-conflict', 'Negócios', 'upgrade-other'),"
                " ('upgrade-long-title', %s, 'g-upgrade-inteli',"
                "  'old-graph-long', 'Liderança', 'upgrade-inteli'),"
                " ('upgrade-ungrouped', 'Ungrouped', NULL,"
                "  'old-graph-ungrouped', 'Computação', 'upgrade-other'),"
                " ('upgrade-unknown', 'Unresolved', NULL,"
                "  'old-graph-unknown', 'Unknown subject', 'missing-institution')",
                ("x" * 256,),
            )
            conn.execute(
                "INSERT INTO syllabus_version"
                " (id, syllabus_id, seq, origin, file_name, file_sha, file_body)"
                " VALUES ('upgrade-match:v0001', 'upgrade-match', 1, 'upload',"
                " 'original.xlsx', 'sha-original', %s)",
                (b"original workbook bytes",),
            )
            conn.execute(
                "INSERT INTO syllabus_lesson"
                " (id, version_id, week, seq, kind, title, subject)"
                " VALUES ('upgrade-lesson', 'upgrade-match:v0001', 1, 1,"
                " 'Class', 'Original lesson', 'COM')"
            )
            conn.execute(
                "INSERT INTO source (id, identity, title, media_type)"
                " VALUES ('upgrade-source', '{\"canonical_url\": "
                "\"https://example.com/upgrade\"}', 'Upgrade source', 'article')"
            )
            conn.execute(
                "INSERT INTO syllabus_source_reference"
                " (id, version_id, lesson_id, seq, title, url, media_type, source_id)"
                " VALUES ('upgrade-reference', 'upgrade-match:v0001',"
                " 'upgrade-lesson', 1, 'Upgrade source',"
                " 'https://example.com/upgrade', 'article', 'upgrade-source')"
            )
            conn.commit()
            before_version = conn.execute(
                "SELECT id, syllabus_id, seq, file_name, file_sha, file_body"
                " FROM syllabus_version WHERE id = 'upgrade-match:v0001'"
            ).fetchone()
            before_lesson = conn.execute(
                "SELECT id, version_id, week, seq, kind, title, subject"
                " FROM syllabus_lesson WHERE id = 'upgrade-lesson'"
            ).fetchone()
            before_reference = conn.execute(
                "SELECT id, version_id, lesson_id, seq, title, url, media_type, source_id"
                " FROM syllabus_source_reference WHERE id = 'upgrade-reference'"
            ).fetchone()

            assert migrate(conn) == [
                "0061_syllabus_institution_lesson_subjects",
                "0062_syllabus_graph_identity",
            ]

            assert conn.execute(
                "SELECT id, syllabus_id, seq, file_name, file_sha, file_body"
                " FROM syllabus_version WHERE id = 'upgrade-match:v0001'"
            ).fetchone() == before_version
            assert conn.execute(
                "SELECT id, version_id, week, seq, kind, title, subject"
                " FROM syllabus_lesson WHERE id = 'upgrade-lesson'"
            ).fetchone() == before_lesson
            assert conn.execute(
                "SELECT id, version_id, lesson_id, seq, title, url, media_type, source_id"
                " FROM syllabus_source_reference WHERE id = 'upgrade-reference'"
            ).fetchone() == before_reference
            assert conn.execute(
                "SELECT institution_id, graph_id FROM syllabus"
                " WHERE id = 'upgrade-match'"
            ).fetchone() == ("upgrade-inteli", "old-graph-match")
            assert conn.execute(
                "SELECT institution_id, graph_id FROM syllabus"
                " WHERE id = 'upgrade-conflict'"
            ).fetchone() == (None, None)
            assert conn.execute(
                "SELECT institution_id, graph_id FROM syllabus"
                " WHERE id = 'upgrade-long-title'"
            ).fetchone() == ("upgrade-inteli", "old-graph-long")
            assert conn.execute(
                "SELECT institution_id, graph_id FROM syllabus"
                " WHERE id = 'upgrade-ungrouped'"
            ).fetchone() == ("upgrade-other", "old-graph-ungrouped")
            assert conn.execute(
                "SELECT institution_id, graph_id FROM syllabus"
                " WHERE id = 'upgrade-unknown'"
            ).fetchone() == (None, None)
            assert conn.execute(
                "SELECT graph_id, display_name, institution_slug"
                " FROM syllabus_legacy_graph_metadata"
                " WHERE syllabus_id = 'upgrade-conflict'"
            ).fetchone() == (
                "old-graph-conflict",
                "Negócios",
                "upgrade-other",
            )
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')


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
