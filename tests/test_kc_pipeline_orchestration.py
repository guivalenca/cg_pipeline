"""Public KC pipeline targeting and exact stage recipes.

Runs against the shared session database; every row uses the `kcpipe`
namespace and no test launches a subprocess.  Seeds mirror production shape:
stage answers are real parseable verdicts, task rows hang off generation run
items, and judge run items carry no artifact.
"""

import json

import pytest
from psycopg.types.json import Jsonb

from universe import defaults, harness, kc_pipeline
from universe.blocks import BLOCKER_VERSION
from universe.effective_evidence import effective_task_manifest_sha
from universe.pipeline_scope import expected_judge_build_key
from universe.recipe_identity import recipe_identity

P = "kcpipe"


def opt(argv: list[str], flag: str) -> str:
    """The value following a CLI flag."""
    return argv[argv.index(flag) + 1]


def seed_source(
    db, tag, *, snapshot=True, artifact=True, blocks=True, media_type="article"
):
    source_id = f"src_{P}_{tag}"
    artifact_id = f"art_{P}_{tag}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, %s)",
        (source_id, Jsonb({}), f"KC pipeline test {tag}", media_type),
    )
    if snapshot:
        db.execute(
            "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
            " VALUES (%s, %s, %s, 'ok')",
            (f"snap_{P}_{tag}", source_id, "hash"),
        )
    if artifact:
        db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
            " VALUES (%s, %s, 'markdown', 'tool', 'body')",
            (artifact_id, f"snap_{P}_{tag}"),
        )
    if blocks:
        db.execute(
            "INSERT INTO block (id, artifact_id, blocker_version, seq, kind,"
            " start_char, end_char, body)"
            " VALUES (%s, %s, %s, 0, 'paragraph', 0, 4, 'text')",
            (f"blk_{P}_{tag}", artifact_id, BLOCKER_VERSION),
        )
    db.commit()
    return source_id, artifact_id


def seed_run(
    db,
    run_id,
    stage,
    artifact_id,
    *,
    current=True,
    status="done",
    started="2026-01-01 00:00:00+00",
    items=None,
    params=None,
    prompt_sha=None,
):
    """A run with one row per item dict (passage_id/task_id/response/error).

    With no items given, one generic artifact-scoped ok item is written.
    Judge runs are seeded with ``artifact_id=None`` items, production shape.
    """
    default = defaults.STAGE_DEFAULTS.get(stage, {"model": "m", "prompt_ref": "p"})
    stamped_params = dict(params or {})
    if current:
        try:
            identity = recipe_identity(stage)
        except ValueError:
            identity = None
        if identity is not None:
            stamped_params = {
                **identity["model_params"],
                **identity["input_contract"],
                **stamped_params,
            }
            prompt_sha = prompt_sha or identity["prompt_sha"]
    model = default["model"] if current else "retired-model"
    prompt_ref = default["prompt_ref"] if current else f"{stage}/v000"
    prompt_sha = prompt_sha or "sha"
    if stage in {
        "task-triage",
        "task-substance",
        "kc-statement",
        "task-modality",
        "task-knowledge",
    } and "effective_task_manifest_sha" not in stamped_params:
        task_ids = sorted({
            item.get("task_id") for item in (items or []) if item.get("task_id")
        })
        rows = (
            db.execute(
                "SELECT id, body, answer FROM task WHERE id = ANY(%s) ORDER BY id",
                (task_ids,),
            ).fetchall()
            if task_ids
            else []
        )
        stamped_params["effective_task_manifest_sha"] = effective_task_manifest_sha(
            [
                {"id": task_id, "body": body, "answer": answer}
                for task_id, body, answer in rows
            ]
        )
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, params, status, started_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            run_id,
            stage,
            model,
            prompt_ref,
            prompt_sha,
            Jsonb(stamped_params),
            status,
            started,
        ),
    )
    if items is None:
        items = [{}]
    for seq, item in enumerate(items, 1):
        db.execute(
            "INSERT INTO run_item"
            " (id, run_id, artifact_id, passage_id, task_id, response, error)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                f"{run_id}-i{seq}",
                run_id,
                item.get("artifact_id", artifact_id),
                item.get("passage_id"),
                item.get("task_id"),
                item.get(
                    "response",
                    '{"tasks":[]}' if stage == "task-generation" else "{}",
                ) if not item.get("error") else None,
                item.get("error"),
            ),
        )
    db.commit()
    return run_id


def seed_cuts_done(db, tag, artifact_id, *, current=True, started="2026-01-01 00:00:00+00"):
    """A completed passage-cuts run plus the passage it materialized."""
    run_id = seed_run(
        db, f"r_{P}_{tag}_cut", "passage-cuts", artifact_id, current=current, started=started
    )
    db.execute(
        "INSERT INTO passage (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, %s, 0, 1)",
        (f"pass_{P}_{tag}", artifact_id, BLOCKER_VERSION),
    )
    db.execute(
        "INSERT INTO passage_origin (passage_id, run_id) VALUES (%s, %s)",
        (f"pass_{P}_{tag}", run_id),
    )
    db.commit()
    return run_id


def verdict_items(task_ids, verdict, **extra):
    return [
        {"task_id": task_id, "response": json.dumps({"verdict": verdict, **extra})}
        for task_id in task_ids
    ]


def seed_chain_through_revision(db, tag, *, rewritten_body=None):
    """One production-shaped task chain ready for support triage."""
    source_id, artifact_id = seed_source(db, tag)
    passage_id = f"pass_{P}_{tag}"
    seed_cuts_done(db, tag, artifact_id)
    seed_run(
        db,
        f"r_{P}_{tag}_ptri",
        "passage-triage",
        artifact_id,
        items=[
            {"passage_id": passage_id, "response": '{"verdict":"not_filler"}'}
        ],
        started="2030-01-02 00:00:00+00",
    )
    generation = seed_run(
        db,
        f"r_{P}_{tag}_gen",
        "task-generation",
        artifact_id,
        items=[
            {
                "passage_id": passage_id,
                "response": '{"tasks":[{"task":"Q raw","answer":"A"}]}',
            }
        ],
        started="2030-01-03 00:00:00+00",
    )
    task_id = f"{generation}-i1:t01"
    db.execute(
        "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
        " VALUES (%s, %s, %s, 1, 'Q raw', 'A')",
        (task_id, f"{generation}-i1", passage_id),
    )
    db.commit()
    granularity = seed_run(
        db,
        f"r_{P}_{tag}_gran",
        "task-granularity",
        artifact_id,
        items=verdict_items([task_id], "single"),
        started="2030-01-04 00:00:00+00",
    )
    revision_response = (
        {"verdict": "rewritten", "task": rewritten_body}
        if rewritten_body is not None
        else {"verdict": "stands"}
    )
    revision = seed_run(
        db,
        f"r_{P}_{tag}_rev",
        "task-revision",
        artifact_id,
        items=[{"task_id": task_id, "response": json.dumps(revision_response)}],
        started="2030-01-05 00:00:00+00",
    )
    return source_id, artifact_id, task_id, generation, granularity, revision


def seed_complete_single_task_source(db, tag):
    """One production-shaped corpus participant with a stated singleton."""
    source_id, artifact_id, task_id, generation, granularity, revision = (
        seed_chain_through_revision(db, tag)
    )
    common = {
        "gen_runs": [generation],
        "granularity_run": granularity,
        "revision_run": revision,
        "parts_revision_run": revision,
    }
    triage = seed_run(
        db,
        f"r_{P}_{tag}_task_triage",
        "task-triage",
        artifact_id,
        items=verdict_items([task_id], "supported"),
        params=common,
        started="2030-01-06 00:00:00+00",
    )
    substance = seed_run(
        db,
        f"r_{P}_{tag}_substance",
        "task-substance",
        artifact_id,
        items=verdict_items([task_id], "works"),
        params={**common, "triage_run": triage},
        started="2030-01-07 00:00:00+00",
    )
    statement = seed_run(
        db,
        f"r_{P}_{tag}_statement",
        "kc-statement",
        artifact_id,
        items=[
            {
                "task_id": task_id,
                "response": json.dumps(
                    {"verdict": "stated", "statement": f"Statement {tag}"}
                ),
            }
        ],
        params={**common, "triage_run": triage, "substance_run": substance},
        started="2030-01-08 00:00:00+00",
    )
    modality = seed_run(
        db,
        f"r_{P}_{tag}_modality",
        "task-modality",
        artifact_id,
        items=verdict_items([task_id], "do", reason="acts"),
        params=common,
        started="2030-01-09 00:00:00+00",
    )
    knowledge = seed_run(
        db,
        f"r_{P}_{tag}_knowledge",
        "task-knowledge",
        artifact_id,
        items=verdict_items([task_id], "concept", reason="idea"),
        params=common,
        started="2030-01-10 00:00:00+00",
    )
    return {
        "source_id": source_id,
        "artifact_id": artifact_id,
        "task_id": task_id,
        "statement": statement,
        "modality": modality,
        "knowledge": knowledge,
    }


class TestNextStepDecision:
    def test_unknown_source_raises(self, db):
        with pytest.raises(LookupError):
            kc_pipeline.next_step(db, f"src_{P}_missing")

    def test_blocks_step_is_local_and_names_the_artifact(self, db):
        source_id, artifact_id = seed_source(db, "blk", blocks=False)
        step = kc_pipeline.next_step(db, source_id)
        assert step["stage"] == "blocks"
        assert step["runnable"] is True
        assert step["spends_model_calls"] is False
        assert step["argv"][-2:] == ["universe.blocks", artifact_id]

    def test_passage_cuts_argv_matches_the_reference_recipe(self, db):
        source_id, artifact_id = seed_source(db, "cut")
        step = kc_pipeline.next_step(db, source_id)
        assert step["stage"] == "passage-cuts"
        assert step["runnable"] is True
        assert step["spends_model_calls"] is True
        argv = step["argv"]
        assert opt(argv, "--stage") == "passage-cuts"
        assert opt(argv, "--artifacts") == artifact_id
        assert opt(argv, "--body-from") == "blocks"
        assert opt(argv, "--prompt") == "v001"
        assert opt(argv, "--model") == defaults.STAGE_DEFAULTS["passage-cuts"]["model"]
        assert opt(argv, "--tool") == "prompts/passage-cuts/tool-v001.json"
        assert opt(argv, "--workers") == "16"
        assert opt(argv, "--max-tokens") == "65536"
        extra = json.loads(opt(argv, "--extra"))
        assert extra["thinking"] == {"type": "enabled"}
        assert extra["reasoning_effort"] == "high"
        assert extra["tool_choice"] == "auto"
        assert extra["provider"] == {
            "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
            "ignore": ["SiliconFlow"],
        }
        assert step["model"] == "deepseek-v4-flash"

    def test_passage_triage_is_scoped_by_this_sources_cuts_run(self, db):
        source_id, artifact_id = seed_source(db, "tri")
        cuts_run = seed_cuts_done(db, "tri", artifact_id)
        step = kc_pipeline.next_step(db, source_id)
        assert step["stage"] == "passage-triage"
        assert step["runnable"] is True
        assert opt(step["argv"], "--cuts-runs") == cuts_run

    def test_superseded_cuts_reopen_the_cut_step(self, db):
        """A source cut only by a superseded recipe needs re-cutting: the
        passages it left behind are history, not triage targets."""
        source_id, artifact_id = seed_source(db, "sup")
        seed_cuts_done(db, "sup", artifact_id, current=False)
        step = kc_pipeline.next_step(db, source_id)
        assert step["stage"] == "passage-cuts"
        assert step["runnable"] is True
        assert opt(step["argv"], "--artifacts") == artifact_id

    def test_raw_artifact_cut_is_not_the_numbered_block_recipe(self, db):
        source_id, artifact_id = seed_source(db, "raw_cut")
        run_id = seed_run(
            db,
            f"r_{P}_raw_cut",
            "passage-cuts",
            artifact_id,
            params={"body_from": "artifact"},
        )
        passage_id = f"pass_{P}_raw_cut"
        db.execute(
            "INSERT INTO passage (id, artifact_id, blocker_version, first_seq, last_seq)"
            " VALUES (%s, %s, %s, 0, 1)",
            (passage_id, artifact_id, BLOCKER_VERSION),
        )
        db.execute(
            "INSERT INTO passage_origin (passage_id, run_id) VALUES (%s, %s)",
            (passage_id, run_id),
        )
        db.commit()

        step = kc_pipeline.next_step(db, source_id)

        assert step["stage"] == "passage-cuts"
        assert step["runnable"] is True
        assert opt(step["argv"], "--body-from") == "blocks"

    def test_durable_running_stage_is_not_runnable_again(self, db):
        source_id, artifact_id = seed_source(db, "running")
        run_id = seed_run(
            db,
            f"r_{P}_running_cut",
            "passage-cuts",
            artifact_id,
            status="running",
        )
        lease = kc_pipeline._acquire_lease(
            db,
            scope_key=f"source:{source_id}",
            stage="passage-cuts",
            owner_id="active-test-worker",
        )
        assert lease is not None
        db.execute(
            "UPDATE run SET params = %s WHERE id = %s",
            (
                Jsonb(
                    {
                        "pipeline_lease": {
                            "scope_key": lease.scope_key,
                            "stage": lease.stage,
                            "token": lease.token,
                            "owner_id": lease.owner_id,
                        }
                    }
                ),
                run_id,
            ),
        )
        db.commit()

        step = kc_pipeline.next_step(db, source_id)

        assert step["stage"] == "passage-cuts"
        assert step["stage_status"] == "running"
        assert step["runnable"] is False
        assert run_id in step["reason"]

    def test_orphaned_running_run_without_a_live_lease_is_recoverable(self, db):
        source_id, artifact_id = seed_source(db, "orphan_running")
        seed_run(
            db,
            f"r_{P}_orphan_running_cut",
            "passage-cuts",
            artifact_id,
            status="running",
        )

        step = kc_pipeline.next_step(db, source_id)

        assert step["stage"] == "passage-cuts"
        assert step["stage_status"] == "pending"
        assert step["runnable"] is True

    def test_mixed_artifact_run_is_not_a_scope_witness(self, db):
        source_id, artifact_id = seed_source(db, "pure_a")
        other_source, old_artifact = seed_source(db, "pure_b_old")
        run_id = seed_run(
            db,
            f"r_{P}_mixed_cut",
            "passage-cuts",
            artifact_id,
            items=[
                {"artifact_id": artifact_id},
                {"artifact_id": old_artifact},
            ],
        )
        db.execute(
            "INSERT INTO passage (id, artifact_id, blocker_version, first_seq, last_seq)"
            " VALUES (%s, %s, %s, 0, 1)",
            (f"pass_{P}_pure_a", artifact_id, BLOCKER_VERSION),
        )
        db.execute(
            "INSERT INTO passage_origin (passage_id, run_id) VALUES (%s, %s)",
            (f"pass_{P}_pure_a", run_id),
        )
        # Supersede the other artifact after the mixed run was recorded.
        db.execute(
            "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
            " VALUES (%s, %s, 'new-hash', 'ok')",
            (f"snap_{P}_pure_b_new", other_source),
        )
        db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
            " VALUES (%s, %s, 'markdown', 'tool', 'new body')",
            (f"art_{P}_pure_b_new", f"snap_{P}_pure_b_new"),
        )
        db.commit()

        step = kc_pipeline.next_step(db, source_id)

        assert step["stage"] == "passage-cuts"
        assert step["runnable"] is True
        assert kc_pipeline.spine.source_progress(db)[source_id]["stages"][
            "passage-cuts"
        ]["status"] == "pending"

    def test_split_retry_coverage_does_not_masquerade_as_one_revision(self, db):
        source_id, artifact_id = seed_source(db, "revision_witness")
        passage_id = f"pass_{P}_revision_witness"
        seed_cuts_done(db, "revision_witness", artifact_id)
        seed_run(
            db,
            f"r_{P}_rw_tri",
            "passage-triage",
            artifact_id,
            items=[
                {"passage_id": passage_id, "response": '{"verdict":"not_filler"}'}
            ],
            started="2028-01-02 00:00:00+00",
        )
        generation = seed_run(
            db,
            f"r_{P}_rw_gen",
            "task-generation",
            artifact_id,
            items=[{"passage_id": passage_id}],
            started="2028-01-03 00:00:00+00",
        )
        task_ids = [f"task_{P}_rw_1", f"task_{P}_rw_2"]
        for seq, task_id in enumerate(task_ids, 1):
            db.execute(
                "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
                " VALUES (%s, %s, %s, %s, 'Q?', 'A')",
                (task_id, f"{generation}-i1", passage_id, seq),
            )
        db.commit()
        seed_run(
            db,
            f"r_{P}_rw_gran",
            "task-granularity",
            artifact_id,
            items=verdict_items(task_ids, "single"),
            started="2028-01-04 00:00:00+00",
        )
        seed_run(
            db,
            f"r_{P}_rw_rev1",
            "task-revision",
            artifact_id,
            items=[
                {"task_id": task_ids[0], "response": '{"verdict":"stands"}'},
                {"task_id": task_ids[1], "error": "timeout"},
            ],
            started="2028-01-05 00:00:00+00",
        )
        seed_run(
            db,
            f"r_{P}_rw_rev2",
            "task-revision",
            artifact_id,
            items=[
                {"task_id": task_ids[0], "error": "timeout"},
                {"task_id": task_ids[1], "response": '{"verdict":"stands"}'},
            ],
            started="2028-01-06 00:00:00+00",
        )

        step = kc_pipeline.next_step(db, source_id)

        assert step["stage"] == "task-revision"
        assert step["runnable"] is True

    def test_failed_current_judge_build_never_falls_back_to_old_done_build(self, db):
        expected = {
            "statements_from": [f"r_{P}_current_statements"],
            "embedding_run": f"r_{P}_current_embedding",
            "modality_runs": [f"r_{P}_current_modality"],
            "knowledge_runs": [f"r_{P}_current_knowledge"],
        }
        judge_sha = harness.load_prompt(
            "kc-judge", "v003-surmise-pair", require_body=False
        ).sha
        old = seed_run(
            db,
            f"r_{P}_old_judge_build",
            "kc-judge",
            None,
            started="2028-02-01 00:00:00+00",
            prompt_sha=judge_sha,
        )
        db.execute(
            "UPDATE run SET params = %s WHERE id = %s",
            (
                Jsonb(
                    {
                        "build_key": "old-build",
                        **expected,
                    }
                ),
                old,
            ),
        )
        failed = seed_run(
            db,
            f"r_{P}_failed_current_judge",
            "kc-judge",
            None,
            status="failed",
            started="2028-02-02 00:00:00+00",
            prompt_sha=judge_sha,
        )
        db.execute(
            "UPDATE run SET params = %s WHERE id = %s",
            (
                Jsonb(
                    {
                        "build_key": expected_judge_build_key(expected),
                        **expected,
                    }
                ),
                failed,
            ),
        )
        db.commit()

        assert kc_pipeline._completed_judge_build_for_inputs(db, expected) is None

    def test_done_limited_judge_attempt_is_not_a_complete_build(self, db):
        expected = {
            "statements_from": [f"r_{P}_limited_statements"],
            "embedding_run": f"r_{P}_limited_embedding",
            "modality_runs": [f"r_{P}_limited_modality"],
            "knowledge_runs": [f"r_{P}_limited_knowledge"],
        }
        judge_sha = harness.load_prompt(
            "kc-judge", "v003-surmise-pair", require_body=False
        ).sha
        partial = seed_run(
            db,
            f"r_{P}_limited_judge",
            "kc-judge",
            None,
            started="2028-02-03 00:00:00+00",
            prompt_sha=judge_sha,
            params={
                "build_key": expected_judge_build_key(expected),
                **expected,
            },
        )

        assert harness.fetch_run(db, partial)["status"] == "done"
        assert kc_pipeline._completed_judge_build_for_inputs(db, expected) is None

    def test_wrong_prompt_or_reasoning_cannot_close_a_live_stage(self, db):
        source_id, artifact_id, task_id, *_ = seed_chain_through_revision(
            db, "strict_recipe"
        )
        identity = recipe_identity("task-triage")
        seed_run(
            db,
            f"r_{P}_strict_recipe_bad_prompt",
            "task-triage",
            artifact_id,
            items=verdict_items([task_id], "supported"),
            prompt_sha="0" * 64,
            started="2030-01-06 00:00:00+00",
        )
        seed_run(
            db,
            f"r_{P}_strict_recipe_bad_reasoning",
            "task-triage",
            artifact_id,
            items=verdict_items([task_id], "supported"),
            params={"reasoning_effort": "low"},
            started="2030-01-07 00:00:00+00",
        )

        assert kc_pipeline.next_step(db, source_id)["stage"] == "task-triage"

        seed_run(
            db,
            f"r_{P}_strict_recipe_exact",
            "task-triage",
            artifact_id,
            items=verdict_items([task_id], "supported"),
            prompt_sha=identity["prompt_sha"],
            started="2030-01-08 00:00:00+00",
        )

        assert kc_pipeline.next_step(db, source_id)["stage"] == "task-substance"

    def test_new_revision_text_reopens_every_effective_text_stage(self, db):
        source_id, artifact_id, task_id, _, _, _ = seed_chain_through_revision(
            db, "revision_provenance", rewritten_body="Q A"
        )
        manifest_a = effective_task_manifest_sha(
            [{"id": task_id, "body": "Q A", "answer": "A"}]
        )
        common = {"effective_task_manifest_sha": manifest_a}
        seed_run(
            db,
            f"r_{P}_revision_provenance_triage",
            "task-triage",
            artifact_id,
            items=verdict_items([task_id], "supported"),
            params=common,
            started="2030-01-06 00:00:00+00",
        )
        seed_run(
            db,
            f"r_{P}_revision_provenance_substance",
            "task-substance",
            artifact_id,
            items=verdict_items([task_id], "works"),
            params=common,
            started="2030-01-07 00:00:00+00",
        )
        seed_run(
            db,
            f"r_{P}_revision_provenance_statement",
            "kc-statement",
            artifact_id,
            items=verdict_items([task_id], "stated", statement="S"),
            params=common,
            started="2030-01-08 00:00:00+00",
        )
        seed_run(
            db,
            f"r_{P}_revision_provenance_modality",
            "task-modality",
            artifact_id,
            items=verdict_items([task_id], "do", reason="R"),
            params=common,
            started="2030-01-09 00:00:00+00",
        )
        seed_run(
            db,
            f"r_{P}_revision_provenance_knowledge",
            "task-knowledge",
            artifact_id,
            items=verdict_items([task_id], "concept", reason="R"),
            params=common,
            started="2030-01-10 00:00:00+00",
        )
        before = kc_pipeline.spine.source_progress(db)[source_id]["stages"]
        assert all(
            before[stage]["status"] == "done"
            for stage in (
                "task-triage",
                "task-substance",
                "kc-statement",
                "task-modality",
                "task-knowledge",
            )
        )

        seed_run(
            db,
            f"r_{P}_revision_provenance_rev_b",
            "task-revision",
            artifact_id,
            items=[
                {
                    "task_id": task_id,
                    "response": '{"verdict":"rewritten","task":"Q B"}',
                }
            ],
            started="2030-02-01 00:00:00+00",
        )

        after = kc_pipeline.spine.source_progress(db)[source_id]["stages"]
        assert all(
            after[stage]["status"] == "pending"
            for stage in (
                "task-triage",
                "task-substance",
                "kc-statement",
                "task-modality",
                "task-knowledge",
            )
        )


@pytest.fixture(scope="module")
def chain(db):
    """A source with the per-source chain genuinely complete up to substance.

    Two tasks materialized from the first current generation run, every gate
    stage answering for both with real verdicts, so the spine's union
    semantics read each stage as done the way production data does.
    """
    # Earlier runner tests intentionally leave claimed runs open to assert the
    # ledger's initial `running` state. They are unrelated historical scopes,
    # so close those test claims before exercising the corpus-wide launch
    # guard here. This module creates its own explicit running-run case above.
    db.execute(
        "UPDATE run SET status = 'failed', finished_at = now()"
        " WHERE status = 'running' AND stage = ANY(%s)",
        (["task-embedding", "kc-judge", "grouped", "kc-canonical-statement"],),
    )
    db.commit()
    source_id, artifact_id = seed_source(db, "chain")
    passage_id = f"pass_{P}_chain"
    cuts_run = seed_cuts_done(db, "chain", artifact_id)
    generation_item_id = f"r_{P}_ch_g1-i1"
    task_ids = [f"{generation_item_id}:t01", f"{generation_item_id}:t02"]
    runs = {
        "cuts": cuts_run,
        "triage": seed_run(
            db, f"r_{P}_ch_tri", "passage-triage", artifact_id,
            items=[{"passage_id": passage_id, "response": '{"verdict": "not_filler"}'}],
            started="2026-01-02 00:00:00+00",
        ),
        "gen_old": seed_run(
            db, f"r_{P}_ch_g0", "task-generation", artifact_id,
            current=False, started="2026-01-03 00:00:00+00",
            items=[{"passage_id": passage_id}],
        ),
        "gen1": seed_run(
            db, f"r_{P}_ch_g1", "task-generation", artifact_id,
            started="2026-01-04 00:00:00+00",
            items=[{
                "passage_id": passage_id,
                "response": (
                    '{"tasks":['
                    '{"task":"Q1?","answer":"A1"},'
                    '{"task":"Q2?","answer":"A2"}'
                    ']}'
                ),
            }],
        ),
    }
    for seq, task_id in enumerate(task_ids, 1):
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (task_id, generation_item_id, passage_id, seq, f"Q{seq}?", f"A{seq}"),
        )
    db.commit()
    runs.update(
        gran1=seed_run(
            db, f"r_{P}_ch_gr1", "task-granularity", artifact_id,
            started="2026-01-06 00:00:00+00",
            items=verdict_items(task_ids, "single"),
        ),
        gran2=seed_run(
            db, f"r_{P}_ch_gr2", "task-granularity", artifact_id,
            started="2026-01-07 00:00:00+00",
            items=verdict_items(task_ids, "single"),
        ),
        revision=seed_run(
            db, f"r_{P}_ch_rev", "task-revision", artifact_id,
            started="2026-01-08 00:00:00+00",
            items=verdict_items(task_ids, "stands"),
        ),
        ttriage=seed_run(
            db, f"r_{P}_ch_tt", "task-triage", artifact_id,
            started="2026-01-09 00:00:00+00",
            items=verdict_items(task_ids, "supported"),
        ),
        substance=seed_run(
            db, f"r_{P}_ch_sub", "task-substance", artifact_id,
            started="2026-01-10 00:00:00+00",
            items=verdict_items(task_ids, "works"),
        ),
    )
    return source_id, artifact_id, task_ids, runs


class TestChainScoping:
    def test_kc_statement_wires_the_whole_source_chain(self, db, chain):
        source_id, _, _, runs = chain
        step = kc_pipeline.next_step(db, source_id)
        assert step["stage"] == "kc-statement"
        assert step["runnable"] is True
        argv = step["argv"]
        # The minimal folded generation witness; the superseded run stays out.
        assert opt(argv, "--gen-runs") == runs["gen1"]
        # Single-valued references use the latest current-generation run.
        assert opt(argv, "--granularity-run") == runs["gran2"]
        assert opt(argv, "--revision-run") == runs["revision"]
        assert opt(argv, "--parts-revision-run") == runs["revision"]
        assert opt(argv, "--triage-run") == runs["ttriage"]
        assert opt(argv, "--substance-run") == runs["substance"]
        assert opt(argv, "--prompt") == "v005"
        assert opt(argv, "--tool") == "prompts/kc-statement/tool-v007.json"
        assert opt(argv, "--workers") == "16"

    def test_task_modality_runs_two_workers_without_thinking(self, db, chain):
        source_id, artifact_id, task_ids, runs = chain
        runs["statement"] = seed_run(
            db, f"r_{P}_ch_st", "kc-statement", artifact_id,
            started="2026-01-11 00:00:00+00",
            items=[
                {"task_id": t, "response": f'{{"verdict": "stated", "statement": "S {t}"}}'}
                for t in task_ids
            ],
            params={
                "gen_runs": [runs["gen1"]],
                "granularity_run": runs["gran2"],
                "revision_run": runs["revision"],
                "parts_revision_run": runs["revision"],
            },
        )
        step = kc_pipeline.next_step(db, source_id)
        assert step["stage"] == "task-modality"
        argv = step["argv"]
        assert opt(argv, "--workers") == "2"
        extra = json.loads(opt(argv, "--extra"))
        assert extra["reasoning"] == {"enabled": False}
        assert "thinking" not in extra
        assert extra["provider"]["ignore"] == ["SiliconFlow"]

    def test_retry_chain_union_completes_modality(self, db, chain):
        """Two runs whose union covers every task: the stage is done and the
        Run button must not offer the paid re-run again."""
        source_id, artifact_id, task_ids, runs = chain
        runs["modality_a"] = seed_run(
            db, f"r_{P}_ch_modA", "task-modality", artifact_id,
            started="2026-01-12 00:00:00+00",
            items=verdict_items(task_ids, "do", reason="acts"),
        )
        # The newer retry re-ran everything and 429ed on the second task:
        # alone it is partial, the union is complete.
        runs["modality_b"] = seed_run(
            db, f"r_{P}_ch_modB", "task-modality", artifact_id,
            started="2026-01-13 00:00:00+00",
            items=[
                {"task_id": task_ids[0], "response": '{"verdict": "explain", "reason": "talks"}'},
                {"task_id": task_ids[1], "error": "429 rate limited"},
            ],
        )
        step = kc_pipeline.next_step(db, source_id)
        assert step["stage"] == "task-knowledge"
