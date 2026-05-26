import json
import threading
import time

import pytest

from concept_graph_creation.runtime.stage_runner import StageBlockedError
from concept_graph_creation.stages.self_study_extraction import run_self_study_extraction_phase


def test_self_study_extraction_phase_writes_one_isolated_artifact_per_usable_self_study(tmp_path):
    source_body_path = tmp_path / "cg_pipeline" / "extraction" / "intro.md"
    source_body_path.parent.mkdir(parents=True)
    source_body_path.write_text(
        "# Intro\n\nA neural network learns weights.\n\n![Neuron](https://example.test/neuron.png)\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [
                    {
                        "lesson_id": "lesson-2026-01-01-intro",
                        "display_code": "L01",
                        "title": "Intro",
                        "date": "01/01/2026",
                        "description": "Introduction lesson",
                    }
                ],
                "self_studies": [
                    {
                        "self_study_id": "3",
                        "lesson_id": "lesson-2026-01-01-intro",
                        "source_body_status": "usable_source_body",
                        "workbook_metadata": {
                            "title": "Neural Network Intro",
                            "description": "Read the intro.",
                            "url": "https://example.test/source",
                            "related_labels": ["Redes neurais"],
                        },
                        "source_body": {
                            "path": "extraction/intro.md",
                            "sha256": "fake",
                            "word_count": 7,
                            "source_markdown": "https://example.test/source",
                        },
                    },
                    {
                        "self_study_id": "4",
                        "lesson_id": "lesson-2026-01-01-intro",
                        "source_body_status": "unavailable_source_body",
                        "workbook_metadata": {"title": "Blocked"},
                        "source_body": {"availability_failures": ["manual_access_required"]},
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["self_study_extraction_input.json"]
        calls.append(
            {
                "route": route.alias,
                "stage_name": stage_name,
                "self_study_id": model_input["self_study"]["self_study_id"],
                "source_markdown": model_input["source_body"]["markdown"],
                "allowed_image_urls": model_input["web_access_policy"]["allowed_image_urls"],
                "web_search_allowed": model_input["web_access_policy"]["web_search_allowed"],
                "repair_context": repair_context,
            }
        )
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": "candidate-3-001",
                        "label": "Neural network weights",
                        "description": "Weights are adjustable values learned during training.",
                        "coverage_criteria": ["Student can state that training changes weights."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "The source says the network learns weights.",
                            "granularity_rationale": "This is one checkable concept, not a broad topic.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": "Intro"}],
                        "evidence_type": "source_body",
                        "source_name": "Neural Network Intro",
                        "source_year": None,
                        "name_drops": [],
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    result = run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        model_call=model_call,
        initial_concurrency=8,
    )

    set_path = (
        run_dir
        / "lessons"
        / "lesson-2026-01-01-intro"
        / "self_studies"
        / "3"
        / "self_study_extraction_set.json"
    )
    pass_path = (
        run_dir
        / "lessons"
        / "lesson-2026-01-01-intro"
        / "self_studies"
        / "3"
        / "extraction_passes"
        / "pro-thinking"
        / "self_study_extraction.json"
    )
    extraction_set = json.loads(set_path.read_text(encoding="utf-8"))
    artifact = json.loads(pass_path.read_text(encoding="utf-8"))
    assert result["summary"] == {
        "usable_self_study_count": 1,
        "extracted_self_study_count": 1,
        "extraction_pass_count": 1,
        "reused_extraction_pass_count": 0,
        "skipped_count": 1,
    }
    assert calls == [
        {
            "route": "Pro Thinking",
            "stage_name": "self_study_extraction",
            "self_study_id": "3",
            "source_markdown": "# Intro\n\nA neural network learns weights.\n\n![Neuron](https://example.test/neuron.png)\n",
            "allowed_image_urls": ["https://example.test/neuron.png"],
            "web_search_allowed": False,
            "repair_context": None,
        }
    ]
    assert [item["route_alias"] for item in extraction_set["extraction_passes"]] == ["Pro Thinking"]
    assert artifact["artifact_type"] == "self_study_extraction"
    assert artifact["model_route"] == "Pro Thinking"
    assert artifact["self_study_id"] == "3"
    assert artifact["candidate_concepts"][0]["candidate_id"] == "candidate-3-001"
    assert artifact["candidate_concepts"][0]["evidence_type"] == "source_body"


def test_self_study_extraction_blocks_final_concepts_and_dependency_edges(tmp_path):
    source_body_path = tmp_path / "cg_pipeline" / "extraction" / "intro.md"
    source_body_path.parent.mkdir(parents=True)
    source_body_path.write_text("# Intro\n\nA neural network learns weights.\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": [
                    {
                        "self_study_id": "3",
                        "lesson_id": "lesson-1",
                        "source_body_status": "usable_source_body",
                        "workbook_metadata": {"title": "Neural Network Intro"},
                        "source_body": {"path": "extraction/intro.md", "sha256": "fake", "word_count": 6},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def model_call(**_kwargs):
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": "candidate-3-001",
                        "concept_id": "final-neural-network",
                        "label": "Neural network weights",
                        "description": "Weights are adjustable values learned during training.",
                        "coverage_criteria": ["Student can state that training changes weights."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "The source says the network learns weights.",
                            "granularity_rationale": "This is one checkable concept.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": "Intro"}],
                        "evidence_type": "source_body",
                    }
                ],
                "dependency_edges": [{"from": "final-neural-network", "to": "other"}],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    with pytest.raises(StageBlockedError, match="concept_id is forbidden|dependency_edges is forbidden"):
        run_self_study_extraction_phase(
            cg_pipeline_root=tmp_path / "cg_pipeline",
            run_dir=run_dir,
            model_call=model_call,
        )


def test_self_study_extraction_canonicalizes_source_role_aliases(tmp_path):
    source_body_path = tmp_path / "cg_pipeline" / "extraction" / "intro.md"
    source_body_path.parent.mkdir(parents=True)
    source_body_path.write_text("# Intro\n\nThis source concludes by motivating why NLP matters.\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": [
                    {
                        "self_study_id": "15",
                        "lesson_id": "lesson-1",
                        "source_body_status": "usable_source_body",
                        "workbook_metadata": {"title": "NLP Intro"},
                        "source_body": {"path": "extraction/intro.md", "sha256": "fake", "word_count": 9},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def model_call(**_kwargs):
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": "candidate-15-001",
                        "label": "NLP as an evolving field",
                        "description": "NLP matters because it supports everyday applications and future technology.",
                        "coverage_criteria": ["Student can explain why NLP has practical importance."],
                        "source_roles": [
                            "concluding",
                            "motivating",
                            "example",
                            "reference",
                            "deriving",
                            "mentioning",
                            "recommending",
                        ],
                        "extraction_reason": {
                            "source_grounded_rationale": "The conclusion motivates why NLP matters.",
                            "granularity_rationale": "This is one checkable source-local idea.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": "Intro"}],
                        "evidence_type": "source_body",
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    result = run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        model_call=model_call,
    )

    pass_path = result["pass_artifact_paths"][0]
    artifact = json.loads(pass_path.read_text(encoding="utf-8"))
    assert artifact["candidate_concepts"][0]["source_roles"] == [
        "explaining",
        "introducing",
        "demonstrating",
        "referencing",
        "incidental_mention",
    ]


def test_self_study_extraction_reduces_concurrency_after_deepseek_pressure(tmp_path):
    extraction_dir = tmp_path / "cg_pipeline" / "extraction"
    extraction_dir.mkdir(parents=True)
    self_studies = []
    for index in range(1, 9):
        self_study_id = str(index)
        (extraction_dir / f"{self_study_id}.md").write_text(
            f"# Source {self_study_id}\n\nThis source teaches one local idea.\n",
            encoding="utf-8",
        )
        self_studies.append(
            {
                "self_study_id": self_study_id,
                "lesson_id": "lesson-1",
                "source_body_status": "usable_source_body",
                "workbook_metadata": {"title": f"Source {self_study_id}"},
                "source_body": {"path": f"extraction/{self_study_id}.md", "sha256": "fake", "word_count": 8},
            }
        )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": self_studies,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    lock = threading.Lock()
    active = 0
    max_active = 0
    pressure_raised = False

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal active, max_active, pressure_raised
        model_input = inputs["self_study_extraction_input.json"]
        self_study_id = str(model_input["self_study"]["self_study_id"])
        with lock:
            active += 1
            max_active = max(max_active, active)
            should_raise_pressure = not pressure_raised and self_study_id == "1"
            if should_raise_pressure:
                pressure_raised = True
        time.sleep(0.01)
        with lock:
            active -= 1
        if should_raise_pressure:
            raise StageBlockedError("DeepSeek HTTP 429: rate limit reached")
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": f"candidate-{self_study_id}-001",
                        "label": f"Local idea {self_study_id}",
                        "description": "A source-local candidate.",
                        "coverage_criteria": ["Student can explain the local idea."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "The assigned source teaches this idea.",
                            "granularity_rationale": "The idea is checkable in one focused question.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": f"Source {self_study_id}"}],
                        "evidence_type": "source_body",
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    result = run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        model_call=model_call,
        initial_concurrency=60,
        pressure_backoff_seconds=0,
    )

    assert max_active == 8
    assert result["summary"]["extracted_self_study_count"] == 8
    assert result["concurrency"] == {
        "initial": 60,
        "final": 50,
        "pressure_error_count": 1,
        "reductions": [{"from": 60, "to": 50, "reason": "DeepSeek HTTP 429"}],
    }


def test_self_study_extraction_reuses_valid_completed_passes_on_rerun(tmp_path):
    extraction_dir = tmp_path / "cg_pipeline" / "extraction"
    extraction_dir.mkdir(parents=True)
    (extraction_dir / "1.md").write_text("# Source 1\n\nThis source teaches one local idea.\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    pass_dir = run_dir / "lessons" / "lesson-1" / "self_studies" / "1" / "extraction_passes" / "pro-thinking"
    pass_dir.mkdir(parents=True)
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": [
                    {
                        "self_study_id": "1",
                        "lesson_id": "lesson-1",
                        "source_body_status": "usable_source_body",
                        "workbook_metadata": {"title": "Source 1"},
                        "source_body": {"path": "extraction/1.md", "sha256": "fake", "word_count": 8},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (pass_dir / "self_study_extraction.json").write_text(
        json.dumps(
            {
                "artifact_type": "self_study_extraction",
                "schema_version": "self_study_extraction.v0",
                "source_artifact": "source_ledger.json",
                "model_route": "Pro Thinking",
                "lesson_id": "lesson-1",
                "self_study_id": "1",
                "source_body_path": "extraction/1.md",
                "source_body_sha256": "fake",
                "candidate_concepts": [
                    {
                        "candidate_id": "candidate-1-001",
                        "label": "Existing local idea",
                        "description": "A previously completed candidate.",
                        "coverage_criteria": ["Student can explain the local idea."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "The assigned source teaches this idea.",
                            "granularity_rationale": "The idea is checkable in one focused question.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": "Source 1"}],
                        "evidence_type": "source_body",
                    }
                ],
                "source_local_connector_candidates": [],
                "summary": {"candidate_count": 1, "source_local_connector_candidate_count": 0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def model_call(**_kwargs):
        raise AssertionError("completed valid extraction pass should not be called again")

    result = run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        model_call=model_call,
        initial_concurrency=2,
    )

    extraction_set = json.loads(
        (run_dir / "lessons" / "lesson-1" / "self_studies" / "1" / "self_study_extraction_set.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["summary"]["reused_extraction_pass_count"] == 1
    assert result["summary"]["extraction_pass_count"] == 1
    assert extraction_set["extraction_passes"][0]["artifact_path"] == (
        "lessons/lesson-1/self_studies/1/extraction_passes/pro-thinking/self_study_extraction.json"
    )


def test_self_study_extraction_retries_deepseek_timeout_with_reduced_concurrency(tmp_path):
    extraction_dir = tmp_path / "cg_pipeline" / "extraction"
    extraction_dir.mkdir(parents=True)
    self_studies = []
    for index in range(1, 9):
        self_study_id = str(index)
        (extraction_dir / f"{self_study_id}.md").write_text(
            f"# Source {self_study_id}\n\nThis source teaches one local idea.\n",
            encoding="utf-8",
        )
        self_studies.append(
            {
                "self_study_id": self_study_id,
                "lesson_id": "lesson-1",
                "source_body_status": "usable_source_body",
                "workbook_metadata": {"title": f"Source {self_study_id}"},
                "source_body": {"path": f"extraction/{self_study_id}.md", "sha256": "fake", "word_count": 8},
            }
        )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": self_studies,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    pressure_raised = False

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal pressure_raised
        model_input = inputs["self_study_extraction_input.json"]
        self_study_id = str(model_input["self_study"]["self_study_id"])
        if not pressure_raised and self_study_id == "1":
            pressure_raised = True
            raise StageBlockedError("DeepSeek request timed out while reading response: The read operation timed out")
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": f"candidate-{self_study_id}-001",
                        "label": f"Local idea {self_study_id}",
                        "description": "A source-local candidate.",
                        "coverage_criteria": ["Student can explain the local idea."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "The assigned source teaches this idea.",
                            "granularity_rationale": "The idea is checkable in one focused question.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": f"Source {self_study_id}"}],
                        "evidence_type": "source_body",
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    result = run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        model_call=model_call,
        initial_concurrency=8,
        pressure_backoff_seconds=0,
    )

    assert result["summary"]["extracted_self_study_count"] == 8
    assert result["concurrency"] == {
        "initial": 8,
        "final": 6,
        "pressure_error_count": 1,
        "reductions": [{"from": 8, "to": 6, "reason": "DeepSeek request timed out"}],
    }


def test_self_study_extraction_retries_empty_deepseek_message_with_reduced_concurrency(tmp_path):
    extraction_dir = tmp_path / "cg_pipeline" / "extraction"
    extraction_dir.mkdir(parents=True)
    (extraction_dir / "1.md").write_text(
        "# Source 1\n\nThis source teaches one local idea.\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": [
                    {
                        "self_study_id": "1",
                        "lesson_id": "lesson-1",
                        "source_body_status": "usable_source_body",
                        "workbook_metadata": {"title": "Source 1"},
                        "source_body": {"path": "extraction/1.md", "sha256": "fake", "word_count": 8},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal calls
        calls += 1
        model_input = inputs["self_study_extraction_input.json"]
        self_study_id = str(model_input["self_study"]["self_study_id"])
        if calls == 1:
            raise StageBlockedError("DeepSeek returned an empty message")
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": f"candidate-{self_study_id}-001",
                        "label": f"Local idea {self_study_id}",
                        "description": "A source-local candidate.",
                        "coverage_criteria": ["Student can explain the local idea."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "The assigned source teaches this idea.",
                            "granularity_rationale": "The idea is checkable in one focused question.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": f"Source {self_study_id}"}],
                        "evidence_type": "source_body",
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    result = run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        model_call=model_call,
        initial_concurrency=8,
        pressure_backoff_seconds=0,
    )

    assert calls == 2
    assert result["summary"]["extracted_self_study_count"] == 1
    assert result["concurrency"] == {
        "initial": 8,
        "final": 6,
        "pressure_error_count": 1,
        "reductions": [{"from": 8, "to": 6, "reason": "DeepSeek returned an empty message"}],
    }


def test_self_study_extraction_continuously_refills_workers_without_waiting_for_batch_straggler(tmp_path):
    extraction_dir = tmp_path / "cg_pipeline" / "extraction"
    extraction_dir.mkdir(parents=True)
    self_studies = []
    for index in range(1, 10):
        self_study_id = str(index)
        (extraction_dir / f"{self_study_id}.md").write_text(
            f"# Source {self_study_id}\n\nThis source teaches one local idea.\n",
            encoding="utf-8",
        )
        self_studies.append(
            {
                "self_study_id": self_study_id,
                "lesson_id": "lesson-1",
                "source_body_status": "usable_source_body",
                "workbook_metadata": {"title": f"Source {self_study_id}"},
                "source_body": {"path": f"extraction/{self_study_id}.md", "sha256": "fake", "word_count": 8},
            }
        )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": self_studies,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    lock = threading.Lock()
    finished = set()
    ninth_started_before_first_finished = False

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal ninth_started_before_first_finished
        model_input = inputs["self_study_extraction_input.json"]
        self_study_id = str(model_input["self_study"]["self_study_id"])
        with lock:
            if self_study_id == "9" and "1" not in finished:
                ninth_started_before_first_finished = True
        time.sleep(0.08 if self_study_id == "1" else 0.01)
        with lock:
            finished.add(self_study_id)
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": f"candidate-{self_study_id}-001",
                        "label": f"Local idea {self_study_id}",
                        "description": "A source-local candidate.",
                        "coverage_criteria": ["Student can explain the local idea."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "The assigned source teaches this idea.",
                            "granularity_rationale": "The idea is checkable in one focused question.",
                        },
                        "source_anchors": [{"kind": "markdown_heading", "locator": f"Source {self_study_id}"}],
                        "evidence_type": "source_body",
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    result = run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        model_call=model_call,
        initial_concurrency=8,
    )

    assert result["summary"]["extraction_pass_count"] == 9
    assert ninth_started_before_first_finished is True
