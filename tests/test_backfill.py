from universe.backfill import backfill


def test_backfill_is_lossless_and_idempotent(db, fixture_dir):
    first_run = backfill(db, fixture_dir)
    assert first_run == {
        "sources": 69,
        "snapshots_ok": 67,
        "snapshots_failed": 2,
        "artifacts": 67,
        "skipped": 0,
    }
    assert db.execute(
        "SELECT count(*) FROM source WHERE id NOT LIKE 'acqx-%'"
    ).fetchone()[0] == 69
    assert db.execute(
        "SELECT count(*) FROM source_snapshot sn"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE s.id NOT LIKE 'acqx-%'"
    ).fetchone()[0] == 69
    assert db.execute(
        "SELECT count(*) FROM artifact a"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE s.id NOT LIKE 'acqx-%'"
    ).fetchone()[0] == 67

    by_status = dict(
        db.execute(
            "SELECT sn.status, count(*) FROM source_snapshot sn"
            " JOIN source s ON s.id = sn.source_id"
            " WHERE s.id NOT LIKE 'acqx-%' GROUP BY sn.status"
        ).fetchall()
    )
    assert by_status == {"ok": 67, "failed": 2}
    failed = db.execute(
        "SELECT sn.content_hash, sn.failure_note FROM source_snapshot sn"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE sn.status = 'failed' AND s.id NOT LIKE 'acqx-%'"
    ).fetchall()
    assert len(failed) == 2
    assert all(content_hash is None and note for content_hash, note in failed)
    assert not db.execute(
        "SELECT 1 FROM artifact a JOIN source_snapshot s ON s.id = a.snapshot_id"
        " JOIN source src ON src.id = s.source_id"
        " WHERE s.status = 'failed' AND src.id NOT LIKE 'acqx-%'"
    ).fetchall()
    reached = db.execute(
        "SELECT count(*), count(DISTINCT src.id) FROM artifact a"
        " JOIN source_snapshot s ON s.id = a.snapshot_id"
        " JOIN source src ON src.id = s.source_id"
        " WHERE src.id NOT LIKE 'acqx-%'"
    ).fetchone()
    assert reached == (67, 67)
    again = backfill(db, fixture_dir)
    assert again == {
        "sources": 0,
        "snapshots_ok": 0,
        "snapshots_failed": 0,
        "artifacts": 0,
        "skipped": 69,
    }
    assert db.execute(
        "SELECT count(*) FROM source_snapshot sn"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE s.id NOT LIKE 'acqx-%'"
    ).fetchone()[0] == 69
