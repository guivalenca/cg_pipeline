import pytest

from universe.backfill import backfill


@pytest.fixture(scope="session")
def first_run(db, fixture_dir) -> dict[str, int]:
    return backfill(db, fixture_dir)


def test_first_run_inserts_the_whole_fixture(first_run):
    assert first_run == {
        "sources": 69,
        "snapshots_ok": 67,
        "snapshots_failed": 2,
        "artifacts": 67,
        "skipped": 0,
    }


def test_row_counts(db, first_run):
    assert db.execute("SELECT count(*) FROM source").fetchone()[0] == 69
    assert db.execute("SELECT count(*) FROM source_snapshot").fetchone()[0] == 69
    assert db.execute("SELECT count(*) FROM artifact").fetchone()[0] == 67

    by_status = dict(
        db.execute("SELECT status, count(*) FROM source_snapshot GROUP BY status").fetchall()
    )
    assert by_status == {"ok": 67, "failed": 2}


def test_failed_snapshots_carry_a_reason_and_no_hash(db, first_run):
    failed = db.execute(
        "SELECT content_hash, failure_note FROM source_snapshot WHERE status = 'failed'"
    ).fetchall()
    assert len(failed) == 2
    assert all(content_hash is None and note for content_hash, note in failed)
    assert not db.execute(
        "SELECT 1 FROM artifact a JOIN source_snapshot s ON s.id = a.snapshot_id"
        " WHERE s.status = 'failed'"
    ).fetchall()


def test_every_artifact_reaches_its_source(db, first_run):
    reached = db.execute(
        "SELECT count(*), count(DISTINCT src.id) FROM artifact a"
        " JOIN source_snapshot s ON s.id = a.snapshot_id"
        " JOIN source src ON src.id = s.source_id"
    ).fetchone()
    assert reached == (67, 67)


def test_second_run_inserts_nothing(db, first_run, fixture_dir):
    again = backfill(db, fixture_dir)
    assert again == {
        "sources": 0,
        "snapshots_ok": 0,
        "snapshots_failed": 0,
        "artifacts": 0,
        "skipped": 69,
    }
    assert db.execute("SELECT count(*) FROM source_snapshot").fetchone()[0] == 69
