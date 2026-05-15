-- Phase 10 crawl pipeline: per-attempt crawl log
-- Every fetch attempt (success, 304, or failure) writes one row here.
-- See docs/specs/0016 + 0017 — "each crawl attempt writes a run artifact or crawl log row".

CREATE TABLE IF NOT EXISTS evidence.crawl_logs (
    attempt_id TEXT PRIMARY KEY,
    frontier_url_id TEXT REFERENCES evidence.source_frontier_urls(frontier_url_id) ON DELETE SET NULL,
    ticker TEXT REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    source_id TEXT REFERENCES evidence.source_registry(source_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL,
    fetch_method TEXT NOT NULL CHECK (fetch_method IN ('http_get', 'http_head', 'http_304', 'stub', 'error')),
    http_status INTEGER,
    latency_ms INTEGER,
    bytes_fetched INTEGER,
    capture_id TEXT REFERENCES evidence.source_raw_captures(capture_id) ON DELETE SET NULL,
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS crawl_logs_ticker_attempted_idx
    ON evidence.crawl_logs (ticker, attempted_at DESC);

CREATE INDEX IF NOT EXISTS crawl_logs_attempted_idx
    ON evidence.crawl_logs (attempted_at DESC);
