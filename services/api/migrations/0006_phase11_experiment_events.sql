CREATE TABLE IF NOT EXISTS audit.experiment_events (
    event_id TEXT PRIMARY KEY CHECK (event_id LIKE 'audit-evt-%'),
    kind TEXT NOT NULL,
    run_id TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('info','warn','error')) DEFAULT 'info',
    payload JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS experiment_events_occurred_at_idx
    ON audit.experiment_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS experiment_events_run_id_idx
    ON audit.experiment_events (run_id);
CREATE INDEX IF NOT EXISTS experiment_events_kind_idx
    ON audit.experiment_events (kind);
