# Architecture

## Runtime Boundary

The v1 runtime is split into separate services:

- `web`: Next.js read-only control room. No direct database access and no business logic.
- `api`: FastAPI boundary for validation, repositories, read-only dashboard feeds, evidence, recommendations, evaluations, runs, agent bootstrap, and local journal APIs.
- `worker`: ingestion, crawl scheduling, evidence processing, deterministic analysis, backtests, advisory runs, and background jobs.
- `postgres`: PostgreSQL + pgvector, the v1 canonical data spine.
- `migrate`: one-shot migration runner.

Docker Compose is the local/runtime boundary. Cloud deployments should preserve the same service responsibilities.

## Data Spine

PostgreSQL + pgvector owns all v1 durable records:

- portfolio facts and local trade journal
- evidence metadata, chunks, claims, embeddings, captures, and crawl logs
- model runs and run artifacts
- market snapshots, factor rows, signal bundles, target weights
- recommendation artifacts and recommendation audits
- backtest, evaluation, incident, and data-quality records

Raw PDFs, CSVs, downloaded reports, private research files, and exports may live on ignored local filesystem paths. PostgreSQL stores metadata, hashes, provenance, and audit links.

DuckDB/Parquet is future optional analytical scale-out only. It is not a v1 dependency and must not become the source of truth for portfolio holdings or recommendations.

## Domain Boundary

Shared deterministic logic lives under `packages/core`. Product services call it rather than duplicating rules in API, worker, or UI code.

Core ownership:

- evidence contracts, adapters, chunks, claims, and embeddings
- AI equity intelligence watchlist/frontier/capture/event logic
- deterministic signals, technical/fundamental/sentiment integrations, valuation, and forward indicators
- portfolio constraints, target weights, trade comparison, and shadow simulation
- recommendation publication policy and audit checks
- evaluation, backtest, stress, bias, cost, and run artifacts
- model routing policy and profile loading

## Crawler Boundary

The crawler is advisory evidence ingestion, not trading execution. It uses the configurable AI equity watchlist, source registry, frontier queue, refresh jobs, captures, typed events, and audit logs to build an evidence-backed investment view. It must not create market action endpoints or UI controls.

## UI Boundary

The UI renders API data and local journal workflows. It must not contain scoring, routing, portfolio, or recommendation business logic. It must not expose order placement, broker connection, execution controls, or execution-like wording.
