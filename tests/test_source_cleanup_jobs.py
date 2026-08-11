"""Durable orchestration from one enriched source artifact to clean Markdown."""

import json
from pathlib import Path

from psycopg.types.json import Jsonb

from universe.acquisition import source_cleanup_jobs
from universe.harness import PROMPTS_DIR, load_tool
from universe.model_client import ModelClient


def test_default_cleanup_prompt_drops_citation_only_bibliographies():
    prompt = (
        Path(PROMPTS_DIR) / "passage-triage" / "v005.md"
    ).read_text(encoding="utf-8")

    assert source_cleanup_jobs.TRIAGE_PROMPT_VERSION == "v005"
    assert "bibliographic references" in prompt
    assert "without explanatory teaching" in prompt
    assert "Judge images by the same" in prompt
    assert "rule as every other element" in prompt


def _tool_response(name: str, arguments: dict) -> dict:
    return {
        "choices": [{"message": {"content": "", "tool_calls": [
            {"function": {"name": name, "arguments": json.dumps(arguments)}}
        ]}, "finish_reason": "tool_calls"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        "provider": "test",
    }


def _client(decide, stage: str, tool: str) -> ModelClient:
    def transport(_url, _headers, payload, _timeout):
        name = payload["tools"][0]["function"]["name"]
        return _tool_response(name, decide(name, payload["messages"][0]["content"]))
    return ModelClient(
        "fake/model",
        api_base="https://example.invalid/v1",
        transport=transport,
        extra=load_tool(str(PROMPTS_DIR / stage / tool)),
    )


def _source_artifact(
    db, marker: str, *, metadata: dict | None = None
) -> tuple[str, str, str]:
    source_id = f"source-cleanup-{marker}"
    acquisition_job_id = f"acq-cleanup-{marker}"
    snapshot_id = f"{source_id}:snapshot"
    base_artifact_id = f"{snapshot_id}:markdown"
    artifact_id = f"{base_artifact_id}:images"
    db.execute("INSERT INTO source (id, identity, title, media_type) VALUES (%s, '{\"kind\": \"test\"}', 'Cleanup source', 'article')", (source_id,))
    db.execute("INSERT INTO source_snapshot (id, source_id, content_hash, status) VALUES (%s, %s, 'cleanup-hash', 'ok')", (snapshot_id, source_id))
    db.execute("INSERT INTO artifact (id, snapshot_id, kind, tool, body) VALUES (%s, %s, 'markdown', 'firecrawl', '# Base')", (base_artifact_id, snapshot_id))
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body, metadata) VALUES (%s, %s, 'markdown', 'article-image-association', %s, %s)",
        (
            artifact_id,
            snapshot_id,
            "Cookie settings.\n\n# Real lesson\n\nUseful teaching.\n\n# Recommended resources\n\nCards and footer.\n",
            Jsonb({"source_markdown_artifact_id": base_artifact_id, **(metadata or {})}),
        ),
    )
    db.execute("INSERT INTO acquisition_job (id, source_id, status, provider, artifact_id, finished_at) VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, now())", (acquisition_job_id, source_id, base_artifact_id))
    db.commit()
    return source_id, acquisition_job_id, artifact_id


def test_cleanup_job_runs_blocks_cuts_triage_and_publishes_only_clean_markdown(db):
    source_id, acquisition_job_id, artifact_id = _source_artifact(db, "full")
    queued = source_cleanup_jobs.enqueue_source_cleanup(db, acquisition_job_id=acquisition_job_id, source_artifact_id=artifact_id)
    calls = []
    triaged = []
    def cuts(_name, _prompt):
        calls.append("cuts")
        return {"cuts": [3]}
    def triage(_name, prompt):
        calls.append("triage")
        focus = prompt.rsplit("<passage>", 1)[1].split("</passage>", 1)[0]
        triaged.append(focus)
        return {"verdict": "drop" if "Cookie settings." in focus or "Recommended resources" in focus else "keep"}
    result = source_cleanup_jobs.process_next_source_cleanup(
        db, job_id=queued["id"],
        cuts_client=_client(cuts, "passage-cuts", "tool-v001.json"),
        triage_client=_client(triage, "passage-triage", "tool-v003.json"),
        atomic_triage_client=_client(
            triage, "passage-triage", "tool-v003-atomic.json"
        ),
        refine_client=_client(
            lambda _name, _prompt: {"drop_elements": []},
            "passage-refine", "tool-v002.json",
        ),
    )
    assert result["status"] == "succeeded", result
    assert result["source_id"] == source_id
    assert result["canonical_artifact_id"]
    assert calls == ["cuts", "triage", "triage"]
    assert all("Cookie settings." not in focus for focus in triaged)
    canonical = db.execute("SELECT body, tool, metadata FROM artifact WHERE id = %s", (result["canonical_artifact_id"],)).fetchone()
    assert canonical[0] == "# Real lesson\n\nUseful teaching.\n"
    assert canonical[1] == "passage-cleanup"
    main_artifact_id = canonical[2]["source_markdown_artifact_id"]
    assert main_artifact_id == f"{artifact_id}:main"
    boundary = db.execute(
        "SELECT body, tool, metadata FROM artifact WHERE id = %s",
        (main_artifact_id,),
    ).fetchone()
    assert boundary[0].startswith("# Real lesson")
    assert boundary[1] == "article-main-content-boundary"
    assert boundary[2]["source_markdown_artifact_id"] == artifact_id


def test_pdf_cleanup_allows_an_enriched_visual_drop_verdict(db):
    _source_id, acquisition_job_id, artifact_id = _source_artifact(
        db, "pdf-visual", metadata={"pdf_page_pipeline": True}
    )
    db.execute(
        "UPDATE artifact SET body = %s WHERE id = %s",
        (
            "# Table continuation\n\n"
            "![Page 7 table](/api/source-assets/page-7)\n\n"
            "Image summary: The table continues.\n\n"
            "OCR: Concurrent processes.\n",
            artifact_id,
        ),
    )
    db.commit()
    queued = source_cleanup_jobs.enqueue_source_cleanup(
        db,
        acquisition_job_id=acquisition_job_id,
        source_artifact_id=artifact_id,
    )

    result = source_cleanup_jobs.process_next_source_cleanup(
        db,
        job_id=queued["id"],
        cuts_client=_client(
            lambda _name, _prompt: {"cuts": []},
            "passage-cuts",
            "tool-v001.json",
        ),
        triage_client=_client(
            lambda _name, _prompt: {"verdict": "drop"},
            "passage-triage",
            "tool-v003.json",
        ),
        atomic_triage_client=_client(
            lambda _name, _prompt: {"verdict": "drop"},
            "passage-triage",
            "tool-v003-atomic.json",
        ),
        refine_client=_client(
            lambda _name, _prompt: {"drop_elements": []},
            "passage-refine",
            "tool-v002.json",
        ),
    )

    assert result["status"] == "succeeded", result
    canonical = db.execute(
        "SELECT body FROM artifact WHERE id = %s",
        (result["canonical_artifact_id"],),
    ).fetchone()[0]
    assert "![Page 7 table]" not in canonical
    assert "Concurrent processes" not in canonical
    assert db.execute(
        "SELECT verdict, policy_reason FROM passage_cleanup_result"
        " WHERE cleanup_id = %s",
        (result["cleanup_id"],),
    ).fetchone() == ("drop", None)


def test_cleanup_queue_and_claim_are_idempotent_for_refresh_and_two_workers(db):
    _source_id, acquisition_job_id, artifact_id = _source_artifact(db, "dedupe")
    first = source_cleanup_jobs.enqueue_source_cleanup(db, acquisition_job_id=acquisition_job_id, source_artifact_id=artifact_id)
    second = source_cleanup_jobs.enqueue_source_cleanup(db, acquisition_job_id=acquisition_job_id, source_artifact_id=artifact_id)
    assert first["id"] == second["id"]
    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert source_cleanup_jobs.claim_next_source_cleanup(db, job_id=first["id"])
    assert source_cleanup_jobs.claim_next_source_cleanup(db, job_id=first["id"]) is None
    assert db.execute("SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s", (acquisition_job_id,)).fetchone()[0] == 1


def test_default_cleanup_client_uses_auto_exacto_routing_and_fails_over_once():
    calls = []

    def primary_transport(_url, _headers, payload, _timeout):
        calls.append(("primary", payload))
        return {
            "choices": [{"message": {"content": "prose", "tool_calls": []}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 3, "cost": 0.001},
            "provider": "primary-provider",
            "model": "deepseek/deepseek-v4-flash",
        }

    def fallback_transport(_url, _headers, payload, _timeout):
        calls.append(("fallback", payload))
        return _tool_response("report_cuts", {"cuts": [2]}) | {
            "usage": {"prompt_tokens": 13, "completion_tokens": 2, "cost": 0.002},
            "provider": "fallback-provider",
            "model": "google/gemini-2.5-flash",
        }

    primary = ModelClient(
        "deepseek/deepseek-v4-flash",
        api_base="https://example.invalid/v1",
        transport=primary_transport,
        extra={
            **load_tool(str(PROMPTS_DIR / "passage-cuts" / "tool-v001.json")),
            "provider": {"allow_fallbacks": True, "data_collection": "deny"},
        },
    )
    fallback = ModelClient(
        "google/gemini-2.5-flash",
        api_base="https://example.invalid/v1",
        transport=fallback_transport,
        extra={
            **load_tool(str(PROMPTS_DIR / "passage-cuts" / "tool-v001.json")),
            "provider": {"allow_fallbacks": True, "data_collection": "deny"},
        },
    )
    client = source_cleanup_jobs.ResilientToolClient(primary, fallback)

    response, usage, _duration = client.complete("numbered blocks")

    assert json.loads(response) == {"cuts": [2]}
    assert [name for name, _payload in calls] == ["primary", "fallback"]
    assert all(call[1]["provider"] == {
        "allow_fallbacks": True, "data_collection": "deny"
    } for call in calls)
    assert usage["prompt_tokens"] == 24
    assert usage["completion_tokens"] == 5
    assert usage["cost"] == 0.003
    assert usage["fallback_used"] is True
    assert usage["provider"] == "fallback-provider"
    assert usage["response_model"] == "google/gemini-2.5-flash"
    assert usage["attempts"][0]["error"] == "ModelError"

    default_client = source_cleanup_jobs._client(
        PROMPTS_DIR / "passage-cuts" / "tool-v001.json"
    )
    assert default_client.primary.params["provider"] == {
        "allow_fallbacks": True,
        "data_collection": "deny",
    }
    assert default_client.primary.params["reasoning"] == {
        "effort": "high", "exclude": True
    }
    assert default_client.primary.timeout == 90.0
    assert default_client.fallback.timeout == 90.0


def test_resilient_cleanup_client_does_not_retry_a_successful_tool_call():
    calls = []

    def transport(_url, _headers, payload, _timeout):
        calls.append(payload["model"])
        return _tool_response("report_cuts", {"cuts": []})

    primary = ModelClient(
        "primary/model", api_base="https://example.invalid/v1", transport=transport,
        extra=load_tool(str(PROMPTS_DIR / "passage-cuts" / "tool-v001.json")),
    )
    fallback = ModelClient(
        "fallback/model", api_base="https://example.invalid/v1", transport=transport,
        extra=load_tool(str(PROMPTS_DIR / "passage-cuts" / "tool-v001.json")),
    )
    client = source_cleanup_jobs.ResilientToolClient(primary, fallback)

    client.complete("numbered blocks")

    assert calls == ["primary/model"]
