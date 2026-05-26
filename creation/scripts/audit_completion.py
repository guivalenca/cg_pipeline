from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
CG_PIPELINE_ROOT = REPO_ROOT / "cg_pipeline"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Concept Graph Creation prototype completion evidence.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=CG_PIPELINE_ROOT / "runs" / "prototype-smoke",
        help="Named run directory to audit.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON file to write the audit payload.")
    args = parser.parse_args()

    checks: list[tuple[str, bool, str]] = []

    checks.append(("creation_root_exists", PROJECT_ROOT.is_dir(), str(PROJECT_ROOT)))
    checks.append(("pytest_config_exists", (PROJECT_ROOT / "pyproject.toml").is_file(), "pyproject.toml"))
    checks.append(("source_package_exists", (PROJECT_ROOT / "src/concept_graph_creation").is_dir(), "src/"))
    checks.append(("tests_exist", any((PROJECT_ROOT / "tests").glob("test_*.py")), "tests/test_*.py"))

    run_dir = args.run_dir
    source_ledger = _load_json(run_dir / "source_ledger.json")
    workbook_labels = _load_json(run_dir / "workbook_label_interpretation.json")
    run_summary = _load_json(run_dir / "run_summary.json")
    validation_failure = run_dir / "validation_failure_demo.txt"

    checks.append(("run_dir_exists", run_dir.is_dir(), str(run_dir)))
    checks.append(("lesson_dir_exists", (run_dir / "lessons").is_dir(), str(run_dir / "lessons")))
    checks.append(("critics_dir_exists", (run_dir / "critics").is_dir(), str(run_dir / "critics")))
    checks.append(("repairs_dir_exists", (run_dir / "repairs").is_dir(), str(run_dir / "repairs")))
    checks.append(("source_ledger_exists", source_ledger is not None, str(run_dir / "source_ledger.json")))
    checks.append(
        (
            "source_ledger_reads_real_inputs",
            bool(
                source_ledger
                and source_ledger.get("inputs", {}).get("workbook_path") == "source/si_mod6.xlsx"
                and source_ledger.get("inputs", {}).get("index_path") == "index.json"
                and source_ledger.get("inputs", {}).get("extraction_dir") == "extraction"
            ),
            "source_ledger.inputs",
        )
    )
    checks.append(
        (
            "source_ledger_expected_counts",
            bool(
                source_ledger
                and source_ledger.get("summary", {}).get("lesson_count") == 13
                and source_ledger.get("summary", {}).get("self_study_count") == 69
                and source_ledger.get("summary", {}).get("available_count") == 67
                and source_ledger.get("summary", {}).get("unavailable_count") == 2
            ),
            "source_ledger.summary",
        )
    )
    checks.append(
        (
            "workbook_label_artifact_exists",
            workbook_labels is not None,
            str(run_dir / "workbook_label_interpretation.json"),
        )
    )
    checks.append(
        (
            "workbook_label_expected_outputs",
            bool(
                workbook_labels
                and workbook_labels.get("summary", {}).get("unique_label_count") == 58
                and isinstance(workbook_labels.get("active_outputs", {}).get("prerequisite_hints"), list)
                and isinstance(workbook_labels.get("active_outputs", {}).get("lesson_clusters"), list)
                and isinstance(workbook_labels.get("audit_only", {}).get("application_adjacent_signals"), list)
                and isinstance(workbook_labels.get("ignored_ambiguous"), list)
            ),
            "workbook_label_interpretation active/audit/ignored outputs",
        )
    )
    checks.append(("run_summary_exists", run_summary is not None, str(run_dir / "run_summary.json")))
    checks.append(
        (
            "validation_failure_is_clear",
            validation_failure.is_file()
            and validation_failure.read_text(encoding="utf-8").startswith(
                "Stage 'validation_failure_demo' failed Stage Contract:"
            ),
            str(validation_failure),
        )
    )

    payload = {
        "ok": all(ok for _, ok, _ in checks),
        "project_root": str(PROJECT_ROOT),
        "run_dir": str(run_dir),
        "checks": [
            {
                "name": name,
                "ok": ok,
                "evidence": evidence,
            }
            for name, ok, evidence in checks
        ],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
