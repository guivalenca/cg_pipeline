"""Per-source pipeline targeting: next-step decisions, argv recipes, 409 logic.

Runs against the shared session database; every row uses the `ingnx`
namespace and no test launches a subprocess.  Seeds mirror production shape:
stage answers are real parseable verdicts, task rows hang off generation run
items, and judge run items carry no artifact.
"""

import json
import sys

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

import universe.web.app as web_app
from universe import defaults, ingest
from universe.blocks import BLOCKER_VERSION

P = "ingnx"


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
        (source_id, Jsonb({}), f"Ingest test {tag}", media_type),
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
):
    """A run with one row per item dict (passage_id/task_id/response/error).

    With no items given, one generic artifact-scoped ok item is written.
    Judge runs are seeded with ``artifact_id=None`` items, production shape.
    """
    default = defaults.STAGE_DEFAULTS.get(stage, {"model": "m", "prompt_ref": "p"})
    model = default["model"] if current else "retired-model"
    prompt_ref = default["prompt_ref"] if current else f"{stage}/v000"
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, params, status, started_at)"
        " VALUES (%s, %s, %s, %s, 'sha', %s, %s, %s)",
        (run_id, stage, model, prompt_ref, Jsonb({}), status, started),
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
                item.get("response", "{}") if not item.get("error") else None,
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


class TestNextStepDecision:
    def test_unacquired_article_offers_the_acquisition_cli(self, db):
        source_id, _ = seed_source(db, "raw", snapshot=False, artifact=False, blocks=False)
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "acquisition"
        assert step["runnable"] is True
        assert step["model"] is None
        assert step["spends_model_calls"] is False
        assert step["argv"] == [
            sys.executable,
            "-m",
            "universe.acquisition",
            "run",
            "--sources",
            source_id,
            "--only-missing",
        ]

    @pytest.mark.parametrize(
        ("media_type", "reason_text"),
        [
            ("video", "video sources do not have a fetcher yet"),
            ("book", "chapter, page range, or unit"),
        ],
    )
    def test_unacquired_unsupported_media_is_not_runnable(
        self, db, media_type, reason_text
    ):
        source_id, _ = seed_source(
            db,
            f"unsupported_{media_type}",
            snapshot=False,
            artifact=False,
            blocks=False,
            media_type=media_type,
        )

        step = ingest.next_step(db, source_id)

        assert step["stage"] == "acquisition"
        assert step["runnable"] is False
        assert step["argv"] is None
        assert reason_text in step["reason"].lower()

    def test_unknown_source_raises(self, db):
        with pytest.raises(LookupError):
            ingest.next_step(db, f"src_{P}_missing")

    def test_blocks_step_is_local_and_names_the_artifact(self, db):
        source_id, artifact_id = seed_source(db, "blk", blocks=False)
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "blocks"
        assert step["runnable"] is True
        assert step["spends_model_calls"] is False
        assert step["argv"][-2:] == ["universe.blocks", artifact_id]

    def test_passage_cuts_argv_matches_the_reference_recipe(self, db):
        source_id, _ = seed_source(db, "cut")
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "passage-cuts"
        assert step["runnable"] is True
        assert step["spends_model_calls"] is True
        argv = step["argv"]
        assert opt(argv, "--stage") == "passage-cuts"
        assert opt(argv, "--sources") == source_id
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
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "passage-triage"
        assert step["runnable"] is True
        assert opt(step["argv"], "--cuts-runs") == cuts_run

    def test_superseded_cuts_reopen_the_cut_step(self, db):
        """A source cut only by a superseded recipe needs re-cutting: the
        passages it left behind are history, not triage targets."""
        source_id, artifact_id = seed_source(db, "sup")
        seed_cuts_done(db, "sup", artifact_id, current=False)
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "passage-cuts"
        assert step["runnable"] is True
        assert opt(step["argv"], "--sources") == source_id


@pytest.fixture(scope="module")
def chain(db):
    """A source with the per-source chain genuinely complete up to substance.

    Two tasks materialized from the first current generation run, every gate
    stage answering for both with real verdicts, so the spine's union
    semantics read each stage as done the way production data does.
    """
    source_id, artifact_id = seed_source(db, "chain")
    passage_id = f"pass_{P}_chain"
    cuts_run = seed_cuts_done(db, "chain", artifact_id)
    task_ids = [f"task_{P}_chain_1", f"task_{P}_chain_2"]
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
            items=[{"passage_id": passage_id}],
        ),
        "gen2": seed_run(
            db, f"r_{P}_ch_g2", "task-generation", artifact_id,
            started="2026-01-05 00:00:00+00",
            items=[{"passage_id": passage_id}],
        ),
    }
    for seq, task_id in enumerate(task_ids, 1):
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, %s, 'Q?', 'A')",
            (task_id, f"r_{P}_ch_g1-i1", passage_id, seq),
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
    def test_task_substance_wires_the_support_triage_gate(self, db, chain):
        source_id, _, _, runs = chain

        argv = ingest._build_task_substance(db, source_id)["argv"]

        assert opt(argv, "--triage-run") == runs["ttriage"]

    def test_kc_statement_wires_the_whole_source_chain(self, db, chain):
        source_id, _, _, runs = chain
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "kc-statement"
        assert step["runnable"] is True
        argv = step["argv"]
        # Every current-generation task-generation run, oldest first; the
        # superseded one stays out.
        assert opt(argv, "--gen-runs") == f"{runs['gen1']},{runs['gen2']}"
        # Single-valued references use the latest current-generation run.
        assert opt(argv, "--granularity-run") == runs["gran2"]
        assert opt(argv, "--revision-run") == runs["revision"]
        assert opt(argv, "--parts-revision-run") == runs["revision"]
        assert opt(argv, "--triage-run") == runs["ttriage"]
        assert opt(argv, "--substance-run") == runs["substance"]
        assert opt(argv, "--prompt") == "v005"
        assert opt(argv, "--tool") == "prompts/kc-statement/tool-v007.json"
        assert opt(argv, "--workers") == "16"

    def test_task_modality_runs_serially_without_thinking(self, db, chain):
        source_id, artifact_id, task_ids, runs = chain
        runs["statement"] = seed_run(
            db, f"r_{P}_ch_st", "kc-statement", artifact_id,
            started="2026-01-11 00:00:00+00",
            items=[
                {"task_id": t, "response": f'{{"verdict": "stated", "statement": "S {t}"}}'}
                for t in task_ids
            ],
        )
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "task-modality"
        argv = step["argv"]
        assert opt(argv, "--workers") == "1"
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
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "task-knowledge"

    def test_embedding_scope_is_every_current_statement_run(self, db, chain):
        source_id, artifact_id, task_ids, runs = chain
        runs["knowledge"] = seed_run(
            db, f"r_{P}_ch_kn", "task-knowledge", artifact_id,
            started="2026-01-14 00:00:00+00",
            items=verdict_items(task_ids, "concept", reason="idea"),
        )
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "task-embedding"
        assert step["runnable"] is True
        argv = step["argv"]
        assert opt(argv, "--prompt") == "v002"
        assert opt(argv, "--model") == "qwen/qwen3-embedding-8b"
        # Corpus-wide scope: our statement run is in it, whatever else the
        # shared database holds.
        assert runs["statement"] in opt(argv, "--statements-from").split(",")
        assert opt(argv, "--workers") == "8"
        assert "--tool" not in argv

    def test_kc_judge_uses_its_own_defaults_and_corpus_scope(self, db, chain):
        source_id, artifact_id, task_ids, runs = chain
        embedding = seed_run(
            db, f"r_{P}_ch_emb", "task-embedding", artifact_id,
            started="2027-01-01 00:00:00+00",
            items=[{"task_id": t} for t in task_ids],
        )
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "kc-judge"
        assert step["runnable"] is True
        argv = step["argv"]
        assert argv[2] == "universe.kc_judge"
        assert opt(argv, "--embedding-run") == embedding
        assert runs["statement"] in opt(argv, "--statements-from").split(",")
        modality_runs = opt(argv, "--modality-run").split(",")
        assert runs["modality_a"] in modality_runs
        assert runs["modality_b"] in modality_runs
        assert runs["knowledge"] in opt(argv, "--knowledge-run").split(",")
        assert opt(argv, "--workers") == "12"
        assert "--model" not in argv
        assert "--extra" not in argv

    def test_judge_verdicts_and_fresh_grouping_complete_the_source(self, db, chain):
        """Judge coverage is read per stated task from the verdict ledger
        (judge run items carry no artifact), and a grouping snapshot newer
        than the verdicts closes the pipeline."""
        source_id, _, task_ids, runs = chain
        default = defaults.STAGE_DEFAULTS["kc-judge"]
        runs["judge"] = seed_run(
            db, f"r_{P}_ch_judge", "kc-judge", None,
            started="2027-01-02 00:00:00+00",
            items=[{"task_id": task_ids[0]}],
        )
        first, second = sorted(task_ids)
        # Not mutual on purpose: coverage needs the tasks to appear in a
        # verdict, and a mutual pair would seed a clique into the corpus
        # grouping snapshots other tests compute.
        db.execute(
            "INSERT INTO kc_verdict"
            " (run_item_id, task_a_id, task_b_id, a_implies_b, b_implies_a,"
            "  judge_model, judge_prompt)"
            " VALUES (%s, %s, %s, 'clear_yes', 'clear_no', %s, %s)",
            (f"r_{P}_ch_judge-i1", first, second, default["model"], default["prompt_ref"]),
        )
        db.commit()
        step = ingest.next_step(db, source_id)
        assert step["stage"] == "grouped"
        assert step["runnable"] is False

        # Production-shaped grouping id; g0000 keeps next_grouping_id's
        # counter untouched for the kc_groups tests that follow.
        db.execute(
            "INSERT INTO kc_grouping (id, params) VALUES ('g0000', %s)",
            (Jsonb({}),),
        )
        db.commit()
        step = ingest.next_step(db, source_id)
        assert step["stage"] is None
        assert step["stage_status"] == "complete"


class TestAlreadyRunning:
    def test_registry_guard_blocks_a_second_launch(self, db, monkeypatch):
        source_id, _ = seed_source(db, "reg")

        class FakeProcess:
            pid = 4242

            def poll(self):
                return None

        ingest._RUNNING[source_id] = {
            "stage": "passage-cuts", "process": FakeProcess(), "log": "x.log",
        }
        try:
            assert ingest.running_step(source_id)["stage"] == "passage-cuts"
            with pytest.raises(ingest.StepAlreadyRunning):
                ingest.start_step(source_id)
        finally:
            ingest._RUNNING.pop(source_id, None)

    def test_finished_process_disappears_from_running(self, db):
        source_id = f"src_{P}_gone"

        class DoneProcess:
            pid = 4243

            def poll(self):
                return 0

        ingest._RUNNING[source_id] = {
            "stage": "passage-cuts", "process": DoneProcess(), "log": "x.log",
        }
        assert ingest.running_step(source_id) is None
        assert source_id not in ingest._RUNNING

    def test_ledger_running_run_blocks_launch_without_spawning(
        self, db, test_database_url, monkeypatch
    ):
        source_id, artifact_id = seed_source(db, "busy")
        seed_run(
            db, f"r_{P}_busy_cut", "passage-cuts", artifact_id, status="running"
        )
        monkeypatch.setattr(
            ingest, "connect", lambda: psycopg.connect(test_database_url)
        )
        monkeypatch.setattr(
            ingest.subprocess, "Popen",
            lambda *a, **k: pytest.fail("must not launch while a run is in flight"),
        )
        with pytest.raises(ingest.StepAlreadyRunning):
            ingest.start_step(source_id)


class TestEndpoints:
    @pytest.fixture()
    def client(self, db, test_database_url, monkeypatch):
        db.commit()
        connect = lambda: psycopg.connect(test_database_url)  # noqa: E731
        monkeypatch.setattr(web_app, "connect", connect)
        monkeypatch.setattr(ingest, "connect", connect)
        monkeypatch.setattr(
            ingest.subprocess, "Popen",
            lambda *a, **k: pytest.fail("endpoint tests must not launch"),
        )
        with TestClient(web_app.create_app()) as test_client:
            yield test_client

    def test_next_step_shape(self, db, client):
        source_id, _ = seed_source(db, "api")
        payload = client.get(f"/api/sources/{source_id}/next-step").json()
        assert payload["source_id"] == source_id
        assert payload["running"] is None
        assert payload["next"]["stage"] == "passage-cuts"
        assert payload["next"]["runnable"] is True
        assert payload["next"]["description"] == "Cut this source into passages"

    def test_next_step_unknown_source_is_404(self, client):
        assert client.get(f"/api/sources/src_{P}_nope/next-step").status_code == 404

    def test_run_next_step_conflicts_while_a_run_is_in_flight(self, db, client):
        source_id, artifact_id = seed_source(db, "api409")
        seed_run(
            db, f"r_{P}_api409_cut", "passage-cuts", artifact_id, status="running"
        )
        response = client.post(f"/api/sources/{source_id}/run-next-step")
        assert response.status_code == 409
        assert "already running" in response.json()["detail"]

    def test_run_next_step_rejects_a_step_that_is_not_runnable(self, db, client):
        source_id, _ = seed_source(
            db,
            "api400",
            snapshot=False,
            artifact=False,
            blocks=False,
            media_type="video",
        )
        response = client.post(f"/api/sources/{source_id}/run-next-step")
        assert response.status_code == 400
        assert "fetcher" in response.json()["detail"]
