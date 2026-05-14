ALTER TABLE signals.equity_events
    ADD COLUMN IF NOT EXISTS available_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS evidence_claim_ids TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS model_run_ids TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'deterministic';

UPDATE signals.equity_events
SET available_at = event_time
WHERE available_at IS NULL;

ALTER TABLE signals.equity_events
    ALTER COLUMN available_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS equity_events_evidence_claim_ids_idx ON signals.equity_events USING gin (evidence_claim_ids);
CREATE INDEX IF NOT EXISTS equity_events_model_run_ids_idx ON signals.equity_events USING gin (model_run_ids);
CREATE INDEX IF NOT EXISTS equity_events_review_status_idx ON signals.equity_events (review_status);
