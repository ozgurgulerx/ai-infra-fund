# Phase 2 Boundary Notes: PostgreSQL Data Spine

## Scope

These notes prepared Phase 2 before implementation. Deployment readiness now implements the foundation with versioned SQL migrations under `services/api/migrations/`.

V1 uses PostgreSQL + pgvector as the only database. DuckDB/Parquet remains a future optional analytical scale-out path, not a Phase 2 dependency.

## Contract To Table Mapping

| Phase 1 Contract | PostgreSQL Table |
|---|---|
| `Position` | `core.positions` |
| `TradeEntry` | `core.trade_entries` |
| `TradeJournal` | logical aggregate over `core.trade_entries`; optional `core.trade_journals` metadata table if journal snapshots are needed |
| `UniverseMember` | `core.universe_members` |
| `DatasetSnapshot` | `audit.data_snapshots` |
| `EvidenceItem` | `evidence.evidence_items` |
| `EvidenceClaim` | `evidence.evidence_claims` |
| `FeatureSet` | `signals.feature_sets` |
| `ModelRun` | `audit.model_runs` |
| `SignalBundle` | `signals.signal_bundles` |
| `TargetWeights` | `recommendations.target_weights` |
| `ImplementationEstimate` | `signals.implementation_estimates` |
| `BacktestRun` | `audit.backtest_runs` |
| `ModelInventoryEntry` | `governance.model_inventory` |
| `RecommendationArtifact` | `recommendations.recommendation_artifacts` |
| `RecommendationAudit` | `recommendations.recommendation_audits` |
| `IncidentRecord` | `governance.incident_records` |
| `DataQualityCheck` | `governance.data_quality_checks` |
| `RunArtifact` | `audit.run_artifacts` |

Additional Phase 2 tables needed by data architecture:

- `evidence.evidence_chunks`: chunk text plus pgvector embeddings.
- `core.portfolio_snapshots`: point-in-time portfolio summary.
- `core.portfolio_snapshot_positions`: point-in-time position lines.
- `signals.market_snapshots`: v1 market data storage in PostgreSQL.
- `signals.factor_rows`: v1 factor and indicator storage in PostgreSQL.

## Migration Ordering

1. Extensions
   - `vector`
   - `pgcrypto` if UUID generation or hashing helpers are needed in SQL
2. Schemas
   - `core`
   - `evidence`
   - `audit`
   - `signals`
   - `recommendations`
   - `governance`
3. Enum/check-constraint support
   - data class
   - asset type
   - trade side
   - trade status
   - recommendation action
   - advisory label
   - model run status
   - incident severity
   - data quality status
4. Core tables
   - universe
   - positions
   - trade entries
   - portfolio snapshots
   - portfolio snapshot positions
5. Audit foundations
   - data snapshots
   - model runs
   - run artifacts
6. Evidence tables
   - evidence items
   - evidence chunks
   - evidence claims
7. Signal tables
   - feature sets
   - market snapshots
   - factor rows
   - signal bundles
   - implementation estimates
8. Recommendation tables
   - target weights
   - recommendation artifacts
   - recommendation audits
9. Governance tables
   - model inventory
   - incident records
   - data quality checks
10. Indexes
   - foreign-key indexes
   - content-hash unique indexes
   - point-in-time indexes on `as_of`, `available_at`, and `created_at`
   - pgvector index for evidence chunk embeddings
11. Seed/reference data
   - enum-like lookup values only if check constraints are not sufficient

## Migration Tool Decision

Use versioned SQL migrations for the v1 deployment-ready foundation.

Reason:

- Phase 2 needs deterministic DDL more than ORM mapping.
- The current API and worker only need service shells.
- SQL keeps pgvector indexes, check constraints, and schemas explicit.
- Alembic can be introduced later if SQLAlchemy models become useful.

The migration runner is `services/api/src/ai_infra_fund_api/migrate.py`. It applies files from `services/api/migrations/` in lexical order and records applied files in `audit.schema_migrations`.

## pgvector Dimension Decision

The initial migration uses `vector(1024)`.

Assumption:

- `vector(1024)` if the local `bge-m3` embedding implementation returns 1024-dimensional vectors.

Decision rule:

- Do not mix embedding dimensions in the same vector column.
- If multiple embedding models are needed later, use separate embedding tables or versioned embedding columns.
- Store `embedding_model` with every embedded chunk and claim.

## Phase 2 Blockers

- Confirm pgvector embedding dimension against the actual local `bge-m3` implementation before ingesting evidence.
- Decide whether `core.positions` remains mutable current state long-term or becomes a materialized view derived from `core.trade_entries`.
- Decide whether public raw prompt/output storage is allowed or only hashes/metadata.
- Decide whether recommendation payload JSON remains fully denormalized in v1.
