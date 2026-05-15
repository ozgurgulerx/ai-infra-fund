CREATE TABLE IF NOT EXISTS audit.backtest_requests (
    request_id TEXT PRIMARY KEY CHECK (request_id LIKE 'backtest-req-%'),
    strategy_id TEXT NOT NULL,
    dataset_snapshot_ids TEXT[] NOT NULL,
    validation_protocol TEXT NOT NULL,
    cost_assumptions JSONB NOT NULL,
    pipeline_inputs JSONB NOT NULL,
    formula_version TEXT NOT NULL,
    model_run_id TEXT NOT NULL,
    git_sha TEXT NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued','leased','running','succeeded','failed')),
    leased_by TEXT,
    lease_expires_at TIMESTAMPTZ,
    attempt_count INT NOT NULL DEFAULT 0,
    backtest_run_id TEXT,
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS backtest_requests_status_idx
    ON audit.backtest_requests (status, created_at);
CREATE INDEX IF NOT EXISTS backtest_requests_strategy_idx
    ON audit.backtest_requests (strategy_id);
