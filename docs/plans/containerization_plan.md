# Containerization Plan: Portable Frontend And Backend Split

## Purpose

Define the v1 container architecture for the AI Infrastructure Fund Control Room.

The goal is portability without overbuilding. V1 should run locally with Docker Compose and preserve clean service boundaries so it can later move to a VM, Container Apps, ECS, Kubernetes, or another orchestrator without redesigning the app.

The implementation sequence for turning this scaffold into a locally deployable baseline is tracked in `docs/plans/deployment_readiness_plan.md`.

`docker-compose.yml` is the local/dev runtime definition. Use `docker-compose.prod.example.yml` as a production/portable deployment overlay example, or implement equivalent controls in the target platform.

## Core Rule

Use Docker Compose for v1. Do not introduce Kubernetes, service mesh, object storage, Redis, Celery, or distributed schedulers until the implementation proves they are needed.

Local deployment-ready means the Compose stack builds, migrates, starts, and answers health/readiness checks. Production-ready additionally requires real secrets, TLS/reverse proxy, host/network policy, backup/restore, monitoring, and CI/CD. Product-feature-complete is a later state that includes ingestion, scoring, recommendation, evaluation, and UI workflows.

## Service Split

| Service | Path | Runtime | Responsibility |
|---|---|---|---|
| `web` | `apps/web` | Next.js | Read-only advisory dashboard and local trade-journal UI |
| `api` | `services/api` | FastAPI | HTTP API, auth boundary, read/write application operations |
| `worker` | `services/worker` | Python | ingestion, embeddings, deterministic scoring, backtests, scheduled runs |
| `postgres` | image | PostgreSQL + pgvector | only v1 database |
| `migrate` | `services/api` image | Python migration command | one-shot database migration before API/worker start |

API and worker may share Python contracts through `packages/core`, but they must run as separate containers.

## Compose Layout

Recommended files:

```text
docker-compose.yml
.env.example
.dockerignore
apps/web/Dockerfile
services/api/Dockerfile
services/worker/Dockerfile
```

Use Compose service names for internal networking:

- `postgres` for the database host
- `api` for frontend-to-backend calls inside Compose
- `host.docker.internal:11434` for local Ollama on macOS

Do not hard-code `localhost` inside service code. `localhost` inside a container means the container itself, not the host or another service.

## Volumes

Use a named Docker volume for PostgreSQL:

```text
postgres_data
```

Use an ignored bind mount for local source files:

```text
./data:/app/data
```

The `data/` directory stores raw PDFs, CSVs, downloaded reports, private research files, and exports. Canonical metadata, hashes, facts, audits, embeddings, market snapshots, and recommendation artifacts remain in PostgreSQL.

## Configuration

All runtime configuration must come from environment variables.

Required v1 variables:

```text
AI_INFRA_FUND_DATABASE_URL=postgresql://ai_infra_fund:ai_infra_fund@postgres:5432/ai_infra_fund
AI_INFRA_FUND_DATA_DIR=/app/data
AI_INFRA_FUND_MODEL_PROFILES=config/model_profiles.yaml
AI_INFRA_FUND_ENV=local
AZURE_AI_FOUNDRY_ENDPOINT=
AZURE_AI_FOUNDRY_API_KEY=
OLLAMA_BASE_URL=http://host.docker.internal:11434
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`.env.example` may contain empty or dummy values. Real secrets belong in local ignored env files or a secret manager.

For production-like Compose validation:

```bash
POSTGRES_PASSWORD=replace-with-secret AI_INFRA_FUND_INTERNAL_TOKEN=replace-with-secret docker compose -f docker-compose.yml -f docker-compose.prod.example.yml config
```

The production overlay removes the host-published PostgreSQL port and replaces local/dev database defaults with environment-provided credentials and an internal API token.

## Startup Order

1. `postgres` starts and exposes health checks.
2. `migrate` waits for `postgres` and applies migrations.
3. `api` starts after successful migration.
4. `worker` starts after successful migration.
5. `web` starts and talks to `api`.

The API should expose:

- `GET /health`
- `GET /ready`

The worker should expose logs and a simple process health signal. It does not need an HTTP server in v1 unless operational needs require one.

## Container Boundaries

- `web` must not connect directly to PostgreSQL.
- `web` must not call cloud model APIs directly.
- `api` may read and write PostgreSQL through validated application services.
- `worker` owns long-running ingestion, embedding, scoring, and evaluation jobs.
- `migrate` is the only container that applies schema migrations automatically.
- No container should contain real secrets in the image.

## Test And Verification

Phase 0 architecture policy tests should verify:

- required Dockerfiles exist
- `docker-compose.yml` defines `web`, `api`, `worker`, `postgres`, and `migrate`
- Compose uses a named `postgres_data` volume
- Compose mounts ignored `./data`
- `.env.example` exists and has no real secrets
- `web` does not receive a database URL
- model profile path is provided through environment
- no v1 service depends on DuckDB/Parquet

Later phases should add:

- API health check tests
- migration container smoke test
- worker startup smoke test
- frontend API connectivity E2E test
- Compose build verification

Current local checks:

```bash
python3 -m unittest discover -s tests
python3 -m compileall packages services tests
cd apps/web && npm audit --omit=dev
docker compose config
scripts/compose_smoke.sh
docker compose down
```

## Future Portability

Keep the Compose design portable:

- stateless `web`, `api`, and `worker` containers
- PostgreSQL state in one explicit volume
- raw file state in one explicit data mount
- no path assumptions outside `/app`
- no local-only absolute paths in committed config
- no provider-specific deployment metadata in application code

When the project is ready to move beyond one machine, map the same services to the target platform instead of changing application boundaries.
