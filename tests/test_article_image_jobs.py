"""Durable article-image jobs never own the source Markdown lifecycle."""

import hashlib
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from PIL import Image
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from universe.acquisition.image_jobs import (
    DownloadedImage,
    ImageJobError,
    _analysis_failure_diagnostics,
    _validated_download,
    claim_next_source_image_analysis,
    download_public_image,
    finalize_article_image_association,
    insert_article_image_candidates,
    list_article_images_for_artifact,
    prepare_article_image_candidates,
    process_next_article_image,
    process_next_source_image_analysis,
    queue_source_image_analysis_if_ready,
)
from universe.acquisition.source_images import (
    SourceImageAnalysis,
    SourceImageBatchResult,
    input_manifest_hash,
    prompt_stamp,
)
from universe.assets import LocalAssetStore
from universe.migrate import migrate
from universe.model_client import ModelError
from universe.settings import openrouter_multimodal_provider_routing


def _batch_result(markdown, images, analyses, *, unresolved=None):
    prompt_ref, prompt_sha, _template = prompt_stamp()
    return SourceImageBatchResult(
        analyses={item.image_id: item for item in analyses},
        unresolved=unresolved or {},
        requested_model="fake/vision",
        response_model="fake/resolved",
        provider="Fake Provider",
        usage={"total_tokens": 10},
        duration_ms=4,
        prompt_ref=prompt_ref,
        prompt_sha=prompt_sha,
        input_manifest_hash=input_manifest_hash(markdown, images),
    )


def _png_body(color="white"):
    buffer = io.BytesIO()
    Image.new("RGB", (120, 80), color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(scope="module")
def article_image_db(test_database_url):
    """Keep durable image-job facts out of the session-wide backfill schema."""
    schema = "article_image_test"
    with psycopg.connect(test_database_url) as admin:
        admin.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        admin.commit()
    scoped_url = make_conninfo(
        test_database_url, options=f"-csearch_path={schema},public"
    )
    with psycopg.connect(scoped_url) as conn:
        migrate(conn)
        yield conn


def test_candidate_preparation_deduplicates_occurrences_without_semantic_filtering():
    markdown = """![Chart](https://cdn.example/chart.png)

![Chart again](https://cdn.example/chart.png)

![LinkedIn logo](https://cdn.example/linkedin-logo.png)
"""

    candidates = prepare_article_image_candidates(
        markdown,
        [
            "https://cdn.example/chart.png",
            "https://cdn.example/photo.jpg",
        ],
    )

    assert [item["original_url"] for item in candidates] == [
        "https://cdn.example/chart.png",
        "https://cdn.example/linkedin-logo.png",
        "https://cdn.example/photo.jpg",
    ]
    assert candidates[0]["status"] == "queued"
    assert len(candidates[0]["placement"]["occurrences"]) == 2
    assert candidates[0]["placement"]["discovered_by"] == [
        "markdown",
        "firecrawl_images",
    ]
    assert candidates[1]["status"] == "queued"
    assert candidates[2]["status"] == "queued"
    assert candidates[2]["failure_code"] is None


def test_candidate_preparation_never_drops_content_by_quantity():
    markdown = "\n".join(
        f"![Diagram {ordinal}](https://cdn.example/diagram-{ordinal}.png)"
        for ordinal in range(1, 31)
    )

    candidates = prepare_article_image_candidates(markdown)

    assert len(candidates) == 30
    assert {item["status"] for item in candidates} == {"queued"}
    assert all(item["failure_code"] is None for item in candidates)


def test_article_asset_ordinal_above_50_persists(article_image_db, tmp_path):
    db = article_image_db
    markdown = "\n".join(
        f"![Diagram {ordinal}](https://cdn.example/diagram-{ordinal}.png)"
        for ordinal in range(1, 52)
    )
    ids = _parent_markdown(db, "ordinal-51", markdown)
    candidates = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=markdown,
    )
    db.commit()
    body = _png_body("purple")
    digest = hashlib.sha256(body).hexdigest()

    result = process_next_article_image(
        db,
        candidate_id=candidates[50]["id"],
        asset_store=LocalAssetStore(tmp_path / "ordinal-51-assets"),
        downloader=lambda url: DownloadedImage(
            body, "image/png", "diagram-51.png", url, 120, 80, digest
        ),
    )

    assert result["status"] == "downloaded"
    assert db.execute(
        "SELECT c.ordinal, a.ordinal, a.kind FROM source_image_candidate c"
        " JOIN source_asset a ON a.id = c.asset_id WHERE c.id = %s",
        (candidates[50]["id"],),
    ).fetchone() == (51, 51, "article_image")


def test_competing_workers_claim_one_source_call_once(
    article_image_db, test_database_url, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "single-source-claim",
        "# Lesson\n\n![Diagram](https://cdn.example/claim.png)\n",
    )
    candidate = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
    )[0]
    db.commit()
    body = _png_body("orange")
    digest = hashlib.sha256(body).hexdigest()
    process_next_article_image(
        db,
        candidate_id=candidate["id"],
        asset_store=LocalAssetStore(tmp_path / "claim-assets"),
        downloader=lambda url: DownloadedImage(
            body, "image/png", "claim.png", url, 120, 80, digest
        ),
    )
    call_id = db.execute(
        "SELECT id FROM source_image_analysis_call WHERE markdown_artifact_id = %s",
        (ids["artifact"],),
    ).fetchone()[0]
    db.commit()
    scoped_url = make_conninfo(
        test_database_url, options="-csearch_path=article_image_test,public"
    )
    barrier = threading.Barrier(2)

    def claim_once():
        with psycopg.connect(scoped_url) as worker:
            barrier.wait()
            return claim_next_source_image_analysis(worker, call_id=call_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(pool.map(lambda _index: claim_once(), range(2)))

    winners = [item for item in claimed if item is not None]
    assert len(winners) == 1
    assert winners[0]["id"] == call_id
    assert winners[0]["attempt_count"] == 1
    assert db.execute(
        "SELECT count(*) FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s",
        (ids["artifact"],),
    ).fetchone()[0] == 1


def test_interface_filenames_are_left_for_the_source_level_model():
    markdown = """![Social](https://cdn.example/linkedin.svg)

![Loader](https://cdn.example/preloader.png)

![Topology](https://cdn.example/linkedin-network-topology.png)
"""

    candidates = prepare_article_image_candidates(markdown)

    assert [item["status"] for item in candidates] == ["queued", "queued", "queued"]


def test_private_network_image_is_rejected_before_any_request():
    candidate = prepare_article_image_candidates(
        "![Internal](http://127.0.0.1/admin.png)"
    )[0]

    assert candidate["status"] == "failed"
    assert candidate["failure_code"] == "invalid_image_url"
    try:
        download_public_image("http://127.0.0.1/admin.png")
    except ImageJobError as exc:
        assert exc.code == "invalid_image_url"
    else:  # pragma: no cover - a regression would attempt a forbidden request
        raise AssertionError("private image URL was accepted")


@pytest.mark.parametrize(
    ("body", "declared", "expected_mime"),
    [
        (b"\x00\x00\x00\x18ftypavif\x00\x00\x00\x00fixture", "image/avif", "image/avif"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml", "image/svg+xml"),
    ],
)
def test_avif_and_svg_are_preserved_even_when_not_model_inputs(
    body, declared, expected_mime
):
    downloaded = _validated_download(
        body, declared, f"https://cdn.example/visual.{expected_mime.rsplit('/', 1)[-1]}"
    )

    assert downloaded.mime_type == expected_mime
    assert downloaded.sha256 == hashlib.sha256(body).hexdigest()


def test_avif_is_preserved_as_original_and_analyzed_through_png(
    article_image_db, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "preserved-avif",
        "# Lesson\n\n![Diagram](https://cdn.example/diagram.avif)\n",
    )
    candidate = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
    )[0]
    buffer = io.BytesIO()
    Image.new("RGB", (120, 80), "white").save(buffer, format="AVIF")
    body = buffer.getvalue()
    digest = hashlib.sha256(body).hexdigest()

    def download(url):
        return DownloadedImage(body, "image/avif", "diagram.avif", url, 0, 0, digest)

    def analyze(markdown, images):
        assert len(images) == 1
        assert images[0].model_image_url.startswith("data:image/jpeg;base64,")
        assert images[0].asset_sha256 == digest
        return _batch_result(
            markdown,
            images,
            [
                SourceImageAnalysis(
                    images[0].image_id,
                    True,
                    "information",
                    None,
                    "A white educational diagram.",
                    None,
                )
            ],
        )

    result = process_next_article_image(
        db,
        candidate_id=candidate["id"],
        asset_store=LocalAssetStore(tmp_path / "avif-assets"),
        downloader=download,
        analyzer=analyze,
    )

    assert result["status"] == "useful"
    assert result["failure_code"] is None
    assert result["asset_id"]
    assert result["diagnostics"]["source_mime_type"] == "image/avif"
    assert result["diagnostics"]["model_input_mime_type"] == "image/jpeg"
    assert result["diagnostics"]["model_input_converted"] is True
    enriched = db.execute(
        "SELECT body FROM artifact WHERE id = %s",
        (f"{ids['artifact']}:images",),
    ).fetchone()[0]
    assert f"![Diagram](/api/source-assets/{result['asset_id']})" in enriched
    assert "Image description: A white educational diagram." in enriched


def test_unsupported_svg_is_omitted_from_article_markdown_but_kept_in_the_ledger(
    article_image_db, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "preserved-svg",
        "# Lesson\n\n![Diagram](https://cdn.example/diagram.svg)\n",
    )
    candidate = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
    )[0]
    body = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    digest = hashlib.sha256(body).hexdigest()

    def download(url):
        return DownloadedImage(body, "image/svg+xml", "diagram.svg", url, 0, 0, digest)

    def unexpected_analysis(*_args):  # pragma: no cover - must not be called
        raise AssertionError("SVG should be preserved without a model call")

    result = process_next_article_image(
        db,
        candidate_id=candidate["id"],
        asset_store=LocalAssetStore(tmp_path / "svg-assets"),
        downloader=download,
        analyzer=unexpected_analysis,
    )

    assert result["status"] == "failed"
    assert result["failure_code"] == "image_analysis_unsupported_type"
    assert result["asset_id"]
    enriched = db.execute(
        "SELECT body FROM artifact WHERE id = %s",
        (f"{ids['artifact']}:images",),
    ).fetchone()[0]
    assert enriched.strip() == "# Lesson"
    assert "Image analysis: unresolved" not in enriched
    sidecar = list_article_images_for_artifact(db, f"{ids['artifact']}:images")
    assert sidecar[0]["status"] == "failed"
    assert sidecar[0]["failure_code"] == "image_analysis_unsupported_type"
    assert sidecar[0]["asset_url"] == f"/api/source-assets/{result['asset_id']}"


def test_relative_markdown_image_joins_the_source_url_without_duplication():
    candidate = prepare_article_image_candidates(
        "![Diagram](/media/diagram.png)",
        ["https://example.test/media/diagram.png"],
        base_url="https://example.test/lesson/week-1",
    )

    assert len(candidate) == 1
    assert candidate[0]["original_url"] == "https://example.test/media/diagram.png"
    assert candidate[0]["placement"]["discovered_by"] == [
        "markdown",
        "firecrawl_images",
    ]


def test_useful_image_is_external_audited_and_enriches_without_mutating_parent(
    article_image_db, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "useful",
        "# Lesson\n\n![Results](https://cdn.example/results.png)\n",
    )
    inserted = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
        firecrawl_urls=["https://cdn.example/results.png"],
    )
    db.commit()
    body = _png_body("blue")
    digest = hashlib.sha256(body).hexdigest()

    def download(url):
        assert url == "https://cdn.example/results.png"
        return DownloadedImage(
            body, "image/png", "results.png", url, 640, 480, digest
        )

    def analyze(markdown, images):
        assert "Lesson" in markdown
        assert len(images) == 1
        assert images[0].asset_sha256 == digest
        return _batch_result(
            markdown,
            images,
            [
                SourceImageAnalysis(
                    images[0].image_id,
                    True,
                    "information",
                    "2024 2025",
                    "A chart shows results increasing over time.",
                    None,
                )
            ],
        )

    result = process_next_article_image(
        db,
        candidate_id=inserted[0]["id"],
        asset_store=LocalAssetStore(tmp_path / "article-assets"),
        downloader=download,
        analyzer=analyze,
    )

    assert result["status"] == "useful"
    assert result["failure_code"] is None
    parent = db.execute(
        "SELECT status, artifact_id FROM acquisition_job WHERE id = %s",
        (ids["job"],),
    ).fetchone()
    assert parent == ("succeeded", ids["artifact"])
    assert db.execute(
        "SELECT body FROM artifact WHERE id = %s", (ids["artifact"],)
    ).fetchone()[0] == ids["markdown"]
    asset = db.execute(
        "SELECT storage_key, sha256, original_url FROM source_asset WHERE id = %s",
        (result["asset_id"],),
    ).fetchone()
    assert asset[0].startswith("sha256/")
    assert asset[1:] == (digest, "https://cdn.example/results.png")
    assert "body" not in {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'source_asset'"
        )
    }
    analysis = db.execute(
        "SELECT result, diagnostics FROM source_asset_analysis WHERE id = %s",
        (result["analysis_id"],),
    ).fetchone()
    assert analysis[0]["description"].startswith("A chart")
    assert analysis[0]["retain"] is True
    assert analysis[0]["reason_code"] == "information"
    assert analysis[1]["asset_sha256"] == digest
    assert "data:image" not in json.dumps(analysis[1])
    enriched = db.execute(
        "SELECT body, metadata FROM artifact WHERE id = %s",
        (f"{ids['artifact']}:images",),
    ).fetchone()
    assert f"/api/source-assets/{result['asset_id']}" in enriched[0]
    assert "Image description: A chart shows results increasing over time." in enriched[0]
    assert "OCR: 2024 2025" in enriched[0]
    assert enriched[1]["source_markdown_artifact_id"] == ids["artifact"]
    cleanup = db.execute(
        "SELECT acquisition_job_id, source_artifact_id, status"
        " FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (ids["job"],),
    ).fetchone()
    assert cleanup == (
        ids["job"],
        f"{ids['artifact']}:images",
        "queued",
    )
    sidecar = list_article_images_for_artifact(db, f"{ids['artifact']}:images")
    assert sidecar[0]["status"] == "useful"
    assert sidecar[0]["asset_url"] == f"/api/source-assets/{result['asset_id']}"


def test_two_downloads_produce_one_source_call_and_missing_result_omits_only_that_image(
    article_image_db, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "grouped-partial",
        (
            "# Lesson\n\n![Chart](https://cdn.example/chart.png)\n\n"
            "![Photo](https://cdn.example/photo.png)\n"
        ),
    )
    candidates = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
    )
    db.commit()
    bodies = {
        candidates[0]["original_url"]: _png_body("yellow"),
        candidates[1]["original_url"]: _png_body("purple"),
    }

    def download(url):
        body = bodies[url]
        return DownloadedImage(
            body,
            "image/png",
            url.rsplit("/", 1)[-1],
            url,
            120,
            80,
            hashlib.sha256(body).hexdigest(),
        )

    calls = []

    def analyze(markdown, images):
        calls.append([item.image_id for item in images])
        return _batch_result(
            markdown,
            images,
            [
                SourceImageAnalysis(
                    images[0].image_id,
                    True,
                    "information",
                    "92%",
                    "A result chart.",
                    None,
                )
            ],
            unresolved={images[1].image_id: "missing_result"},
        )

    first = process_next_article_image(
        db,
        candidate_id=candidates[0]["id"],
        asset_store=LocalAssetStore(tmp_path / "grouped-assets"),
        downloader=download,
    )
    assert first["status"] == "downloaded"
    assert calls == []

    second = process_next_article_image(
        db,
        candidate_id=candidates[1]["id"],
        asset_store=LocalAssetStore(tmp_path / "grouped-assets"),
        downloader=download,
        analyzer=analyze,
    )

    assert len(calls) == 1
    assert calls[0] == [candidates[0]["id"], candidates[1]["id"]]
    outcomes = db.execute(
        "SELECT id, status, failure_code FROM source_image_candidate"
        " WHERE markdown_artifact_id = %s ORDER BY ordinal",
        (ids["artifact"],),
    ).fetchall()
    assert outcomes == [
        (candidates[0]["id"], "useful", None),
        (candidates[1]["id"], "failed", "image_analysis_unavailable"),
    ]
    assert second["status"] == "failed"
    call = db.execute(
        "SELECT status, usage, diagnostics FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s",
        (ids["artifact"],),
    ).fetchone()
    assert call[0] == "succeeded"
    assert call[1] == {"total_tokens": 10}
    assert call[2]["unresolved"] == {candidates[1]["id"]: "missing_result"}
    assert db.execute(
        "SELECT count(*) FROM source_asset_analysis"
        " WHERE analysis_call_id = (SELECT id FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s)",
        (ids["artifact"],),
    ).fetchone()[0] == 1
    enriched = db.execute(
        "SELECT body FROM artifact WHERE id = %s",
        (f"{ids['artifact']}:images",),
    ).fetchone()[0]
    assert "# Lesson" in enriched
    assert "Image description: A result chart." in enriched
    assert "photo.png" not in enriched
    assert "Image analysis: unresolved" not in enriched
    sidecar = list_article_images_for_artifact(db, f"{ids['artifact']}:images")
    assert sidecar[1]["status"] == "failed"
    assert sidecar[1]["failure_code"] == "image_analysis_unavailable"
    assert sidecar[1]["asset_url"]


def test_image_analysis_failure_omits_article_image_but_text_and_ledger_survive(
    article_image_db, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "failed-analysis",
        "# Lesson\n\n![Diagram](https://cdn.example/diagram.png)\n",
    )
    candidate = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
    )[0]
    db.commit()
    body = _png_body("red")
    digest = hashlib.sha256(body).hexdigest()

    def download(url):
        return DownloadedImage(body, "image/png", "diagram.png", url, 20, 10, digest)

    def fail_analysis(*_args):
        raise RuntimeError("provider unavailable")

    result = process_next_article_image(
        db,
        candidate_id=candidate["id"],
        asset_store=LocalAssetStore(tmp_path / "failed-assets"),
        downloader=download,
        analyzer=fail_analysis,
    )

    assert result["status"] == "failed"
    assert result["failure_code"] == "image_analysis_failed"
    assert result["diagnostics"]["category"] == "image_analysis_failed"
    assert db.execute(
        "SELECT status, artifact_id FROM acquisition_job WHERE id = %s",
        (ids["job"],),
    ).fetchone() == ("succeeded", ids["artifact"])
    enriched = db.execute(
        "SELECT body FROM artifact WHERE id = %s",
        (f"{ids['artifact']}:images",),
    ).fetchone()[0]
    assert enriched.strip() == "# Lesson"
    assert "Image analysis: unresolved" not in enriched
    sidecar = list_article_images_for_artifact(db, f"{ids['artifact']}:images")
    assert sidecar[0]["status"] == "failed"
    assert sidecar[0]["failure_code"] == "image_analysis_failed"
    assert sidecar[0]["asset_url"] == f"/api/source-assets/{result['asset_id']}"


def test_changed_visual_outcome_creates_a_new_immutable_enrichment(
    article_image_db, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "enrichment-revision",
        "# Lesson\n\n![Diagram](https://cdn.example/diagram.png)\n",
    )
    candidate = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
    )[0]
    db.commit()
    db.execute(
        "UPDATE source_image_candidate SET status = 'failed',"
        " failure_code = 'image_analysis_failed', finished_at = now()"
        " WHERE id = %s",
        (candidate["id"],),
    )
    db.execute(
        "UPDATE source_image_analysis_call SET status = 'skipped',"
        " finished_at = now() WHERE markdown_artifact_id = %s",
        (ids["artifact"],),
    )
    db.commit()
    first_enrichment = finalize_article_image_association(db, ids["artifact"])
    body = _png_body("green")
    digest = hashlib.sha256(body).hexdigest()

    db.execute(
        "UPDATE source_image_candidate SET status = 'queued', failure_code = NULL,"
        " diagnostics = '{}', analysis_id = NULL, finished_at = NULL"
        " WHERE id = %s",
        (candidate["id"],),
    )
    db.execute(
        "UPDATE source_image_analysis_call SET status = 'waiting',"
        " failure_code = NULL, diagnostics = '{}', finished_at = NULL"
        " WHERE markdown_artifact_id = %s",
        (ids["artifact"],),
    )
    db.commit()

    def download(url):
        return DownloadedImage(body, "image/png", "diagram.png", url, 20, 10, digest)

    def analyze(markdown, images):
        return _batch_result(
            markdown,
            images,
            [
                SourceImageAnalysis(
                    images[0].image_id,
                    True,
                    "information",
                    "Diagram",
                    "A locally preserved diagram.",
                    None,
                )
            ],
        )

    process_next_article_image(
        db,
        candidate_id=candidate["id"],
        asset_store=LocalAssetStore(tmp_path / "revision-assets"),
        downloader=download,
        analyzer=analyze,
    )
    enrichments = db.execute(
        "SELECT id, body FROM artifact"
        " WHERE metadata->>'source_markdown_artifact_id' = %s"
        " ORDER BY created_at, id",
        (ids["artifact"],),
    ).fetchall()

    assert enrichments[0][0] == first_enrichment
    assert len(enrichments) == 2
    assert enrichments[1][0] != first_enrichment
    assert "/api/source-assets/" in enrichments[1][1]
    assert "A locally preserved diagram." in enrichments[1][1]


def test_openrouter_routing_failure_has_an_actionable_image_only_diagnostic():
    diagnostics = _analysis_failure_diagnostics(
        ModelError(
            "HTTP 404: No endpoints found that can handle the requested parameters"
        ),
        reference_id="article-image-ref:0001:test",
        asset_sha256="a" * 64,
    )

    assert diagnostics == {
        "category": "model_routing_unavailable",
        "exception": "ModelError",
        "reference_id": "article-image-ref:0001:test",
        "asset_sha256": "a" * 64,
        "provider_http_status": 404,
        "detail": "HTTP 404: No endpoints found that can handle the requested parameters",
    }


def test_multimodal_routing_keeps_privacy_and_fallbacks_without_metadata_filter():
    routing = openrouter_multimodal_provider_routing()

    assert routing == {"allow_fallbacks": True, "data_collection": "deny"}
    assert "require_parameters" not in routing


def test_interface_image_is_removed_only_after_the_grouped_model_decision(
    article_image_db, tmp_path
):
    db = article_image_db
    ids = _parent_markdown(
        db,
        "filtered",
        "# Lesson\n\n![LinkedIn logo](https://cdn.example/linkedin-logo.png)\n",
    )
    candidates = insert_article_image_candidates(
        db,
        acquisition_job_id=ids["job"],
        source_id=ids["source"],
        snapshot_id=ids["snapshot"],
        markdown_artifact_id=ids["artifact"],
        markdown=ids["markdown"],
    )
    db.commit()

    assert candidates[0]["status"] == "queued"
    body = _png_body("gray")
    digest = hashlib.sha256(body).hexdigest()

    def download(url):
        return DownloadedImage(body, "image/png", "logo.png", url, 120, 80, digest)

    def analyze(markdown, images):
        return _batch_result(
            markdown,
            images,
            [
                SourceImageAnalysis(
                    images[0].image_id,
                    False,
                    "interface",
                    "LinkedIn",
                    "A LinkedIn navigation logo.",
                    "No additional educational content.",
                )
            ],
        )

    result = process_next_article_image(
        db,
        candidate_id=candidates[0]["id"],
        asset_store=LocalAssetStore(tmp_path / "interface-assets"),
        downloader=download,
        analyzer=analyze,
    )
    enriched_id = f"{ids['artifact']}:images"

    assert result["status"] == "not_important"
    body = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (enriched_id,)
    ).fetchone()[0]
    assert "linkedin-logo" not in body
    raw_result = db.execute(
        "SELECT result FROM source_asset_analysis WHERE id = %s",
        (result["analysis_id"],),
    ).fetchone()[0]
    assert raw_result["retain"] is False
    assert raw_result["ocr"] == "LinkedIn"
    assert raw_result["description"] == "A LinkedIn navigation logo."


def _parent_markdown(db, suffix: str, markdown: str) -> dict[str, str]:
    source_id = f"source-image-job-{suffix}"
    snapshot_id = f"{source_id}:snap"
    artifact_id = f"{snapshot_id}:markdown"
    job_id = f"acq-image-job-{suffix}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, 'article')",
        (
            source_id,
            Jsonb({"canonical_url": f"https://example.test/{suffix}"}),
            f"Image lesson {suffix}",
        ),
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, captured_at, content_hash, status)"
        " VALUES (%s, %s, now(), %s, 'ok')",
        (snapshot_id, source_id, hashlib.sha256(markdown.encode()).hexdigest()),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'firecrawl-v2', %s)",
        (artifact_id, snapshot_id, markdown),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, attempt_count, artifact_id, finished_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', 1, %s, now())",
        (job_id, source_id, artifact_id),
    )
    db.commit()
    return {
        "source": source_id,
        "snapshot": snapshot_id,
        "artifact": artifact_id,
        "job": job_id,
        "markdown": markdown,
    }
