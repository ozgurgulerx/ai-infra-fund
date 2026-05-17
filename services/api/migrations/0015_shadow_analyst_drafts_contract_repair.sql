DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'analyst'
          AND table_name = 'shadow_analyst_drafts'
          AND column_name = 'model_run_id'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'analyst'
          AND table_name = 'shadow_analyst_drafts'
          AND column_name = 'source_model_run_id'
    ) THEN
        ALTER TABLE analyst.shadow_analyst_drafts
            RENAME COLUMN model_run_id TO source_model_run_id;
    END IF;
END $$;

ALTER TABLE analyst.shadow_analyst_drafts
    DROP CONSTRAINT IF EXISTS shadow_analyst_drafts_scope_check;

UPDATE analyst.shadow_analyst_drafts
    SET scope = 'daily'
    WHERE scope = 'daily_brief';

ALTER TABLE analyst.shadow_analyst_drafts
    DROP CONSTRAINT IF EXISTS shadow_analyst_drafts_status_check;

ALTER TABLE analyst.shadow_analyst_drafts
    ADD CONSTRAINT shadow_analyst_drafts_scope_check
    CHECK (scope IN ('daily', 'ticker'));

ALTER TABLE analyst.shadow_analyst_drafts
    ADD CONSTRAINT shadow_analyst_drafts_status_check
    CHECK (status IN ('review_required', 'rejected', 'fallback', 'accepted_for_publication', 'denied'));

DROP INDEX IF EXISTS analyst.shadow_analyst_drafts_model_run_idx;

CREATE INDEX IF NOT EXISTS shadow_analyst_drafts_model_run_idx
    ON analyst.shadow_analyst_drafts (source_model_run_id);
