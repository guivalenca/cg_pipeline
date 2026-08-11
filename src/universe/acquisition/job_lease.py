"""Keep a durable queue claim alive while its worker performs slow I/O."""

from __future__ import annotations

import logging
import math
import threading
from types import TracebackType
from typing import Callable

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from universe.db import database_url
from universe.settings import acquisition_lease_minutes


ConnectionFactory = Callable[[], psycopg.Connection]
LOGGER = logging.getLogger(__name__)

LEASE_TABLES = frozenset(
    {
        "acquisition_job",
        "source_image_candidate",
        "source_image_analysis_call",
        "source_cleanup_job",
        "video_stt_chunk",
    }
)


class JobLeaseLost(RuntimeError):
    """The durable claim no longer belongs to this worker token."""


class JobLeaseUnavailable(RuntimeError):
    """The claim could not be renewed within the bounded database window."""


def separate_connection_factory(
    conn: psycopg.Connection,
) -> ConnectionFactory:
    """Fallback factory for direct calls on the configured database server.

    Production dispatchers inject their own factory. Psycopg deliberately omits
    passwords from a live connection's DSN, so this fallback may borrow only
    the password from ``DATABASE_URL`` and refuses a different host or user.
    """
    parameters = conn.info.get_parameters()
    configured = conninfo_to_dict(database_url())
    for key in ("user", "host", "port"):
        expected = configured.get(key)
        observed = parameters.get(key)
        if expected and observed and expected != observed:
            raise RuntimeError(
                "a custom database connection requires an explicit"
                " lease_connection_factory"
            )
    overrides = {
        key: parameters[key]
        for key in ("dbname", "options")
        if parameters.get(key)
    }
    overrides["connect_timeout"] = "5"
    dsn = make_conninfo(database_url(), **overrides)
    return lambda: psycopg.connect(dsn)


class JobLease:
    """Renew one token-fenced claim on a dedicated database connection."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        table: str,
        row_id: str,
        claim_token: str,
        lease_seconds: float | None = None,
        heartbeat_seconds: float | None = None,
        operation_timeout_seconds: float = 5.0,
    ) -> None:
        if table not in LEASE_TABLES:
            raise ValueError(f"unsupported lease table: {table}")
        resolved_lease_seconds = (
            float(lease_seconds)
            if lease_seconds is not None
            else float(acquisition_lease_minutes()) * 60
        )
        resolved_heartbeat_seconds = (
            float(heartbeat_seconds)
            if heartbeat_seconds is not None
            else max(0.01, resolved_lease_seconds / 3)
        )
        resolved_operation_timeout = float(operation_timeout_seconds)
        if (
            resolved_lease_seconds <= 0
            or resolved_heartbeat_seconds <= 0
            or resolved_operation_timeout <= 0
        ):
            raise ValueError(
                "lease, heartbeat, and operation durations must be positive"
            )
        self._connection_factory = connection_factory
        self._table = table
        self._row_id = row_id
        self._claim_token = claim_token
        self._lease_seconds = resolved_lease_seconds
        self._heartbeat_seconds = resolved_heartbeat_seconds
        self._operation_timeout_seconds = resolved_operation_timeout
        self._stop = threading.Event()
        self._failure: BaseException | None = None
        self._thread: threading.Thread | None = None
        self._renew_inflight = threading.Lock()
        self._failure_lock = threading.Lock()

    def __enter__(self) -> JobLease:
        self._renew()
        self._thread = threading.Thread(
            target=self._run,
            name=f"job-lease-{self._row_id}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self._stop.set()
        assert self._thread is not None
        self._thread.join(timeout=self._operation_timeout_seconds)
        if self._thread.is_alive():
            LOGGER.warning(
                "lease heartbeat did not stop within %.3fs for %s %s",
                self._operation_timeout_seconds,
                self._table,
                self._row_id,
            )
        with self._failure_lock:
            failure = self._failure
        if exc_type is None and isinstance(failure, JobLeaseLost):
            raise failure
        if exc_type is None and failure is not None:
            try:
                self._renew()
            except JobLeaseLost:
                raise
            except Exception:
                # The caller's token-fenced terminal UPDATE remains the final
                # authority when PostgreSQL is still transiently unavailable.
                LOGGER.warning(
                    "could not verify lease during shutdown for %s %s",
                    self._table,
                    self._row_id,
                    exc_info=True,
                )
            else:
                with self._failure_lock:
                    if not isinstance(self._failure, JobLeaseLost):
                        self._failure = None
        return False

    def _run(self) -> None:
        while not self._stop.wait(self._heartbeat_seconds):
            try:
                self._renew()
            except JobLeaseLost as exc:
                with self._failure_lock:
                    self._failure = exc
                self._stop.set()
            except Exception as exc:
                # A database outage also prevents a competing worker from
                # claiming the row. Keep retrying so a brief outage does not
                # abandon an otherwise healthy long-running claim.
                with self._failure_lock:
                    if not isinstance(self._failure, JobLeaseLost):
                        self._failure = exc
                LOGGER.warning(
                    "transient lease heartbeat failure for %s %s",
                    self._table,
                    self._row_id,
                    exc_info=True,
                )
            else:
                with self._failure_lock:
                    if not isinstance(self._failure, JobLeaseLost):
                        self._failure = None

    def _renew(self) -> None:
        with self._failure_lock:
            if isinstance(self._failure, JobLeaseLost):
                raise self._failure
        if not self._renew_inflight.acquire(blocking=False):
            raise JobLeaseUnavailable(
                f"previous lease renewal is still running for"
                f" {self._table} {self._row_id}"
            )

        completed = threading.Event()
        outcome: dict[str, BaseException] = {}

        def renew_once() -> None:
            try:
                self._renew_once()
            except BaseException as exc:
                outcome["exception"] = exc
                if isinstance(exc, JobLeaseLost):
                    with self._failure_lock:
                        self._failure = exc
            finally:
                self._renew_inflight.release()
                completed.set()

        worker = threading.Thread(
            target=renew_once,
            name=f"job-lease-db-{self._row_id}",
            daemon=True,
        )
        try:
            worker.start()
        except BaseException:
            self._renew_inflight.release()
            raise
        if not completed.wait(self._operation_timeout_seconds):
            raise JobLeaseUnavailable(
                f"lease renewal timed out for {self._table} {self._row_id}"
            )
        failure = outcome.get("exception")
        if failure is not None:
            raise failure

    def _renew_once(self) -> None:
        statement = sql.SQL(
            "UPDATE {} SET lease_expires_at ="
            " now() + (%s * interval '1 second'), updated_at = now()"
            " WHERE id = %s AND status = 'running' AND claim_token = %s"
        ).format(sql.Identifier(self._table))
        with self._connection_factory() as conn:
            statement_timeout = (
                f"{max(1, math.ceil(self._operation_timeout_seconds * 1000))}ms"
            )
            conn.execute(
                "SELECT set_config('statement_timeout', %s, false)",
                (statement_timeout,),
            )
            updated = conn.execute(
                statement,
                (self._lease_seconds, self._row_id, self._claim_token),
            )
        if updated.rowcount != 1:
            raise JobLeaseLost(
                f"lease lost for {self._table} {self._row_id}"
            )
