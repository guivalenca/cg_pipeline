-- A refiner may ask to remove a visual whose analysis is unresolved. Preserve
-- that passage as unknown and stamp the structural override separately from
-- the model decision that remains in its run item.

ALTER TABLE passage_cleanup_result
    DROP CONSTRAINT passage_cleanup_result_policy_reason_check;

ALTER TABLE passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_policy_reason_check CHECK (
        policy_reason IS NULL
        OR policy_reason IN (
            'primary_enriched_image_preserved',
            'unresolved_image_preserved'
        )
    );
