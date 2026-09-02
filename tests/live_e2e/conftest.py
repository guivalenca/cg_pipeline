"""Hard opt-in and isolated storage for paid live extraction tracers.

Nothing in this directory may contact a provider unless both the pytest flag
and the exact environment acknowledgement are present.  Live evidence is
kept in a fresh database and asset directory for inspection after the run.
"""

from __future__ import annotations

import os
import re
import shutil
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from universe.assets import LocalAssetStore
from universe.db import database_url
from universe.migrate import migrate


LIVE_ACKNOWLEDGEMENT = "I_UNDERSTAND_THIS_CALLS_EXTERNAL_PROVIDERS"
ALLOWED_CASES = frozenset({"xlsx", "article", "pdf", "video", "book"})
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIVE_TEST_DIRECTORY = Path(__file__).resolve().parent


@dataclass(frozen=True)
class LiveRun:
    run_id: str
    database_name: str
    conn: psycopg.Connection
    asset_store: LocalAssetStore
    evidence_dir: Path


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("live-e2e")
    group.addoption(
        "--live-e2e",
        action="store_true",
        default=False,
        help="allow this gated directory after the environment acknowledgement",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    enabled = _live_gate_enabled(config)
    if enabled:
        return
    reason = (
        "live provider tests require both --live-e2e and "
        f"RUN_LIVE_SOURCE_E2E={LIVE_ACKNOWLEDGEMENT}"
    )
    marker = pytest.mark.skip(reason=reason)
    for item in items:
        if Path(str(item.path)).resolve().is_relative_to(LIVE_TEST_DIRECTORY):
            item.add_marker(marker)


def _live_gate_enabled(config: pytest.Config) -> bool:
    return bool(config.getoption("--live-e2e")) and (
        os.getenv("RUN_LIVE_SOURCE_E2E", "").strip() == LIVE_ACKNOWLEDGEMENT
    )


@pytest.fixture(scope="session", autouse=True)
def _hard_directory_gate(pytestconfig: pytest.Config) -> None:
    """Fail closed for every test below this conftest, marker or not."""
    if _live_gate_enabled(pytestconfig):
        return
    pytest.skip(
        "live provider tests require both --live-e2e and "
        f"RUN_LIVE_SOURCE_E2E={LIVE_ACKNOWLEDGEMENT}"
    )


@pytest.fixture(scope="session")
def live_cases() -> tuple[str, ...]:
    raw = os.getenv("LIVE_E2E_CASES", "").strip()
    if not raw:
        pytest.fail(
            "LIVE_E2E_CASES must explicitly list one or more of: "
            + ", ".join(sorted(ALLOWED_CASES))
        )
    requested = tuple(dict.fromkeys(part.strip() for part in raw.split(",") if part.strip()))
    unknown = sorted(set(requested) - ALLOWED_CASES)
    if unknown:
        pytest.fail(f"unknown LIVE_E2E_CASES: {', '.join(unknown)}")
    return tuple(
        case
        for case in ("xlsx", "article", "pdf", "video", "book")
        if case in requested
    )


@pytest.fixture(scope="session")
def live_openrouter_budget(live_cases: tuple[str, ...]) -> Decimal:
    if not set(live_cases) - {"xlsx"}:
        return Decimal("0")
    raw = os.getenv("LIVE_E2E_MAX_OPENROUTER_USD", "").strip()
    try:
        value = Decimal(raw)
    except InvalidOperation:
        pytest.fail("LIVE_E2E_MAX_OPENROUTER_USD must be an explicit decimal amount")
    if value <= 0 or value > Decimal("1.00"):
        pytest.fail("LIVE_E2E_MAX_OPENROUTER_USD must be greater than 0 and at most 1.00")
    return value


def _require_any(*names: str) -> None:
    if not any(os.getenv(name, "").strip() for name in names):
        pytest.fail(f"missing required credential setting (one of {', '.join(names)})")


def _validate_provider_configuration(cases: tuple[str, ...]) -> None:
    paid = set(cases) - {"xlsx"}
    if paid:
        _require_any("OPENROUTER_API_KEY", "OPEN_ROUTER_API_KEY", "MODEL_API_KEY")
    if paid & {"article", "pdf", "book"}:
        _require_any("FIRECRAWL_API_KEY")
    if paid & {"pdf", "book"}:
        if os.getenv("FIRECRAWL_ALLOW_PRIVATE_PDF_UPLOADS", "").strip() != "1":
            pytest.fail("PDF/book live tracers require FIRECRAWL_ALLOW_PRIVATE_PDF_UPLOADS=1")
        if os.getenv("OPENROUTER_ALLOW_PRIVATE_PDF_PAGE_UPLOADS", "").strip() != "1":
            pytest.fail(
                "PDF/book live tracers require "
                "OPENROUTER_ALLOW_PRIVATE_PDF_PAGE_UPLOADS=1"
            )
    if "video" in paid:
        missing = [
            name
            for name in ("yt-dlp", "ffmpeg", "ffprobe", "node")
            if shutil.which(name) is None
        ]
        if missing:
            pytest.fail(f"video live tracer is missing runtime tools: {', '.join(missing)}")
        summarize = PROJECT_ROOT / "node_modules" / ".bin" / "summarize"
        if not summarize.exists():
            pytest.fail("video live tracer requires the pinned summarize install (`npm ci`)")
    if "book" in paid:
        _require_any("BROWSERBASE_API_KEY")
        context_id = os.getenv("BROWSERBASE_CONTEXT_ID", "").strip()
        context_file = Path(
            os.getenv(
                "BROWSERBASE_CONTEXT_FILE",
                PROJECT_ROOT / ".data" / "browserbase_context.json",
            )
        ).expanduser()
        if not context_id and not context_file.exists():
            _require_any("CG_PIPELINE_LIBRARY_USERNAME", "LIBRARY_USERNAME")
            _require_any("CG_PIPELINE_LIBRARY_PASSWORD", "LIBRARY_PASSWORD")


def _local_database_base() -> tuple[str, str]:
    base = database_url()
    parsed = conninfo_to_dict(base)
    host = str(parsed.get("host") or "localhost").strip().lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail(
            "live E2E refuses a non-local DATABASE_URL; use the local compose database"
        )
    return base, make_conninfo(base, dbname="postgres")


@pytest.fixture(scope="session")
def live_run(
    live_cases: tuple[str, ...], live_openrouter_budget: Decimal
) -> LiveRun:
    del live_openrouter_budget  # validation happens before any database/provider work
    _validate_provider_configuration(live_cases)
    base_url, admin_url = _local_database_base()
    run_id = os.getenv("LIVE_E2E_RUN_ID", "").strip().lower()
    if not run_id:
        run_id = uuid.uuid4().hex[:12]
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,31}", run_id):
        pytest.fail("LIVE_E2E_RUN_ID must contain 3-32 lowercase letters, digits, _ or -")
    database_name = f"universe_live_e2e_{run_id.replace('-', '_')}"
    evidence_dir = Path(
        os.getenv("LIVE_E2E_EVIDENCE_DIR", PROJECT_ROOT / ".data" / "live-e2e" / run_id)
    ).expanduser().resolve()
    evidence_dir.mkdir(parents=True, exist_ok=False)
    asset_store = LocalAssetStore(evidence_dir / "source-assets")

    with psycopg.connect(admin_url, autocommit=True) as admin:
        exists = admin.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
        ).fetchone()
        if exists:
            pytest.fail(f"isolated live E2E database already exists: {database_name}")
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    live_url = make_conninfo(base_url, dbname=database_name)
    conn = psycopg.connect(live_url)
    try:
        migrate(conn)
        (evidence_dir / "run.txt").write_text(
            f"run_id={run_id}\ndatabase={database_name}\n",
            encoding="utf-8",
        )
        yield LiveRun(run_id, database_name, conn, asset_store, evidence_dir)
    finally:
        conn.close()
        # Deliberately preserve the database and content-addressed evidence.
        # Cleanup is a separate, explicit operator action after inspection.
