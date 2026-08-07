"""Freeze and run the four-source Pro-high versus Flash-low benchmark.

The production database is read only during ``prepare``.  Every frozen case
and every live Flash response is written to a database whose name must be
``universe_pipeline_flash_shadow_20260807``.  No pipeline run is materialized
and no production selector or default is changed by this experiment.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from universe.harness import load_prompt, load_tool
from universe.model_client import ModelClient, is_transient_failure
from universe.passages import passage_text, source_text


PRODUCTION_DATABASE = "universe"
EXPERIMENT_DATABASE = "universe_pipeline_flash_shadow_20260807"
FLASH_MODEL = "deepseek/deepseek-v4-flash-0731"
SOURCE_IDS = (
    "si-mod6-0022-a-simple-explanation-of-the-bag-of-words-model",
    "si-mod6-0024-representacao-vetorial-de-textos-bag-of-words",
    "si-mod6-0025-getting-started-with-natural-language-processing-bag-of-words",
    "si-mod6-0026-atividade-bag-of-words",
)
REFERENCE_RUNS = {
    "task-generation": "r0139",
    "task-granularity": "r0141",
    "task-revision": "r0142",
    "task-triage": "r0145",
    "task-substance": "r0146",
    "kc-statement": "r0147",
    "task-knowledge": "r0149",
}
PROMPT_VERSIONS = {
    "task-generation": "v004",
    "task-granularity": "v004",
    "task-revision": "v004",
    "task-triage": "v001",
    "task-substance": "v004",
    "kc-statement": "v005",
    "task-knowledge": "v003",
}
TOOL_PATHS = {
    "task-generation": "prompts/task-generation/tool-v001.json",
    "task-granularity": "prompts/task-granularity/tool-v001.json",
    "task-revision": "prompts/task-revision/tool-v003.json",
    "task-triage": "prompts/task-triage/tool-v001.json",
    "task-substance": "prompts/task-substance/tool-v004.json",
    "kc-statement": "prompts/kc-statement/tool-v007.json",
    "task-knowledge": "prompts/task-knowledge/tool-v002.json",
}


def database_name(conn: psycopg.Connection) -> str:
    return conn.execute("SELECT current_database()").fetchone()[0]


def assert_database(conn: psycopg.Connection, expected: str) -> None:
    actual = database_name(conn)
    if actual != expected:
        raise SystemExit(f"expected database {expected}, got {actual}; refusing to continue")


def parse_response(raw: str) -> dict:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("response is not a JSON object")
    return parsed


def create_experiment_tables(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eval_case (
            case_id text PRIMARY KEY,
            stage text NOT NULL,
            source_id text NOT NULL,
            source_title text,
            stratum text NOT NULL,
            reference_run_id text NOT NULL,
            reference_run_item_id text NOT NULL,
            artifact_id text NOT NULL,
            passage_id text,
            task_id text,
            prompt_ref text NOT NULL,
            prompt_sha text NOT NULL,
            rendered_prompt text NOT NULL,
            input jsonb NOT NULL,
            reference_response text NOT NULL,
            reference_usage jsonb NOT NULL,
            reference_params jsonb NOT NULL,
            tool_path text NOT NULL,
            tool_payload jsonb NOT NULL,
            frozen_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eval_trial (
            case_id text NOT NULL REFERENCES eval_case(case_id),
            replicate integer NOT NULL CHECK (replicate > 0),
            model text NOT NULL,
            params jsonb NOT NULL,
            response text,
            usage jsonb NOT NULL DEFAULT '{}'::jsonb,
            duration_ms integer,
            error text,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (case_id, replicate)
        )
        """
    )
    conn.commit()


def fetch_revision_overlay(conn: psycopg.Connection) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT task_id, response FROM run_item"
        " WHERE run_id = 'r0142' AND error IS NULL AND task_id IS NOT NULL"
    ).fetchall()
    return {task_id: parse_response(response) for task_id, response in rows}


def fetch_task(conn: psycopg.Connection, task_id: str) -> dict:
    row = conn.execute(
        "SELECT t.id, t.body, t.answer, t.passage_id, p.artifact_id,"
        " p.blocker_version, s.id, s.title"
        " FROM task t JOIN passage p ON p.id=t.passage_id"
        " JOIN artifact a ON a.id=p.artifact_id"
        " JOIN source_snapshot sn ON sn.id=a.snapshot_id"
        " JOIN source s ON s.id=sn.source_id WHERE t.id=%s",
        (task_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"unknown task {task_id}")
    keys = (
        "id body answer passage_id artifact_id blocker_version source_id source_title"
    ).split()
    return dict(zip(keys, row))


def fetch_passage(conn: psycopg.Connection, passage_id: str) -> dict:
    row = conn.execute(
        "SELECT p.id, p.artifact_id, p.blocker_version, p.first_seq, p.last_seq,"
        " s.id, s.title FROM passage p"
        " JOIN artifact a ON a.id=p.artifact_id"
        " JOIN source_snapshot sn ON sn.id=a.snapshot_id"
        " JOIN source s ON s.id=sn.source_id WHERE p.id=%s",
        (passage_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"unknown passage {passage_id}")
    keys = (
        "id artifact_id blocker_version first_seq last_seq source_id source_title"
    ).split()
    return dict(zip(keys, row))


def case_material(
    conn: psycopg.Connection,
    stage: str,
    row: dict,
    revisions: dict[str, dict],
) -> dict:
    if stage == "task-generation":
        passage = fetch_passage(conn, row["passage_id"])
        whole_source = source_text(conn, passage["artifact_id"], passage["blocker_version"])
        focus = passage_text(conn, passage)
        return {
            "source_id": passage["source_id"],
            "source_title": passage["source_title"],
            "artifact_id": passage["artifact_id"],
            "passage_id": passage["id"],
            "task_id": None,
            "fields": {"body": whole_source, "passage": focus},
            "input": {"source": whole_source, "passage": focus},
            "length": len(focus),
        }

    task = fetch_task(conn, row["task_id"])
    body = task["body"]
    if stage in {"task-triage", "task-substance", "kc-statement", "task-knowledge"}:
        revision = revisions.get(task["id"])
        if revision and revision.get("verdict") == "rewritten":
            body = revision["task"]
    fields = {"task": body, "answer": task["answer"]}
    if stage == "task-triage":
        whole_source = source_text(conn, task["artifact_id"], task["blocker_version"])
        fields["body"] = whole_source
        visible_input = {
            "source": whole_source,
            "task": body,
            "answer": task["answer"],
        }
    else:
        visible_input = fields
    return {
        "source_id": task["source_id"],
        "source_title": task["source_title"],
        "artifact_id": task["artifact_id"],
        "passage_id": task["passage_id"],
        "task_id": task["id"],
        "fields": fields,
        "input": visible_input,
        "length": len(body) + len(task["answer"]),
    }


def choose_two(stage: str, rows: list[dict]) -> list[dict]:
    """Choose two deliberately different cases, deterministically."""
    rows = sorted(rows, key=lambda row: (row["length"], row["run_item_id"]))
    by_verdict: dict[str, list[dict]] = {}
    for row in rows:
        by_verdict.setdefault(row["verdict"], []).append(row)

    desired = {
        "task-granularity": ("composite", "single"),
        "task-revision": ("unfixable", "rewritten", "stands"),
        "task-substance": ("does_not_work", "works"),
        "task-knowledge": ("procedure", "concept"),
    }.get(stage)
    chosen: list[dict] = []
    if desired:
        for verdict in desired:
            candidates = by_verdict.get(verdict, [])
            if candidates:
                candidate = candidates[-1]
                if candidate not in chosen:
                    chosen.append(candidate)
            if len(chosen) == 2:
                return chosen
    for candidate in (rows[-1], rows[0]):
        if candidate not in chosen:
            chosen.append(candidate)
        if len(chosen) == 2:
            return chosen
    raise ValueError(f"{stage} has fewer than two distinct cases")


def reference_rows(conn: psycopg.Connection, run_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT i.id, i.artifact_id, i.passage_id, i.task_id, i.response,"
        " i.usage, s.id, s.title FROM run_item i"
        " JOIN artifact a ON a.id=i.artifact_id"
        " JOIN source_snapshot sn ON sn.id=a.snapshot_id"
        " JOIN source s ON s.id=sn.source_id"
        " WHERE i.run_id=%s AND i.error IS NULL AND s.id=ANY(%s) ORDER BY i.id",
        (run_id, list(SOURCE_IDS)),
    ).fetchall()
    keys = (
        "run_item_id artifact_id passage_id task_id response usage source_id source_title"
    ).split()
    return [dict(zip(keys, row)) for row in rows]


def prepare(production_url: str, shadow_url: str) -> None:
    with psycopg.connect(production_url) as prod, psycopg.connect(shadow_url) as shadow:
        assert_database(prod, PRODUCTION_DATABASE)
        assert_database(shadow, EXPERIMENT_DATABASE)
        prod.execute("SET TRANSACTION READ ONLY")
        create_experiment_tables(shadow)
        revisions = fetch_revision_overlay(prod)

        frozen: list[dict] = []
        for stage, run_id in REFERENCE_RUNS.items():
            prompt = load_prompt(stage, PROMPT_VERSIONS[stage], require_body=stage in {"task-generation", "task-triage"})
            run = prod.execute(
                "SELECT prompt_ref, prompt_sha, params FROM run WHERE id=%s AND status='done'",
                (run_id,),
            ).fetchone()
            if not run:
                raise SystemExit(f"missing completed reference run {run_id}")
            prompt_ref, prompt_sha, reference_params = run
            if (prompt.ref, prompt.sha) != (prompt_ref, prompt_sha):
                raise SystemExit(f"local {prompt.ref} does not match frozen {run_id}")

            enriched = []
            for row in reference_rows(prod, run_id):
                material = case_material(prod, stage, row, revisions)
                response = parse_response(row["response"])
                verdict = response.get("verdict", "tasks")
                enriched.append({**row, **material, "verdict": verdict})

            tool_path = TOOL_PATHS[stage]
            tool_payload = load_tool(tool_path)
            for source_id in SOURCE_IDS:
                source_rows = [row for row in enriched if row["source_id"] == source_id]
                for position, row in enumerate(choose_two(stage, source_rows), 1):
                    case_id = f"{stage}:{SOURCE_IDS.index(source_id)+1:02d}:{position:02d}"
                    rendered = prompt.render_fields(row["fields"])
                    frozen.append(
                        {
                            **row,
                            "case_id": case_id,
                            "stage": stage,
                            "stratum": row["verdict"],
                            "reference_run_id": run_id,
                            "prompt_ref": prompt.ref,
                            "prompt_sha": prompt.sha,
                            "rendered_prompt": rendered,
                            "reference_params": reference_params,
                            "tool_path": tool_path,
                            "tool_payload": tool_payload,
                        }
                    )

        for row in frozen:
            shadow.execute(
                "INSERT INTO eval_case (case_id,stage,source_id,source_title,stratum,"
                "reference_run_id,reference_run_item_id,artifact_id,passage_id,task_id,"
                "prompt_ref,prompt_sha,rendered_prompt,input,reference_response,"
                "reference_usage,reference_params,tool_path,tool_payload)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                " ON CONFLICT (case_id) DO UPDATE SET"
                " rendered_prompt=excluded.rendered_prompt,input=excluded.input,"
                " reference_response=excluded.reference_response,"
                " reference_usage=excluded.reference_usage,reference_params=excluded.reference_params",
                (
                    row["case_id"], row["stage"], row["source_id"], row["source_title"],
                    row["stratum"], row["reference_run_id"], row["run_item_id"],
                    row["artifact_id"], row["passage_id"], row["task_id"], row["prompt_ref"],
                    row["prompt_sha"], row["rendered_prompt"], Jsonb(row["input"]),
                    row["response"], Jsonb(row["usage"] or {}), Jsonb(row["reference_params"]),
                    row["tool_path"], Jsonb(row["tool_payload"]),
                ),
            )
        shadow.commit()
        print(f"froze {len(frozen)} cases in {EXPERIMENT_DATABASE}")


def complete_case(row: dict) -> dict:
    params = {
        **row["tool_payload"],
        "reasoning_effort": "low",
        "provider": {
            "sort": "throughput",
            "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
            "ignore": ["SiliconFlow"],
        },
    }
    max_tokens = int(row["reference_params"].get("max_tokens", 65536))
    client = ModelClient(FLASH_MODEL, max_tokens=max_tokens, extra=params)
    last_error = None
    for attempt in range(4):
        try:
            response, usage, duration_ms = client.complete(row["rendered_prompt"])
            parse_response(response)
            return {
                "case_id": row["case_id"], "response": response, "usage": usage,
                "duration_ms": duration_ms, "error": None, "params": client.params,
            }
        except Exception as exc:  # preserve a failed case for audit
            last_error = f"{type(exc).__name__}: {exc}"
            if not is_transient_failure(exc) or attempt == 3:
                break
            time.sleep((2, 6, 18)[attempt])
    return {
        "case_id": row["case_id"], "response": None, "usage": {},
        "duration_ms": None, "error": last_error, "params": client.params,
    }


def run_trials(shadow_url: str, replicates: list[int], workers: int) -> None:
    with psycopg.connect(shadow_url) as conn:
        assert_database(conn, EXPERIMENT_DATABASE)
        rows = conn.execute(
            "SELECT case_id,rendered_prompt,reference_params,tool_payload FROM eval_case ORDER BY case_id"
        ).fetchall()
        keys = "case_id rendered_prompt reference_params tool_payload".split()
        cases = [dict(zip(keys, row)) for row in rows]
        if len(cases) != 56:
            raise SystemExit(f"expected 56 frozen cases, found {len(cases)}")

    for replicate in replicates:
        with psycopg.connect(shadow_url) as conn:
            existing = {
                row[0] for row in conn.execute(
                    "SELECT case_id FROM eval_trial WHERE replicate=%s", (replicate,)
                ).fetchall()
            }
        pending = [case for case in cases if case["case_id"] not in existing]
        print(f"replicate {replicate}: {len(pending)} pending case(s)", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(complete_case, case): case for case in pending}
            for completed, future in enumerate(as_completed(futures), 1):
                result = future.result()
                with psycopg.connect(shadow_url) as conn:
                    assert_database(conn, EXPERIMENT_DATABASE)
                    conn.execute(
                        "INSERT INTO eval_trial (case_id,replicate,model,params,response,usage,duration_ms,error)"
                        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            result["case_id"], replicate, FLASH_MODEL, Jsonb(result["params"]),
                            result["response"], Jsonb(result["usage"]), result["duration_ms"],
                            result["error"],
                        ),
                    )
                    conn.commit()
                status = "ok" if result["error"] is None else result["error"]
                print(f"  {completed:02d}/{len(pending):02d} {result['case_id']} {status}", flush=True)


def export(shadow_url: str, output: Path) -> None:
    with psycopg.connect(shadow_url) as conn:
        assert_database(conn, EXPERIMENT_DATABASE)
        cases = conn.execute(
            "SELECT case_id,stage,source_id,source_title,stratum,reference_run_id,"
            "reference_run_item_id,artifact_id,passage_id,task_id,prompt_ref,prompt_sha,"
            "input,reference_response,reference_usage FROM eval_case ORDER BY case_id"
        ).fetchall()
        case_keys = (
            "case_id stage source_id source_title stratum reference_run_id reference_run_item_id "
            "artifact_id passage_id task_id prompt_ref prompt_sha input reference_response reference_usage"
        ).split()
        trials = conn.execute(
            "SELECT case_id,replicate,model,params,response,usage,duration_ms,error"
            " FROM eval_trial ORDER BY case_id,replicate"
        ).fetchall()
        trial_keys = "case_id replicate model params response usage duration_ms error".split()
    payload = {
        "name": "Concept Universe four-source pipeline Flash-low benchmark v001",
        "isolation": {"database": EXPERIMENT_DATABASE, "production_database_written": False},
        "reference_model": "deepseek/deepseek-v4-pro",
        "test_model": FLASH_MODEL,
        "cases": [dict(zip(case_keys, row)) for row in cases],
        "trials": [dict(zip(trial_keys, row)) for row in trials],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")
    print(f"wrote {len(payload['cases'])} cases and {len(payload['trials'])} trials to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "export"))
    parser.add_argument(
        "--production-url",
        default=os.environ.get("PRODUCTION_DATABASE_URL", "postgresql://universe:universe@localhost:5433/universe"),
    )
    parser.add_argument(
        "--shadow-url",
        default=os.environ.get(
            "DATABASE_URL",
            f"postgresql://universe:universe@localhost:5433/{EXPERIMENT_DATABASE}",
        ),
    )
    parser.add_argument("--replicates", default="1,2")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("evals/pipeline-flash-benchmark-v001.json"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.production_url, args.shadow_url)
    elif args.command == "run":
        replicates = [int(value) for value in args.replicates.split(",") if value]
        run_trials(args.shadow_url, replicates, args.workers)
    else:
        export(args.shadow_url, args.out)


if __name__ == "__main__":
    main()
