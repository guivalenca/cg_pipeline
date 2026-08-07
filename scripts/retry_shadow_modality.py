"""Retry only modality tasks still uncovered in the isolated regex experiment."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

from universe import defaults, report
from universe.db import connect
from universe.harness import execute, fetch_items, load_prompt, load_tool
from universe.ingest import MAX_TOKENS, PROVIDER, TOOLS, next_step
from universe.model_client import ModelClient
from universe.task_modality import build_targets, modality_of, select_tasks

from run_shadow_regex_pipeline import SOURCE_IDS, assert_isolated, current_run_ids


STAGE = "task-modality"


def option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


def task_args(argv: list[str]) -> SimpleNamespace:
    comma_list = option(argv, "--gen-runs")
    passages = option(argv, "--passages-from")
    return SimpleNamespace(
        gen_runs=comma_list.split(",") if comma_list else [],
        passages_from=passages.split(",") if passages else None,
        revision_run=option(argv, "--revision-run"),
        granularity_run=option(argv, "--granularity-run"),
        parts_revision_run=option(argv, "--parts-revision-run"),
        triage_run=option(argv, "--triage-run"),
        substance_run=option(argv, "--substance-run"),
    )


def usable_task_ids(source_id: str) -> set[str]:
    covered: set[str] = set()
    with connect() as conn:
        for run_id in current_run_ids(STAGE, source_id):
            for item in fetch_items(conn, run_id):
                if item["task_id"] and isinstance(modality_of(item), dict):
                    covered.add(item["task_id"])
    return covered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=SOURCE_IDS)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    assert_isolated()

    with connect() as conn:
        step = next_step(conn, args.source)
        if step["stage"] != STAGE:
            raise SystemExit(f"{args.source} is at {step['stage']}, not {STAGE}")
        refs = task_args(step["argv"])
        tasks = select_tasks(conn, refs)
        covered = usable_task_ids(args.source)
        missing = [task for task in tasks if task["id"] not in covered]
        if args.limit is not None:
            missing = missing[: args.limit]
        if not missing:
            raise SystemExit("no uncovered modality tasks")
        targets = build_targets(conn, missing)

        prompt = load_prompt(STAGE, "v003", require_body=False)
        extra = dict(load_tool(TOOLS[STAGE]))
        provider = {
            **PROVIDER,
            "order": [args.provider],
            "allow_fallbacks": False,
        }
        extra.update({"reasoning": {"enabled": False}, "provider": provider})
        client = ModelClient(
            defaults.STAGE_DEFAULTS[STAGE]["model"],
            max_tokens=int(MAX_TOKENS),
            extra=extra,
        )
        print(
            f"{len(missing)} uncovered task(s) via {args.provider};"
            f" {len(covered)}/{len(tasks)} already covered",
            flush=True,
        )
        summary = execute(
            conn,
            prompt,
            client,
            targets,
            workers=1,
            run_params={
                "gen_runs": refs.gen_runs,
                "passages_from": refs.passages_from,
                "revision_run": refs.revision_run,
                "granularity_run": refs.granularity_run,
                "parts_revision_run": refs.parts_revision_run,
                "triage_run": refs.triage_run,
                "substance_run": refs.substance_run,
                "research_retry_missing_only": True,
            },
        )
        items = fetch_items(conn, summary["run_id"])

    tally: dict[str, int] = {}
    for item in items:
        parsed = modality_of(item)
        label = parsed["verdict"] if isinstance(parsed, dict) else parsed
        tally[label] = tally.get(label, 0) + 1
    usage = report.aggregate_usage(items)
    print(
        f"{summary['run_id']} {summary['status']} {tally};"
        f" {report.format_usage(usage) or 'no usage reported'}",
        flush=True,
    )


if __name__ == "__main__":
    main()
