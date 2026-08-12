"""Provider-free checks that KC consumers share post-split task evidence."""

import argparse

from universe import kc_statement_report, task_embedding, task_substance_report


def _part(body: str = "Rewritten part") -> dict:
    return {
        "id": "split-i1:t01",
        "run_item_id": "split-i1",
        "artifact_id": "artifact",
        "passage_id": "passage",
        "seq": 1,
        "body": body,
        "answer": "Effective answer",
    }


def test_legacy_embedding_renders_the_shared_post_split_scope(monkeypatch):
    selected = [_part()]
    captured = {}
    monkeypatch.setattr(
        task_embedding,
        "effective_tasks",
        lambda _conn, **kwargs: captured.update(kwargs) or selected,
    )
    args = argparse.Namespace(
        gen_runs=["generation"],
        passages_from=["cuts"],
        revision_run="base-revision",
        granularity_run="split",
        parts_revision_run="parts-revision",
    )

    tasks, rendered = task_embedding.task_answer_embedding_inputs(
        object(),
        args,
        argparse.Namespace(
            render_fields=lambda fields: f"{fields['task']} | {fields['answer']}"
        ),
    )

    assert tasks == selected
    assert rendered == ["Rewritten part | Effective answer"]
    assert captured == {
        "generation_runs": ["generation"],
        "passages_from": ["cuts"],
        "granularity_run": "split",
        "revision_run": "base-revision",
        "parts_revision_run": "parts-revision",
    }


def test_substance_report_resolves_split_before_revision(monkeypatch):
    selected = [_part()]
    selection = {}
    labeled = {}
    monkeypatch.setattr(
        task_substance_report,
        "effective_tasks",
        lambda _conn, **kwargs: selection.update(kwargs) or selected,
    )
    monkeypatch.setattr(
        task_substance_report,
        "label_map",
        lambda _conn, tasks, generation, splits: (
            labeled.update(tasks=tasks, generation=generation, splits=splits)
            or {selected[0]["id"]: "T01 part 1"}
        ),
    )
    monkeypatch.setattr(
        task_substance_report,
        "fetch_run",
        lambda *_args: {"stage": "task-substance", "model": "model"},
    )
    monkeypatch.setattr(
        task_substance_report,
        "fetch_items",
        lambda *_args: [
            {
                "id": "substance-i1",
                "task_id": selected[0]["id"],
                "response": '{"verdict":"works"}',
                "error": None,
            }
        ],
    )

    report = task_substance_report.render_runs(
        object(),
        ["substance"],
        ["generation"],
        revision_run="base-revision",
        passages_from=["cuts"],
        granularity_run="split",
        parts_revision_run="parts-revision",
        triage_run="triage",
    )

    assert selection == {
        "generation_runs": ["generation"],
        "passages_from": ["cuts"],
        "granularity_run": "split",
        "revision_run": "base-revision",
        "parts_revision_run": "parts-revision",
        "triage_run": "triage",
    }
    assert labeled["tasks"] is selected
    assert "T01 part 1: Rewritten part" in report


def test_statement_report_labels_the_exact_effective_tasks(monkeypatch):
    selected = [_part()]
    labeled = {}
    monkeypatch.setattr(
        kc_statement_report, "select_tasks", lambda _conn, _args: selected
    )
    monkeypatch.setattr(
        kc_statement_report,
        "label_map",
        lambda _conn, tasks, generation, splits: (
            labeled.update(tasks=tasks, generation=generation, splits=splits)
            or {selected[0]["id"]: "T01 part 1"}
        ),
    )
    monkeypatch.setattr(
        kc_statement_report,
        "fetch_run",
        lambda *_args: {"stage": "kc-statement", "model": "model"},
    )
    monkeypatch.setattr(
        kc_statement_report,
        "fetch_items",
        lambda *_args: [
            {
                "id": "statement-i1",
                "task_id": selected[0]["id"],
                "response": '{"verdict":"stated","statement":"Learner knows it."}',
                "error": None,
            }
        ],
    )

    report = kc_statement_report.render_runs(
        object(),
        ["statement"],
        ["generation"],
        revision_run="base-revision",
        passages_from=["cuts"],
        granularity_run="split",
        parts_revision_run="parts-revision",
    )

    assert labeled == {
        "tasks": selected,
        "generation": ["generation"],
        "splits": ["split"],
    }
    assert "### T01 part 1" in report
    assert "> Rewritten part" in report
