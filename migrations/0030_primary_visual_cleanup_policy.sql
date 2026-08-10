-- A cleanup decision may be overridden by an explicit loss-prevention policy.
-- Keep the model run item as the interpretation fact and stamp the structural
-- policy separately instead of pretending the model returned another verdict.

ALTER TABLE passage_cleanup_result
    ADD COLUMN policy_reason TEXT;

ALTER TABLE passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_policy_reason_check CHECK (
        policy_reason IS NULL
        OR policy_reason = 'primary_enriched_image_preserved'
    );
