"""Effective task evidence follows the exact revision witness, provider-free."""

from psycopg.types.json import Jsonb

from universe.effective_evidence import (
    effective_task_manifest_sha,
    resolve_statement_tasks,
)


def test_statement_evidence_uses_rewritten_text_and_changes_its_manifest(db):
    prefix = "effective-evidence"
    source_id = f"{prefix}-source"
    snapshot_id = f"{source_id}-snapshot"
    artifact_id = f"{snapshot_id}-markdown"
    passage_id = f"{artifact_id}-passage"
    generation_run = f"{prefix}-generation"
    generation_item = f"{generation_run}-item"
    task_id = f"{generation_item}:t01"
    granularity_run = f"{prefix}-granularity"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{}', 'Effective evidence', 'markdown')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'effective-hash', 'ok')",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'Body')",
        (artifact_id, snapshot_id),
    )
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, 'test', 1, 1)",
        (passage_id, artifact_id),
    )
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'task-generation', 'fake', 'task-generation/v004', 'sha', 'done')",
        (generation_run,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, passage_id, response)"
        " VALUES (%s, %s, %s, %s, '{}')",
        (generation_item, generation_run, artifact_id, passage_id),
    )
    db.execute(
        "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
        " VALUES (%s, %s, %s, 1, 'Raw question', 'Stable answer')",
        (task_id, generation_item, passage_id),
    )
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'task-granularity', 'fake',"
        " 'task-granularity/v004', 'sha', 'done')",
        (granularity_run,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
        " VALUES (%s, %s, %s, %s, '{\"verdict\":\"single\"}')",
        (f"{granularity_run}-item", granularity_run, artifact_id, task_id),
    )

    statement_runs = []
    for index, body in enumerate(("Question A", "Question B"), 1):
        revision_run = f"{prefix}-revision-{index}"
        statement_run = f"{prefix}-statement-{index}"
        statement_runs.append(statement_run)
        db.execute(
            "INSERT INTO run"
            " (id, stage, model, prompt_ref, prompt_sha, status, started_at)"
            " VALUES (%s, 'task-revision', 'fake', 'task-revision/v004',"
            " 'sha', 'done', %s)",
            (revision_run, f"2026-01-0{index} 00:00:00+00"),
        )
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, %s)",
            (
                f"{revision_run}-item",
                revision_run,
                artifact_id,
                task_id,
                Jsonb({"verdict": "rewritten", "task": body}),
            ),
        )
        db.execute(
            "INSERT INTO run"
            " (id, stage, model, prompt_ref, prompt_sha, params, status, started_at)"
            " VALUES (%s, 'kc-statement', 'fake', 'kc-statement/v005',"
            " 'sha', %s, 'done', %s)",
            (
                statement_run,
                Jsonb(
                    {
                        "gen_runs": [generation_run],
                        "granularity_run": granularity_run,
                        "revision_run": revision_run,
                    }
                ),
                f"2026-02-0{index} 00:00:00+00",
            ),
        )
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, %s)",
            (
                f"{statement_run}-item",
                statement_run,
                artifact_id,
                task_id,
                Jsonb({"verdict": "stated", "statement": "One invariant"}),
            ),
        )
    db.commit()

    first = resolve_statement_tasks(db, [statement_runs[0]])
    second = resolve_statement_tasks(db, [statement_runs[1]])

    assert first[0]["body"] == "Question A"
    assert second[0]["body"] == "Question B"
    assert "Raw question" not in {first[0]["body"], second[0]["body"]}
    assert effective_task_manifest_sha(first) != effective_task_manifest_sha(second)
