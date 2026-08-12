"""Perfect-clique KC grouping and its append-only database snapshots."""

import hashlib

import pytest

from universe import harness, pipeline_lease
from universe.kc_groups import compute_groups, compute_snapshot, fetch_latest_verdicts


def test_only_complete_mutual_clear_yes_components_become_groups():
    verdicts = [
        ("t01", "t02", "clear_yes", "clear_yes"),
        ("t01", "t03", "clear_yes", "clear_yes"),
        ("t02", "t03", "clear_yes", "clear_yes"),
        ("t10", "t11", "clear_yes", "clear_yes"),
        ("t11", "t12", "clear_yes", "clear_yes"),
        ("t20", "t21", "clear_yes", "likely"),
    ]

    members = ["t01", "t02", "t03"]
    digest = hashlib.sha256("\n".join(members).encode()).hexdigest()[:12]
    assert compute_groups(verdicts) == [
        {"members": members, "id": f"kc-{digest}"},
    ]


def _insert_tasks(db, prefix, count):
    source_id = f"{prefix}-source"
    snapshot_id = f"{source_id}:snapshot"
    artifact_id = f"{snapshot_id}:markdown"
    passage_id = f"{artifact_id}:p01"
    generation_run = harness.next_run_id(db)
    generation_item = f"{generation_run}-0001"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'KC groups', 'article')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'groups-hash', 'ok')",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'Body')",
        (artifact_id, snapshot_id),
    )
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'task-generation', 'fake/model', 'test/v001', 'abc', 'done')",
        (generation_run,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, '{}')",
        (generation_item, generation_run, artifact_id),
    )
    db.execute(
        "INSERT INTO passage (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, 'test', 1, 1)",
        (passage_id, artifact_id),
    )
    task_ids = [f"{prefix}-t{number:02d}" for number in range(1, count + 1)]
    for seq, task_id in enumerate(task_ids, 1):
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (task_id, generation_item, passage_id, seq, f"Task {seq}", f"Answer {seq}"),
        )
    db.commit()
    return task_ids


def test_snapshots_persist_groups_members_and_stable_group_ids(db):
    task_ids = _insert_tasks(db, "groups-db", 3)
    judge_run = harness.claim_run(db, "kc-judge", "fake/model", "kc-judge/test", "abc", {})
    for index, (task_a, task_b) in enumerate(
        [(task_ids[0], task_ids[1]), (task_ids[0], task_ids[2]), (task_ids[1], task_ids[2])],
        1,
    ):
        item_id = f"{judge_run}-{index:04d}"
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, NULL, %s, '{}')",
            (item_id, judge_run, task_a),
        )
        db.execute(
            "INSERT INTO kc_verdict"
            " (run_item_id, task_a_id, task_b_id, a_implies_b, b_implies_a,"
            "  judge_model, judge_prompt)"
            " VALUES (%s, %s, %s, 'clear_yes', 'clear_yes',"
            "  'fake/model', 'kc-judge/test')",
            (item_id, task_a, task_b),
        )
    db.commit()
    # Historical rows may contain superseded generations for the same pair;
    # a grouping pins the effective latest-verdict projection, not raw ledger
    # cardinality.
    verdict_count = len(fetch_latest_verdicts(db))

    first_id, first_groups = compute_snapshot(db)
    second_id, second_groups = compute_snapshot(db)

    assert first_id != second_id
    assert int(second_id[1:]) == int(first_id[1:]) + 1
    assert first_groups == second_groups
    fixture_group = next(
        group for group in first_groups if group["members"] == task_ids
    )
    group_id = fixture_group["id"]
    assert db.execute(
        "SELECT params->>'rule', (params->>'verdict_count')::int"
        " FROM kc_grouping WHERE id = %s",
        (first_id,),
    ).fetchone() == ("mutual_clear_yes_perfect_clique", verdict_count)
    assert {
        row[0]
        for row in db.execute(
            "SELECT id FROM kc_group WHERE grouping_id = %s", (first_id,)
        ).fetchall()
    } == {group["id"] for group in first_groups}
    assert [row[0] for row in db.execute(
        "SELECT task_id FROM kc_group_member"
        " WHERE grouping_id = %s AND group_id = %s ORDER BY task_id",
        (first_id, group_id),
    ).fetchall()] == task_ids
    assert db.execute(
        "SELECT count(*) FROM kc_grouping_verdict WHERE grouping_id = %s",
        (first_id,),
    ).fetchone()[0] == verdict_count


def test_latest_verdict_per_pair_supersedes_older_generations(db):
    task_a, task_b = sorted(_insert_tasks(db, "groups-gen", 2))
    for run_no, (model, prompt, verdict, age) in enumerate(
        [
            ("old/model", "kc-judge/old", "clear_yes", "1 hour"),
            ("new/model", "kc-judge/new", "unlikely", "0 minutes"),
        ],
        1,
    ):
        judge_run = harness.claim_run(db, "kc-judge", model, prompt, "abc", {})
        item_id = f"{judge_run}-{run_no:04d}"
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, NULL, %s, '{}')",
            (item_id, judge_run, task_a),
        )
        db.execute(
            "INSERT INTO kc_verdict"
            " (run_item_id, task_a_id, task_b_id, a_implies_b, b_implies_a,"
            "  judge_model, judge_prompt, build_key, input_key, created_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now() - %s::interval)",
            (
                item_id, task_a, task_b, verdict, verdict, model, prompt,
                f"build-{run_no}", f"input-{run_no}", age,
            ),
        )
    db.commit()

    latest = {(a, b): (ab, ba) for a, b, ab, ba in fetch_latest_verdicts(db)}
    assert latest[(task_a, task_b)] == ("unlikely", "unlikely")
    _, groups = compute_snapshot(db, dry_run=True)
    grouped_tasks = {member for group in groups for member in group["members"]}
    assert not {task_a, task_b} & grouped_tasks


def test_lost_grouped_lease_fails_before_any_snapshot_is_published(db, monkeypatch):
    class LostSupervisor:
        def fence(self, conn):
            raise pipeline_lease.LeaseLost("taken over")

    monkeypatch.setattr(
        pipeline_lease,
        "current_supervisor",
        lambda *, required=False: LostSupervisor(),
    )
    before = db.execute("SELECT count(*) FROM kc_grouping").fetchone()[0]

    with pytest.raises(pipeline_lease.LeaseLost, match="taken over"):
        compute_snapshot(db)

    db.rollback()
    assert db.execute("SELECT count(*) FROM kc_grouping").fetchone()[0] == before
