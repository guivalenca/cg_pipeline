"""Adapter from durable Lesson Builds to the vendored six-stage creation pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Callable

import psycopg
from psycopg.types.json import Jsonb

from concept_graph_creation.runtime.fixture_model import FixtureModelClient
from concept_graph_creation.runtime.model_client import PipelineModelClient
from concept_graph_creation.runtime.stage_runner import ModelRoute, ModelRouter
from concept_graph_creation.stages.dependency_deferral import run_dependency_deferral_phase
from concept_graph_creation.stages.final_graph_assembly import run_final_graph_assembly_phase
from concept_graph_creation.stages.knowledge_type_classification import (
    run_knowledge_type_classification_phase,
)
from concept_graph_creation.stages.lesson_reconciliation import (
    run_lesson_reconciliation_phase,
)
from concept_graph_creation.stages.lesson_reconciliation_passthrough import (
    run_lesson_reconciliation_passthrough_phase,
)
from concept_graph_creation.stages.lesson_segmentation import run_lesson_segmentation_phase
from concept_graph_creation.stages.self_study_extraction import (
    run_self_study_extraction_phase,
)
from universe import lesson_build_identity, lesson_build_plan, pipeline_lease


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGES = {stage.name: stage for stage in lesson_build_plan.registered_stages()}
RESULT_PATHS = {stage.name: stage.result_path for stage in STAGES.values()}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha(body: str | bytes) -> str:
    raw = body.encode("utf-8") if isinstance(body, str) else body
    return hashlib.sha256(raw).hexdigest()


def _implementation_sha256(stage: str) -> str:
    if stage not in STAGES:
        raise ValueError(f"unknown Lesson creation stage {stage!r}")
    return lesson_build_identity.creation_implementation_sha256(PROJECT_ROOT)


def _prompt_path(build: dict[str, Any], stage: str) -> Path | None:
    frozen = build["manifest"]["prompts"][stage]
    path_ref = frozen.get("path")
    if not path_ref:
        return None
    path = PROJECT_ROOT / str(path_ref)
    if lesson_build_identity.path_sha256(path) != frozen.get("sha256"):
        raise RuntimeError(
            f"Lesson creation stage {stage} no longer matches its frozen prompt hash"
        )
    return path


def _frozen_router(build: dict[str, Any]) -> ModelRouter:
    raw_routes = build["manifest"].get("routing")
    if not isinstance(raw_routes, dict) or not raw_routes:
        raise RuntimeError("Lesson Build manifest has no frozen model routing")
    try:
        routes = {
            str(alias): ModelRoute(
                alias=str(alias),
                provider=str(raw["provider"]),
                model=str(raw["model"]),
                thinking_enabled=bool(raw["thinking_enabled"]),
                reasoning_effort=raw.get("reasoning_effort"),
                provider_sort=raw.get("provider_sort"),
                allow_provider_fallbacks=bool(raw["allow_provider_fallbacks"]),
                require_provider_parameters=bool(raw["require_provider_parameters"]),
            )
            for alias, raw in raw_routes.items()
            if isinstance(raw, dict)
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Lesson Build manifest has invalid frozen model routing") from exc
    if len(routes) != len(raw_routes):
        raise RuntimeError("Lesson Build manifest has invalid frozen model routing")
    return ModelRouter(routes=routes)


def _stage_fingerprint(
    manifest_sha256: str, stage: str, upstream: list[tuple[str, str]]
) -> str:
    raw = json.dumps(
        {"manifest_sha256": manifest_sha256, "stage": stage, "upstream": upstream},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validated_checkpoints(
    conn: psycopg.Connection, build_id: str, manifest_sha256: str
) -> tuple[tuple[str, ...], list[tuple], list[tuple[str, str]]]:
    rows = conn.execute(
        "SELECT id, stage, path, body, content_sha256, stage_fingerprint,"
        " is_stage_result FROM lesson_build_checkpoint"
        " WHERE build_id = %s ORDER BY created_at, id",
        (build_id,),
    ).fetchall()
    by_stage: dict[str, list[tuple]] = {}
    for row in rows:
        by_stage.setdefault(row[1], []).append(row)
    completed: list[str] = []
    valid_rows: list[tuple] = []
    upstream: list[tuple[str, str]] = []
    for plan in lesson_build_plan.registered_stages():
        stage_rows = by_stage.get(plan.name, [])
        result = next(
            (
                row
                for row in stage_rows
                if row[2] == plan.result_path and bool(row[6])
            ),
            None,
        )
        if result is None:
            break
        fingerprint = _stage_fingerprint(manifest_sha256, plan.name, upstream)
        for row in stage_rows:
            if _sha(row[3]) != row[4]:
                raise RuntimeError(
                    f"Lesson Build checkpoint {row[0]} failed its content hash"
                )
            if row[5] != fingerprint:
                raise RuntimeError(
                    f"Lesson Build checkpoint {row[0]} failed its stage fingerprint"
                )
        completed.append(plan.name)
        valid_rows.extend(stage_rows)
        upstream.append((plan.name, result[4]))
    return tuple(completed), valid_rows, upstream


def completed_stages(conn: psycopg.Connection, build_id: str) -> tuple[str, ...]:
    row = conn.execute(
        "SELECT manifest_sha256 FROM lesson_build WHERE id = %s", (build_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown Lesson build {build_id!r}")
    completed, _, _ = _validated_checkpoints(conn, build_id, row[0])
    return completed


def _load_build(conn: psycopg.Connection, work_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT build.id, build.lesson_id, build.manifest, build.manifest_sha256,"
        " work.id FROM lesson_build_work work"
        " JOIN lesson_build build ON build.id = work.build_id"
        " WHERE work.id = %s",
        (work_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown Lesson build work {work_id!r}")
    return {
        "id": row[0],
        "lesson_id": row[1],
        "manifest": row[2],
        "manifest_sha256": row[3],
        "work_id": row[4],
    }


def _source_ledger(conn: psycopg.Connection, build: dict[str, Any], run_dir: Path) -> dict:
    manifest = build["manifest"]
    references = manifest["references"]
    bodies = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT artifact.id, artifact.body FROM artifact"
            " JOIN lesson_build_work work ON work.artifact_id = artifact.id"
            " WHERE work.build_id = %s",
            (build["id"],),
        ).fetchall()
    }
    extracted_at = []
    self_studies = []
    for reference in references:
        publication = reference["publication"]
        body = bodies.get(publication["artifact_id"])
        if body is None:
            raise RuntimeError(
                f"frozen Source Publication {publication['artifact_id']} is unavailable"
            )
        source_path = run_dir / "source_bodies" / f"{reference['reference_id']}.md"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(body, encoding="utf-8")
        if publication.get("created_at"):
            extracted_at.append(publication["created_at"])
        self_studies.append(
            {
                "self_study_id": reference["reference_id"],
                "lesson_id": build["lesson_id"],
                "source_body_status": "usable_source_body",
                "metadata_only_candidate": False,
                "exclusion_reason": None,
                "workbook_metadata": {
                    "title": reference["title"],
                    "description": reference["description"],
                    "url": reference["url"],
                    "resource_code": reference["resource_code"] or "",
                    "required": True,
                    "related_labels": [],
                    "parent_class": manifest["lesson"]["title"],
                },
                "source_body": {
                    "corpus_record_present": True,
                    "type": reference["media_type"],
                    "status": "passed",
                    "discarded": False,
                    "discard_reason": None,
                    "path": f"source_bodies/{reference['reference_id']}.md",
                    "sha256": _sha(body),
                    "word_count": len(body.split()),
                    "bytes": len(body.encode("utf-8")),
                    "availability_warnings": [],
                    "availability_failures": [],
                },
                "ledger_warnings": [],
            }
        )
    lesson = manifest["lesson"]
    return {
        "artifact_type": "source_ledger",
        "schema_version": "source_ledger.v0",
        "generated_at": max(extracted_at) if extracted_at else "1970-01-01T00:00:00+00:00",
        "source_extracted_at": max(extracted_at) if extracted_at else "1970-01-01T00:00:00+00:00",
        "course_id": manifest["syllabus"]["id"],
        "module_id": manifest["syllabus"]["version_id"],
        "subject_id": lesson.get("lesson_subject_code")
        or (lesson.get("subjects") or ["LESSON"])[0],
        "subject_graph_id": lesson.get("subject_graph_id"),
        "institution_id": manifest["syllabus"].get("institution_id"),
        "subject_sheet": None,
        "subject": None,
        "inputs": {
            "lesson_build_id": build["id"],
            "lesson_build_manifest_sha256": build["manifest_sha256"],
            "lesson": lesson,
            "source_publications": [
                {
                    "reference_id": reference["reference_id"],
                    **reference["publication"],
                }
                for reference in references
            ],
        },
        "lessons": [
            {
                "lesson_id": lesson["id"],
                "display_code": lesson["id"],
                "title": lesson["title"],
                "description": lesson["description"],
                "kind": lesson["kind"],
                "week": lesson.get("week"),
                "date": lesson.get("date"),
                "workbook_row_number": lesson.get("activity_order")
                or lesson.get("seq"),
                "axis": (lesson.get("subjects") or [None])[0],
                "related_labels": lesson.get("subjects") or [],
            }
        ],
        "self_studies": self_studies,
    }


def _materialize(
    conn: psycopg.Connection,
    build: dict[str, Any],
    run_dir: Path,
    checkpoint_rows: list[tuple],
) -> None:
    (run_dir / "source_ledger.json").write_text(
        _json(_source_ledger(conn, build, run_dir)), encoding="utf-8"
    )
    for row in checkpoint_rows:
        path, body = row[2], row[3]
        target = run_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


def _record_usage_event(
    database_url: str,
    build: dict[str, Any],
    stage: str,
    lease: pipeline_lease.Lease,
    event: dict[str, Any],
) -> None:
    attempt_id = f"lesson-attempt-{uuid.uuid4().hex}"
    run_id = f"lesson-run-{uuid.uuid4().hex}"
    outcome = str(event.get("outcome") or "unknown")
    succeeded = outcome.startswith("success")
    prompt = build["manifest"]["prompts"].get(stage, {})
    prompt_sha = prompt.get("sha256") or prompt.get("implementation_sha256")
    duration = event.get("elapsed_seconds")
    duration_ms = (
        max(0, round(float(duration) * 1000))
        if isinstance(duration, (int, float)) and not isinstance(duration, bool)
        else None
    )
    with psycopg.connect(database_url) as usage_conn:
        if not pipeline_lease.fence(usage_conn, lease):
            raise pipeline_lease.LeaseLost(
                "Lesson model Attempt lost its pipeline lease before publication"
            )
        usage_conn.execute(
            "INSERT INTO run"
            " (id, stage, model, prompt_ref, prompt_sha, params, status, finished_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, now())",
            (
                run_id,
                stage,
                str(event.get("requested_model") or "unknown"),
                str(prompt.get("path") or f"implementation:{stage}"),
                str(prompt_sha),
                Jsonb({"route_alias": event.get("route_alias")}),
                "done" if succeeded else "failed",
            ),
        )
        usage_conn.execute(
            "INSERT INTO run_item"
            " (id, run_id, response, error, usage, duration_ms, lesson_build_id,"
            " lesson_id, requested_model, response_model, provider, generation_id,"
            " outcome, attempt_token)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                attempt_id,
                run_id,
                _json(event) if succeeded else None,
                None if succeeded else outcome,
                Jsonb(event.get("usage") or {}),
                duration_ms,
                build["id"],
                build["lesson_id"],
                event.get("requested_model"),
                event.get("response_model"),
                event.get("response_provider"),
                event.get("generation_id"),
                outcome,
                lease.token,
            ),
        )


def _live_model_call(
    database_url: str, build: dict[str, Any], stage: str, attempt_token: str
) -> Callable[..., str]:
    supervisor = pipeline_lease.current_supervisor(required=True)
    if supervisor is None or supervisor.lease is None:
        raise pipeline_lease.LeaseLost(
            "Lesson model calls require an active pipeline lease"
        )
    if supervisor.lease.token != attempt_token:
        raise pipeline_lease.LeaseLost(
            "Lesson model-call token does not match the active pipeline lease"
        )
    lease = supervisor.lease
    client = PipelineModelClient.from_env(project_root=PROJECT_ROOT)
    events = threading.local()
    original = client._append_usage_event

    def record(event: dict[str, Any]) -> None:
        original(event)
        _record_usage_event(database_url, build, stage, lease, event)
        events.count = getattr(events, "count", 0) + 1

    client._append_usage_event = record  # type: ignore[method-assign]

    def call(**kwargs: Any) -> str:
        events.count = 0
        try:
            refreshed = supervisor.before_provider_call()
            if refreshed is None or refreshed.token != attempt_token:
                raise pipeline_lease.LeaseLost(
                    "Lesson model-call token lost before provider work"
                )
            return client.call(**kwargs)
        except pipeline_lease.LeaseLost:
            raise
        except BaseException as exc:
            if getattr(events, "count", 0) == 0:
                route = kwargs.get("route")
                _record_usage_event(
                    database_url,
                    build,
                    stage,
                    lease,
                    {
                        "stage_name": kwargs.get("stage_name"),
                        "route_alias": getattr(route, "alias", None),
                        "requested_model": getattr(route, "model", None),
                        "response_provider": getattr(route, "provider", None),
                        "outcome": "client_error",
                        "error_type": type(exc).__name__,
                        "usage": {},
                    },
                )
            raise

    return call


def _model_call(
    database_url: str,
    build: dict[str, Any],
    stage: str,
    attempt_token: str,
    fixture_path: Path | None,
) -> Callable[..., str]:
    configured = fixture_path or (
        Path(os.environ["LESSON_BUILD_FIXTURE_MODEL_PATH"])
        if os.environ.get("LESSON_BUILD_FIXTURE_MODEL_PATH")
        else None
    )
    if configured is not None:
        return FixtureModelClient.from_file(configured)
    return _live_model_call(database_url, build, stage, attempt_token)


def _execute_stage(
    stage: str,
    run_dir: Path,
    model_call: Callable[..., str],
    prompt_path: Path | None,
    router: ModelRouter,
) -> None:
    if stage == "candidate-concepts":
        run_self_study_extraction_phase(
            cg_pipeline_root=PROJECT_ROOT,
            run_dir=run_dir,
            model_call=model_call,
            router=router,
            prompt_path=prompt_path,
            pressure_backoff_seconds=0,
        )
    elif stage == "lesson-reconciliation":
        run_lesson_reconciliation_phase(
            run_dir=run_dir,
            model_call=model_call,
            router=router,
            prompt_path=prompt_path,
            provider_retry_backoff_seconds=0,
        )
        run_lesson_reconciliation_passthrough_phase(run_dir=run_dir)
    elif stage == "dependency-deferral":
        run_dependency_deferral_phase(run_dir=run_dir)
    elif stage == "lesson-segmentation":
        run_lesson_segmentation_phase(
            run_dir=run_dir,
            model_call=model_call,
            router=router,
            prompt_path=prompt_path,
            provider_retry_backoff_seconds=0,
        )
    elif stage == "knowledge-types":
        run_knowledge_type_classification_phase(
            run_dir=run_dir,
            model_call=model_call,
            router=router,
            prompt_path=prompt_path,
            provider_retry_backoff_seconds=0,
        )
    elif stage == "lesson-fragment":
        run_final_graph_assembly_phase(run_dir=run_dir, cg_pipeline_root=PROJECT_ROOT)
    else:
        raise ValueError(f"unknown Lesson creation stage {stage!r}")


def _family(path: str) -> str:
    if "self_study_extraction" in path:
        return "candidate_concepts"
    if "lesson_reconciliation" in path or path == "subject_merge.json":
        return "lesson_concepts"
    if "lesson_segment" in path or "lesson_segmentation" in path:
        return "lesson_segments"
    if "knowledge_type" in path:
        return "knowledge_types"
    if path.startswith("final_graph/"):
        return "lesson_fragment"
    return "raw_artifacts"


def run_stage(
    conn: psycopg.Connection,
    *,
    work_id: str,
    stage: str,
    fixture_path: Path | None = None,
    model_call: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """Run and atomically checkpoint one stage under the inherited lease fence."""
    build = _load_build(conn, work_id)
    plan = STAGES.get(stage)
    if plan is None:
        raise ValueError(f"unknown Lesson creation stage {stage!r}")
    frozen_implementation = build["manifest"]["prompts"][stage][
        "implementation_sha256"
    ]
    if frozen_implementation != _implementation_sha256(stage):
        raise RuntimeError(
            f"Lesson creation stage {stage} no longer matches its frozen fingerprint"
        )
    prompt_path = _prompt_path(build, stage)
    router = _frozen_router(build)
    completed, checkpoint_rows, upstream = _validated_checkpoints(
        conn, build["id"], build["manifest_sha256"]
    )
    fingerprint = _stage_fingerprint(build["manifest_sha256"], stage, upstream)
    if stage in completed:
        prior = next(
            row
            for row in checkpoint_rows
            if row[1] == stage and row[2] == plan.result_path and bool(row[6])
        )
        return {"stage": stage, "checkpoint_id": prior[0], "reused": True}
    next_plan = lesson_build_plan.next_stage(completed=completed)
    if next_plan is None or next_plan.name != stage:
        raise RuntimeError(
            f"Lesson creation stage {stage} is not next after {list(completed)}"
        )
    supervisor = pipeline_lease.current_supervisor(required=True)
    if supervisor is None or supervisor.lease is None:
        raise pipeline_lease.LeaseLost("Lesson creation requires an active pipeline lease")
    database_url = pipeline_lease.connection_dsn(conn)
    attempt_token = supervisor.lease.token
    with tempfile.TemporaryDirectory(prefix="lesson-build-") as directory:
        run_dir = Path(directory)
        _materialize(conn, build, run_dir, checkpoint_rows)
        before = {
            path.relative_to(run_dir).as_posix(): _sha(path.read_bytes())
            for path in run_dir.rglob("*.json")
        }
        selected_call = model_call or _model_call(
            database_url, build, stage, attempt_token, fixture_path
        )
        _execute_stage(stage, run_dir, selected_call, prompt_path, router)
        result_path = plan.result_path
        generated = [
            path
            for path in sorted(run_dir.rglob("*.json"))
            if path.relative_to(run_dir).as_posix() != "source_ledger.json"
            and before.get(path.relative_to(run_dir).as_posix())
            != _sha(path.read_bytes())
        ]
        if not (run_dir / result_path).is_file():
            raise RuntimeError(f"Lesson creation stage {stage} did not publish {result_path}")
        supervisor.fence(conn)
        checkpoint_ids: dict[str, str] = {}
        for path in generated:
            relative = path.relative_to(run_dir).as_posix()
            body = path.read_text(encoding="utf-8")
            checkpoint_id = f"lesson-checkpoint-{uuid.uuid4().hex}"
            conn.execute(
                "INSERT INTO lesson_build_checkpoint"
                " (id, build_id, stage, family, path, body, content_sha256,"
                " stage_fingerprint, is_stage_result)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (build_id, stage, path) DO NOTHING",
                (
                    checkpoint_id,
                    build["id"],
                    stage,
                    _family(relative),
                    relative,
                    body,
                    _sha(body),
                    fingerprint,
                    relative == result_path,
                ),
            )
            checkpoint_ids[relative] = checkpoint_id
        conn.commit()
    return {
        "stage": stage,
        "checkpoint_id": checkpoint_ids[result_path],
        "reused": False,
    }
