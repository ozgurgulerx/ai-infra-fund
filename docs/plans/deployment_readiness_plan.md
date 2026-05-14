# Deployment Readiness Plan

## Purpose

Turn the current Phase 0/Phase 1 scaffold into a locally deployable, containerized v1 foundation.

This plan does not make the product feature-complete. It creates a deployment-ready platform base for later ingestion, scoring, recommendation, evaluation, and UI work.

The deployment-ready baseline means:

- frontend dependencies install and build reproducibly from a lockfile
- PostgreSQL + pgvector migrations create the Phase 2 data spine
- API and worker containers are real service shells with health/readiness behavior
- Docker Compose can build, migrate, and start the local stack
- tests and smoke checks are green before the scaffold is committed

## Status Vocabulary

- Local deployment-ready: the local/dev Docker Compose stack builds, migrates, starts, and passes health/readiness smoke checks on one machine.
- Production-ready: the same service boundaries run with real secret management, TLS/reverse proxy, host/network policy, backup/restore, monitoring, and CI/CD.
- Product-feature-complete: ingestion, evidence extraction, model routing, deterministic scoring, recommendation artifacts, evaluation harness, and UI workflows are implemented and verified.

Current status after this plan: local deployment-ready only. The scaffold is not production-ready and is not product-feature-complete.

## Guardrails

- Keep v1 advisory-only.
- Do not add live order placement.
- Do not add broker execution endpoints.
- Manual buy/sell entry remains local trade-journal behavior only.
- Do not implement ingestion, scoring, recommendations, cloud model calls, or product UI workflows in this readiness pass.
- PostgreSQL + pgvector remains the only v1 database.
- DuckDB + Parquet remains future optional analytical scale-out only, not a deployment-readiness dependency.
- Docker Compose remains the v1 runtime boundary with `web`, `api`, `worker`, `postgres`, and `migrate` services.
- Real secrets must not be committed.
- `docker-compose.yml` is the local/dev Compose file.
- Portable or production-like deployments must use `docker-compose.prod.example.yml` or equivalent secrets and network controls.

## Read First

Before implementing this plan, read:

- `AGENTS.md`
- `docs/plans/containerization_plan.md`
- `docs/plans/deployment_harness.md`
- `docs/plans/data_plan.md`
- `docs/plans/database_design.md`
- `docs/plans/phase2_boundary_notes.md`
- `docs/specs/0002-trading-policy.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0012-data-architecture.md`
- `docs/specs/0015-containerized-deployment.md`

## Phase A: Frontend Build Reproducibility

### Goal

Make the `web` container reproducible and buildable from committed dependency metadata.

### Work

1. Fix `apps/web/package.json`.
   - Replace invalid or unavailable dependency pins with resolvable versions.
   - Keep the dependency set minimal until Phase 8 UI work begins.
   - Do not introduce UI feature work in this phase.

2. Generate and commit `apps/web/package-lock.json`.
   - Use `npm install --package-lock-only` or `npm install` from `apps/web`.
   - Review the lockfile before commit.

3. Update `apps/web/Dockerfile`.
   - Use `npm ci`, not `npm install`.
   - Use a separate build stage.
   - Keep runtime minimal.
   - Prefer `next start` for the production runtime once a real UI exists.

4. Verify local frontend commands.
   - `npm ci`
   - `npm run build`
   - `docker compose build web`

### Exit Criteria

- `apps/web/package-lock.json` exists.
- `web` image builds from the lockfile.
- No frontend dependency install step depends on floating package resolution.
- No product UI workflow is added.

## Phase B: Phase 2 PostgreSQL + pgvector Migrations

### Goal

Create a usable PostgreSQL + pgvector schema for the Phase 1 contracts and the v1 data spine.

### Work

1. Choose and document the migration tool.
   - Prefer Alembic/SQLAlchemy if the backend remains Python/FastAPI.
   - Use versioned SQL files only if the project intentionally avoids an ORM/migration layer.
   - Record the decision in `docs/plans/phase2_boundary_notes.md` or `docs/plans/database_design.md`.

2. Resolve Phase 2 blockers.
   - Confirm pgvector embedding dimension for the local `bge-m3` path.
   - Decide whether `core.positions` is mutable current state or derived/materialized from `core.trade_entries`.
   - Decide raw prompt/output retention policy.
   - Decide whether recommendation payload JSON is fully denormalized in v1.

3. Add migrations for platform foundations.
   - `CREATE EXTENSION IF NOT EXISTS vector`
   - optional `pgcrypto` if SQL-side UUID generation or hash helpers are needed
   - schemas: `core`, `evidence`, `audit`, `signals`, `recommendations`, `governance`

4. Add migrations for Phase 1 contract tables.
   - `core.positions`
   - `core.trade_entries`
   - `core.universe_members`
   - `audit.data_snapshots`
   - `evidence.evidence_items`
   - `evidence.evidence_claims`
   - `signals.feature_sets`
   - `audit.model_runs`
   - `signals.signal_bundles`
   - `recommendations.target_weights`
   - `signals.implementation_estimates`
   - `audit.backtest_runs`
   - `governance.model_inventory`
   - `recommendations.recommendation_artifacts`
   - `recommendations.recommendation_audits`
   - `governance.incident_records`
   - `governance.data_quality_checks`
   - `audit.run_artifacts`

5. Add migrations for data-spine tables.
   - `evidence.evidence_chunks` with pgvector embedding column
   - `core.portfolio_snapshots`
   - `core.portfolio_snapshot_positions`
   - `signals.market_snapshots`
   - `signals.factor_rows`

6. Add constraints and indexes.
   - foreign keys for evidence, model runs, signal bundles, target weights, and audits
   - required content-hash constraints for source-derived records
   - point-in-time indexes on `as_of`, `available_at`, and `created_at`
   - pgvector index for evidence chunk retrieval
   - uniqueness constraints where IDs or content hashes must be stable

7. Add migration tests.
   - migration applies to a clean PostgreSQL database
   - `vector` extension is available
   - evidence chunk insert supports the selected embedding dimension
   - vector similarity query succeeds
   - content-hash and advisory-label constraints reject invalid records

### Exit Criteria

- `migrate` container applies the schema to a clean database.
- migration tests pass.
- pgvector extension and similarity query tests pass.
- schema maps cleanly to Phase 1 contracts.

## Phase C: Replace API And Worker Scaffolds

### Goal

Replace placeholder service entrypoints with real service shells while keeping business logic stubbed.

### API Work

1. Move from the current stdlib HTTP placeholder to FastAPI.
2. Add endpoints:
   - `GET /health`: process health, no database dependency
   - `GET /ready`: database readiness and required config checks
   - `GET /version`: service metadata and build/runtime version
3. Add config loading for:
   - `AI_INFRA_FUND_DATABASE_URL`
   - `AI_INFRA_FUND_DATA_DIR`
   - `AI_INFRA_FUND_MODEL_PROFILES`
   - `AI_INFRA_FUND_ENV`
4. Add database connectivity check for readiness.
5. Use a consistent response envelope.
6. Do not add recommendation, ingestion, scoring, or broker endpoints.

### Worker Work

1. Add real startup and shutdown lifecycle.
2. Load the same core config.
3. Check database connectivity at startup.
4. Emit clear structured logs.
5. Exit non-zero on invalid required config.
6. Keep jobs stubbed until Phase 3 or later explicitly requests ingestion, scoring, or model routing.

### Tests

- API `/health` test.
- API `/ready` test with database unavailable.
- API `/ready` test with database available.
- API config validation test.
- Worker startup config test.
- Worker database connectivity failure test.
- Migration command invocation test.

### Exit Criteria

- API and worker are real service shells.
- service startup fails clearly on invalid config.
- API readiness reflects database state.
- no product workflows or live trading paths are added.

## Phase D: Compose Smoke Tests

### Goal

Make local deployment verification repeatable with one command or a small documented command sequence.

### Smoke Test Coverage

Add a script or test target that verifies:

1. `docker compose config`
2. `docker compose build api worker web`
3. `docker compose up -d postgres`
4. `docker compose run --rm migrate`
5. `docker compose up -d api worker web`
6. `curl http://localhost:8000/health`
7. `curl http://localhost:8000/ready`
8. `docker compose ps`
9. `docker compose logs --no-color --tail=100`

Useful local commands:

```bash
python3 -m unittest discover -s tests
python3 -m compileall packages services tests
cd apps/web && npm audit --omit=dev
docker compose config
POSTGRES_PASSWORD=replace-with-secret docker compose -f docker-compose.yml -f docker-compose.prod.example.yml config
scripts/compose_smoke.sh
docker compose down
```

### Policy Checks

The smoke test or architecture policy tests should also verify:

- PostgreSQL uses a named volume.
- `./data` is ignored and mounted.
- `web` has no database URL.
- `web` has no Azure Foundry or model API secrets.
- no secrets are committed.
- no v1 service requires DuckDB or Parquet.
- `migrate` is the only service that applies schema migrations automatically.

### Exit Criteria

- one documented command can prove the local container stack starts cleanly.
- Compose smoke tests are deterministic enough to run before commits.
- logs show API/worker startup and no hidden broker/order path.

## Phase E: Green Gate And Commit

### Required Verification

Run before committing:

```bash
python3 -m unittest discover -s tests
python3 -m compileall packages services tests
docker compose config
docker compose build api worker web
```

Run after Phase B/C/D are implemented:

```bash
docker compose up -d postgres
docker compose run --rm migrate
docker compose up -d api worker web
curl http://localhost:8000/health
curl http://localhost:8000/ready
docker compose ps
```

Inspect before commit:

```bash
git status --short
git diff --stat
```

### Commit Conditions

Commit only when:

- unit tests pass
- architecture policy tests pass
- compile check passes
- web image builds
- API and worker images build
- migrations apply to a clean database
- Compose smoke tests pass
- secrets are absent
- generated cache files like `__pycache__` are not tracked
- dependency lockfiles are intentional and reviewed

Suggested commit:

```bash
git add .
git commit -m "feat: add deployable container foundation"
```

## Risks And Decisions

| Risk/Decision | Required Resolution |
|---|---|
| frontend packages are currently unpinned or invalid | pin resolvable versions and commit lockfile |
| migration tool not chosen | decide Alembic/SQLAlchemy vs versioned SQL before Phase B |
| embedding dimension unknown | confirm local `bge-m3` output dimension before pgvector migration |
| position persistence model unclear | choose mutable current table, trade-derived view, or both |
| prompt/output retention policy unclear | decide whether to store raw payloads or only hashes/metadata |
| service shells may grow into product work | keep API/worker endpoints limited to health, readiness, version, config, and migration boundaries |
| smoke checks may depend on local dirty state | make smoke checks start from Compose services and committed config only |

## Ready For Deployment Definition

The repo is deployment-ready when containers build, migrations apply, API and worker start, health/readiness checks pass, Compose smoke checks are repeatable, and the baseline is committed without secrets or generated caches.

This means local deployment-ready. Production-ready still requires:

- real secrets supplied by the environment or a secret manager
- TLS/reverse proxy in front of public HTTP surfaces
- host firewall and network policy
- database backup/restore runbook and restore test
- monitoring, log retention, and alerting
- CI/CD checks for tests, builds, migrations, and smoke verification
- deployment-specific data retention and incident procedures
