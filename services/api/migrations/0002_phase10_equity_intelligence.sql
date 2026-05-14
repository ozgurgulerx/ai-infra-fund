CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS core.watched_equities (
    ticker TEXT PRIMARY KEY CHECK (ticker <> ''),
    company_name TEXT NOT NULL CHECK (company_name <> ''),
    exchange TEXT,
    asset_type TEXT NOT NULL DEFAULT 'equity' CHECK (asset_type IN ('equity', 'etf', 'cash', 'future', 'option', 'crypto', 'other')),
    active BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 0,
    tags TEXT[] NOT NULL DEFAULT '{}',
    thesis TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS watched_equities_active_priority_idx ON core.watched_equities (active, priority DESC, ticker);
CREATE INDEX IF NOT EXISTS watched_equities_tags_idx ON core.watched_equities USING gin (tags);

CREATE TABLE IF NOT EXISTS evidence.source_registry (
    source_id TEXT PRIMARY KEY CHECK (source_id <> ''),
    source_name TEXT NOT NULL CHECK (source_name <> ''),
    source_type TEXT NOT NULL CHECK (source_type <> ''),
    base_url TEXT NOT NULL CHECK (base_url <> ''),
    license_label TEXT NOT NULL CHECK (license_label <> ''),
    data_class TEXT NOT NULL CHECK (data_class IN ('public_market_data', 'public_evidence', 'user_portfolio', 'private_research', 'run_audit', 'derived_analytics', 'secrets')),
    reliability_score NUMERIC CHECK (reliability_score IS NULL OR (reliability_score >= 0 AND reliability_score <= 1)),
    metadata_json JSONB NOT NULL DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS source_registry_type_idx ON evidence.source_registry (source_type);
CREATE INDEX IF NOT EXISTS source_registry_data_class_idx ON evidence.source_registry (data_class);
CREATE INDEX IF NOT EXISTS source_registry_active_idx ON evidence.source_registry (active);

CREATE TABLE IF NOT EXISTS evidence.source_frontier_urls (
    frontier_url_id TEXT PRIMARY KEY CHECK (frontier_url_id <> ''),
    source_id TEXT NOT NULL REFERENCES evidence.source_registry(source_id) ON DELETE CASCADE,
    url TEXT NOT NULL CHECK (url <> ''),
    url_hash TEXT NOT NULL CHECK (url_hash <> ''),
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 0,
    discovered_at TIMESTAMPTZ NOT NULL,
    next_attempt_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'leased', 'captured', 'retry', 'failed', 'skipped')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    leased_by TEXT,
    lease_expires_at TIMESTAMPTZ,
    last_error_summary TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, url_hash)
);

CREATE INDEX IF NOT EXISTS source_frontier_urls_ticker_priority_idx ON evidence.source_frontier_urls (ticker, priority DESC);
CREATE INDEX IF NOT EXISTS source_frontier_urls_due_idx ON evidence.source_frontier_urls (status, next_attempt_at, priority DESC);
CREATE INDEX IF NOT EXISTS source_frontier_urls_lease_idx ON evidence.source_frontier_urls (lease_expires_at);

CREATE TABLE IF NOT EXISTS evidence.source_refresh_jobs (
    refresh_job_id TEXT PRIMARY KEY CHECK (refresh_job_id <> ''),
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    reason TEXT NOT NULL CHECK (reason <> ''),
    priority_boost INTEGER NOT NULL DEFAULT 0,
    requested_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS source_refresh_jobs_ticker_requested_idx ON evidence.source_refresh_jobs (ticker, requested_at DESC);
CREATE INDEX IF NOT EXISTS source_refresh_jobs_status_idx ON evidence.source_refresh_jobs (status);

CREATE TABLE IF NOT EXISTS evidence.crawl_frontier_queue (
    queue_id TEXT PRIMARY KEY CHECK (queue_id <> ''),
    frontier_url_id TEXT NOT NULL REFERENCES evidence.source_frontier_urls(frontier_url_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('queued', 'leased', 'captured', 'retry', 'failed', 'skipped')),
    next_attempt_at TIMESTAMPTZ NOT NULL,
    leased_by TEXT,
    lease_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (frontier_url_id)
);

CREATE INDEX IF NOT EXISTS crawl_frontier_queue_due_idx ON evidence.crawl_frontier_queue (status, next_attempt_at, priority DESC);
CREATE INDEX IF NOT EXISTS crawl_frontier_queue_ticker_idx ON evidence.crawl_frontier_queue (ticker);

CREATE TABLE IF NOT EXISTS evidence.source_raw_captures (
    capture_id TEXT PRIMARY KEY CHECK (capture_id <> ''),
    frontier_url_id TEXT REFERENCES evidence.source_frontier_urls(frontier_url_id) ON DELETE SET NULL,
    source_id TEXT NOT NULL REFERENCES evidence.source_registry(source_id) ON DELETE CASCADE,
    url TEXT NOT NULL CHECK (url <> ''),
    captured_at TIMESTAMPTZ NOT NULL,
    http_status INTEGER CHECK (http_status IS NULL OR (http_status >= 100 AND http_status <= 599)),
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    storage_uri TEXT NOT NULL CHECK (storage_uri <> ''),
    content_type TEXT,
    byte_size INTEGER CHECK (byte_size IS NULL OR byte_size >= 0),
    metadata_json JSONB NOT NULL DEFAULT '{}',
    embedding vector(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS source_raw_captures_content_hash_idx ON evidence.source_raw_captures (content_hash);
CREATE INDEX IF NOT EXISTS source_raw_captures_source_captured_idx ON evidence.source_raw_captures (source_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS source_raw_captures_frontier_url_idx ON evidence.source_raw_captures (frontier_url_id);

CREATE TABLE IF NOT EXISTS signals.equity_events (
    event_id TEXT PRIMARY KEY CHECK (event_id <> ''),
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type <> ''),
    event_time TIMESTAMPTZ NOT NULL,
    source_capture_id TEXT REFERENCES evidence.source_raw_captures(capture_id) ON DELETE SET NULL,
    summary TEXT NOT NULL CHECK (summary <> ''),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    metadata_json JSONB NOT NULL DEFAULT '{}',
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS equity_events_content_hash_idx ON signals.equity_events (content_hash);
CREATE INDEX IF NOT EXISTS equity_events_ticker_time_idx ON signals.equity_events (ticker, event_time DESC);
CREATE INDEX IF NOT EXISTS equity_events_evidence_ids_idx ON signals.equity_events USING gin (evidence_ids);

CREATE TABLE IF NOT EXISTS signals.sentiment_snapshots (
    snapshot_id TEXT PRIMARY KEY CHECK (snapshot_id <> ''),
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    as_of TIMESTAMPTZ NOT NULL,
    source_capture_id TEXT REFERENCES evidence.source_raw_captures(capture_id) ON DELETE SET NULL,
    sentiment_score NUMERIC NOT NULL CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    confidence NUMERIC NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    drivers_json JSONB NOT NULL DEFAULT '{}',
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS sentiment_snapshots_content_hash_idx ON signals.sentiment_snapshots (content_hash);
CREATE INDEX IF NOT EXISTS sentiment_snapshots_ticker_as_of_idx ON signals.sentiment_snapshots (ticker, as_of DESC);

CREATE TABLE IF NOT EXISTS signals.technical_snapshots (
    snapshot_id TEXT PRIMARY KEY CHECK (snapshot_id <> ''),
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    as_of TIMESTAMPTZ NOT NULL,
    indicators_json JSONB NOT NULL DEFAULT '{}',
    trend_label TEXT NOT NULL CHECK (trend_label <> ''),
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS technical_snapshots_content_hash_idx ON signals.technical_snapshots (content_hash);
CREATE INDEX IF NOT EXISTS technical_snapshots_ticker_as_of_idx ON signals.technical_snapshots (ticker, as_of DESC);

CREATE TABLE IF NOT EXISTS signals.fundamental_snapshots (
    snapshot_id TEXT PRIMARY KEY CHECK (snapshot_id <> ''),
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    as_of TIMESTAMPTZ NOT NULL,
    metrics_json JSONB NOT NULL DEFAULT '{}',
    rating_label TEXT NOT NULL CHECK (rating_label <> ''),
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS fundamental_snapshots_content_hash_idx ON signals.fundamental_snapshots (content_hash);
CREATE INDEX IF NOT EXISTS fundamental_snapshots_ticker_as_of_idx ON signals.fundamental_snapshots (ticker, as_of DESC);

CREATE TABLE IF NOT EXISTS audit.equity_intelligence_runs (
    run_id TEXT PRIMARY KEY CHECK (run_id <> ''),
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
    source_refresh_job_ids TEXT[] NOT NULL DEFAULT '{}',
    frontier_url_ids TEXT[] NOT NULL DEFAULT '{}',
    capture_ids TEXT[] NOT NULL DEFAULT '{}',
    event_ids TEXT[] NOT NULL DEFAULT '{}',
    sentiment_snapshot_id TEXT REFERENCES signals.sentiment_snapshots(snapshot_id) ON DELETE SET NULL,
    technical_snapshot_id TEXT REFERENCES signals.technical_snapshots(snapshot_id) ON DELETE SET NULL,
    fundamental_snapshot_id TEXT REFERENCES signals.fundamental_snapshots(snapshot_id) ON DELETE SET NULL,
    summary_json JSONB NOT NULL DEFAULT '{}',
    model_run_ids TEXT[] NOT NULL DEFAULT '{}',
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS equity_intelligence_runs_ticker_started_idx ON audit.equity_intelligence_runs (ticker, started_at DESC);
CREATE INDEX IF NOT EXISTS equity_intelligence_runs_status_idx ON audit.equity_intelligence_runs (status);
CREATE INDEX IF NOT EXISTS equity_intelligence_runs_model_run_ids_idx ON audit.equity_intelligence_runs USING gin (model_run_ids);
