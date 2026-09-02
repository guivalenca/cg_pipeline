"""Source-publication pilot web application."""

import os
from collections.abc import Callable

import psycopg
from fastapi import FastAPI

from universe.assets import AssetStore, asset_store_from_env
from universe.db import connect as default_connect
from universe.web import acquisition_app
connect = default_connect

# Keep the acquisition helpers import-compatible for tests and local tools.
_diagnostic_message = acquisition_app._diagnostic_message
_image_failure_message = acquisition_app._image_failure_message
_summarize_image_counts = acquisition_app._summarize_image_counts
_latest_source_state = acquisition_app._latest_source_state
_work_one = acquisition_app._work_one
acquisition_poll_seconds = acquisition_app.acquisition_poll_seconds


async def _worker_loop(
    connect_factory,
    asset_store_factory,
    stop,
    video_adapter_factory=None,
):
    """Run the acquisition loop while honoring wrapper-level test hooks."""
    acquisition_app._work_one = _work_one
    acquisition_app.acquisition_poll_seconds = acquisition_poll_seconds
    return await acquisition_app._worker_loop(
        connect_factory,
        asset_store_factory,
        stop,
        video_adapter_factory,
    )


def create_app(
    connect_factory: Callable[[], psycopg.Connection] | None = None,
    *,
    start_worker: bool = False,
    asset_store_factory: Callable[[], AssetStore] = asset_store_from_env,
    video_adapter_factory=acquisition_app.YtDlpYouTubeAdapter,
    companion_namespace_provider: Callable[[], dict] | None = None,
) -> FastAPI:
    """Create the syllabus and Source Publication application."""
    connect_factory = connect_factory or connect
    return acquisition_app.create_app(
        connect_factory,
        start_worker=start_worker,
        asset_store_factory=asset_store_factory,
        video_adapter_factory=video_adapter_factory,
        companion_namespace_provider=companion_namespace_provider,
    )


app = create_app(
    start_worker=os.environ.get("ACQUISITION_WORKER_IN_WEB", "0") == "1"
)
