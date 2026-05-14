# Data Plan: PostgreSQL-First Local Storage

## Purpose

Define the storage architecture for the AI Infrastructure Fund Control Room.

The system is local-first and advisory-only. Cloud models may be used through Azure AI Foundry for allowed data classes, but portfolio facts, evidence metadata, run ledgers, recommendations, audits, deterministic outputs, and retrieval indexes should be stored locally by default.

The core storage rule is:

V1 uses PostgreSQL + pgvector as the only database. Relational facts, audit records, semantic retrieval, market snapshots, deterministic outputs, backtest summaries, and evaluation results live in PostgreSQL. Raw source files may live on the ignored local filesystem with metadata and hashes in PostgreSQL. DuckDB/Parquet is a future analytical scale-out option only, not a v1 dependency.

## Storage Responsibilities

Use PostgreSQL as the single v1 data spine with clear ownership.

| Layer | Technology | Owns | Does Not Own |
|---|---|---|---|
| Fact, audit, and analytics store | PostgreSQL | portfolio facts, evidence metadata, claims, market snapshots, factor rows, model runs, signal bundles, target weights, recommendations, audits, run ledger, backtest summaries, evaluation results | raw binary files, secrets |
| Semantic retrieval | PostgreSQL + pgvector | evidence chunk embeddings, claim embeddings, thesis/recommendation rationale embeddings, semantic search indexes | source-of-truth portfolio positions |
| Raw file store | ignored local filesystem | PDFs, CSVs, downloaded reports, exported artifacts | canonical metadata, facts, audit state |
| Future analytical scale-out | DuckDB + Parquet | optional large historical OHLCV/factor matrices and full backtest result frames if PostgreSQL becomes too slow | v1 canonical storage, recommendation truth |

PostgreSQL remains the only required database for v1.

## Why PostgreSQL + pgvector

Portfolio holdings and evidence claims should not be stored only as vectors. They are structured facts with ownership, timestamps, provenance, constraints, and foreign-key relationships.

PostgreSQL should be the default system of record because it provides:

- durable local storage
- transactions
- constraints and foreign keys
- migrations
- audit-friendly relational joins
- concurrent API and worker access
- pgvector semantic search
- clear backup and restore semantics

pgvector should be used for semantic retrieval over text-like objects:

- evidence chunks
- normalized evidence claims
- thesis map nodes
- recommendation rationales
- reviewer findings

Do not use vector search as the only way to retrieve portfolio facts. Use ordinary relational queries for positions, holdings, weights, scores, recommendations, and audit trails.

## Future Analytical Scale-Out

Do not implement DuckDB/Parquet in v1. Keep it as a future option if PostgreSQL becomes too slow for:

- fast local scans over price history
- technical indicator inputs
- factor matrices
- futures/proxy time series
- backtest result tables
- walk-forward splits
- Monte Carlo stress outputs
- exportable research datasets

If that point arrives, Parquet files can make large datasets portable and inspectable outside the application. Until then, PostgreSQL tables and materialized views are simpler, easier to migrate, easier to test, and sufficient for the private local dashboard.

DuckDB can support vector search through its VSS extension, but that should not be used for this system. The canonical retrieval store is PostgreSQL + pgvector.

## Data Classification

Every persisted object should have an explicit data class.

| Data Class | Examples | Default Storage | Cloud Model Allowed |
|---|---|---|---|
| public_market_data | yfinance OHLCV, public futures/proxy data | PostgreSQL | yes |
| public_evidence | public filings, press releases, public articles | PostgreSQL + pgvector | yes |
| user_portfolio | positions, cost basis, account labels, manual notes | PostgreSQL | only if explicitly allowed by task policy |
| private_research | user-supplied paid reports, private notes | PostgreSQL + pgvector local only | no by default |
| run_audit | model runs, signal bundles, recommendation audits | PostgreSQL | metadata only unless allowed |
| derived_analytics | factors, indicators, backtests, stress outputs | PostgreSQL | yes if no restricted source text |
| secrets | API keys, account credentials | environment/secret store only | never |

The model router must check data class before sending content to any cloud model.

## Canonical PostgreSQL Tables

### Portfolio And Universe

`positions`

- `position_id`
- `ticker`
- `quantity`
- `cost_basis`
- `currency`
- `account_label`
- `asset_type`
- `opened_at`
- `notes`
- `created_at`
- `updated_at`

`portfolio_snapshots`

- `snapshot_id`
- `as_of`
- `cash_value`
- `total_market_value`
- `source`
- `content_hash`
- `created_at`

`portfolio_snapshot_positions`

- `snapshot_id`
- `ticker`
- `quantity`
- `market_price`
- `market_value`
- `portfolio_weight`
- `unrealized_pnl`

`universe_members`

- `ticker`
- `name`
- `theme`
- `role`
- `watchlist_status`
- `max_weight`
- `liquidity_floor`
- `thesis_source`
- `created_at`
- `updated_at`

### Evidence

`evidence_items`

- `evidence_id`
- `source_uri`
- `source_type`
- `title`
- `publisher`
- `author`
- `published_at`
- `ingested_at`
- `content_hash`
- `license_label`
- `data_class`
- `tickers`
- `themes`
- `summary`
- `storage_uri`

`evidence_chunks`

- `chunk_id`
- `evidence_id`
- `chunk_index`
- `chunk_text`
- `span_ref`
- `content_hash`
- `embedding_model`
- `embedding`
- `created_at`

`evidence_claims`

- `claim_id`
- `evidence_id`
- `chunk_id`
- `ticker_or_theme`
- `claim_type`
- `direction`
- `magnitude`
- `time_horizon`
- `confidence`
- `quote_or_span_ref`
- `extracted_by_model_run_id`
- `validated_at`
- `created_at`

### Signals And Recommendations

`signal_bundles`

- `signal_bundle_id`
- `ticker`
- `as_of`
- `strategic_thesis_score`
- `tactical_technical_score`
- `forward_indicator_score`
- `portfolio_risk_score`
- `formula_versions`
- `input_snapshot_hash`
- `created_at`

`target_weights`

- `target_weights_id`
- `as_of`
- `portfolio_id`
- `cash_weight`
- `weights_json`
- `constraints_json`
- `source_signal_bundle_ids`
- `generated_by`
- `validation_status`
- `created_at`

`recommendation_artifacts`

- `recommendation_id`
- `ticker_or_portfolio`
- `advisory_label`
- `action`
- `horizon`
- `score_breakdown_json`
- `target_weights_id`
- `evidence_ids`
- `model_run_ids`
- `risks_json`
- `contradictions_json`
- `final_payload_json`
- `created_at`

`recommendation_audits`

- `audit_id`
- `recommendation_id`
- `target_weights_id`
- `signal_bundle_id`
- `evidence_ids`
- `model_run_ids`
- `deterministic_checks_json`
- `reviewer_findings_json`
- `schema_valid`
- `created_at`

### Runs And Models

`model_runs`

- `model_run_id`
- `task_role`
- `model_id`
- `deployment`
- `provider`
- `prompt_version`
- `input_hash`
- `output_hash`
- `latency_ms`
- `token_estimate_input`
- `token_estimate_output`
- `cost_estimate`
- `schema_valid`
- `retry_count`
- `data_classes`
- `created_at`

`run_artifacts`

- `run_id`
- `run_type`
- `started_at`
- `completed_at`
- `inputs_hash`
- `output_hash`
- `artifact_uri`
- `status`
- `error_summary`

`data_snapshots`

- `snapshot_id`
- `dataset_name`
- `as_of`
- `storage_uri`
- `content_hash`
- `row_count`
- `created_at`

### Governance

`data_entitlements`

- `entitlement_id`
- `source_name`
- `license_label`
- `allowed_uses`
- `cloud_model_allowed`
- `notes`
- `created_at`

`incident_records`

- `incident_id`
- `severity`
- `affected_artifacts`
- `freeze_status`
- `root_cause`
- `remediation`
- `reopen_criteria`
- `created_at`
- `resolved_at`

## pgvector Embedding Design

Use pgvector for embeddings on `evidence_chunks` and optional claim-level embeddings.

Local default embedding model:

- `bge-m3`
- local Ollama
- use for local/private evidence by default

Cloud optional embedding model:

- `text-embedding-3-small`
- Azure AI Foundry deployment
- only for allowed data classes

Because embedding dimensions can differ by model, use one of these approaches:

1. Keep separate embedding columns by model family.
2. Keep separate embedding tables per embedding model.
3. Use a fixed local-first default for v1 and migrate later if needed.

Recommended v1 approach:

- Use local `bge-m3` as the default embedding model.
- Store the embedding dimension in schema comments and migration metadata.
- Do not mix embedding dimensions in one vector column.

Example direction:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE evidence_chunks (
  chunk_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL REFERENCES evidence_items(evidence_id),
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  span_ref TEXT,
  content_hash TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding vector(1024),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX evidence_chunks_embedding_hnsw
ON evidence_chunks
USING hnsw (embedding vector_cosine_ops);
```

The exact vector dimension must match the embedding model used by implementation. If the chosen local embedding model produces a different dimension, update the migration before loading data.

## Local File Layout

Use a local data directory that is ignored by git.

Recommended layout:

```text
data/
  raw/
    market/
    filings/
    reports/
    manual/
  exports/
```

Store canonical metadata, hashes, data snapshots, backtest summaries, and recommendation artifacts in PostgreSQL. The filesystem stores raw source files and human-readable exports only.

If future analytical scale-out is added, document it in a separate spec and keep PostgreSQL as the canonical source of metadata and audit state.

## Data Flow

### Portfolio Import

1. User supplies positions as CSV or manual entry.
2. Validate ticker, quantity, cost basis, currency, and account label.
3. Insert or update `positions`.
4. Create a `portfolio_snapshot`.
5. Store derived weights in `portfolio_snapshot_positions`.
6. Do not embed portfolio holdings as semantic text unless creating a separate analyst-facing note.

### Evidence Ingestion

1. Source adapter fetches or receives content.
2. Store source metadata in `evidence_items`.
3. Save raw files under ignored local storage when permitted.
4. Compute `content_hash`.
5. Chunk text deterministically.
6. Create local embeddings using `bge-m3`.
7. Store chunks and embeddings in `evidence_chunks`.
8. Use model router to extract claims only if data class allows the selected model.
9. Store extracted claims in `evidence_claims`.

### Signal Computation

1. Load market/factor data, evidence claims, and portfolio facts from PostgreSQL.
3. Compute deterministic scores in Python.
4. Store `signal_bundles`.
5. Record formula versions and input hashes.

### Recommendation Generation

1. Load `signal_bundles`.
2. Generate `target_weights` deterministically.
3. Validate constraints.
4. Use LLMs only to explain and review.
5. Store `model_runs`.
6. Store `recommendation_artifacts`.
7. Store `recommendation_audits`.

## API Access Pattern

The FastAPI service should use PostgreSQL for app state, semantic retrieval, market snapshots, and v1 analytics.

Recommended pattern:

- PostgreSQL connection pool for ordinary API requests.
- Worker service owns heavy ingestion, embeddings, backtests, and scheduled runs.
- API reads completed artifacts; it should not perform long-running computations inline.

For UI screens:

- Build frontend screens with `everything-claude-code:frontend-patterns` and verify critical flows with `everything-claude-code:e2e-testing` once the UI phase begins.
- Keep the interface modern, polished, dense, and scan-friendly for trading analysis.
- System architecture / ops-room view reads module status from test results, policy checks, run artifacts, health checks, data freshness records, and incident records.
- Portfolio view reads PostgreSQL.
- Evidence library reads PostgreSQL + pgvector.
- Signal detail reads PostgreSQL.
- Backtest/evaluation views read PostgreSQL summary and result tables.
- Recommendation audit view reads PostgreSQL.

## Migrations

Use a migration tool from the first implementation phase.

Recommended options:

- Alembic if the Python API uses SQLAlchemy.
- SQL migration files if using a lighter database layer.

Migrations must include:

- schema changes
- indexes
- pgvector extension setup
- foreign keys
- check constraints
- immutable audit table policies where feasible

Do not rely on ad hoc table creation from application code.

## Local PostgreSQL Setup Requirements

The implementation should assume local PostgreSQL with pgvector capability.

Required checks:

- PostgreSQL server is running locally.
- Database exists, for example `ai_infra_fund`.
- `vector` extension can be created.
- Application user has only required privileges.
- Connection settings come from environment variables or local ignored config.

Environment variables:

```text
AI_INFRA_FUND_DATABASE_URL=postgresql://...
AI_INFRA_FUND_DATA_DIR=...
```

Secrets and database URLs with credentials must not be committed.

## Backup And Recovery

Back up PostgreSQL and raw local files separately.

PostgreSQL backup should cover:

- portfolio facts
- evidence metadata
- evidence claims
- market snapshots
- factor and indicator rows
- model runs
- signal bundles
- backtest summaries
- evaluation results
- recommendations
- audits
- governance records

Raw file backup should cover source PDFs, CSVs, downloaded reports, and exported artifacts when permitted by data policy.

Every daily run should be reproducible from:

- PostgreSQL run metadata
- PostgreSQL market and data snapshot records
- PostgreSQL signal, recommendation, and evaluation records
- referenced data snapshot hashes
- model run hashes
- prompt versions
- formula versions

## Testing Requirements

Add data-layer tests early.

Unit tests:

- schema validation for contracts
- portfolio CSV validation
- content hash stability
- evidence chunking stability
- formula version presence

Integration tests:

- create pgvector extension
- insert and query evidence chunks
- run vector similarity query
- insert portfolio snapshot
- create signal bundle
- create target weights
- create recommendation artifact and audit
- ensure recommendation cannot exist without evidence IDs and advisory label

Architecture policy tests:

- no LLM client imports in deterministic scoring modules
- no model names hard-coded outside `config/model_profiles.yaml` and tests
- no live order or broker execution endpoint
- no private report paths committed
- PostgreSQL owns canonical facts and audit state
- PostgreSQL owns v1 market snapshots, derived analytics, backtest summaries, and evaluation results
- no DuckDB/Parquet dependency is required for v1

Data quality tests:

- no future data in backtest windows
- point-in-time snapshots are immutable
- duplicate evidence content hashes are handled deterministically
- stale evidence receives a staleness penalty before recommendation generation

## Storage Architecture To Use In All Plans

All plans should use:

- PostgreSQL + pgvector: canonical facts, portfolio records, trade journal, evidence metadata, evidence claims, embeddings, run ledger, model runs, market snapshots, factor rows, signal bundles, target weights, recommendation artifacts, audits, backtest summaries, evaluation results, and local semantic retrieval.
- Ignored local filesystem: raw PDFs, CSVs, downloaded reports, and human-readable exports.
- DuckDB + Parquet: future optional analytical scale-out only, not a v1 dependency.

Keep Azure Search optional. It may be useful later for hosted search, but it is not required for v1 local-first operation.

## Non-Goals For V1

- No live broker integration.
- No order execution storage.
- No cloud-only database dependency.
- No paid-report scraping.
- No arbitrary code execution from LLM-generated factor ideas.
- No vector-only source of truth for portfolio facts.
- No storing secrets in PostgreSQL or raw local files.

## Phase Alignment

- Phase 0 creates `docs/specs/0012-data-architecture.md` and architecture policy tests.
- Phase 1 defines data contracts and schema contracts.
- Phase 2 implements PostgreSQL + pgvector migrations, local environment example, data-class enum, evidence chunk embedding table, portfolio snapshot tables, trade journal persistence, position reconstruction persistence, market snapshot tables, backtest/evaluation summary tables, and storage ownership policy tests.
- Phase 3 adds model-router data-class checks before cloud model calls.
- Phase 5 adds embedding ingestion pipeline using local `bge-m3` and evidence provenance.
