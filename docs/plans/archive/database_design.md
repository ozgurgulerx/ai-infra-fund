# Database Design: PostgreSQL And pgvector

## Purpose

Define the concrete database design for the AI Infrastructure Fund Control Room.

This design turns the data plan into an implementation-ready blueprint for PostgreSQL + pgvector. It should be used as the foundation for `docs/specs/0012-data-architecture.md`, Phase 2 migrations, data-layer tests, and storage ownership policy checks.

The core database rule is:

PostgreSQL + pgvector is the canonical local application database, semantic retrieval store, v1 analytical store, and audit ledger. Portfolio facts are relational; vectors are for evidence and semantic retrieval. Raw files may live on the ignored local filesystem with metadata and hashes in PostgreSQL. DuckDB/Parquet is a future analytical scale-out option only, not a v1 dependency.

## Design Goals

The database layer must support:

- local-first operation
- advisory-only recommendations
- deterministic scoring and target-weight generation
- auditability from recommendation back to evidence, signal, model run, and data snapshot
- point-in-time correctness for backtests and signal generation
- local semantic search over evidence chunks and claims
- safe handling of private research and paid reports
- reproducible daily and on-demand runs
- clear separation between canonical facts, semantic retrieval, and raw local files

## Storage Architecture

| Responsibility | Technology | Reason |
|---|---|---|
| Canonical facts | PostgreSQL | constraints, joins, transactions, migrations |
| Semantic retrieval | PostgreSQL + pgvector | local vector search tied to evidence metadata |
| Audit ledger | PostgreSQL | durable append-friendly records and foreign keys |
| Market/factor analytics | PostgreSQL | simplest v1 storage with migrations, constraints, and shared query path |
| Backtest/evaluation outputs | PostgreSQL | reproducible summary tables tied to run artifacts and data snapshots |
| Raw local files | ignored filesystem paths | PDFs, CSVs, downloaded reports, exports |
| Future analytical scale-out | DuckDB + Parquet | optional large matrix scans if PostgreSQL is later outgrown |

Do not introduce DuckDB/Parquet as a v1 dependency. Do not use vectors as the source of truth for portfolio holdings.

## Local Database Names And Environment

Recommended local database:

```text
ai_infra_fund
```

Recommended environment variables:

```text
AI_INFRA_FUND_DATABASE_URL=postgresql://localhost:5432/ai_infra_fund
AI_INFRA_FUND_DATA_DIR=./data
AI_INFRA_FUND_PRIVATE_REPORTS_DIR=./data/raw/reports/private
```

If credentials are required, place them only in local ignored files or a secret manager. Do not commit database URLs with passwords.

## Required Extensions

Required:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Recommended:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

`vector` enables pgvector columns and indexes. `pgcrypto` is useful for UUID generation and hashing helpers, although the application should still compute content hashes explicitly.

## Schema Namespaces

Use schemas to preserve domain boundaries.

```sql
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS evidence;
CREATE SCHEMA IF NOT EXISTS signals;
CREATE SCHEMA IF NOT EXISTS recommendations;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS governance;
```

Schema ownership:

| Schema | Owns |
|---|---|
| `core` | portfolio, universe, trade journal, snapshots |
| `evidence` | evidence items, chunks, claims, embeddings |
| `signals` | deterministic signal bundles and formula outputs |
| `recommendations` | target weights, recommendation artifacts, recommendation audits |
| `audit` | model runs, run artifacts, data snapshots |
| `governance` | data entitlements, incidents, data-quality checks, approvals |

## Naming Rules

- Use snake_case table and column names.
- Use text IDs where IDs are externally meaningful or content-addressable.
- Use UUIDs for internal generated IDs when no stable external ID exists.
- Use `created_at` on all tables.
- Use `updated_at` only where rows are mutable.
- Use `content_hash` for any source-derived record.
- Use `as_of`, `effective_at`, and `available_at` where point-in-time correctness matters.
- Keep raw model inputs/outputs out of audit tables unless the data class allows storage.

## Common Types

Use enums only when values are stable. Otherwise use constrained text.

Recommended enum-like constrained values:

- `data_class`: `public_market_data`, `public_evidence`, `user_portfolio`, `private_research`, `run_audit`, `derived_analytics`, `secrets`
- `trade_status`: `intended`, `paper`, `completed`, `cancelled`, `ignored`
- `trade_side`: `buy`, `sell`
- `asset_type`: `equity`, `etf`, `cash`, `future`, `option`, `crypto`, `other`
- `recommendation_action`: `core_buy`, `accumulate`, `hold`, `watch`, `trim`, `avoid`, `exit_candidate`
- `run_status`: `pending`, `running`, `succeeded`, `failed`, `cancelled`
- `incident_status`: `open`, `frozen`, `mitigated`, `resolved`

Prefer check constraints for v1 so migrations remain simple.

## Core Schema

### `core.positions`

Canonical current manual/imported position facts.

Columns:

- `position_id UUID PRIMARY KEY`
- `ticker TEXT NOT NULL`
- `quantity NUMERIC NOT NULL`
- `cost_basis NUMERIC`
- `currency TEXT NOT NULL DEFAULT 'USD'`
- `account_label TEXT`
- `asset_type TEXT NOT NULL`
- `opened_at DATE`
- `notes TEXT`
- `source TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(ticker)`
- `(account_label)`

Notes:

- This table is relational source-of-truth state, not vectorized text.
- Positions may be derived from trade journal in later phases; if so, this table can become a current-state materialization.

### `core.trade_entries`

Manual, paper, completed, cancelled, or ignored trade records.

Columns:

- `trade_id UUID PRIMARY KEY`
- `ticker TEXT NOT NULL`
- `side TEXT NOT NULL CHECK (side IN ('buy', 'sell'))`
- `quantity NUMERIC NOT NULL CHECK (quantity > 0)`
- `price NUMERIC`
- `fees NUMERIC DEFAULT 0`
- `trade_date DATE NOT NULL`
- `settlement_date DATE`
- `account_label TEXT`
- `status TEXT NOT NULL CHECK (status IN ('intended', 'paper', 'completed', 'cancelled', 'ignored'))`
- `source TEXT NOT NULL DEFAULT 'manual'`
- `notes TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(ticker, trade_date)`
- `(status)`
- `(account_label)`

Rules:

- This table must never transmit orders.
- There must be no broker API key, route, or execution state.

### `core.portfolio_snapshots`

Point-in-time portfolio summary snapshots.

Columns:

- `snapshot_id UUID PRIMARY KEY`
- `as_of TIMESTAMPTZ NOT NULL`
- `cash_value NUMERIC NOT NULL DEFAULT 0`
- `total_market_value NUMERIC NOT NULL`
- `source TEXT NOT NULL`
- `content_hash TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(as_of)`
- unique `(content_hash)`

### `core.portfolio_snapshot_positions`

Snapshot position lines.

Columns:

- `snapshot_id UUID NOT NULL REFERENCES core.portfolio_snapshots(snapshot_id)`
- `ticker TEXT NOT NULL`
- `quantity NUMERIC NOT NULL`
- `market_price NUMERIC`
- `market_value NUMERIC`
- `portfolio_weight NUMERIC`
- `unrealized_pnl NUMERIC`
- `PRIMARY KEY (snapshot_id, ticker)`

Indexes:

- `(ticker)`

### `core.universe_members`

Investable and watchlist universe.

Columns:

- `ticker TEXT PRIMARY KEY`
- `name TEXT`
- `theme TEXT`
- `role TEXT`
- `watchlist_status TEXT`
- `max_weight NUMERIC`
- `liquidity_floor NUMERIC`
- `thesis_source TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(theme)`
- `(watchlist_status)`

## Evidence Schema

### `evidence.evidence_items`

Source-level evidence record.

Columns:

- `evidence_id TEXT PRIMARY KEY`
- `source_uri TEXT NOT NULL`
- `source_type TEXT NOT NULL`
- `title TEXT`
- `publisher TEXT`
- `author TEXT`
- `published_at TIMESTAMPTZ`
- `ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `content_hash TEXT NOT NULL`
- `license_label TEXT NOT NULL`
- `data_class TEXT NOT NULL`
- `tickers TEXT[] NOT NULL DEFAULT '{}'`
- `themes TEXT[] NOT NULL DEFAULT '{}'`
- `summary TEXT`
- `storage_uri TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- unique `(content_hash)`
- `(published_at)`
- `(data_class)`
- GIN `(tickers)`
- GIN `(themes)`

Rules:

- Paid/private reports must use `data_class = 'private_research'` unless explicitly classified otherwise.
- Do not commit raw report files.

### `evidence.evidence_chunks`

Chunked text and local embeddings.

Columns:

- `chunk_id TEXT PRIMARY KEY`
- `evidence_id TEXT NOT NULL REFERENCES evidence.evidence_items(evidence_id)`
- `chunk_index INTEGER NOT NULL`
- `chunk_text TEXT NOT NULL`
- `span_ref TEXT`
- `content_hash TEXT NOT NULL`
- `embedding_model TEXT NOT NULL`
- `embedding vector(1024)`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(evidence_id, chunk_index)`
- unique `(content_hash)`
- HNSW vector cosine index on `embedding`

Example:

```sql
CREATE INDEX evidence_chunks_embedding_hnsw
ON evidence.evidence_chunks
USING hnsw (embedding vector_cosine_ops);
```

Dimension note:

- `vector(1024)` assumes local `bge-m3` embeddings.
- If implementation chooses a different embedding dimension, update the migration before ingesting data.
- Do not mix embeddings of different dimensions in the same vector column.

### `evidence.evidence_claims`

Normalized claims extracted from evidence.

Columns:

- `claim_id TEXT PRIMARY KEY`
- `evidence_id TEXT NOT NULL REFERENCES evidence.evidence_items(evidence_id)`
- `chunk_id TEXT REFERENCES evidence.evidence_chunks(chunk_id)`
- `ticker_or_theme TEXT NOT NULL`
- `claim_type TEXT NOT NULL`
- `direction TEXT`
- `magnitude NUMERIC`
- `time_horizon TEXT`
- `confidence NUMERIC CHECK (confidence >= 0 AND confidence <= 1)`
- `quote_or_span_ref TEXT`
- `extracted_by_model_run_id TEXT`
- `validated_at TIMESTAMPTZ`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(ticker_or_theme)`
- `(claim_type)`
- `(evidence_id)`
- `(extracted_by_model_run_id)`

Rules:

- Claims must cite evidence and preferably a chunk/span.
- LLMs can extract claims, but deterministic code decides how claims affect scores.

## Audit Schema

### `audit.model_runs`

Record of each model call.

Columns:

- `model_run_id TEXT PRIMARY KEY`
- `task_role TEXT NOT NULL`
- `model_id TEXT NOT NULL`
- `deployment TEXT NOT NULL`
- `provider TEXT NOT NULL`
- `prompt_version TEXT NOT NULL`
- `input_hash TEXT NOT NULL`
- `output_hash TEXT`
- `latency_ms INTEGER`
- `token_estimate_input INTEGER`
- `token_estimate_output INTEGER`
- `cost_estimate NUMERIC`
- `schema_valid BOOLEAN NOT NULL DEFAULT false`
- `retry_count INTEGER NOT NULL DEFAULT 0`
- `data_classes TEXT[] NOT NULL DEFAULT '{}'`
- `status TEXT NOT NULL`
- `error_summary TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(task_role)`
- `(model_id)`
- `(deployment)`
- `(prompt_version)`
- `(status)`
- `(created_at)`
- GIN `(data_classes)`

Rules:

- Do not store secrets.
- Store raw prompts/outputs only in a separate allowed table or file path if data policy permits it.

### `audit.run_artifacts`

Daily or on-demand run records.

Columns:

- `run_id TEXT PRIMARY KEY`
- `run_type TEXT NOT NULL`
- `started_at TIMESTAMPTZ NOT NULL`
- `completed_at TIMESTAMPTZ`
- `inputs_hash TEXT NOT NULL`
- `output_hash TEXT`
- `artifact_uri TEXT`
- `status TEXT NOT NULL`
- `error_summary TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(run_type)`
- `(status)`
- `(started_at)`

### `audit.data_snapshots`

Point-in-time dataset snapshot registry.

Columns:

- `snapshot_id TEXT PRIMARY KEY`
- `dataset_name TEXT NOT NULL`
- `source TEXT NOT NULL`
- `license_label TEXT NOT NULL`
- `retrieved_at TIMESTAMPTZ NOT NULL`
- `effective_at TIMESTAMPTZ`
- `available_at TIMESTAMPTZ NOT NULL`
- `storage_uri TEXT NOT NULL`
- `content_hash TEXT NOT NULL`
- `schema_version TEXT NOT NULL`
- `row_count INTEGER`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(dataset_name, available_at)`
- `(source)`
- unique `(content_hash)`

Rules:

- Backtests must use `available_at`, not just `effective_at`.

## Signals Schema

### `signals.signal_bundles`

Deterministic score bundle.

Columns:

- `signal_bundle_id TEXT PRIMARY KEY`
- `ticker TEXT NOT NULL`
- `as_of TIMESTAMPTZ NOT NULL`
- `strategic_thesis_score NUMERIC NOT NULL`
- `tactical_technical_score NUMERIC NOT NULL`
- `forward_indicator_score NUMERIC NOT NULL`
- `portfolio_risk_score NUMERIC NOT NULL`
- `formula_versions JSONB NOT NULL`
- `input_snapshot_hash TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(ticker, as_of)`
- GIN `(formula_versions)`

Rules:

- Scores must come from deterministic code.
- LLM modules must not write score columns directly.

## Recommendations Schema

### `recommendations.target_weights`

Deterministically generated portfolio target weights.

Columns:

- `target_weights_id TEXT PRIMARY KEY`
- `as_of TIMESTAMPTZ NOT NULL`
- `portfolio_id TEXT`
- `cash_weight NUMERIC NOT NULL`
- `weights_json JSONB NOT NULL`
- `constraints_json JSONB NOT NULL`
- `source_signal_bundle_ids TEXT[] NOT NULL`
- `generated_by TEXT NOT NULL`
- `validation_status TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(as_of)`
- `(validation_status)`
- GIN `(source_signal_bundle_ids)`

Rules:

- Generated by deterministic portfolio code only.
- Cannot be raw LLM output.

### `recommendations.recommendation_artifacts`

Final advisory recommendation artifact.

Columns:

- `recommendation_id TEXT PRIMARY KEY`
- `ticker_or_portfolio TEXT NOT NULL`
- `advisory_label TEXT NOT NULL`
- `action TEXT NOT NULL`
- `horizon TEXT NOT NULL`
- `score_breakdown_json JSONB NOT NULL`
- `target_weights_id TEXT NOT NULL REFERENCES recommendations.target_weights(target_weights_id)`
- `evidence_ids TEXT[] NOT NULL`
- `model_run_ids TEXT[] NOT NULL`
- `risks_json JSONB NOT NULL`
- `contradictions_json JSONB`
- `final_payload_json JSONB NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(ticker_or_portfolio)`
- `(action)`
- `(created_at)`
- GIN `(evidence_ids)`
- GIN `(model_run_ids)`

Check constraints:

- `advisory_label <> ''`
- `array_length(evidence_ids, 1) > 0`
- `array_length(model_run_ids, 1) > 0`

### `recommendations.recommendation_audits`

Recommendation audit record.

Columns:

- `audit_id TEXT PRIMARY KEY`
- `recommendation_id TEXT NOT NULL REFERENCES recommendations.recommendation_artifacts(recommendation_id)`
- `target_weights_id TEXT NOT NULL REFERENCES recommendations.target_weights(target_weights_id)`
- `signal_bundle_id TEXT NOT NULL REFERENCES signals.signal_bundles(signal_bundle_id)`
- `evidence_ids TEXT[] NOT NULL`
- `model_run_ids TEXT[] NOT NULL`
- `deterministic_checks_json JSONB NOT NULL`
- `reviewer_findings_json JSONB`
- `schema_valid BOOLEAN NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(recommendation_id)`
- `(signal_bundle_id)`
- `(schema_valid)`

## Governance Schema

### `governance.data_entitlements`

Data source and use restrictions.

Columns:

- `entitlement_id TEXT PRIMARY KEY`
- `source_name TEXT NOT NULL`
- `license_label TEXT NOT NULL`
- `allowed_uses TEXT[] NOT NULL`
- `cloud_model_allowed BOOLEAN NOT NULL DEFAULT false`
- `notes TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(source_name)`
- `(license_label)`

### `governance.incident_records`

Incident and freeze workflow.

Columns:

- `incident_id TEXT PRIMARY KEY`
- `severity TEXT NOT NULL`
- `affected_artifacts TEXT[] NOT NULL`
- `freeze_status TEXT NOT NULL`
- `root_cause TEXT`
- `remediation TEXT`
- `reopen_criteria TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `resolved_at TIMESTAMPTZ`

Indexes:

- `(severity)`
- `(freeze_status)`
- GIN `(affected_artifacts)`

### `governance.data_quality_checks`

Data quality check results.

Columns:

- `check_id TEXT PRIMARY KEY`
- `dataset_id TEXT`
- `check_name TEXT NOT NULL`
- `status TEXT NOT NULL`
- `severity TEXT NOT NULL`
- `observed_value TEXT`
- `threshold TEXT`
- `checked_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(dataset_id)`
- `(status)`
- `(severity)`
- `(checked_at)`

## Future Analytical Scale-Out

Do not implement DuckDB/Parquet in Phase 2 or v1. PostgreSQL should store v1 market snapshots, factor rows, backtest summaries, Monte Carlo summaries, walk-forward summaries, and evaluation records.

DuckDB/Parquet may be added later if large historical matrices or full backtest result frames make PostgreSQL too slow. If that happens, keep PostgreSQL as the canonical metadata and audit store, and record every external analytical file in `audit.data_snapshots`.

Possible future layout:

```text
data/
  raw/
    market/
    filings/
    reports/
    manual/
  lake/
    prices/
    factors/
    indicators/
    futures/
    backtests/
    monte_carlo/
    walk_forward/
  duckdb/
    research.duckdb
```

Possible future Parquet partitions:

```text
data/lake/prices/source=yfinance/ticker=NVDA/year=2026/*.parquet
data/lake/indicators/ticker=NVDA/frequency=1d/*.parquet
data/lake/factors/factor_set=baseline/year=2026/*.parquet
data/lake/backtests/strategy_id=baseline_weighted/year=2026/*.parquet
```

PostgreSQL `audit.data_snapshots` should record the snapshot metadata for these files if this future scale-out is implemented.

## Migration Strategy

Use migrations from the first implementation phase that touches the database.

Recommended:

- Alembic if using SQLAlchemy.
- SQL migration files if using a lighter database layer.

Migration order:

1. extensions
2. schemas
3. core tables
4. evidence tables
5. audit tables
6. signals tables
7. recommendation tables
8. governance tables
9. indexes
10. seed reference data where required

Every migration must be deterministic and re-runnable in test setup.

## Test Strategy

Database tests are mandatory before product logic uses the database.

### Unit Tests

- contract validation
- ID generation
- content hash stability
- data-class validation
- formula version serialization

### Integration Tests

- PostgreSQL connection works
- `vector` extension can be created
- schema migrations apply cleanly
- evidence chunk insert succeeds
- vector similarity query works
- portfolio snapshot insert/query works
- trade entry insert/query works
- signal bundle insert/query works
- target weights insert/query works
- recommendation artifact cannot exist without required links
- recommendation audit insert/query works

### Architecture Policy Tests

- PostgreSQL owns canonical facts and audit state
- PostgreSQL owns v1 market snapshots, derived analytics, backtest summaries, and evaluation results
- no DuckDB/Parquet dependency is required for v1
- portfolio holdings are not vector-only
- no model names hard-coded outside model profile config and tests
- no broker execution tables or endpoints
- private reports are ignored
- secrets are not committed

## Security And Privacy

Rules:

- Do not store secrets in PostgreSQL or raw local files.
- Do not commit local database files.
- Do not commit raw private reports.
- Store cloud model inputs/outputs only when data policy allows it.
- Store hashes and metadata for audit when raw content is restricted.
- Use local embeddings for private research by default.
- Redact account labels before cloud model calls unless explicitly allowed.

## Backup And Recovery

PostgreSQL backups should cover:

- portfolio facts
- trade journal
- evidence metadata
- evidence claims
- market snapshots
- factor and indicator rows
- model runs
- signal bundles
- target weights
- backtest summaries
- evaluation results
- recommendations
- audits
- governance records

Raw file backups should cover source PDFs, CSVs, downloaded reports, and exports when permitted by data policy.

Recovery should be able to reproduce a daily recommendation from:

- PostgreSQL run records
- PostgreSQL signal and recommendation artifacts
- PostgreSQL market/data snapshots and evaluation records
- content hashes
- prompt versions
- model profile versions
- formula versions

## Open Design Questions

Resolve before implementation:

1. Exact Python database layer: SQLAlchemy/Alembic or direct SQL migrations.
2. Exact embedding dimension for local `bge-m3` in the chosen Ollama embedding API.
3. Whether `positions` is a mutable current-state table or only a materialized view from trade journal.
4. Whether raw prompt/output storage is allowed for public evidence.
5. Whether recommendation artifact JSON should be fully denormalized or partially normalized in later phases.

## Phase 2 Definition Of Done

Phase 2 data spine is complete only when:

- local PostgreSQL setup is documented
- pgvector extension migration exists
- all schemas exist
- core portfolio tables exist
- evidence vector tables exist
- audit ledger tables exist
- signal and recommendation tables exist
- governance tables exist
- integration tests pass
- architecture policy tests pass
- no deprecated storage references remain as v1 canonical storage
