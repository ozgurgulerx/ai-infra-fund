ALTER TABLE audit.backtest_requests ADD COLUMN IF NOT EXISTS formula_version TEXT;
ALTER TABLE audit.backtest_requests ADD COLUMN IF NOT EXISTS model_run_id TEXT;
ALTER TABLE audit.backtest_requests ADD COLUMN IF NOT EXISTS git_sha TEXT;

UPDATE audit.backtest_requests
SET formula_version = 'legacy-backfill-v1'
WHERE formula_version IS NULL;

UPDATE audit.backtest_requests
SET model_run_id = 'model-run-legacy-backfill'
WHERE model_run_id IS NULL;

UPDATE audit.backtest_requests
SET git_sha = 'legacy-backfill'
WHERE git_sha IS NULL;

ALTER TABLE audit.backtest_requests ALTER COLUMN formula_version SET NOT NULL;
ALTER TABLE audit.backtest_requests ALTER COLUMN model_run_id SET NOT NULL;
ALTER TABLE audit.backtest_requests ALTER COLUMN git_sha SET NOT NULL;
