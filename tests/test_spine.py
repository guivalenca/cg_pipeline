"""Tests for the ingestion spine: pipeline progress and attention alerts.

Stage status is union-of-runs: a unit counts once its newest usable answer
parses, whichever run produced it.  Rows here use the `sp`/`spu` prefixes
against the shared session database.
"""

import pytest
from psycopg.types.json import Jsonb

from universe import defaults
from universe.spine import source_progress, attention, STAGE_ORDER


# --- seeding helpers ---------------------------------------------------------


def seed_source(db, tag):
    """A source with one ok snapshot and one artifact."""
    db.execute(
        "INSERT INTO source (id, identity, title) VALUES (%s, %s, %s)",
        (f"src_{tag}", Jsonb({}), f"Spine test {tag}"),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'hash', 'ok')",
        (f"snap_{tag}", f"src_{tag}"),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'tool', 'body')",
        (f"art_{tag}", f"snap_{tag}"),
    )
    db.commit()
    return f"src_{tag}", f"art_{tag}"


def seed_passages(db, tag, artifact_id, count=1, *, current=True):
    """Passages with a cuts-run origin; scope follows the run's generation."""
    default = defaults.STAGE_DEFAULTS["passage-cuts"]
    cuts_run = f"r_{tag}_cut"
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'passage-cuts', %s, %s, 'sha', 'done')",
        (
            cuts_run,
            default["model"] if current else "old-model",
            default["prompt_ref"] if current else "passage-cuts/v000",
        ),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, '{}')",
        (f"{cuts_run}-i1", cuts_run, artifact_id),
    )
    ids = []
    for seq in range(1, count + 1):
        passage_id = f"pass_{tag}_{seq}"
        db.execute(
            "INSERT INTO passage (id, artifact_id, blocker_version, first_seq, last_seq)"
            " VALUES (%s, %s, 'v1', %s, %s)",
            (passage_id, artifact_id, seq, seq + 1),
        )
        db.execute(
            "INSERT INTO passage_origin (passage_id, run_id) VALUES (%s, %s)",
            (passage_id, cuts_run),
        )
        ids.append(passage_id)
    db.commit()
    return ids


def seed_run(db, run_id, stage, items, *, started="2026-01-01 00:00:00+00", current=True):
    """A completed run with one row per item dict (passage_id/task_id/response/error)."""
    default = defaults.STAGE_DEFAULTS.get(stage, {"model": "m", "prompt_ref": "p"})
    model = default["model"] if current else "old-model"
    prompt_ref = default["prompt_ref"] if current else f"{stage}/v000"
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status, started_at)"
        " VALUES (%s, %s, %s, %s, 'sha', 'done', %s)",
        (run_id, stage, model, prompt_ref, started),
    )
    for seq, item in enumerate(items, 1):
        db.execute(
            "INSERT INTO run_item"
            " (id, run_id, artifact_id, passage_id, task_id, response, error)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                f"{run_id}-i{seq}",
                run_id,
                item.get("artifact_id"),
                item.get("passage_id"),
                item.get("task_id"),
                item.get("response"),
                item.get("error"),
            ),
        )
    db.commit()
    return run_id


def seed_tasks(db, tag, gen_run_id, passage_id, count=2):
    ids = []
    for seq in range(1, count + 1):
        task_id = f"task_{tag}_{seq}"
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, %s, 'Q?', 'A')",
            (task_id, f"{gen_run_id}-i1", passage_id, seq),
        )
        ids.append(task_id)
    db.commit()
    return ids


def seed_task_chain(db, tag, *, count=2):
    """A source whose tasks passed triage and substance: axis stages in scope."""
    source_id, artifact_id = seed_source(db, tag)
    (passage_id,) = seed_passages(db, tag, artifact_id)
    seed_run(
        db, f"r_{tag}_ptri", "passage-triage",
        [{"passage_id": passage_id, "response": '{"verdict": "not_filler"}'}],
        started="2026-01-01 00:00:00+00",
    )
    gen_run = seed_run(
        db, f"r_{tag}_gen", "task-generation",
        [{"artifact_id": artifact_id, "passage_id": passage_id, "response": '{"tasks": []}'}],
        started="2026-01-02 00:00:00+00",
    )
    tasks = seed_tasks(db, tag, gen_run, passage_id, count)
    seed_run(
        db, f"r_{tag}_gran", "task-granularity",
        [{"task_id": t, "response": '{"verdict": "single"}'} for t in tasks],
        started="2026-01-03 00:00:00+00",
    )
    seed_run(
        db, f"r_{tag}_rev", "task-revision",
        [{"task_id": t, "response": '{"verdict": "stands"}'} for t in tasks],
        started="2026-01-04 00:00:00+00",
    )
    seed_run(
        db, f"r_{tag}_tt", "task-triage",
        [{"task_id": t, "response": '{"verdict": "supported"}'} for t in tasks],
        started="2026-01-05 00:00:00+00",
    )
    seed_run(
        db, f"r_{tag}_sub", "task-substance",
        [{"task_id": t, "response": '{"verdict": "works"}'} for t in tasks],
        started="2026-01-06 00:00:00+00",
    )
    return source_id, artifact_id, tasks


def seed_statements(db, tag, tasks, *, started="2026-01-07 00:00:00+00"):
    return seed_run(
        db, f"r_{tag}_st", "kc-statement",
        [
            {"task_id": t, "response": f'{{"verdict": "stated", "statement": "S {t}"}}'}
            for t in tasks
        ],
        started=started,
    )


def seed_verdict(db, tag, task_a, task_b, *, current=True, created_at=None, suffix=""):
    """A judge run item (artifact NULL, production shape) plus its verdict."""
    default = defaults.STAGE_DEFAULTS["kc-judge"]
    judge_model = default["model"] if current else "old-judge"
    judge_prompt = default["prompt_ref"] if current else "kc-judge/v000"
    run_id = f"r_{tag}_judge{suffix}"
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'kc-judge', %s, %s, 'sha', 'done')",
        (run_id, judge_model, judge_prompt),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
        " VALUES (%s, %s, NULL, %s, '{}')",
        (f"{run_id}-i1", run_id, task_a),
    )
    first, second = sorted((task_a, task_b))
    db.execute(
        "INSERT INTO kc_verdict"
        " (run_item_id, task_a_id, task_b_id, a_implies_b, b_implies_a,"
        "  judge_model, judge_prompt, created_at)"
        " VALUES (%s, %s, %s, 'clear_yes', 'clear_yes', %s, %s, coalesce(%s, now()))",
        (f"{run_id}-i1", first, second, judge_model, judge_prompt, created_at),
    )
    db.commit()


def stage_of(db, source_id, stage):
    return source_progress(db)[source_id]["stages"][stage]


# --- tests -------------------------------------------------------------------


class TestSourceProgress:
    def test_snapshot_done(self, db):
        """Source with ok snapshot shows done."""
        db.execute("INSERT INTO source (id, identity, title) VALUES (%s, %s, %s)", ("src_sp1", Jsonb({"url": "http://t1"}), "T1"))
        db.execute("INSERT INTO source_snapshot (id, source_id, content_hash, status) VALUES (%s, %s, %s, %s)", ("snap_sp1", "src_sp1", "abc", "ok"))
        db.commit()
        prog = source_progress(db)
        assert prog["src_sp1"]["snapshot_status"] == "ok"
        assert prog["src_sp1"]["stages"]["snapshot"]["status"] == "done"

    def test_snapshot_pending(self, db):
        """Source with no snapshot shows pending."""
        db.execute("INSERT INTO source (id, identity, title) VALUES (%s, %s, %s)", ("src_sp2", Jsonb({}), "T2"))
        db.commit()
        prog = source_progress(db)
        assert prog["src_sp2"]["snapshot_status"] == "pending"
        assert prog["src_sp2"]["stages"]["snapshot"]["status"] == "pending"

    def test_stage_order(self, db):
        """Stages appear in correct order."""
        db.execute("INSERT INTO source (id, identity, title) VALUES (%s, %s, %s)", ("src_sp3", Jsonb({}), "T3"))
        db.commit()
        prog = source_progress(db)
        assert list(prog["src_sp3"]["stages"].keys()) == STAGE_ORDER

    def test_artifact_done(self, db):
        """Artifact stage with artifact shows done."""
        source_id, _ = seed_source(db, "sp4")
        assert stage_of(db, source_id, "artifact")["status"] == "done"

    def test_blocks_done(self, db):
        """Blocks stage with blocks shows done."""
        source_id, artifact_id = seed_source(db, "sp5")
        db.execute("INSERT INTO block (id, artifact_id, blocker_version, seq, kind, start_char, end_char, body) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", ("blk_sp5", artifact_id, "v1", 0, "paragraph", 0, 4, "text"))
        db.commit()
        assert stage_of(db, source_id, "blocks")["status"] == "done"

    def test_passages_done(self, db):
        """Passage-cuts stage with current-recipe passages shows done."""
        source_id, artifact_id = seed_source(db, "sp6")
        seed_passages(db, "sp6", artifact_id)
        facts = stage_of(db, source_id, "passage-cuts")
        assert facts["status"] == "done"
        assert facts["run_id"] == "r_sp6_cut"

    def test_superseded_cuts_leave_the_stage_open(self, db):
        """A source cut only by a superseded recipe still needs the cut."""
        source_id, artifact_id = seed_source(db, "sp11")
        seed_passages(db, "sp11", artifact_id, current=False)
        facts = stage_of(db, source_id, "passage-cuts")
        assert facts["status"] == "pending"
        assert facts["generation"] == "superseded"
        # Its passages are history, not triage targets.
        assert stage_of(db, source_id, "passage-triage")["total"] == 0

    def test_model_stage_done(self, db):
        """Model stage whose every unit has a usable answer shows done."""
        source_id, artifact_id = seed_source(db, "sp7")
        (passage_id,) = seed_passages(db, "sp7", artifact_id)
        seed_run(
            db, "r_sp7_tri", "passage-triage",
            [{"passage_id": passage_id, "response": '{"verdict": "not_filler"}'}],
        )
        facts = stage_of(db, source_id, "passage-triage")
        assert facts["status"] == "done"
        assert (facts["done"], facts["total"]) == (1, 1)

    def test_model_stage_partial(self, db):
        """Model stage with mixed success/failure shows partial."""
        source_id, artifact_id = seed_source(db, "sp8")
        passages = seed_passages(db, "sp8", artifact_id, count=2)
        seed_run(
            db, "r_sp8_tri", "passage-triage",
            [
                {"passage_id": passages[0], "response": '{"verdict": "not_filler"}'},
                {"passage_id": passages[1], "error": "Error"},
            ],
        )
        facts = stage_of(db, source_id, "passage-triage")
        assert facts["status"] == "partial"
        assert (facts["done"], facts["total"]) == (1, 2)

    def test_model_stage_failed(self, db):
        """Model stage with all failures shows failed."""
        source_id, artifact_id = seed_source(db, "sp9")
        (passage_id,) = seed_passages(db, "sp9", artifact_id)
        seed_run(
            db, "r_sp9_tri", "passage-triage",
            [{"passage_id": passage_id, "error": "Error"}],
        )
        assert stage_of(db, source_id, "passage-triage")["status"] == "failed"

    def test_unparseable_answer_is_not_done(self, db):
        """An answer the stage parser rejects does not count as coverage."""
        source_id, artifact_id = seed_source(db, "sp10")
        (passage_id,) = seed_passages(db, "sp10", artifact_id)
        seed_run(
            db, "r_sp10_tri", "passage-triage",
            [{"passage_id": passage_id, "response": '{"v": "ok"}'}],
        )
        facts = stage_of(db, source_id, "passage-triage")
        assert facts["status"] == "failed"
        assert facts["done"] == 0


class TestUnionAcrossRuns:
    def test_retry_chain_union_reads_done(self, db):
        """Union coverage completes a stage the latest run alone left partial."""
        source_id, _, tasks = seed_task_chain(db, "spu_retry")
        seed_run(
            db, "r_spu_retry_modA", "task-modality",
            [
                {"task_id": t, "response": '{"verdict": "do", "reason": "acts"}'}
                for t in tasks
            ],
            started="2026-02-01 00:00:00+00",
        )
        # A newer retry re-ran everything and hit rate limits on one task.
        seed_run(
            db, "r_spu_retry_modB", "task-modality",
            [
                {"task_id": tasks[0], "response": '{"verdict": "explain", "reason": "talks"}'},
                {"task_id": tasks[1], "error": "429 rate limited"},
            ],
            started="2026-02-02 00:00:00+00",
        )
        facts = stage_of(db, source_id, "task-modality")
        assert facts["status"] == "done"
        assert (facts["done"], facts["total"]) == (2, 2)
        assert facts["run_id"] == "r_spu_retry_modB"

    def test_superseded_generation_answer_still_counts(self, db):
        """Old-generation answers keep a stage done; the badge says superseded."""
        source_id, _, tasks = seed_task_chain(db, "spu_gen")
        seed_run(
            db, "r_spu_gen_mod", "task-modality",
            [
                {"task_id": t, "response": '{"verdict": "do", "reason": "acts"}'}
                for t in tasks
            ],
            started="2026-02-01 00:00:00+00",
            current=False,
        )
        facts = stage_of(db, source_id, "task-modality")
        assert facts["status"] == "done"
        assert facts["generation"] == "superseded"

    def test_gate_dropped_tasks_leave_the_scope(self, db):
        """Denominators shrink to the tasks the stage would actually call."""
        source_id, _, tasks = seed_task_chain(db, "spu_gate", count=3)
        # Overrule the chain: task 2 unsupported, task 3 does not work.
        seed_run(
            db, "r_spu_gate_tt2", "task-triage",
            [{"task_id": tasks[1], "response": '{"verdict": "unsupported"}'}],
            started="2026-02-01 00:00:00+00",
        )
        seed_run(
            db, "r_spu_gate_sub2", "task-substance",
            [{"task_id": tasks[2], "response": '{"verdict": "does_not_work"}'}],
            started="2026-02-02 00:00:00+00",
        )
        stages = source_progress(db)[source_id]["stages"]
        assert stages["task-triage"]["total"] == 3
        assert stages["task-substance"]["total"] == 2  # supported only
        assert stages["kc-statement"]["total"] == 1    # substance-kept only
        assert stages["kc-statement"]["status"] == "pending"

    def test_all_filler_source_completes_vacuously(self, db):
        """A source whose passages were all filler has nothing left to run."""
        source_id, artifact_id = seed_source(db, "spu_filler")
        db.execute(
            "INSERT INTO block (id, artifact_id, blocker_version, seq, kind,"
            " start_char, end_char, body) VALUES (%s, %s, 'v1', 0, 'paragraph', 0, 4, 'text')",
            ("blk_spu_filler", artifact_id),
        )
        db.commit()
        (passage_id,) = seed_passages(db, "spu_filler", artifact_id)
        seed_run(
            db, "r_spu_filler_tri", "passage-triage",
            [{"passage_id": passage_id, "response": '{"verdict": "filler"}'}],
            started="2026-01-02 00:00:00+00",
        )
        stages = source_progress(db)[source_id]["stages"]
        assert stages["passage-triage"]["status"] == "done"
        assert all(
            stages[name]["status"] == "done" for name in STAGE_ORDER
        ), stages

    def test_virgin_source_stays_pending(self, db):
        """Empty scopes never cascade to done before their predecessor ran."""
        source_id, _ = seed_source(db, "spu_virgin")
        stages = source_progress(db)[source_id]["stages"]
        assert stages["passage-cuts"]["status"] == "pending"
        assert stages["passage-triage"]["status"] == "pending"
        assert stages["kc-statement"]["status"] == "pending"
        assert stages["grouped"]["status"] == "pending"


class TestJudgeAndGrouped:
    def test_judge_reads_pair_verdicts_for_stated_tasks(self, db):
        """Judge status comes from the verdict ledger, not artifact joins."""
        source_id, _, tasks = seed_task_chain(db, "spu_judge")
        seed_statements(db, "spu_judge", tasks)
        facts = stage_of(db, source_id, "kc-judge")
        assert facts["status"] == "pending"
        assert (facts["done"], facts["total"]) == (0, 2)

        seed_verdict(db, "spu_judge", tasks[0], tasks[1])
        facts = stage_of(db, source_id, "kc-judge")
        assert facts["status"] == "done"
        assert (facts["done"], facts["total"]) == (2, 2)

    def test_superseded_judge_generation_does_not_cover(self, db):
        """Old-generation verdicts are history, not current coverage."""
        source_id, _, tasks = seed_task_chain(db, "spu_oldj")
        seed_statements(db, "spu_oldj", tasks)
        seed_verdict(db, "spu_oldj", tasks[0], tasks[1], current=False)
        facts = stage_of(db, source_id, "kc-judge")
        assert facts["status"] == "pending"
        assert (facts["done"], facts["total"]) == (0, 2)

    def test_grouped_tracks_snapshot_freshness_not_membership(self, db):
        """Grouped is done when the snapshot postdates the newest verdict."""
        source_id, _, tasks = seed_task_chain(db, "spu_grp")
        seed_statements(db, "spu_grp", tasks)
        seed_verdict(
            db, "spu_grp", tasks[0], tasks[1], created_at="2126-01-01 00:00:00+00"
        )
        # No snapshot after the verdict yet: pending.
        assert stage_of(db, source_id, "grouped")["status"] == "pending"

        # A snapshot computed after the verdict: done, even though only a
        # subset (or none) of the stated tasks are group members.
        db.execute(
            "INSERT INTO kc_grouping (id, params, computed_at)"
            " VALUES ('kg_spu_grp', '{}', '2126-06-01 00:00:00+00')"
        )
        db.execute(
            "INSERT INTO kc_group (grouping_id, id) VALUES ('kg_spu_grp', 'g_spu_grp')"
        )
        db.execute(
            "INSERT INTO kc_group_member (grouping_id, group_id, task_id)"
            " VALUES ('kg_spu_grp', 'g_spu_grp', %s)",
            (tasks[0],),
        )
        db.commit()
        facts = stage_of(db, source_id, "grouped")
        assert facts["status"] == "done"
        assert (facts["done"], facts["total"]) == (1, 2)

    def test_new_verdict_reopens_grouped(self, db):
        """A verdict newer than the snapshot makes grouped pending again."""
        source_id, _, tasks = seed_task_chain(db, "spu_stale")
        seed_statements(db, "spu_stale", tasks)
        seed_verdict(
            db, "spu_stale", tasks[0], tasks[1],
            created_at="2126-12-01 00:00:00+00",
        )
        facts = stage_of(db, source_id, "grouped")
        assert facts["status"] == "pending"


class TestAttention:
    def test_coverage_gap(self, db):
        """Syllabus item with source but no ok snapshot alerts."""
        db.execute("INSERT INTO source (id, identity, title) VALUES (%s, %s, %s)", ("src_a1", Jsonb({}), "A1"))
        db.execute("INSERT INTO syllabus (id, title) VALUES (%s, %s)", ("syl_a1", "Syl"))
        db.execute("INSERT INTO syllabus_version (id, syllabus_id, seq, origin) VALUES (%s, %s, %s, %s)", ("sv_a1", "syl_a1", 1, "upload"))
        db.execute("INSERT INTO syllabus_item (id, version_id, title, kind, source_id) VALUES (%s, %s, %s, %s, %s)", ("si_a1", "sv_a1", "Item", "book", "src_a1"))
        db.commit()
        alerts = attention(db)
        gaps = [a for a in alerts if a["kind"] == "coverage_gap"]
        assert len(gaps) > 0

    def test_acquisition_failed(self, db):
        """Syllabus item for failed snapshot alerts."""
        db.execute("INSERT INTO source (id, identity, title) VALUES (%s, %s, %s)", ("src_a2", Jsonb({}), "A2"))
        db.execute("INSERT INTO source_snapshot (id, source_id, status, failure_note) VALUES (%s, %s, %s, %s)", ("snap_a2", "src_a2", "failed", "Error"))
        db.execute("INSERT INTO syllabus (id, title) VALUES (%s, %s)", ("syl_a2", "Syl"))
        db.execute("INSERT INTO syllabus_version (id, syllabus_id, seq, origin) VALUES (%s, %s, %s, %s)", ("sv_a2", "syl_a2", 1, "upload"))
        db.execute("INSERT INTO syllabus_item (id, version_id, title, kind, source_id) VALUES (%s, %s, %s, %s, %s)", ("si_a2", "sv_a2", "Item", "book", "src_a2"))
        db.commit()
        alerts = attention(db)
        fails = [a for a in alerts if a["kind"] == "acquisition_failed"]
        assert len(fails) > 0

    def test_book_scope_missing_is_stored_but_not_an_alert(self, db):
        """The flag is a fact for acquisition time, not a dashboard alert (founder decision 2026-08-03)."""
        db.execute("INSERT INTO syllabus (id, title) VALUES (%s, %s)", ("syl_a3", "Syl"))
        db.execute("INSERT INTO syllabus_version (id, syllabus_id, seq, origin) VALUES (%s, %s, %s, %s)", ("sv_a3", "syl_a3", 1, "upload"))
        db.execute("INSERT INTO syllabus_item (id, version_id, title, kind, fields) VALUES (%s, %s, %s, %s, %s)", ("si_a3", "sv_a3", "Item", "book", Jsonb({"book_scope_missing": True})))
        db.commit()
        alerts = attention(db)
        assert not [a for a in alerts if a["kind"] == "book_scope_missing"]

    def test_attention_ok_snapshot(self, db):
        """Syllabus item with ok snapshot has no gap alert."""
        db.execute("INSERT INTO source (id, identity, title) VALUES (%s, %s, %s)", ("src_a4", Jsonb({}), "A4"))
        db.execute("INSERT INTO source_snapshot (id, source_id, content_hash, status) VALUES (%s, %s, %s, %s)", ("snap_a4", "src_a4", "abc", "ok"))
        db.execute("INSERT INTO syllabus (id, title) VALUES (%s, %s)", ("syl_a4", "Syl"))
        db.execute("INSERT INTO syllabus_version (id, syllabus_id, seq, origin) VALUES (%s, %s, %s, %s)", ("sv_a4", "syl_a4", 1, "upload"))
        db.execute("INSERT INTO syllabus_item (id, version_id, title, kind, source_id) VALUES (%s, %s, %s, %s, %s)", ("si_a4", "sv_a4", "Item", "book", "src_a4"))
        db.commit()
        alerts = attention(db)
        gaps = [a for a in alerts if a["kind"] == "coverage_gap" and a["item_id"] == "si_a4"]
        assert len(gaps) == 0
