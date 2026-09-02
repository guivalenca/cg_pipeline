"""Exclusive local lease for one persistent Browserbase Context."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:  # pragma: no cover - Unix is the supported deployment runtime.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


EventSink = Callable[[dict[str, Any]], None]


class BrowserbaseContextLockTimeout(RuntimeError):
    pass


def browserbase_context_lock_key(identity: str) -> str:
    digest = hashlib.sha256(str(identity).encode("utf-8")).hexdigest()[:24]
    return f"concept-universe:browserbase-context:{digest}"


@dataclass
class BrowserbaseContextLock:
    identity: str
    lock_file: Path
    event_sink: EventSink | None = None
    wait_seconds: float = 3720
    poll_seconds: float = 0.1

    def __post_init__(self) -> None:
        self._sink = self.event_sink or (lambda _event: None)
        self._key = browserbase_context_lock_key(self.identity)
        self._backend = ""
        self._file_handle: Any | None = None

    def __enter__(self) -> BrowserbaseContextLock:
        self.acquire()
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.release()

    def acquire(self) -> None:
        started = time.monotonic()
        self._emit("browserbase_context_lock_waiting")
        acquired = self._acquire_file()
        waited = round(time.monotonic() - started, 3)
        if not acquired:
            self._emit("browserbase_context_lock_timeout", wait_seconds=waited)
            raise BrowserbaseContextLockTimeout(
                "timed out waiting for the shared Browserbase context"
            )
        self._emit(
            "browserbase_context_lock_acquired",
            lock_backend=self._backend,
            wait_seconds=waited,
        )

    def release(self) -> None:
        if self._backend == "file" and self._file_handle is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_UN)
            finally:
                self._file_handle.close()
        if self._backend:
            self._emit(
                "browserbase_context_lock_released", lock_backend=self._backend
            )
        self._backend = ""
        self._file_handle = None

    def _acquire_file(self) -> bool:
        self._backend = "file"
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock_file.open("a+b")
        self._file_handle = handle
        if fcntl is None:  # pragma: no cover
            return True
        deadline = time.monotonic() + max(0.0, float(self.wait_seconds))
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    handle.close()
                    self._file_handle = None
                    return False
                time.sleep(max(0.01, float(self.poll_seconds)))

    def _emit(self, kind: str, **details: Any) -> None:
        event = {
            "kind": kind,
            "provider": "browserbase",
            "lock_key": self._key.rsplit(":", 1)[-1],
            **details,
        }
        try:
            self._sink(event)
        except Exception:
            pass
