"""Exclusive cross-worker lease for one persistent Browserbase Context."""

from __future__ import annotations

import hashlib
import os
import threading
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
    redis_url: str | None = None
    wait_seconds: float = 3720
    lease_seconds: float = 300
    redis_client: Any | None = None
    poll_seconds: float = 0.1

    def __post_init__(self) -> None:
        self._sink = self.event_sink or (lambda _event: None)
        self._key = browserbase_context_lock_key(self.identity)
        self._backend = ""
        self._redis_lock: Any | None = None
        self._file_handle: Any | None = None
        self._renew_stop = threading.Event()
        self._renew_thread: threading.Thread | None = None

    def __enter__(self) -> BrowserbaseContextLock:
        self.acquire()
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.release()

    def acquire(self) -> None:
        started = time.monotonic()
        self._emit("browserbase_context_lock_waiting")
        acquired = self._acquire_redis() if self._redis_configured() else self._acquire_file()
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
        if self._backend == "redis":
            self._renew_stop.set()
            if self._renew_thread is not None:
                self._renew_thread.join(timeout=2)
            if self._redis_lock is not None:
                try:
                    self._redis_lock.release()
                except Exception:
                    self._emit("browserbase_context_lock_release_failed")
        elif self._backend == "file" and self._file_handle is not None:
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
        self._redis_lock = None
        self._file_handle = None

    def _redis_configured(self) -> bool:
        value = self.redis_url if self.redis_url is not None else os.getenv("REDIS_URL", "")
        return bool(str(value or "").strip())

    def _acquire_redis(self) -> bool:
        self._backend = "redis"
        client = self.redis_client
        if client is None:
            try:
                import redis
            except ImportError:
                self._emit("browserbase_context_lock_redis_unavailable")
                return False
            client = redis.Redis.from_url(
                str(self.redis_url if self.redis_url is not None else os.getenv("REDIS_URL", "")).strip(),
                socket_connect_timeout=3,
                socket_timeout=3,
                decode_responses=True,
            )
        try:
            lock = client.lock(
                self._key,
                timeout=max(30.0, float(self.lease_seconds)),
                blocking_timeout=max(0.0, float(self.wait_seconds)),
                thread_local=False,
            )
            if not lock.acquire(blocking=True):
                return False
        except Exception:
            # A configured Redis coordinates multiple containers. Failing over
            # to a local file here would permit concurrent context mutation.
            self._emit("browserbase_context_lock_redis_unavailable")
            return False
        self._redis_lock = lock
        self._renew_stop.clear()
        self._renew_thread = threading.Thread(
            target=self._renew_redis,
            name="concept-universe-browserbase-lock-renewal",
            daemon=True,
        )
        self._renew_thread.start()
        return True

    def _renew_redis(self) -> None:
        interval = max(5.0, float(self.lease_seconds) / 3)
        while not self._renew_stop.wait(interval):
            try:
                self._redis_lock.extend(
                    max(30.0, float(self.lease_seconds)), replace_ttl=True
                )
            except Exception:
                self._emit("browserbase_context_lock_renewal_failed")
                return

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
