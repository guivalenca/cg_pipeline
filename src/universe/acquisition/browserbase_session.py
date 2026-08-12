"""Browserbase session lifecycle with the CDP URL confined to this Module."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


EventSink = Callable[[dict[str, Any]], None]


class BrowserbaseSessionError(RuntimeError):
    pass


@dataclass(frozen=True)
class BrowserbaseSessionConfig:
    api_key: str
    project_id: str = ""
    context_id: str = ""
    region: str = "us-west-2"
    timeout_seconds: int = 3600
    viewport_width: int = 2200
    viewport_height: int = 1800
    proxy_enabled: bool = False
    proxy_geolocation: Mapping[str, str] = field(default_factory=dict)
    user_metadata: Mapping[str, str] = field(default_factory=dict)


class BrowserbaseSession:
    def __init__(
        self,
        *,
        session_id: str,
        browser: Any,
        runtime: Any,
        client: Any,
        event_sink: EventSink,
    ) -> None:
        self.session_id = session_id
        self.browser = browser
        self._runtime = runtime
        self._client = client
        self._sink = event_sink
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        try:
            update = getattr(self._client.sessions, "update", None)
            if callable(update):
                update(self.session_id, status="REQUEST_RELEASE")
        except Exception:
            self._emit("browserbase_session_release_request_failed")
        finally:
            try:
                self.browser.close()
            finally:
                self._runtime.stop()
        self._emit("browserbase_session_released")

    def _emit(self, kind: str) -> None:
        try:
            self._sink({"kind": kind, "provider": "browserbase"})
        except Exception:
            pass


def open_browserbase_session(
    config: BrowserbaseSessionConfig,
    event_sink: EventSink | None = None,
) -> BrowserbaseSession:
    """Create and connect one session without exporting its transport URL."""
    if not config.api_key:
        raise BrowserbaseSessionError("Browserbase API key is missing")
    try:
        from browserbase import Browserbase
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise BrowserbaseSessionError(
            "Browserbase capture dependencies are unavailable"
        ) from None

    sink = event_sink or (lambda _event: None)
    client = Browserbase(api_key=config.api_key)
    request = _session_request(config)
    provider_session = None
    for attempt in range(1, 4):
        try:
            provider_session = client.sessions.create(**request)
            break
        except Exception as exc:
            if _status_code(exc) != 429 or attempt == 3:
                raise BrowserbaseSessionError("Browserbase session creation failed") from None
            time.sleep(min(30.0, float(2 ** (attempt - 1))))
    if provider_session is None:  # pragma: no cover
        raise BrowserbaseSessionError("Browserbase session creation failed")
    session_id = str(provider_session.id)
    runtime = sync_playwright().start()
    try:
        browser = runtime.chromium.connect_over_cdp(str(provider_session.connect_url))
    except Exception:
        runtime.stop()
        try:
            update = getattr(client.sessions, "update", None)
            if callable(update):
                update(session_id, status="REQUEST_RELEASE")
        except Exception:
            pass
        raise BrowserbaseSessionError("Browserbase session connection failed") from None
    try:
        sink({"kind": "browserbase_session_connected", "provider": "browserbase"})
    except Exception:
        pass
    return BrowserbaseSession(
        session_id=session_id,
        browser=browser,
        runtime=runtime,
        client=client,
        event_sink=sink,
    )


def create_browserbase_context(api_key: str) -> str:
    if not api_key:
        raise BrowserbaseSessionError("Browserbase API key is missing")
    try:
        from browserbase import Browserbase
    except ImportError:
        raise BrowserbaseSessionError("Browserbase SDK is unavailable") from None
    try:
        return str(Browserbase(api_key=api_key).contexts.create().id)
    except Exception:
        raise BrowserbaseSessionError("Browserbase context creation failed") from None


def _session_request(config: BrowserbaseSessionConfig) -> dict[str, Any]:
    browser_settings: dict[str, Any] = {
        "viewport": {
            "width": config.viewport_width,
            "height": config.viewport_height,
        }
    }
    if config.context_id:
        browser_settings["context"] = {"id": config.context_id, "persist": True}
    request: dict[str, Any] = {
        "region": config.region,
        "api_timeout": max(60, int(config.timeout_seconds)),
        "keep_alive": False,
        "user_metadata": dict(config.user_metadata),
        "browser_settings": browser_settings,
    }
    if config.project_id:
        request["project_id"] = config.project_id
    geolocation = {
        key: str(config.proxy_geolocation.get(key) or "").strip()
        for key in ("city", "state", "country")
        if str(config.proxy_geolocation.get(key) or "").strip()
    }
    if geolocation:
        request["proxies"] = [{"type": "browserbase", "geolocation": geolocation}]
    elif config.proxy_enabled:
        request["proxies"] = True
    return request


def _status_code(exc: Exception) -> int | None:
    value = getattr(exc, "status_code", None)
    if value is None:
        value = getattr(getattr(exc, "response", None), "status_code", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
