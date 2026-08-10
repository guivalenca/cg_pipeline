-- A lease needs an identity, not only an expiry timestamp.  Without a token,
-- an expired worker can finish while a later worker owns the same `running`
-- row and its status-only UPDATE is indistinguishable from the current claim.
--
-- Fence jobs held by binaries from before this migration too.  Their old
-- status-only finalizer cannot make the row terminal without clearing this
-- token, so PostgreSQL rejects that transaction (including any ledger rows it
-- inserted).  A new worker can reclaim the job when its lease expires.

ALTER TABLE acquisition_job
    ADD COLUMN claim_token TEXT;

UPDATE acquisition_job
SET claim_token = 'migration:' || id || ':' || attempt_count::text,
    lease_expires_at = COALESCE(lease_expires_at, now()),
    updated_at = now()
WHERE status = 'running';

ALTER TABLE acquisition_job
    ADD CONSTRAINT acquisition_job_claim_token_shape CHECK (
        (status = 'running' AND claim_token IS NOT NULL)
        OR (status <> 'running' AND claim_token IS NULL)
    );
