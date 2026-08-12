-- A producer has finished every provider attempt before its deterministic
-- rows become queryable.  This durable intermediate state lets a successor
-- lease finish publication without buying the same provider work again.

ALTER TABLE run DROP CONSTRAINT run_status_check;
ALTER TABLE run ADD CONSTRAINT run_status_check
    CHECK (status IN ('running', 'publishing', 'done', 'failed'));
