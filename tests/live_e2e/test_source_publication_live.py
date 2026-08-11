"""Bounded real-provider tracer from source evidence to canonical Markdown.

The hard gate lives in this directory's ``conftest.py``.  This tracer is
deliberately serial: it establishes one trustworthy publication per Adapter
before the separate concurrency/soak suite raises parallelism.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from markdown_it import MarkdownIt
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from universe.acquisition import videos
from universe.acquisition.manual_uploads import ManualAsset, create_manual_upload_job
from universe.acquisition.runner import enqueue_source, process_next_work_item
from universe.syllabus import import_workbook, parse_workbook

if TYPE_CHECKING:
    from .conftest import LiveRun


pytestmark = pytest.mark.live_e2e

WORKBOOK_SHA256 = "873b45e428304988f23446b20e0e58d3ed9edfb8cfb8ba50e9ebe22b81e18fc5"
PDF_SHA256 = "e22b6b7ea0d7e67151b1585ea3108a6eabcf76ccf6a03b69b29adbdbf4920f4f"

# Characterized, public logical Sources.  The PDF is immutable local evidence
# identified by hash and supplied explicitly through LIVE_E2E_PDF.
ARTICLE_URL = (
    "https://www.ibm.com/docs/pt-br/rsas/7.5.0?"
    "topic=topologies-deployment-diagrams"
)
VIDEO_ID = "UFtXy0KRxVI"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
BOOK_RESOURCE_CODE = "9788522128303"
BOOK_SCOPE = "198-205"

# These alternatives are asserted to remain present in the authorized CC07
# workbook.  They are useful for a later corpus-expansion tracer after the
# characterized vertical slices below pass.
WORKBOOK_NATIVE_ARTICLE = "https://www.lucidchart.com/pages/uml-deployment-diagram"
WORKBOOK_NATIVE_PDF = "https://theodpbook.lcc.uma.es/docs/Chapter1.pdf"
WORKBOOK_NATIVE_VIDEO_ID = "vmvSMYaV4oE"
WORKBOOK_NATIVE_BOOK = ("9788577800643", "pages", "66-72")

UNSAFE_MARKDOWN = (
    re.compile(r"video-frame://", re.I),
    re.compile(r"(?:/private/tmp/|/var/folders/)", re.I),
)
ASSET_LINK = re.compile(r"/api/source-assets/([a-zA-Z0-9._:-]+)")
LOCAL_ASSET_LOCATOR = re.compile(
    r"^/api/source-assets/(?P<asset_id>[a-zA-Z0-9][a-zA-Z0-9._:-]*)$"
)
MARKDOWN_PARSER = MarkdownIt("commonmark", {"html": True})


@dataclass(frozen=True)
class CaseBudget:
    openrouter_usd: Decimal
    timeout_seconds: int
    firecrawl_credits: int | None = None


BUDGETS = {
    "article": CaseBudget(Decimal("0.12"), 25 * 60),
    "pdf": CaseBudget(Decimal("0.15"), 40 * 60, firecrawl_credits=32),
    "video": CaseBudget(Decimal("0.12"), 30 * 60),
    "book": CaseBudget(Decimal("0.20"), 60 * 60, firecrawl_credits=16),
}

NONTERMINAL_STATUSES = {
    "acquisition": frozenset({"queued", "running"}),
    "image_candidates": frozenset({"queued", "running", "downloaded"}),
    "image_analysis": frozenset({"waiting", "queued", "running"}),
    "cleanup": frozenset({"queued", "running"}),
    "video_stt_chunks": frozenset({"queued", "running"}),
    "pdf_document_parse": frozenset({"queued", "running"}),
    "pdf_page_analysis": frozenset({"queued", "running"}),
    "pdf_figure_localization": frozenset({"queued", "running"}),
}


def _summarize_work_states(
    components: dict[str, dict[str, int]],
) -> dict[str, Any]:
    nonterminal = {
        component: {
            status: count
            for status, count in components.get(component, {}).items()
            if status in statuses and count
        }
        for component, statuses in NONTERMINAL_STATUSES.items()
    }
    nonterminal = {key: value for key, value in nonterminal.items() if value}
    return {
        "components": components,
        "nonterminal": nonterminal,
        "nonterminal_count": sum(
            count for states in nonterminal.values() for count in states.values()
        ),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_path(name: str, expected_sha256: str) -> Path:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.fail(f"{name} must name the explicit immutable live fixture")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        pytest.fail(f"{name} does not identify a file: {path}")
    actual = _sha256(path)
    if actual != expected_sha256:
        pytest.fail(
            f"{name} SHA-256 changed: expected {expected_sha256}, observed {actual}"
        )
    return path


def _srcset_locators(value: str) -> tuple[str, ...]:
    """Return URL candidates from an HTML srcset.

    Canonical publications only permit simple same-origin asset URLs. A comma
    inside a data URL may therefore split into multiple invalid candidates,
    which is intentionally fail-closed when the locators are validated.
    """
    return tuple(
        part.strip().split(maxsplit=1)[0]
        for part in value.split(",")
        if part.strip()
    )


class _HtmlImageLocatorParser(HTMLParser):
    """Collect image-bearing raw-HTML attributes without rendering HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.locators: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {name.casefold(): value for name, value in attrs if value is not None}
        normalized_tag = tag.casefold()
        if normalized_tag == "img":
            self._append(values.get("src"))
            self._append_srcset(values.get("srcset"))
        elif normalized_tag == "source":
            self._append_srcset(values.get("srcset"))
        elif normalized_tag == "image":
            self._append(values.get("href") or values.get("xlink:href"))
        elif normalized_tag == "input" and values.get("type", "").casefold() == "image":
            self._append(values.get("src"))
        elif normalized_tag == "video":
            self._append(values.get("poster"))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)

    def _append(self, value: str | None) -> None:
        if value and value.strip():
            self.locators.append(value.strip())

    def _append_srcset(self, value: str | None) -> None:
        if value:
            self.locators.extend(_srcset_locators(value))


def _image_locators(markdown: str) -> tuple[str, ...]:
    """Resolve inline/reference Markdown images and image-bearing raw HTML."""
    locators: list[str] = []
    for token in MARKDOWN_PARSER.parse(markdown):
        candidates = [token, *(token.children or [])]
        for candidate in candidates:
            if candidate.type == "image":
                source = candidate.attrGet("src")
                if source:
                    locators.append(source.strip())
            elif candidate.type in {"html_block", "html_inline"}:
                parser = _HtmlImageLocatorParser()
                parser.feed(candidate.content)
                parser.close()
                locators.extend(parser.locators)
    return tuple(locators)


def _validated_asset_ids(markdown: str) -> set[str]:
    """Fail closed unless every rendered image resolves through local assets."""
    asset_ids = set(ASSET_LINK.findall(markdown))
    for locator in _image_locators(markdown):
        match = LOCAL_ASSET_LOCATOR.fullmatch(locator)
        assert match is not None, f"unsafe image locator: {locator}"
        asset_ids.add(match.group("asset_id"))
    return asset_ids


def _seed_source(
    live: LiveRun, source_id: str, *, identity: dict[str, Any], title: str, media_type: str
) -> str:
    live.conn.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, %s)",
        (source_id, Jsonb(identity), title, media_type),
    )
    live.conn.commit()
    return source_id


def _latest_acquisition(live: LiveRun, source_id: str) -> dict[str, Any] | None:
    row = live.conn.execute(
        "SELECT id, status, attempt_count, artifact_id, failure_code, diagnostics"
        " FROM acquisition_job WHERE source_id = %s"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(
        zip(
            ("id", "status", "attempt_count", "artifact_id", "failure_code", "diagnostics"),
            row,
        )
    )


def _latest_cleanup(live: LiveRun, source_id: str) -> dict[str, Any] | None:
    row = live.conn.execute(
        "SELECT c.id, c.status, c.canonical_artifact_id, c.failure_code, c.diagnostics"
        " FROM source_cleanup_job c"
        " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
        " WHERE j.source_id = %s ORDER BY c.created_at DESC, c.id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(
        zip(
            ("id", "status", "canonical_artifact_id", "failure_code", "diagnostics"),
            row,
        )
    )


def _work_state_report(live: LiveRun, source_id: str) -> dict[str, Any]:
    queries = {
        "acquisition": (
            "SELECT status, count(*) FROM acquisition_job"
            " WHERE source_id = %s GROUP BY status",
            (source_id,),
        ),
        "image_candidates": (
            "SELECT status, count(*) FROM source_image_candidate"
            " WHERE source_id = %s GROUP BY status",
            (source_id,),
        ),
        "image_analysis": (
            "SELECT c.status, count(*) FROM source_image_analysis_call c"
            " JOIN artifact a ON a.id = c.markdown_artifact_id"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " WHERE sn.source_id = %s GROUP BY c.status",
            (source_id,),
        ),
        "asset_analysis": (
            "SELECT aa.status, count(*) FROM source_asset_analysis aa"
            " JOIN source_asset a ON a.id = aa.source_asset_id"
            " WHERE a.source_id = %s GROUP BY aa.status",
            (source_id,),
        ),
        "cleanup": (
            "SELECT c.status, count(*) FROM source_cleanup_job c"
            " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
            " WHERE j.source_id = %s GROUP BY c.status",
            (source_id,),
        ),
        "video_stt_chunks": (
            "SELECT c.status, count(DISTINCT c.id) FROM video_stt_chunk c"
            " JOIN video_stt_job_chunk jc ON jc.chunk_id = c.id"
            " JOIN acquisition_job j ON j.id = jc.acquisition_job_id"
            " WHERE j.source_id = %s GROUP BY c.status",
            (source_id,),
        ),
        "video_stt_attempts": (
            "SELECT a.status, count(*) FROM video_stt_attempt a"
            " JOIN video_stt_job_chunk jc ON jc.chunk_id = a.chunk_id"
            " JOIN acquisition_job j ON j.id = jc.acquisition_job_id"
            " WHERE j.source_id = %s GROUP BY a.status",
            (source_id,),
        ),
        "pdf_document_parse": (
            "SELECT c.status, count(*) FROM pdf_document_parse_call c"
            " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
            " WHERE j.source_id = %s GROUP BY c.status",
            (source_id,),
        ),
        "pdf_page_analysis": (
            "SELECT c.status, count(*) FROM pdf_page_analysis_call c"
            " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
            " WHERE j.source_id = %s GROUP BY c.status",
            (source_id,),
        ),
        "pdf_figure_localization": (
            "SELECT c.status, count(*) FROM pdf_figure_localization_call c"
            " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
            " WHERE j.source_id = %s GROUP BY c.status",
            (source_id,),
        ),
        "pdf_figure_regions": (
            "SELECT o.status, count(*) FROM pdf_figure_region_outcome o"
            " JOIN pdf_figure_localization_call c ON c.id = o.localization_call_id"
            " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
            " WHERE j.source_id = %s GROUP BY o.status",
            (source_id,),
        ),
        "pdf_pages": (
            "SELECT p.text_layer_status, count(*) FROM source_pdf_page p"
            " WHERE p.source_id = %s GROUP BY p.text_layer_status",
            (source_id,),
        ),
    }
    components = {
        component: {
            str(status): int(count)
            for status, count in live.conn.execute(query, params).fetchall()
        }
        for component, (query, params) in queries.items()
    }
    return _summarize_work_states(components)


def _assert_terminal_work(live: LiveRun, source_id: str) -> dict[str, Any]:
    report = _work_state_report(live, source_id)
    assert report["nonterminal_count"] == 0, report
    return report


def _drain_to_canonical(
    live: LiveRun, source_id: str, *, timeout_seconds: int
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        acquisition = _latest_acquisition(live, source_id)
        cleanup = _latest_cleanup(live, source_id)
        if acquisition and acquisition["status"] == "failed":
            pytest.fail(
                f"{source_id} acquisition failed: {acquisition['failure_code']} "
                f"({(acquisition['diagnostics'] or {}).get('category')})"
            )
        if cleanup and cleanup["status"] == "failed":
            pytest.fail(
                f"{source_id} cleanup failed: {cleanup['failure_code']} "
                f"({(cleanup['diagnostics'] or {}).get('category')})"
            )
        if cleanup and cleanup["status"] == "succeeded":
            canonical_id = cleanup["canonical_artifact_id"]
            artifact = live.conn.execute(
                "SELECT a.tool, a.tool_version, a.body, a.metadata, sn.source_id"
                " FROM artifact a JOIN source_snapshot sn ON sn.id = a.snapshot_id"
                " WHERE a.id = %s",
                (canonical_id,),
            ).fetchone()
            assert artifact is not None
            return {
                "acquisition": acquisition,
                "cleanup": cleanup,
                "canonical_id": canonical_id,
                "tool": artifact[0],
                "tool_version": artifact[1],
                "body": artifact[2],
                "metadata": artifact[3] or {},
                "source_id": artifact[4],
            }
        work = process_next_work_item(live.conn, asset_store=live.asset_store)
        if work is None:
            work_state = _work_state_report(live, source_id)
            if work_state["nonterminal_count"] == 0:
                category = (acquisition or {}).get("diagnostics") or {}
                pytest.fail(
                    f"{source_id} has no runnable work and no canonical artifact "
                    f"(category={category.get('category')}, "
                    f"visual_incomplete={category.get('visual_incomplete')}, "
                    f"work_state={work_state})"
                )
            time.sleep(1)
    pytest.fail(f"{source_id} exceeded its {timeout_seconds}s live tracer limit")


def _assert_canonical(live: LiveRun, publication: dict[str, Any]) -> str:
    body = publication["body"]
    source_id = publication["source_id"]
    assert publication["tool"] == "passage-cleanup"
    assert publication["canonical_id"]
    assert source_id
    assert isinstance(body, str) and body.strip()
    for pattern in UNSAFE_MARKDOWN:
        assert pattern.search(body) is None, pattern.pattern

    asset_ids = _validated_asset_ids(body)
    for asset_id in asset_ids:
        row = live.conn.execute(
            "SELECT storage_key, sha256 FROM source_asset WHERE id = %s", (asset_id,)
        ).fetchone()
        assert row is not None, asset_id
        payload = live.asset_store.get(row[0])
        assert hashlib.sha256(payload).hexdigest() == row[1]

    task_count = live.conn.execute(
        "SELECT count(*) FROM task t"
        " JOIN passage p ON p.id = t.passage_id"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s",
        (source_id,),
    ).fetchone()[0]
    assert task_count == 0
    return body


def _numeric_cost(usage: dict[str, Any]) -> Decimal | None:
    for key in ("cost", "total_cost"):
        value = usage.get(key)
        if isinstance(value, (int, float, str)) and not isinstance(value, bool):
            try:
                return Decimal(str(value))
            except Exception:
                return None
    return None


def _summarize_usage_observations(
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Conservatively total every durable indication of a provider attempt.

    A nested ``attempts`` ledger is authoritative for application fallback.
    Otherwise the row usage describes only the latest attempt; earlier durable
    attempts remain observable but unpriced and make the live acceptance fail.
    """
    total = Decimal("0")
    observable_attempts = 0
    priced_attempts = 0
    unpriced_attempts = 0
    by_stage: dict[str, dict[str, Any]] = {}

    for observation in observations:
        stage = str(observation["stage"])
        status = str(observation["status"])
        usage = dict(observation.get("usage") or {})
        try:
            minimum_attempts = max(0, int(observation.get("attempt_count") or 0))
        except (TypeError, ValueError):
            minimum_attempts = 0
        raw_attempts = usage.get("attempts")
        embedded = (
            [item for item in raw_attempts if isinstance(item, dict)]
            if isinstance(raw_attempts, list)
            else []
        )
        attempt_usages: list[dict[str, Any]]
        if embedded:
            attempt_usages = [dict(item.get("usage") or {}) for item in embedded]
        elif minimum_attempts or usage:
            attempt_usages = [usage]
        else:
            continue
        attempt_usages.extend(
            {} for _ in range(max(0, minimum_attempts - len(attempt_usages)))
        )

        stage_report = by_stage.setdefault(
            stage,
            {
                "observable_attempts": 0,
                "priced_attempts": 0,
                "unpriced_attempts": 0,
                "observed_cost_usd": Decimal("0"),
                "row_outcomes": {},
            },
        )
        stage_report["row_outcomes"][status] = (
            stage_report["row_outcomes"].get(status, 0) + 1
        )
        for attempt_usage in attempt_usages:
            observable_attempts += 1
            stage_report["observable_attempts"] += 1
            cost = _numeric_cost(attempt_usage)
            if cost is None:
                unpriced_attempts += 1
                stage_report["unpriced_attempts"] += 1
                continue
            priced_attempts += 1
            total += cost
            stage_report["priced_attempts"] += 1
            stage_report["observed_cost_usd"] += cost

    for stage_report in by_stage.values():
        stage_report["observed_cost_usd"] = str(stage_report["observed_cost_usd"])
    return {
        "observable_attempts": observable_attempts,
        "priced_attempts": priced_attempts,
        "unpriced_attempts": unpriced_attempts,
        "observed_cost_usd": str(total),
        "by_stage": by_stage,
    }


def _usage_report(live: LiveRun, source_id: str) -> dict[str, Any]:
    queries = {
        "cleanup": (
            "SELECT CASE WHEN ri.error IS NULL THEN 'succeeded' ELSE 'failed' END,"
            " ri.usage FROM run_item ri"
            " JOIN artifact a ON a.id = ri.artifact_id"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " WHERE sn.source_id = %s",
            (source_id,),
        ),
        "source_visual": (
            "SELECT c.status, c.attempt_count, c.usage"
            " FROM source_image_analysis_call c"
            " JOIN artifact a ON a.id = c.markdown_artifact_id"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " WHERE sn.source_id = %s",
            (source_id,),
        ),
        "pdf_page": (
            "SELECT c.status, c.attempt_count, c.usage"
            " FROM pdf_page_analysis_call c"
            " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
            " WHERE j.source_id = %s",
            (source_id,),
        ),
        "pdf_figure": (
            "SELECT c.status, c.attempt_count, c.usage"
            " FROM pdf_figure_localization_call c"
            " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
            " WHERE j.source_id = %s",
            (source_id,),
        ),
        "video_stt": (
            "SELECT a.status, 1, a.usage FROM video_stt_attempt a"
            " JOIN video_stt_job_chunk jc ON jc.chunk_id = a.chunk_id"
            " JOIN acquisition_job j ON j.id = jc.acquisition_job_id"
            " WHERE j.source_id = %s",
            (source_id,),
        ),
    }
    observations: list[dict[str, Any]] = []
    for stage, (query, params) in queries.items():
        rows = live.conn.execute(query, params).fetchall()
        for row in rows:
            if stage == "cleanup":
                status, raw_usage = row
                usage = dict(raw_usage or {})
                raw_embedded = usage.get("attempts")
                embedded_count = (
                    len([item for item in raw_embedded if isinstance(item, dict)])
                    if isinstance(raw_embedded, list)
                    else 0
                )
                try:
                    retry_count = max(0, int(usage.get("retry_count") or 0))
                except (TypeError, ValueError):
                    retry_count = 0
                attempt_count = retry_count + (embedded_count or 1)
            else:
                status, attempt_count, raw_usage = row
                usage = dict(raw_usage or {})
            observations.append(
                {
                    "stage": stage,
                    "status": status,
                    "attempt_count": attempt_count,
                    "usage": usage,
                }
            )
    return _summarize_usage_observations(observations)


def _firecrawl_report(live: LiveRun, source_id: str) -> dict[str, Any]:
    article = live.conn.execute(
        "SELECT status, attempt_count, diagnostics FROM acquisition_job"
        " WHERE source_id = %s AND provider = 'firecrawl/v2'",
        (source_id,),
    ).fetchall()
    parses = live.conn.execute(
        "SELECT c.status, c.provider_attempts, c.diagnostics"
        " FROM pdf_document_parse_call c"
        " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
        " WHERE j.source_id = %s",
        (source_id,),
    ).fetchall()
    article_attempts = sum(
        int((diagnostics or {}).get("provider_attempts") or attempt_count or 0)
        for _status, attempt_count, diagnostics in article
    )
    parse_attempts = sum(
        int(provider_attempts or 0) for _status, provider_attempts, _ in parses
    )
    credits = 0
    unestimated_credit_attempts = 0
    for _status, provider_attempts, diagnostics in parses:
        value = (diagnostics or {}).get("estimated_credits")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            credits += int(value)
        else:
            unestimated_credit_attempts += int(provider_attempts or 0)
    return {
        "attempts": article_attempts + parse_attempts,
        "article_attempts": article_attempts,
        "parse_attempts": parse_attempts,
        "estimated_credits": credits,
        "unestimated_credit_attempts": unestimated_credit_attempts,
        "row_outcomes": {
            "article": dict(
                (status, sum(1 for row in article if row[0] == status))
                for status in sorted({row[0] for row in article})
            ),
            "document_parse": dict(
                (status, sum(1 for row in parses if row[0] == status))
                for status in sorted({row[0] for row in parses})
            ),
        },
    }


def _assert_budget(
    live: LiveRun, source_id: str, case: str, *, global_budget: Decimal
) -> dict[str, Any]:
    usage = _usage_report(live, source_id)
    cost = Decimal(usage["observed_cost_usd"])
    assert usage["observable_attempts"] > 0, usage
    assert usage["unpriced_attempts"] == 0, usage
    assert cost <= BUDGETS[case].openrouter_usd, usage
    global_reports = [
        _usage_report(live, row[0])
        for row in live.conn.execute(
            "SELECT DISTINCT source_id FROM acquisition_job ORDER BY source_id"
        )
    ]
    global_observed_cost = sum(
        (Decimal(item["observed_cost_usd"]) for item in global_reports), Decimal("0")
    )
    global_unpriced_attempts = sum(
        item["unpriced_attempts"] for item in global_reports
    )
    assert global_unpriced_attempts == 0, global_reports
    assert global_observed_cost <= global_budget
    firecrawl = _firecrawl_report(live, source_id)
    cap = BUDGETS[case].firecrawl_credits
    if case in {"article", "pdf", "book"}:
        assert 1 <= firecrawl["attempts"] <= 4, firecrawl
    if cap is not None:
        assert firecrawl["unestimated_credit_attempts"] == 0, firecrawl
        assert 0 < firecrawl["estimated_credits"] <= cap, firecrawl
    return {
        "openrouter_observed_post_call": usage,
        "firecrawl_observed_post_call": firecrawl,
        "global_openrouter_observed_post_call": {
            "observable_attempts": sum(
                item["observable_attempts"] for item in global_reports
            ),
            "priced_attempts": sum(
                item["priced_attempts"] for item in global_reports
            ),
            "unpriced_attempts": global_unpriced_attempts,
            "observed_cost_usd": str(global_observed_cost),
            "ceiling_usd": str(global_budget),
        },
    }


def _accept_workbook(live: LiveRun) -> dict[str, Any]:
    workbook = _required_path("LIVE_E2E_WORKBOOK", WORKBOOK_SHA256)
    parsed = parse_workbook(workbook)
    references = [
        source
        for lesson in parsed["lessons"]
        for source in lesson["source_references"]
    ]
    assert parsed["format"] == "projetos-21"
    assert parsed["workbook_title"] == "GRAD CC07 - 2026-2A"
    assert parsed["lesson_count"] == 64
    assert parsed["source_count"] == 130
    assert len(references) == 130
    media_counts = {
        kind: sum(item["media_type"] == kind for item in references)
        for kind in ("article", "video", "book")
    }
    assert media_counts == {
        "article": 81,
        "video": 29,
        "book": 20,
    }

    assert any(item.get("url") == WORKBOOK_NATIVE_ARTICLE for item in references)
    assert any(item.get("url") == WORKBOOK_NATIVE_PDF for item in references)
    assert any(
        WORKBOOK_NATIVE_VIDEO_ID in str(item.get("url") or "") for item in references
    )
    assert any(
        (
            item.get("resource_code"),
            item.get("scope_kind"),
            item.get("scope_value"),
        )
        == WORKBOOK_NATIVE_BOOK
        for item in references
    )

    imported = import_workbook(
        live.conn,
        workbook,
        "GRAD CC07 - 2026-2A live E2E",
        syllabus_id=f"live-e2e-cc07-{live.run_id}",
        actor="live-e2e",
    )
    repeated = import_workbook(
        live.conn,
        workbook,
        "GRAD CC07 - 2026-2A live E2E",
        syllabus_id=imported["syllabus_id"],
        actor="live-e2e",
    )
    assert imported["lesson_count"] == 64
    assert imported["reference_count"] == 130
    assert imported["new_source_count"] == 128
    assert repeated["unchanged"] is True
    assert repeated["version_id"] == imported["version_id"]
    stored = live.conn.execute(
        "SELECT file_sha, file_body FROM syllabus_version WHERE id = %s",
        (imported["version_id"],),
    ).fetchone()
    assert stored is not None
    assert stored[0] == WORKBOOK_SHA256
    assert hashlib.sha256(bytes(stored[1])).hexdigest() == WORKBOOK_SHA256
    linked, missing, distinct_sources = live.conn.execute(
        "SELECT count(*) FILTER (WHERE source_id IS NOT NULL),"
        " count(*) FILTER (WHERE source_id IS NULL), count(DISTINCT source_id)"
        " FROM syllabus_source_reference WHERE version_id = %s",
        (imported["version_id"],),
    ).fetchone()
    assert (linked, missing, distinct_sources) == (129, 1, 128)
    return {
        "workbook_sha256": WORKBOOK_SHA256,
        "format": parsed["format"],
        "lessons": 64,
        "references": 130,
        "linked_references": 129,
        "logical_sources": 128,
        "missing_scope_references": 1,
        "version_id": imported["version_id"],
        "idempotent_reimport": True,
    }


def _run_article(live: LiveRun) -> tuple[str, dict[str, Any]]:
    source_id = _seed_source(
        live,
        f"live-article-{live.run_id}",
        identity={"kind": "article", "canonical_url": ARTICLE_URL},
        title="Diagramas de implementação — IBM",
        media_type="article",
    )
    enqueue_source(live.conn, source_id, actor="live-e2e")
    publication = _drain_to_canonical(
        live, source_id, timeout_seconds=BUDGETS["article"].timeout_seconds
    )
    body = _assert_canonical(live, publication)
    normalized = body.casefold()
    assert len(body) >= 2_500
    assert "diagramas de implementação" in normalized
    assert "nós" in normalized or "nodes" in normalized
    assert "artefatos" in normalized or "artifacts" in normalized
    assert "accept all cookies" not in normalized
    statuses = dict(
        live.conn.execute(
            "SELECT status, count(*) FROM source_image_candidate"
            " WHERE source_id = %s GROUP BY status",
            (source_id,),
        ).fetchall()
    )
    assert statuses
    assert not set(statuses) & {"queued", "running", "downloaded"}
    assert statuses.get("useful", 0) >= 1
    assert "/api/source-assets/" in body
    return source_id, {
        "candidate": ARTICLE_URL,
        "canonical_artifact_id": publication["canonical_id"],
        "canonical_characters": len(body),
        "image_outcomes": statuses,
    }


def _run_pdf(live: LiveRun) -> tuple[str, dict[str, Any]]:
    path = _required_path("LIVE_E2E_PDF", PDF_SHA256)
    source_id = _seed_source(
        live,
        f"live-pdf-{live.run_id}",
        identity={"kind": "manual-document", "sha256": PDF_SHA256},
        title="Process mining: From theory to practice",
        media_type="article",
    )
    queued = create_manual_upload_job(
        live.conn,
        source_id,
        [ManualAsset(path.name, "application/pdf", path.read_bytes(), "pdf")],
        actor="live-e2e",
        asset_store=live.asset_store,
    )
    publication = _drain_to_canonical(
        live, source_id, timeout_seconds=BUDGETS["pdf"].timeout_seconds
    )
    body = _assert_canonical(live, publication)
    assert publication["acquisition"]["id"] == queued["id"]
    assert len(body) >= 30_000
    assert "process mining" in body.casefold()
    assert len(re.findall(r"^\|.*\|$", body, flags=re.M)) >= 3
    assert re.search(r"^#{1,6}\s+5\.\s*Conclusions\s*$", body, flags=re.M | re.I)
    assert re.search(r"^#{1,6}\s+References\s*$", body, flags=re.M | re.I) is None

    job_id = queued["id"]
    pages = live.conn.execute(
        "SELECT page_number, text_layer_status FROM source_pdf_page"
        " WHERE acquisition_job_id = %s ORDER BY page_number",
        (job_id,),
    ).fetchall()
    assert pages == [(page, "usable") for page in range(1, 25)]
    calls = live.conn.execute(
        "SELECT batch_ordinal, page_ids, status FROM pdf_figure_localization_call"
        " WHERE acquisition_job_id = %s ORDER BY batch_ordinal",
        (job_id,),
    ).fetchall()
    assert calls and all(row[2] == "succeeded" for row in calls)
    covered = [page_id for _ordinal, page_ids, _status in calls for page_id in page_ids]
    assert len(covered) == 24
    assert len(set(covered)) == 24
    outcomes = live.conn.execute(
        "SELECT o.status, count(*) FROM pdf_figure_region_outcome o"
        " JOIN pdf_figure_localization_call c ON c.id = o.localization_call_id"
        " WHERE c.acquisition_job_id = %s GROUP BY o.status",
        (job_id,),
    ).fetchall()
    assert not any(status == "failed" for status, _count in outcomes)
    figures = live.conn.execute(
        "SELECT count(*) FROM source_asset"
        " WHERE acquisition_job_id = %s AND kind = 'pdf_figure'",
        (job_id,),
    ).fetchone()[0]
    assert figures >= 1
    assert "/api/source-assets/" in body
    return source_id, {
        "candidate_sha256": PDF_SHA256,
        "pages": len(pages),
        "localization_batches": len(calls),
        "region_outcomes": dict(outcomes),
        "figures": figures,
        "canonical_artifact_id": publication["canonical_id"],
        "canonical_characters": len(body),
    }


def _run_video(live: LiveRun) -> tuple[str, dict[str, Any]]:
    source_id = _seed_source(
        live,
        f"live-video-{live.run_id}",
        identity={"kind": "video", "provider": "youtube", "video_id": VIDEO_ID},
        title="Getting started with Natural Language Processing: Bag of words",
        media_type="video",
    )
    refreshed = videos.refresh_preflight(live.conn, source_id)
    assert refreshed["status"] == "succeeded"
    assert refreshed["route"] == "uploaded_caption"
    assert 360 <= float(refreshed["duration_seconds"]) <= 410
    assert refreshed["selected_caption_language"]

    queued = enqueue_source(live.conn, source_id, actor="live-e2e")
    assert queued["video_preflight_id"] == refreshed["id"]
    preflight = live.conn.execute(
        "SELECT route, duration_seconds, selected_caption_language"
        " FROM video_preflight WHERE id = %s",
        (queued["video_preflight_id"],),
    ).fetchone()
    assert preflight is not None
    assert preflight[0] == "uploaded_caption"
    assert 360 <= float(preflight[1]) <= 410
    assert preflight[2]

    publication = _drain_to_canonical(
        live, source_id, timeout_seconds=BUDGETS["video"].timeout_seconds
    )
    body = _assert_canonical(live, publication)
    normalized = body.casefold()
    assert "bag of words" in normalized
    assert "natural language" in normalized
    transcript = live.conn.execute(
        "SELECT id, route, segment_count, visual_analysis FROM video_transcript"
        " WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()
    assert transcript is not None
    assert transcript[1] == "uploaded_caption"
    assert 100 <= transcript[2] <= 160
    segments = live.conn.execute(
        "SELECT seq, start_ms, end_ms, source_kind FROM video_transcript_segment"
        " WHERE transcript_id = %s ORDER BY seq",
        (transcript[0],),
    ).fetchall()
    assert len(segments) == transcript[2]
    assert [row[0] for row in segments] == list(range(1, len(segments) + 1))
    assert all(row[2] >= row[1] and row[3] == "caption_cue" for row in segments)
    assert [row[1] for row in segments] == sorted(row[1] for row in segments)
    caption = live.conn.execute(
        "SELECT octet_length(vtt_bytes), vtt_sha256 FROM video_caption_evidence"
        " WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()
    assert caption and caption[0] > 1_000 and re.fullmatch(r"[0-9a-f]{64}", caption[1])
    assert live.conn.execute(
        "SELECT count(*) FROM video_stt_job_chunk WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == 0

    frames = live.conn.execute(
        "SELECT count(*) FROM source_asset"
        " WHERE acquisition_job_id = %s AND kind = 'video_frame'",
        (queued["id"],),
    ).fetchone()[0]
    assert 1 <= frames <= 20
    statuses = dict(
        live.conn.execute(
            "SELECT status, count(*) FROM source_image_candidate"
            " WHERE acquisition_job_id = %s GROUP BY status",
            (queued["id"],),
        ).fetchall()
    )
    assert not set(statuses) & {"queued", "running", "downloaded"}
    assert statuses.get("useful", 0) >= 1
    assert "/api/source-assets/" in body
    return source_id, {
        "candidate": VIDEO_URL,
        "route": preflight[0],
        "duration_seconds": preflight[1],
        "caption_cues": transcript[2],
        "frame_assets": frames,
        "image_outcomes": statuses,
        "canonical_artifact_id": publication["canonical_id"],
        "canonical_characters": len(body),
    }


def _run_book(live: LiveRun) -> tuple[str, dict[str, Any]]:
    source_id = _seed_source(
        live,
        f"live-book-{live.run_id}",
        identity={
            "kind": "book",
            "resource_code": BOOK_RESOURCE_CODE,
            "scope": {"kind": "pages", "value": BOOK_SCOPE},
        },
        title="Programação linear inteira — páginas 198–205",
        media_type="book",
    )
    queued = enqueue_source(live.conn, source_id, actor="live-e2e")
    publication = _drain_to_canonical(
        live, source_id, timeout_seconds=BUDGETS["book"].timeout_seconds
    )
    body = _assert_canonical(live, publication)
    normalized = body.casefold()
    assert "integralidade" in normalized
    assert "relaxamento" in normalized
    assert len(body) >= 3_000

    pages = live.conn.execute(
        "SELECT a.id, a.ordinal, a.metadata->>'printed_page_label',"
        " a.metadata->>'reader_page_id', length(t.body), a.byte_size"
        " FROM source_asset a JOIN source_asset_text t ON t.source_asset_id = a.id"
        " WHERE a.acquisition_job_id = %s AND a.kind = 'book_page'"
        " ORDER BY a.ordinal",
        (queued["id"],),
    ).fetchall()
    assert [row[2] for row in pages] == [str(page) for page in range(198, 206)]
    assert all(row[3] and row[4] > 80 and row[5] > 1_000 for row in pages)
    assert all(f"/api/source-assets/{row[0]}" not in body for row in pages)
    diagnostics = publication["acquisition"]["diagnostics"] or {}
    assert diagnostics["page_count"] == 8
    assert diagnostics["exact_text_pages"] == 8
    assert diagnostics["extractor"]["document_mode"] == "ocr"
    assert diagnostics["ordered_reconstruction"]["page_count"] == 8
    parse = live.conn.execute(
        "SELECT status, options FROM pdf_document_parse_call"
        " WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()
    assert parse is not None and parse[0] == "succeeded"
    assert parse[1]["parsers"] == [{"type": "pdf", "mode": "ocr"}]
    figures = live.conn.execute(
        "SELECT count(*) FROM source_asset"
        " WHERE acquisition_job_id = %s AND kind = 'pdf_figure'",
        (queued["id"],),
    ).fetchone()[0]
    assert figures >= 1
    return source_id, {
        "candidate": {
            "resource_code": BOOK_RESOURCE_CODE,
            "scope_kind": "pages",
            "scope_value": BOOK_SCOPE,
        },
        "captured_pages": len(pages),
        "figures": figures,
        "attempt_count": publication["acquisition"]["attempt_count"],
        "canonical_artifact_id": publication["canonical_id"],
        "canonical_characters": len(body),
    }


def _write_report(live: LiveRun, report: dict[str, Any]) -> None:
    destination = live.evidence_dir / "quality-report.json"
    temporary = live.evidence_dir / "quality-report.json.tmp"
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def _source_id_for_case(live: LiveRun, case: str) -> str:
    return f"live-{case}-{live.run_id}"


def _safe_failure_summary(exc: BaseException) -> dict[str, str]:
    message = str(exc)
    message = re.sub(
        r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+",
        r"\1[credential redacted]",
        message,
    )
    message = re.sub(
        r"(?i)\b(api[_-]?key|token|password|secret)\s*([=:])\s*[^\s,;]+",
        r"\1\2[credential redacted]",
        message,
    )
    message = re.sub(r"sk-[A-Za-z0-9_-]+", "[key redacted]", message)
    message = re.sub(
        r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[image redacted]", message
    )
    return {"type": type(exc).__name__, "message": message[:1_000]}


def _safe_case_observability(live: LiveRun, source_id: str) -> dict[str, Any]:
    """Best-effort evidence collection that never replaces the primary failure."""
    if live.conn.info.transaction_status == TransactionStatus.INERROR:
        live.conn.rollback()
    report: dict[str, Any] = {}
    collectors = {
        "openrouter_observed_post_call": lambda: _usage_report(live, source_id),
        "firecrawl_observed_post_call": lambda: _firecrawl_report(live, source_id),
        "terminal_work": lambda: _work_state_report(live, source_id),
    }
    for name, collect in collectors.items():
        try:
            report[name] = collect()
        except BaseException as exc:  # reporting must survive a partial schema/transaction
            report[f"{name}_collection_failure"] = _safe_failure_summary(exc)
            if live.conn.info.transaction_status == TransactionStatus.INERROR:
                live.conn.rollback()
    return report


def test_bounded_live_source_publications(
    live_run: LiveRun,
    live_cases: tuple[str, ...],
    live_openrouter_budget: Decimal,
) -> None:
    required = sum(
        (BUDGETS[case].openrouter_usd for case in live_cases if case != "xlsx"),
        Decimal("0"),
    )
    report: dict[str, Any] = {
        "status": "running",
        "run_id": live_run.run_id,
        "database": live_run.database_name,
        "selected_cases": list(live_cases),
        "global_openrouter_observed_post_call_ceiling_usd": str(
            live_openrouter_budget
        ),
        "cases": {},
    }
    _write_report(live_run, report)
    if live_openrouter_budget < required:
        report["status"] = "failed"
        report["configuration_failure"] = {
            "type": "insufficient_observed_post_call_ceiling",
            "message": (
                f"selected case ceilings total ${required}; "
                f"LIVE_E2E_MAX_OPENROUTER_USD is ${live_openrouter_budget}"
            ),
        }
        _write_report(live_run, report)
        pytest.fail(report["configuration_failure"]["message"])

    runners = {
        "article": _run_article,
        "pdf": _run_pdf,
        "video": _run_video,
        "book": _run_book,
    }
    for case in live_cases:
        started = time.monotonic()
        source_id = None if case == "xlsx" else _source_id_for_case(live_run, case)
        case_report: dict[str, Any] = {"status": "running"}
        report["cases"][case] = case_report
        _write_report(live_run, report)
        try:
            if case == "xlsx":
                result = _accept_workbook(live_run)
            else:
                observed_source_id, result = runners[case](live_run)
                assert observed_source_id == source_id
                result["terminal_work"] = _assert_terminal_work(
                    live_run, source_id
                )
                result["observed_post_call"] = _assert_budget(
                    live_run,
                    source_id,
                    case,
                    global_budget=live_openrouter_budget,
                )
                result["openrouter_observed_post_call_ceiling_usd"] = str(
                    BUDGETS[case].openrouter_usd
                )
                result["firecrawl_estimated_credit_ceiling"] = BUDGETS[
                    case
                ].firecrawl_credits
            case_report.update(result)
            case_report["status"] = "succeeded"
        except BaseException as exc:
            case_report["status"] = "failed"
            case_report["failure"] = _safe_failure_summary(exc)
            if source_id is not None:
                case_report["partial_observability"] = _safe_case_observability(
                    live_run, source_id
                )
            report["status"] = "failed"
            report["failed_case"] = case
            raise
        finally:
            case_report["wall_seconds"] = round(time.monotonic() - started, 3)
            _write_report(live_run, report)

    report["status"] = "succeeded"
    _write_report(live_run, report)
