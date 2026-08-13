"""One call per candidate pair, verdict stored in kc_verdict.

    python -m universe.kc_judge run --statements-from r0101,r0102 \
        --embedding-run r0103 --modality-run r0104,r0106 \
        --knowledge-run r0105,r0107
"""

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from universe import harness, judge_manifest, pipeline_lease
from universe.db import connect
from universe.effective_evidence import resolve_statement_tasks
from universe.kc_statement import fetch_usable_statements
from universe.model_client import ModelClient
from universe.recipe_identity import launch_recipe
from universe.task_knowledge import knowledge_of
from universe.task_modality import modality_of
from universe.tasks import fetch_tasks


VERDICTS = {"clear_yes", "likely", "unlikely", "clear_no"}
STAGE = "kc-judge"
_RECIPE = launch_recipe(STAGE)
PROMPT_VERSION = _RECIPE["prompt_ref"].split("/", 1)[1]
TOOL_PATH = Path(__file__).resolve().parents[2] / _RECIPE["tool"]
DEFAULT_WORKERS = _RECIPE["workers"]
DEFAULT_MODEL = _RECIPE["model"]
DEFAULT_MAX_TOKENS = _RECIPE["max_tokens"]
DEFAULT_EXTRA = _RECIPE["extra"]
CANDIDATE_POLICY = _RECIPE["input_contract"]


def universe_build_key(
    *,
    model: str,
    prompt_ref: str,
    prompt_sha: str,
    model_params: dict,
    statement_runs: list[str],
    embedding_run: str,
    modality_runs: list[str],
    knowledge_runs: list[str],
) -> str:
    """Fingerprint everything that can change a Universe judge result."""
    payload = {
        "model": model,
        "prompt_ref": prompt_ref,
        "prompt_sha": prompt_sha,
        "model_params": model_params,
        "statements_from": statement_runs,
        "embedding_run": embedding_run,
        "modality_runs": modality_runs,
        "knowledge_runs": knowledge_runs,
        "candidate_policy": CANDIDATE_POLICY,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def pair_input_key(
    *,
    model: str,
    prompt_ref: str,
    prompt_sha: str,
    model_params: dict,
    item_a: dict,
    item_b: dict,
) -> str:
    """Fingerprint the actual model input for one directional pair call."""
    payload = {
        "model": model,
        "prompt_ref": prompt_ref,
        "prompt_sha": prompt_sha,
        "model_params": model_params,
        "a": {
            "statement": item_a["statement"],
            "task": item_a["body"],
            "answer": item_a["answer"],
        },
        "b": {
            "statement": item_b["statement"],
            "task": item_b["body"],
            "answer": item_b["answer"],
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _matching_verdicts(
    conn: psycopg.Connection,
    descriptors: list[tuple[tuple[str, str, float], str, str]],
) -> dict[tuple[str, str, str], str]:
    """Map exact pair-input identities to reusable verdict run items."""
    input_keys = sorted({input_key for _, _, input_key in descriptors})
    if not input_keys:
        return {}
    return {
        (task_a, task_b, input_key): run_item_id
        for task_a, task_b, input_key, run_item_id in conn.execute(
            "SELECT DISTINCT ON (task_a_id, task_b_id, input_key)"
            " task_a_id, task_b_id, input_key, run_item_id"
            " FROM kc_verdict WHERE input_key = ANY(%s)"
            " ORDER BY task_a_id, task_b_id, input_key,"
            " created_at DESC, run_item_id DESC",
            (input_keys,),
        ).fetchall()
    }


_BUILD_PARAM_KEYS = {
    "build_key",
    "candidate_count",
    "candidate_manifest_complete",
    "candidate_manifest_sha256",
    "statements_from",
    "embedding_run",
    "modality_runs",
    "knowledge_runs",
    "semantic_floor",
    "semantic_cap",
    "lexical_k",
}
_BENCH_MODEL_PARAM_KEYS = {
    "tools",
    "tool_choice",
    "parallel_tool_calls",
    "thinking",
    "reasoning_effort",
    "provider",
    "temperature",
}


def _historical_model_params(params: dict) -> dict:
    """Recover the ModelClient payload fields from a stamped judge run."""
    if isinstance(params.get("bench_params"), dict):
        bench = params["bench_params"]
        result = {
            key: bench[key] for key in _BENCH_MODEL_PARAM_KEYS if key in bench
        }
        result["max_tokens"] = params.get("max_tokens", DEFAULT_MAX_TOKENS)
        return result
    return {key: value for key, value in params.items() if key not in _BUILD_PARAM_KEYS}


def backfill_pair_input_keys(conn: psycopg.Connection) -> tuple[int, int]:
    """Replace migration placeholders with exact historical pair identities."""
    updated = skipped = 0
    runs = conn.execute(
        "SELECT id, model, prompt_ref, prompt_sha, params FROM run"
        " WHERE stage = 'kc-judge' ORDER BY started_at, id"
    ).fetchall()
    for run_id, model, prompt_ref, prompt_sha, params in runs:
        statement_runs = params.get("statements_from") or (
            [params["statement_run"]] if params.get("statement_run") else []
        )
        rows = conn.execute(
            "SELECT v.run_item_id, v.task_a_id, v.task_b_id"
            " FROM kc_verdict v JOIN run_item i ON i.id = v.run_item_id"
            " WHERE i.run_id = %s",
            (run_id,),
        ).fetchall()
        if not rows:
            continue
        if not statement_runs:
            skipped += len(rows)
            continue
        statements = fetch_usable_statements(conn, statement_runs)
        task_ids = sorted({task_id for _, task_a, task_b in rows for task_id in (task_a, task_b)})
        tasks = {task["id"]: task for task in fetch_tasks(conn, task_ids)}
        model_params = _historical_model_params(params)
        for run_item_id, task_a, task_b in rows:
            if task_a not in statements or task_b not in statements:
                skipped += 1
                continue
            item_a = {**tasks[task_a], "statement": statements[task_a]}
            item_b = {**tasks[task_b], "statement": statements[task_b]}
            input_key = pair_input_key(
                model=model,
                prompt_ref=prompt_ref,
                prompt_sha=prompt_sha,
                model_params=model_params,
                item_a=item_a,
                item_b=item_b,
            )
            conn.execute(
                "UPDATE kc_verdict SET input_key = %s WHERE run_item_id = %s",
                (input_key, run_item_id),
            )
            updated += 1
    conn.commit()
    return updated, skipped


def parse_verdicts(response: str) -> dict[str, str]:
    """Validate and normalize one ``record_verdicts`` argument object."""
    try:
        parsed = json.loads(response)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("unparseable verdict JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("verdict result is not an object")

    result = {}
    for direction in ("a_to_b", "b_to_a"):
        verdict_key = f"verdict_{direction}"
        reason_key = f"reason_{direction}"
        verdict = parsed.get(verdict_key)
        reason = parsed.get(reason_key)
        if verdict not in VERDICTS:
            raise ValueError(f"invalid {verdict_key}: {verdict}")
        if not isinstance(reason, str) or not (reason := reason.strip()):
            raise ValueError(f"missing or empty {reason_key}")
        result[verdict_key] = verdict
        result[reason_key] = reason
    return result


def bm25_score(query_tokens, doc_tokens, all_docs, k1=1.2, b=0.75):
    """Score one tokenized document using the judge bench's BM25 formula."""
    n = len(all_docs)
    avg_len = sum(len(document) for document in all_docs) / n if n > 0 else 0
    doc_len = len(doc_tokens)
    score = 0.0
    for token in set(query_tokens):
        if token not in doc_tokens:
            continue
        tf = doc_tokens.count(token)
        df = sum(1 for document in all_docs if token in document)
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        score += idf * tf * (k1 + 1) / (
            tf + k1 * (1 - b + b * doc_len / avg_len)
        )
    return score


def generate_candidates(
    items: list[dict],
    similarities: Mapping[tuple[str, str], float],
    already_judged: Iterable[tuple[str, str]] = (),
    *,
    floor: float = CANDIDATE_POLICY["semantic_floor"],
    semantic_cap: int = CANDIDATE_POLICY["semantic_cap"],
    lexical_k: int = CANDIDATE_POLICY["lexical_k"],
) -> list[tuple[str, str, float]]:
    """Return the normalized semantic/BM25 union after axis filtering."""
    ordered = sorted(items, key=lambda item: item["id"])
    by_id = {item["id"]: item for item in ordered}
    ids = [item["id"] for item in ordered]

    normalized_similarities = {
        tuple(sorted(pair)): float(similarity)
        for pair, similarity in similarities.items()
        if pair[0] != pair[1] and similarity is not None
    }
    judged = {tuple(sorted(pair)) for pair in already_judged}
    proposed: set[tuple[str, str]] = set()

    for task_id in ids:
        neighbors = [
            (other_id, normalized_similarities.get(tuple(sorted((task_id, other_id))), 0.0))
            for other_id in ids
            if other_id != task_id
        ]
        neighbors = [neighbor for neighbor in neighbors if neighbor[1] >= floor]
        neighbors.sort(key=lambda neighbor: (-neighbor[1], neighbor[0]))
        proposed.update(
            tuple(sorted((task_id, other_id)))
            for other_id, _ in neighbors[:semantic_cap]
        )

    tokens = [
        re.findall(r"[a-z0-9_]+", item["statement"].lower()) for item in ordered
    ]
    if lexical_k:
        for index, task_id in enumerate(ids):
            scores = [
                (bm25_score(tokens[index], tokens[other], tokens), ids[other])
                for other in range(len(ids))
                if other != index
            ]
            # Equal BM25 scores prefer the later document in corpus order.
            # Keep this deterministic for rebuilds.
            scores.sort(reverse=True)
            proposed.update(
                tuple(sorted((task_id, other_id)))
                for _, other_id in scores[:lexical_k]
            )

    candidates = []
    for task_a, task_b in proposed:
        a, b = by_id[task_a], by_id[task_b]
        if a["modality"] != b["modality"] or a["knowledge"] != b["knowledge"]:
            continue
        if (task_a, task_b) in judged:
            continue
        similarity = round(normalized_similarities.get((task_a, task_b), 0.0), 4)
        candidates.append((task_a, task_b, similarity))
    return sorted(candidates, key=lambda candidate: (-candidate[2], candidate[0], candidate[1]))


def fetch_usable_axis_verdicts(
    conn: psycopg.Connection,
    run_ids: list[str],
    parser: Callable[[dict], dict | str],
) -> dict[str, str]:
    """Newest usable axis verdict per task across the named runs."""
    rows = conn.execute(
        "SELECT i.id, i.task_id, i.response, i.error"
        " FROM run_item i JOIN run r ON r.id = i.run_id"
        " WHERE r.id = ANY(%s)"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (run_ids,),
    ).fetchall()
    verdicts: dict[str, str] = {}
    for item_id, task_id, response, error in rows:
        if task_id is None:
            raise SystemExit(f"{item_id} is not about a task")
        parsed = parser({"response": response, "error": error})
        if task_id not in verdicts and isinstance(parsed, dict):
            verdict = parsed.get("verdict")
            if isinstance(verdict, str):
                verdicts[task_id] = verdict
    return verdicts


def _run_task_ids(conn: psycopg.Connection, run_ids: list[str]) -> set[str]:
    """All task ids represented by items in the named runs."""
    return {
        task_id
        for task_id, in conn.execute(
            "SELECT DISTINCT task_id FROM run_item WHERE run_id = ANY(%s)",
            (run_ids,),
        ).fetchall()
        if task_id is not None
    }


def _usable_value(run_id: str, task_id: str, result, key: str):
    if not isinstance(result, dict) or key not in result:
        raise SystemExit(
            f"{task_id} has no usable {key} in {run_id}; silence is not a verdict"
        )
    return result[key]


def judged_pairs(
    conn: psycopg.Connection,
    judge_model: str,
    judge_prompt: str,
    build_key: str | None = None,
) -> set[tuple[str, str]]:
    """Pairs this judge generation has already answered.

    A pair is judged once per (model, prompt version); a different
    generation judging the same pair is a new verdict beside the old one
    (migration 0010), so only the current generation's verdicts suppress
    candidates.
    """
    if build_key is not None:
        query = (
            "SELECT task_a_id, task_b_id FROM kc_verdict WHERE build_key = %s"
        )
        params = (build_key,)
    else:
        query = (
            "SELECT task_a_id, task_b_id FROM kc_verdict"
            " WHERE judge_model = %s AND judge_prompt = %s"
        )
        params = (judge_model, judge_prompt)
    return {
        (task_a, task_b)
        for task_a, task_b in conn.execute(query, params).fetchall()
    }


def fetch_candidate_data(
    conn: psycopg.Connection,
    statement_runs: list[str],
    embedding_run: str,
    modality_runs: list[str],
    knowledge_runs: list[str],
    judge_model: str,
    judge_prompt: str,
    *,
    build_key: str | None = None,
    include_judged: bool = False,
) -> tuple[list[dict], dict[tuple[str, str], float], set[tuple[str, str]]]:
    """Read and validate the four stamped interpretations used by candidates."""
    run_stages = [(embedding_run, "task-embedding")]
    run_stages.extend((run_id, "task-modality") for run_id in modality_runs)
    run_stages.extend((run_id, "task-knowledge") for run_id in knowledge_runs)
    for run_id, expected in run_stages:
        actual = harness.fetch_run(conn, run_id)["stage"]
        if actual != expected:
            raise SystemExit(f"{run_id} is a {actual} run, not {expected}")

    statements = fetch_usable_statements(conn, statement_runs)
    modalities = fetch_usable_axis_verdicts(conn, modality_runs, modality_of)
    knowledge = fetch_usable_axis_verdicts(conn, knowledge_runs, knowledge_of)
    embedding_task_ids = {
        row[0]
        for row in conn.execute(
            "SELECT e.task_id FROM task_embedding e"
            " JOIN run_item i ON i.id = e.run_item_id"
            " WHERE i.run_id = %s",
            (embedding_run,),
        ).fetchall()
    }
    task_ids = embedding_task_ids
    statement_run_label = ", ".join(statement_runs)
    modality_run_label = ", ".join(modality_runs)
    knowledge_run_label = ", ".join(knowledge_runs)
    statement_ids = set(statements)
    if statement_ids != task_ids:
        missing = sorted(task_ids - statement_ids)
        extra = sorted(statement_ids - task_ids)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"extra {', '.join(extra)}")
        raise SystemExit(
            f"{statement_run_label} task mismatch: {'; '.join(details)}"
        )
    inputs = {
        modality_run_label: _run_task_ids(conn, modality_runs),
        knowledge_run_label: _run_task_ids(conn, knowledge_runs),
    }
    for run_id, actual_ids in inputs.items():
        missing = sorted(task_ids - actual_ids)
        if missing:
            raise SystemExit(f"{run_id} task mismatch: missing {', '.join(missing)}")

    tasks = {
        task["id"]: task
        for task in resolve_statement_tasks(
            conn, statement_runs, task_ids=sorted(task_ids)
        )
    }
    items = []
    for task_id in sorted(task_ids):
        if task_id not in modalities:
            _usable_value(modality_run_label, task_id, None, "verdict")
        if task_id not in knowledge:
            _usable_value(knowledge_run_label, task_id, None, "verdict")
        task = tasks[task_id]
        items.append(
            {
                "id": task_id,
                "statement": statements[task_id],
                "modality": modalities[task_id],
                "knowledge": knowledge[task_id],
                "body": task["body"],
                "answer": task["answer"],
            }
        )

    rows = conn.execute(
        "SELECT a.task_id, b.task_id,"
        " (1 - (a.embedding <=> b.embedding))::float"
        " FROM task_embedding a"
        " JOIN run_item ia ON ia.id = a.run_item_id"
        " JOIN task_embedding b ON b.task_id > a.task_id"
        " JOIN run_item ib ON ib.id = b.run_item_id"
        " WHERE ia.run_id = %s AND ib.run_id = %s",
        (embedding_run, embedding_run),
    ).fetchall()
    similarities = {
        (task_a, task_b): similarity
        for task_a, task_b, similarity in rows
        if similarity is not None
    }
    judged = set()
    if not include_judged:
        judged = {
            (task_a, task_b)
            for task_a, task_b in judged_pairs(
                conn, judge_model, judge_prompt, build_key
            )
            if task_a in task_ids and task_b in task_ids
        }
    return items, similarities, judged


def run_judge(
    conn: psycopg.Connection,
    statement_runs: list[str],
    embedding_run: str,
    modality_runs: list[str],
    knowledge_runs: list[str],
    client,
    *,
    workers: int = DEFAULT_WORKERS,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Generate candidates, call the injected client, and write the ledger."""
    supervisor = pipeline_lease.current_supervisor(required=True)
    prompt = harness.load_prompt(STAGE, PROMPT_VERSION, require_body=False)
    build_key = universe_build_key(
        model=client.model,
        prompt_ref=prompt.ref,
        prompt_sha=prompt.sha,
        model_params=getattr(client, "params", {}),
        statement_runs=statement_runs,
        embedding_run=embedding_run,
        modality_runs=modality_runs,
        knowledge_runs=knowledge_runs,
    )
    items, similarities, _ = fetch_candidate_data(
        conn,
        statement_runs,
        embedding_run,
        modality_runs,
        knowledge_runs,
        client.model,
        prompt.ref,
        build_key=build_key,
        include_judged=True,
    )
    by_id = {item["id"]: item for item in items}
    descriptors = []
    for candidate in generate_candidates(items, similarities):
        task_a, task_b, _ = candidate
        a, b = by_id[task_a], by_id[task_b]
        text = prompt.render_fields(
            {
                "a_statement": a["statement"],
                "a_task": a["body"],
                "a_answer": a["answer"],
                "b_statement": b["statement"],
                "b_task": b["body"],
                "b_answer": b["answer"],
            }
        )
        input_key = pair_input_key(
            model=client.model,
            prompt_ref=prompt.ref,
            prompt_sha=prompt.sha,
            model_params=getattr(client, "params", {}),
            item_a=a,
            item_b=b,
        )
        descriptors.append((candidate, text, input_key))

    matched = _matching_verdicts(conn, descriptors)
    descriptor_keys = {
        (candidate[0], candidate[1], input_key)
        for candidate, _, input_key in descriptors
    }
    # Multiple corpora may render byte-identical task pairs and therefore
    # share an input key. The lookup intentionally returns durable rows for
    # every matching input, but this run's reuse metric counts only its own
    # exact pair descriptors.
    reused_count = sum(key in matched for key in descriptor_keys)
    pending = [
        (index, descriptor)
        for index, descriptor in enumerate(descriptors, 1)
        if (descriptor[0][0], descriptor[0][1], descriptor[2]) not in matched
    ]
    if limit is not None:
        pending = pending[:limit]
    candidates = [candidate for _, (candidate, _, _) in pending]
    if dry_run:
        return {
            "run_id": None,
            "status": "dry-run",
            "candidates": candidates,
            "reused": reused_count,
        }

    params = {
        **getattr(client, "params", {}),
        "statements_from": statement_runs,
        "embedding_run": embedding_run,
        "modality_runs": modality_runs,
        "knowledge_runs": knowledge_runs,
        **CANDIDATE_POLICY,
        "build_key": build_key,
    }
    run_id = harness.claim_run(
        conn, STAGE, client.model, prompt.ref, prompt.sha, params
    )

    def call(work):
        index, candidate, text, input_key = work
        usage = None
        duration_ms = None
        try:
            if supervisor is not None:
                supervisor.before_provider_call()
            response, usage, duration_ms = client.complete(text)
            parsed = parse_verdicts(response)
            return index, candidate, input_key, response, usage, duration_ms, parsed, None
        except pipeline_lease.LeaseLost:
            raise
        except Exception as exc:
            return (
                index,
                candidate,
                input_key,
                None,
                usage if usage is not None else getattr(exc, "usage", None),
                (
                    duration_ms
                    if duration_ms is not None
                    else getattr(exc, "duration_ms", None)
                ),
                None,
                f"{type(exc).__name__}: {exc}",
            )

    work = [
        (index, candidate, text, input_key)
        for index, (candidate, text, input_key) in pending
    ]
    ok = failed = 0
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(work) or 1))) as pool:
        futures = [pool.submit(call, item) for item in work]
        for future in as_completed(futures):
            (
                index,
                candidate,
                input_key,
                response,
                usage,
                duration_ms,
                parsed,
                error,
            ) = future.result()
            task_a, task_b, _ = candidate
            item_id = f"{run_id}-{index:04d}"
            if supervisor is not None:
                supervisor.fence(conn)
            conn.execute(
                "INSERT INTO run_item"
                " (id, run_id, artifact_id, task_id, response, usage, duration_ms, error)"
                " VALUES (%s, %s, NULL, %s, %s, %s, %s, %s)",
                (
                    item_id,
                    run_id,
                    task_a,
                    response,
                    Jsonb(usage) if usage is not None else None,
                    duration_ms,
                    error,
                ),
            )
            if error:
                failed += 1
                print(f"  {task_a} / {task_b}: {error}", file=sys.stderr)
            else:
                conn.execute(
                    "INSERT INTO kc_verdict"
                    " (run_item_id, task_a_id, task_b_id, a_implies_b, b_implies_a,"
                    "  judge_model, judge_prompt, build_key, input_key)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        item_id,
                        task_a,
                        task_b,
                        parsed["verdict_a_to_b"],
                        parsed["verdict_b_to_a"],
                        client.model,
                        prompt.ref,
                        build_key,
                        input_key,
                    ),
                )
                ok += 1
            conn.commit()

    status = "done" if failed == 0 else "failed"
    candidate_manifest_complete = False
    selected_items: list[str] = []
    if status == "done":
        # Verdicts from earlier attempts are reusable facts. This attempt may
        # certify their union only after every candidate in the exact build
        # resolves to a durable verdict item.
        matched = _matching_verdicts(conn, descriptors)
        maybe_selected = [
            matched.get((candidate[0], candidate[1], input_key))
            for candidate, _, input_key in descriptors
        ]
        candidate_manifest_complete = all(maybe_selected)
        if candidate_manifest_complete:
            selected_items = [item_id for item_id in maybe_selected if item_id]
    if supervisor is not None:
        supervisor.fence(conn)
    completion = None
    if candidate_manifest_complete:
        manifest = judge_manifest.certify(
            conn,
            judge_run_id=run_id,
            run_item_ids=selected_items,
        )
        completion = {
            "candidate_manifest_complete": True,
            "candidate_count": manifest.count,
            "candidate_manifest_sha256": manifest.sha256,
        }
    if completion is None:
        conn.execute(
            "UPDATE run SET status = %s, finished_at = now() WHERE id = %s",
            (status, run_id),
        )
    else:
        conn.execute(
            "UPDATE run SET status = %s, finished_at = now(),"
            " params = params || %s WHERE id = %s",
            (status, Jsonb(completion), run_id),
        )
    conn.commit()
    # Grouping is a separate stage with its own lease. The judge records only
    # verdict facts and, when warranted, the complete-manifest certificate.
    return {
        "run_id": run_id,
        "status": status,
        "ok": ok,
        "failed": failed,
        "candidates": candidates,
        "candidate_count": len(descriptors),
        "candidate_manifest_complete": candidate_manifest_complete,
        "reused": reused_count,
        "build_key": build_key,
    }


# ``execute`` mirrors the naming used by the generic harness while the more
# explicit public name reads better at call sites.
execute = run_judge


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.kc_judge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="judge all not-yet-recorded candidate pairs")
    run.add_argument(
        "--statements-from",
        required=True,
        type=harness.id_list,
        help="comma-separated kc-statement run ids",
    )
    run.add_argument("--embedding-run", required=True)
    run.add_argument(
        "--modality-run",
        dest="modality_runs",
        required=True,
        type=harness.id_list,
        help="comma-separated task-modality run ids",
    )
    run.add_argument(
        "--knowledge-run",
        dest="knowledge_runs",
        required=True,
        type=harness.id_list,
        help="comma-separated task-knowledge run ids",
    )
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--workers", type=harness.positive_int, default=DEFAULT_WORKERS)
    run.add_argument("--limit", type=harness.positive_int)
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_run)
    sub.add_parser(
        "backfill-input-keys",
        help="derive exact reusable pair identities for historical verdicts",
    ).set_defaults(func=cmd_backfill_input_keys)
    return parser


def cmd_run(args: argparse.Namespace) -> None:
    with connect() as conn:
        if args.dry_run:
            class DryClient:
                model = args.model
                params = {}

            summary = run_judge(
                conn,
                args.statements_from,
                args.embedding_run,
                args.modality_runs,
                args.knowledge_runs,
                DryClient(),
                workers=args.workers,
                limit=args.limit,
                dry_run=True,
            )
            print(f"{len(summary['candidates'])} candidate pair(s); no calls made")
            return

        extra = dict(DEFAULT_EXTRA)
        # The tool payload comes last: it replaces DEFAULT_EXTRA's bench-time
        # auto choice with a forced record_verdicts call.
        extra.update(harness.load_tool(str(TOOL_PATH)))
        client = ModelClient(args.model, extra=extra, max_tokens=DEFAULT_MAX_TOKENS)
        summary = run_judge(
            conn,
            args.statements_from,
            args.embedding_run,
            args.modality_runs,
            args.knowledge_runs,
            client,
            workers=args.workers,
            limit=args.limit,
        )
    print(
        f"{summary['run_id']} {summary['status']}:"
        f" {summary['ok']} verdict(s), {summary['failed']} failed"
    )


def cmd_backfill_input_keys(args: argparse.Namespace) -> None:
    del args
    with connect() as conn:
        updated, skipped = backfill_pair_input_keys(conn)
    print(f"{updated} verdict input key(s) backfilled; {skipped} skipped")


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
