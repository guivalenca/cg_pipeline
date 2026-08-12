"""A running worker keeps exclusive ownership during slow provider work."""

import threading
import time

import psycopg
import pytest
from psycopg.types.json import Jsonb

from universe.acquisition.job_lease import (
    JobLease,
    JobLeaseLost,
    JobLeaseUnavailable,
)
from universe.acquisition.runner import claim_next_job


def test_job_lease_bounds_a_connection_factory_that_does_not_return():
    release = threading.Event()
    started = threading.Event()

    def blocked_connect():
        started.set()
        release.wait(timeout=5)
        raise psycopg.OperationalError("connection attempt remained unavailable")

    before = time.monotonic()
    try:
        with pytest.raises(JobLeaseUnavailable, match="renewal timed out"):
            with JobLease(
                blocked_connect,
                table="acquisition_job",
                row_id="acq-bounded-connect",
                claim_token="bounded-connect-worker",
                lease_seconds=1,
                heartbeat_seconds=0.1,
                operation_timeout_seconds=0.03,
            ):
                raise AssertionError("work must not start without a renewed lease")
        assert started.wait(timeout=0.1)
        assert time.monotonic() - before < 0.2
    finally:
        release.set()


def test_job_lease_sets_a_server_timeout_before_the_renewal_statement():
    release = threading.Event()
    timeout_values = []

    class Result:
        rowcount = 1

    class BlockingStatementConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, statement, params=()):
            if isinstance(statement, str) and "set_config" in statement:
                timeout_values.append(params[0])
                return Result()
            release.wait(timeout=5)
            return Result()

    try:
        with pytest.raises(JobLeaseUnavailable, match="renewal timed out"):
            with JobLease(
                BlockingStatementConnection,
                table="acquisition_job",
                row_id="acq-bounded-statement",
                claim_token="bounded-statement-worker",
                lease_seconds=1,
                heartbeat_seconds=0.1,
                operation_timeout_seconds=0.03,
            ):
                raise AssertionError("work must not start before renewal")
        assert timeout_values == ["30ms"]
    finally:
        release.set()


def test_job_lease_shutdown_does_not_wait_forever_for_its_heartbeat_thread():
    release = threading.Event()

    class Result:
        rowcount = 1

    class ImmediateConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _statement, _params=()):
            return Result()

    class StuckHeartbeatLease(JobLease):
        def _run(self):
            release.wait(timeout=0.25)

    before = time.monotonic()
    try:
        with StuckHeartbeatLease(
            ImmediateConnection,
            table="acquisition_job",
            row_id="acq-bounded-shutdown",
            claim_token="bounded-shutdown-worker",
            lease_seconds=1,
            heartbeat_seconds=0.1,
            operation_timeout_seconds=0.03,
        ):
            pass
        assert time.monotonic() - before < 0.15
    finally:
        release.set()


def test_job_lease_keeps_a_slow_claim_exclusive_then_stops_renewing(
    db, test_database_url
):
    source_id = "source-job-lease-slow-claim"
    job_id = "acq-job-lease-slow-claim"
    claim_token = "original-worker"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Lease test', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/lease"})),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, claimed_at, claim_token,"
        "  lease_expires_at)"
        " VALUES (%s, %s, 'running', 'firecrawl/v2', now(), %s,"
        "  now() + interval '120 milliseconds')",
        (job_id, source_id, claim_token),
    )
    db.commit()

    def connect():
        return psycopg.connect(test_database_url)

    with JobLease(
        connect,
        table="acquisition_job",
        row_id=job_id,
        claim_token=claim_token,
        lease_seconds=0.12,
        heartbeat_seconds=0.03,
    ):
        time.sleep(0.3)
        with connect() as contender:
            assert claim_next_job(contender, job_id=job_id) is None

    time.sleep(0.2)
    with connect() as contender:
        reclaimed = claim_next_job(contender, job_id=job_id)

    assert reclaimed is not None
    assert reclaimed["attempt_count"] == 1
    assert reclaimed["claim_token"] != claim_token


def test_job_lease_rejects_a_stale_claim_token_before_work_starts(
    db, test_database_url
):
    source_id = "source-job-lease-stale-token"
    job_id = "acq-job-lease-stale-token"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Stale lease test', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/stale"})),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, claimed_at, claim_token,"
        "  lease_expires_at)"
        " VALUES (%s, %s, 'running', 'firecrawl/v2', now(), 'new-owner',"
        "  now() + interval '1 minute')",
        (job_id, source_id),
    )
    db.commit()

    with pytest.raises(JobLeaseLost, match="lease lost"):
        with JobLease(
            lambda: psycopg.connect(test_database_url),
            table="acquisition_job",
            row_id=job_id,
            claim_token="stale-owner",
            lease_seconds=1,
            heartbeat_seconds=0.1,
        ):
            raise AssertionError("a stale worker must never enter provider work")


def test_job_lease_recovers_from_a_transient_heartbeat_connection_failure(
    db, test_database_url
):
    source_id = "source-job-lease-transient-db"
    job_id = "acq-job-lease-transient-db"
    claim_token = "resilient-worker"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Transient lease test', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/transient"})),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, claimed_at, claim_token,"
        "  lease_expires_at)"
        " VALUES (%s, %s, 'running', 'firecrawl/v2', now(), %s,"
        "  now() + interval '1 second')",
        (job_id, source_id, claim_token),
    )
    db.commit()

    recovered = threading.Event()
    calls = 0

    def flaky_connect():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise psycopg.OperationalError("temporary heartbeat outage")
        if calls >= 3:
            recovered.set()
        return psycopg.connect(test_database_url)

    with JobLease(
        flaky_connect,
        table="acquisition_job",
        row_id=job_id,
        claim_token=claim_token,
        lease_seconds=1,
        heartbeat_seconds=0.02,
    ):
        assert recovered.wait(timeout=1), "heartbeat did not retry after the outage"


def test_a_last_transient_heartbeat_error_does_not_discard_completed_work(
    db, test_database_url
):
    source_id = "source-job-lease-last-tick"
    job_id = "acq-job-lease-last-tick"
    claim_token = "finishing-worker"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Last tick test', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/last-tick"})),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, claimed_at, claim_token,"
        "  lease_expires_at)"
        " VALUES (%s, %s, 'running', 'firecrawl/v2', now(), %s,"
        "  now() + interval '1 second')",
        (job_id, source_id, claim_token),
    )
    db.commit()
    heartbeat_failed = threading.Event()
    calls = 0

    def fail_one_heartbeat():
        nonlocal calls
        calls += 1
        if calls == 2:
            heartbeat_failed.set()
            raise psycopg.OperationalError("last heartbeat was interrupted")
        return psycopg.connect(test_database_url)

    with JobLease(
        fail_one_heartbeat,
        table="acquisition_job",
        row_id=job_id,
        claim_token=claim_token,
        lease_seconds=1,
        heartbeat_seconds=0.02,
    ):
        assert heartbeat_failed.wait(timeout=1)


def test_job_lease_reports_token_takeover_when_provider_work_returns(
    db, test_database_url
):
    source_id = "source-job-lease-takeover"
    job_id = "acq-job-lease-takeover"
    claim_token = "worker-before-takeover"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Takeover test', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/takeover"})),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, claimed_at, claim_token,"
        "  lease_expires_at)"
        " VALUES (%s, %s, 'running', 'firecrawl/v2', now(), %s,"
        "  now() + interval '1 second')",
        (job_id, source_id, claim_token),
    )
    db.commit()
    heartbeat_started = threading.Event()
    takeover_finished = threading.Event()
    calls = 0

    def controlled_connect():
        nonlocal calls
        calls += 1
        if calls == 2:
            heartbeat_started.set()
            assert takeover_finished.wait(timeout=1)
        return psycopg.connect(test_database_url)

    with pytest.raises(JobLeaseLost, match="lease lost"):
        with JobLease(
            controlled_connect,
            table="acquisition_job",
            row_id=job_id,
            claim_token=claim_token,
            lease_seconds=1,
            heartbeat_seconds=0.02,
        ):
            assert heartbeat_started.wait(timeout=1)
            with psycopg.connect(test_database_url) as contender:
                contender.execute(
                    "UPDATE acquisition_job SET claim_token = 'new-worker'"
                    " WHERE id = %s",
                    (job_id,),
                )
            takeover_finished.set()
