"""Build and execute the four-source Flash-low pipeline benchmark notebook."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks/pipeline-flash-benchmark-v001.ipynb"


def main() -> None:
    notebook = nbformat.read(OUT, as_version=4)
    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            """# Flash-low pipeline benchmark

## Objective

Test whether Flash-low can replace Pro-high in seven existing pipeline stages without materially reducing quality. The four production sources and stored Pro-high outputs are frozen as references; all Flash calls live in a dedicated shadow database.

Success requires more than low cost: outputs must remain parseable by the current pipeline, stable across two repetitions, and at least approximately equivalent under blinded semantic review."""
        ),
        nbformat.v4.new_code_cell(
            """from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd()
if not (ROOT / "evals").exists():
    ROOT = ROOT.parent

BENCH = json.loads((ROOT / "evals/pipeline-flash-benchmark-v001.json").read_text())
SUMMARY = json.loads((ROOT / "evals/pipeline-flash-review-v001/summary.json").read_text())
REVIEWS = json.loads((ROOT / "evals/pipeline-flash-review-v001/results.json").read_text())

len(BENCH["cases"]), len(BENCH["trials"]), REVIEWS["review_count"]"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Method

- 56 frozen cases: two per source in each of seven Pro-high stages.
- 112 real Flash-low calls: two independent repetitions per case.
- Stored Pro outputs were not regenerated and were not treated as infallible gold.
- Three subagents reviewed 83 blinded A/B comparisons. A/B order was randomized per case.
- Mechanical checks cover API failures, pipeline usability, verdict agreement, repetition stability, and observed OpenRouter cost.
- Semantic results are a targeted four-source benchmark, not evidence of domain-general equivalence."""
        ),
        nbformat.v4.new_code_cell(
            """rows = []
for stage, metric in SUMMARY["stages"].items():
    winners = REVIEWS["stages"][stage]["consensus_winners"]
    rows.append({
        "stage": stage,
        "cases": metric["cases"],
        "pro_cost": metric["reference_cost"],
        "flash_cost": metric["flash_cost"]["1"],
        "cost_reduction": 1 - metric["flash_single_cost_ratio"],
        "flash_1_usable": metric["flash_1_usable"],
        "flash_2_usable": metric["flash_2_usable"],
        "pro_wins": winners.get("pro", 0),
        "flash_wins": winners.get("flash", 0),
        "ties": winners.get("tie", 0),
    })
stage_df = pd.DataFrame(rows).sort_values("stage").reset_index(drop=True)
display(stage_df.style.format({
    "pro_cost": "${:.4f}", "flash_cost": "${:.4f}", "cost_reduction": "{:.1%}"
}))"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Cost and contract validity

One Flash repetition cost about 12% of the selected Pro references overall. The savings are substantial, but a cheap response that the pipeline cannot materialize is not a usable replacement. The second panel therefore shows the stricter contract-validity check."""
        ),
        nbformat.v4.new_code_cell(
            """plot_df = stage_df.set_index("stage")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
(plot_df[["pro_cost", "flash_cost"]]
 .plot(kind="bar", ax=axes[0], color=["#38598b", "#e59f3a"]))
axes[0].set_title("Observed cost for the same 8 cases")
axes[0].set_ylabel("USD")
axes[0].set_xlabel("")
axes[0].legend(["Stored Pro-high", "Flash-low trial 1"])

valid = plot_df[["flash_1_usable", "flash_2_usable"]] / 8
valid.plot(kind="bar", ax=axes[1], color=["#e59f3a", "#f4c16d"])
axes[1].set_title("Flash outputs usable by the current parser")
axes[1].set_ylabel("Share usable")
axes[1].set_ylim(0, 1.05)
axes[1].set_xlabel("")
axes[1].legend(["Trial 1", "Trial 2"])
plt.tight_layout()
plt.show()"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Blinded semantic review

Consensus is conservative: directional majority wins; conflicting directional votes remain ties. Pro dominated `kc-statement`, `task-granularity`, and `task-revision`. `task-knowledge` and `task-triage` were all ties. Generation was mixed and evaluator-dependent rather than demonstrably equivalent."""
        ),
        nbformat.v4.new_code_cell(
            """review_rows = []
for stage, result in REVIEWS["stages"].items():
    winners = result["consensus_winners"]
    review_rows.append({
        "stage": stage,
        "Pro-high": winners.get("pro", 0),
        "Tie": winners.get("tie", 0),
        "Flash-low": winners.get("flash", 0),
    })
review_df = pd.DataFrame(review_rows).set_index("stage")
review_df[["Pro-high", "Tie", "Flash-low"]].plot(
    kind="barh", stacked=True, figsize=(10, 6),
    color=["#38598b", "#b8bec9", "#e59f3a"]
)
plt.title("Blinded consensus winner by case")
plt.xlabel("Cases (8 per stage)")
plt.ylabel("")
plt.xlim(0, 8)
plt.tight_layout()
plt.show()
display(review_df)"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Decision readout

- **Strongest candidates for a later default change:** `task-knowledge` and `task-triage`. Both were 8/8 usable in both trials, 8/8 internally stable by verdict, and semantically tied with Pro in every reviewed case.
- **Promising but not yet clean:** `task-substance`. Outputs were usable and mostly equivalent, but verdict stability fell to 6/8 and one trial diverged more often from the reference.
- **Inconclusive:** `task-generation`. All responses were structurally valid and much cheaper, but task counts varied and blind reviewers split on coverage, redundancy, and factual quality.
- **Do not switch on this evidence:** `task-granularity`, `task-revision`, and `kc-statement`. They showed missing required fields and/or material quality losses. The second statement trial produced 0/8 usable outputs.

No additional default was changed by this experiment."""
        ),
        nbformat.v4.new_code_cell(
            """assert len(BENCH["cases"]) == 56
assert len(BENCH["trials"]) == 112
assert not any(trial["error"] for trial in BENCH["trials"])
assert BENCH["isolation"]["production_database_written"] is False
assert all(metric["reference_usable"] == 8 for metric in SUMMARY["stages"].values())
assert REVIEWS["case_count"] == 56
print("Integrity checks passed: isolated 56-case corpus, 112 successful calls, 83 blinded reviews.")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Next step

Keep all non-judge pipeline defaults unchanged for now. If a second experiment is worthwhile, focus spend on cross-domain cases for `task-knowledge` and `task-triage`; separately test a contract-enforced Flash configuration for stages whose optional tool fields were omitted. Do not pool these into one global “Flash replaces Pro” decision."""
        ),
    ]
    notebook.metadata.setdefault("kernelspec", {"display_name": "Python 3", "language": "python", "name": "python3"})
    client = NotebookClient(notebook, timeout=180, kernel_name="python3")
    client.execute(cwd=ROOT)
    nbformat.write(notebook, OUT)
    print(f"built and executed {OUT}")


if __name__ == "__main__":
    main()
