"""Provider-free contract tests for the live E2E safety helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest


MODULE_PATH = Path(__file__).parent / "live_e2e" / "test_source_publication_live.py"
SPEC = importlib.util.spec_from_file_location("_live_e2e_contract_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
LIVE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LIVE
SPEC.loader.exec_module(LIVE)


def test_image_locator_parser_covers_reference_markdown_and_raw_html() -> None:
    markdown = """\
![Inline](/api/source-assets/asset-inline)

![Reference][diagram]

[diagram]: /api/source-assets/asset-reference "Diagram"

<picture>
  <source srcset="/api/source-assets/asset-small 1x, /api/source-assets/asset-large 2x">
  <img src="/api/source-assets/asset-html">
</picture>
"""

    assert LIVE._image_locators(markdown) == (
        "/api/source-assets/asset-inline",
        "/api/source-assets/asset-reference",
        "/api/source-assets/asset-small",
        "/api/source-assets/asset-large",
        "/api/source-assets/asset-html",
    )


@pytest.mark.parametrize(
    "markdown",
    (
        "![Remote][diagram]\n\n[diagram]: https://cdn.example/diagram.png\n",
        '<img src="data:image/png;base64,AAAA">',
        (
            '<picture><source srcset="/api/source-assets/safe 1x, '
            'https://cdn.example/x.png 2x"></picture>'
        ),
    ),
)
def test_image_locator_validation_rejects_every_nonlocal_form(markdown: str) -> None:
    with pytest.raises(AssertionError, match="unsafe image locator"):
        LIVE._validated_asset_ids(markdown)


def test_usage_summary_counts_failed_fallback_and_unpriced_attempts() -> None:
    observations = [
        {
            "stage": "cleanup",
            "status": "succeeded",
            "attempt_count": 2,
            "usage": {
                "cost": "0.07",
                "attempts": [
                    {"status": "failed", "usage": {"cost": "0.02"}},
                    {"status": "succeeded", "usage": {"cost": "0.05"}},
                ],
            },
        },
        {
            "stage": "source_visual",
            "status": "failed",
            "attempt_count": 1,
            "usage": {"cost": "0.01"},
        },
        {
            "stage": "video_stt",
            "status": "failed",
            "attempt_count": 1,
            "usage": {},
        },
    ]

    assert LIVE._summarize_usage_observations(observations) == {
        "observable_attempts": 4,
        "priced_attempts": 3,
        "unpriced_attempts": 1,
        "observed_cost_usd": "0.08",
        "by_stage": {
            "cleanup": {
                "observable_attempts": 2,
                "priced_attempts": 2,
                "unpriced_attempts": 0,
                "observed_cost_usd": "0.07",
                "row_outcomes": {"succeeded": 1},
            },
            "source_visual": {
                "observable_attempts": 1,
                "priced_attempts": 1,
                "unpriced_attempts": 0,
                "observed_cost_usd": "0.01",
                "row_outcomes": {"failed": 1},
            },
            "video_stt": {
                "observable_attempts": 1,
                "priced_attempts": 0,
                "unpriced_attempts": 1,
                "observed_cost_usd": "0",
                "row_outcomes": {"failed": 1},
            },
        },
    }


def test_usage_summary_never_hides_prior_retries_behind_latest_cost() -> None:
    summary = LIVE._summarize_usage_observations(
        [
            {
                "stage": "pdf_figure",
                "status": "succeeded",
                "attempt_count": 3,
                "usage": {"cost": "0.02"},
            }
        ]
    )

    assert summary["observable_attempts"] == 3
    assert summary["priced_attempts"] == 1
    assert summary["unpriced_attempts"] == 2
    assert summary["observed_cost_usd"] == "0.02"


def test_usage_summary_does_not_invent_a_paid_attempt_for_skipped_visual_input() -> None:
    summary = LIVE._summarize_usage_observations(
        [
            {
                "stage": "source_visual",
                "status": "skipped",
                "attempt_count": 1,
                "usage": {},
            }
        ]
    )

    assert summary == {
        "observable_attempts": 0,
        "priced_attempts": 0,
        "unpriced_attempts": 0,
        "observed_cost_usd": "0",
        "by_stage": {},
    }


def test_terminal_work_summary_covers_every_runnable_child_queue() -> None:
    components = {
        "acquisition": {"running": 1},
        "image_candidates": {"downloaded": 2},
        "image_analysis": {"waiting": 1},
        "cleanup": {"queued": 1},
        "video_stt_chunks": {"running": 1},
        "pdf_document_parse": {"queued": 1},
        "pdf_page_analysis": {"running": 1},
        "pdf_figure_localization": {"queued": 1},
        "video_stt_attempts": {"failed": 3},
        "pdf_figure_regions": {"placed": 2},
    }

    assert LIVE._summarize_work_states(components) == {
        "components": components,
        "nonterminal": {
            "acquisition": {"running": 1},
            "image_candidates": {"downloaded": 2},
            "image_analysis": {"waiting": 1},
            "cleanup": {"queued": 1},
            "video_stt_chunks": {"running": 1},
            "pdf_document_parse": {"queued": 1},
            "pdf_page_analysis": {"running": 1},
            "pdf_figure_localization": {"queued": 1},
        },
        "nonterminal_count": 9,
    }


def test_quality_report_write_is_atomic_and_replaces_running_snapshot(tmp_path: Path) -> None:
    live = SimpleNamespace(evidence_dir=tmp_path)
    LIVE._write_report(live, {"status": "running", "cases": {}})
    LIVE._write_report(
        live,
        {"status": "failed", "cases": {"article": {"failure": "quality"}}},
    )

    assert not (tmp_path / "quality-report.json.tmp").exists()
    assert json.loads((tmp_path / "quality-report.json").read_text()) == {
        "status": "failed",
        "cases": {"article": {"failure": "quality"}},
    }


def test_quality_assertion_persists_failed_case_from_finally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live = SimpleNamespace(
        run_id="failure-report",
        database_name="unused",
        evidence_dir=tmp_path,
    )

    def fail_quality(_live: object) -> dict[str, object]:
        raise AssertionError("deliberate quality gate")

    monkeypatch.setattr(LIVE, "_accept_workbook", fail_quality)

    with pytest.raises(AssertionError, match="deliberate quality gate"):
        LIVE.test_bounded_live_source_publications(
            live,
            ("xlsx",),
            Decimal("0"),
        )

    report = json.loads((tmp_path / "quality-report.json").read_text())
    assert report["status"] == "failed"
    assert report["failed_case"] == "xlsx"
    assert report["cases"]["xlsx"]["status"] == "failed"
    assert report["cases"]["xlsx"]["failure"] == {
        "type": "AssertionError",
        "message": "deliberate quality gate",
    }
    assert report["cases"]["xlsx"]["wall_seconds"] >= 0


def test_failure_report_redacts_common_credential_shapes() -> None:
    summary = LIVE._safe_failure_summary(
        RuntimeError(
            "Authorization: Bearer bearer-secret api_key=plain-secret "
            "password: library-secret sk-openrouter-secret"
        )
    )

    assert "bearer-secret" not in summary["message"]
    assert "plain-secret" not in summary["message"]
    assert "library-secret" not in summary["message"]
    assert "sk-openrouter-secret" not in summary["message"]
