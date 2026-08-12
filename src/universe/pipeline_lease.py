"""Durable, child-owned and token-fenced ownership of one pipeline stage.

The Module hides the compare-and-swap details behind a small Interface:
``acquire`` establishes one ownership generation, ``active``/``read`` inspect
it, and ``heartbeat``/``release`` can affect it only with that generation's
token.  An expired generation can never be revived, while ``acquire`` may
atomically replace it so an orphan cannot block the pipeline forever.

Every mutation is one atomic PostgreSQL statement. Transaction ownership is
deliberately left to the caller: a scheduler commits before launch, while the
launched worker renews its own generation and fences every ledger publication
in the same transaction as the write. Scheduler death therefore does not
expire a healthy child, and a replaced child cannot publish stale results.
"""

from __future__ import annotations

import math
import os
import threading
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.conninfo import make_conninfo

DEFAULT_TTL_SECONDS = 300.0
DEFAULT_HEARTBEAT_SECONDS = 60.0

_ENVIRONMENT = {
    "scope_key": "UNIVERSE_KC_LEASE_SCOPE",
    "stage": "UNIVERSE_KC_LEASE_STAGE",
    "token": "UNIVERSE_KC_LEASE_TOKEN",
    "owner_id": "UNIVERSE_KC_LEASE_OWNER",
}

_CURRENT_SUPERVISOR: ContextVar["LeaseSupervisor | None"] = ContextVar(
    "kc_pipeline_lease_supervisor", default=None
)


class LeaseLost(RuntimeError):
    """The model child no longer owns the generation that launched it."""


@dataclass(frozen=True, slots=True)
class Lease:
    """One immutable view of a pipeline lease ownership generation."""

    scope_key: str
    stage: str
    token: str
    owner_id: str
    acquired_at: datetime
    heartbeat_at: datetime
    expires_at: datetime


_COLUMNS = (
    "scope_key, stage, token, owner_id, acquired_at, heartbeat_at, expires_at"
)


def _required_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _ttl(ttl_seconds: float) -> float:
    if isinstance(ttl_seconds, bool):
        raise ValueError("ttl_seconds must be a finite positive number")
    try:
        value = float(ttl_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("ttl_seconds must be a finite positive number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError("ttl_seconds must be a finite positive number")
    return value


def _lease(row: tuple | None) -> Lease | None:
    return Lease(*row) if row is not None else None


def acquire(
    conn: psycopg.Connection,
    *,
    scope_key: str,
    stage: str,
    owner_id: str,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
) -> Lease | None:
    """Atomically claim ``(scope_key, stage)`` or replace an expired owner.

    Returns ``None`` while another unexpired generation owns the key.  The
    database clock determines expiry, avoiding scheduler-host clock skew.
    """
    scope_key = _required_text(scope_key, "scope_key")
    stage = _required_text(stage, "stage")
    owner_id = _required_text(owner_id, "owner_id")
    ttl = _ttl(ttl_seconds)
    token = uuid.uuid4().hex
    row = conn.execute(
        "INSERT INTO kc_pipeline_lease AS held"
        " (scope_key, stage, token, owner_id, acquired_at, heartbeat_at, expires_at)"
        " VALUES (%s, %s, %s, %s, clock_timestamp(), clock_timestamp(),"
        " clock_timestamp() + (%s * interval '1 second'))"
        " ON CONFLICT (scope_key, stage) DO UPDATE SET"
        " token = EXCLUDED.token,"
        " owner_id = EXCLUDED.owner_id,"
        " acquired_at = clock_timestamp(),"
        " heartbeat_at = clock_timestamp(),"
        " expires_at = clock_timestamp() + (%s * interval '1 second')"
        " WHERE held.expires_at <= clock_timestamp()"
        f" RETURNING {_COLUMNS}",
        (scope_key, stage, token, owner_id, ttl, ttl),
    ).fetchone()
    return _lease(row)


def read(
    conn: psycopg.Connection,
    *,
    scope_key: str,
    stage: str,
) -> Lease | None:
    """Return the stored generation, including an expired one."""
    scope_key = _required_text(scope_key, "scope_key")
    stage = _required_text(stage, "stage")
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM kc_pipeline_lease"
        " WHERE scope_key = %s AND stage = %s",
        (scope_key, stage),
    ).fetchone()
    return _lease(row)


def active(
    conn: psycopg.Connection,
    *,
    scope_key: str,
    stage: str,
) -> Lease | None:
    """Return the current generation only while its lease is unexpired."""
    scope_key = _required_text(scope_key, "scope_key")
    stage = _required_text(stage, "stage")
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM kc_pipeline_lease"
        " WHERE scope_key = %s AND stage = %s"
        " AND expires_at > clock_timestamp()",
        (scope_key, stage),
    ).fetchone()
    return _lease(row)


def heartbeat(
    conn: psycopg.Connection,
    lease: Lease,
    *,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
) -> Lease | None:
    """Extend an active generation, returning ``None`` if its token lost.

    Expired ownership cannot be revived, even if no successor has acquired it
    yet.  This makes expiry a one-way fencing event for the old worker.
    """
    if not isinstance(lease, Lease):
        raise TypeError("lease must be a Lease")
    ttl = _ttl(ttl_seconds)
    row = conn.execute(
        "UPDATE kc_pipeline_lease SET"
        " heartbeat_at = clock_timestamp(),"
        " expires_at = clock_timestamp() + (%s * interval '1 second')"
        " WHERE scope_key = %s AND stage = %s AND token = %s"
        " AND expires_at > clock_timestamp()"
        f" RETURNING {_COLUMNS}",
        (ttl, lease.scope_key, lease.stage, lease.token),
    ).fetchone()
    return _lease(row)


def release(conn: psycopg.Connection, lease: Lease) -> bool:
    """Delete this generation iff its ownership token still matches."""
    if not isinstance(lease, Lease):
        raise TypeError("lease must be a Lease")
    row = conn.execute(
        "DELETE FROM kc_pipeline_lease"
        " WHERE scope_key = %s AND stage = %s AND token = %s"
        " RETURNING token",
        (lease.scope_key, lease.stage, lease.token),
    ).fetchone()
    return row is not None


def fence(conn: psycopg.Connection, lease: Lease) -> bool:
    """Lock and validate an active token for the caller's next transaction.

    Call this immediately before a ledger mutation and commit that mutation in
    the same transaction. ``FOR UPDATE`` makes an expired-token takeover wait
    until the fenced write commits; a successor token makes the write fail
    closed instead.
    """
    if not isinstance(lease, Lease):
        raise TypeError("lease must be a Lease")
    row = conn.execute(
        "SELECT token FROM kc_pipeline_lease"
        " WHERE scope_key = %s AND stage = %s AND token = %s"
        " AND expires_at > clock_timestamp()"
        " FOR UPDATE",
        (lease.scope_key, lease.stage, lease.token),
    ).fetchone()
    return row is not None


def connection_dsn(conn: psycopg.Connection) -> str:
    """Clone a live connection target, including its hidden password."""
    params = conn.info.get_parameters()
    if password := conn.info.password:
        params["password"] = password
    return make_conninfo(**params)


def environment_present() -> bool:
    """Whether this process was launched with any pipeline lease identity."""
    return any(os.environ.get(name) for name in _ENVIRONMENT.values())


class LeaseSupervisor:
    """Child-owned heartbeat, provider check, and persistence fence.

    The scheduler is only the launcher. Once a model child starts, this object
    validates the inherited token on a dedicated autocommit connection and
    renews it from a child thread. Therefore scheduler death cannot let the
    lease expire underneath a still-running provider job. Any database error,
    expiry, release, or takeover marks ownership lost and all later checks fail
    closed.
    """

    def __init__(
        self,
        lease: Lease | None,
        control: psycopg.Connection | None,
        *,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_SECONDS,
    ) -> None:
        self._lease = lease
        self._control = control
        self._interval = _ttl(heartbeat_interval)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._lost_reason: str | None = None
        self._closed = False
        self._thread: threading.Thread | None = None
        if lease is not None:
            self._thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name=f"kc-child-lease-{lease.stage}",
            )
            self._thread.start()

    @classmethod
    def from_environment(
        cls,
        conn: psycopg.Connection,
        *,
        stage: str,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_SECONDS,
    ) -> "LeaseSupervisor":
        """Start supervision for a launched child, or a no-op for direct CLI use."""
        inherited = {
            name: os.environ.get(environment)
            for name, environment in _ENVIRONMENT.items()
        }
        if not any(inherited.values()):
            return cls(None, None, heartbeat_interval=heartbeat_interval)
        missing = [name for name, value in inherited.items() if not value]
        if missing:
            raise LeaseLost(
                "incomplete pipeline lease environment: " + ", ".join(missing)
            )
        if inherited["stage"] != stage:
            raise LeaseLost(
                "pipeline lease stage mismatch:"
                f" inherited {inherited['stage']}, runner requested {stage}"
            )

        control = psycopg.connect(connection_dsn(conn), autocommit=True)
        try:
            held = active(
                control,
                scope_key=inherited["scope_key"],
                stage=inherited["stage"],
            )
        except BaseException:
            control.close()
            raise
        if held is None or held.token != inherited["token"]:
            control.close()
            raise LeaseLost("pipeline lease ownership lost before child startup")
        if held.owner_id != inherited["owner_id"]:
            control.close()
            raise LeaseLost("pipeline lease owner does not match the launched child")
        return cls(
            held,
            control,
            heartbeat_interval=heartbeat_interval,
        )

    @property
    def enabled(self) -> bool:
        return self._lease is not None

    @property
    def lease(self) -> Lease | None:
        return self._lease

    def __enter__(self) -> "LeaseSupervisor":
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        self.close()

    def _lose(self, reason: str) -> None:
        self._lost_reason = reason
        self._stop.set()

    def _raise_if_lost(self) -> None:
        if self._lost_reason is not None:
            raise LeaseLost(f"pipeline lease ownership lost: {self._lost_reason}")
        if self._closed:
            raise LeaseLost("pipeline lease supervision is already closed")

    def verify(self) -> Lease | None:
        """Synchronously prove ownership immediately before provider work."""
        if not self.enabled:
            return None
        with self._lock:
            self._raise_if_lost()
            try:
                held = active(
                    self._control,
                    scope_key=self._lease.scope_key,
                    stage=self._lease.stage,
                )
            except psycopg.Error as exc:
                self._lose(f"database verification failed: {type(exc).__name__}")
                raise LeaseLost(
                    "pipeline lease ownership lost during database verification"
                ) from exc
            if held is None or held.token != self._lease.token:
                self._lose("token expired, was released, or was replaced")
                self._raise_if_lost()
            self._lease = held
            return held

    def before_provider_call(self) -> Lease | None:
        """Renew synchronously before spending on a provider attempt.

        This is stronger than a read-only check: a successful call starts with
        a fresh full TTL and the update is token fenced. The background child
        heartbeat still protects provider calls that run longer than one
        interval.
        """
        return self.heartbeat_now()

    def heartbeat_now(
        self,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> Lease | None:
        """Renew from the child process now; primarily useful for diagnostics."""
        if not self.enabled:
            return None
        with self._lock:
            self._raise_if_lost()
            try:
                refreshed = heartbeat(
                    self._control,
                    self._lease,
                    ttl_seconds=ttl_seconds,
                )
            except psycopg.Error as exc:
                self._lose(f"database heartbeat failed: {type(exc).__name__}")
                raise LeaseLost(
                    "pipeline lease ownership lost during child heartbeat"
                ) from exc
            if refreshed is None:
                self._lose("heartbeat token is no longer active")
                self._raise_if_lost()
            self._lease = refreshed
            return refreshed

    def fence(self, conn: psycopg.Connection) -> Lease | None:
        """Fence the caller's next ledger mutation in its own transaction."""
        if not self.enabled:
            return None
        with self._lock:
            self._raise_if_lost()
        try:
            owned = fence(conn, self._lease)
        except psycopg.Error as exc:
            with self._lock:
                self._lose(f"persistence fence failed: {type(exc).__name__}")
            raise LeaseLost(
                "pipeline lease ownership lost during persistence fence"
            ) from exc
        if not owned:
            with self._lock:
                self._lose("persistence token is no longer active")
                self._raise_if_lost()
        return self._lease

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self.heartbeat_now()
            except LeaseLost:
                return

    def close(self) -> None:
        """Stop supervision and token-fenced release after child completion."""
        if self._closed:
            return
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, min(self._interval, 5.0)))
        with self._lock:
            if self._control is not None:
                try:
                    if self._lease is not None:
                        release(self._control, self._lease)
                except psycopg.Error:
                    pass
                finally:
                    self._control.close()
            self._closed = True


def current_supervisor(*, required: bool = False) -> LeaseSupervisor | None:
    """Return the worker's authoritative supervisor.

    A lease-bearing process without the worker wrapper is invalid: allowing it
    to stamp or publish would recreate the unfenced-child failure this Module
    exists to prevent.
    """
    supervisor = _CURRENT_SUPERVISOR.get()
    if required and environment_present() and supervisor is None:
        raise LeaseLost(
            "pipeline lease environment requires child-owned supervision"
        )
    return supervisor


@contextmanager
def supervise(
    conn: psycopg.Connection,
    *,
    stage: str,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_SECONDS,
):
    """Bind exactly one authoritative supervisor around a child invocation."""
    existing = _CURRENT_SUPERVISOR.get()
    if existing is not None:
        if existing.enabled and existing.lease.stage != stage:
            raise LeaseLost(
                f"active pipeline lease is for {existing.lease.stage}, not {stage}"
            )
        yield existing
        return

    supervisor = LeaseSupervisor.from_environment(
        conn,
        stage=stage,
        heartbeat_interval=heartbeat_interval,
    )
    token = _CURRENT_SUPERVISOR.set(supervisor)
    try:
        yield supervisor
    except BaseException:
        # A fenced write owns the lease row until its transaction ends. Roll
        # it back before joining the heartbeat thread, otherwise a heartbeat
        # already waiting on that row could deadlock exception unwinding.
        try:
            conn.rollback()
        except psycopg.Error:
            pass
        raise
    finally:
        _CURRENT_SUPERVISOR.reset(token)
        supervisor.close()
