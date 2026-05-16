# 0015 Containerized Deployment

## Purpose

Define the v1 portable runtime boundary and cloud deployment gate.

## Core Rule

V1 runtime is containerized with separate `web`, `api`, `worker`, `postgres`, and `migrate` services.

Cloud is the canonical deployment validation target. Local Docker Compose is a development preflight and does not establish deployment readiness.

PostgreSQL + pgvector remains the only v1 database. DuckDB + Parquet is future optional analytical scale-out only, not a v1 dependency.

## Service Responsibilities

- `web`: Next.js frontend; no direct database access.
- `api`: FastAPI-compatible backend boundary; validates inputs and reads/writes through application services.
- `worker`: ingestion, embeddings, deterministic scoring, backtests, and scheduled runs.
- `postgres`: PostgreSQL + pgvector with named volume.
- `migrate`: one-shot migration container.

## Configuration

All configuration comes from environment variables. Secrets must not be committed.

Use service DNS names for internal networking. Do not hard-code `localhost` inside service code.

## Cloud Deployment Gate

Deployment validation must run against Azure cloud resources:

- build and push `web`, `api`, and `worker` images to the configured Azure Container Registry
- apply the AKS manifest to the canonical cluster and namespace
- run the migration job in AKS
- verify API and worker rollouts in AKS
- roll the frontend App Service to the new web image
- verify public cloud `/health` and `/ready` endpoints and the frontend URL

Local `docker compose config` and `scripts/compose_smoke.sh` may be used as preflight checks only.

## Runtime Ops Preflight

The API `/ready` endpoint returns a redacted runtime preflight payload in addition to database readiness. The payload must not expose database URLs, passwords, internal tokens, or provider secrets.

The readiness payload reports:

- service name and environment
- database check status
- model profile configuration presence
- data directory configuration/presence
- production internal-token policy
- crawl user-agent contact policy when crawl mode requires it
- advisory/reporting-only boundary
- configured-public-source-only crawler policy

Readiness may warn on non-blocking local/runtime conditions such as a missing local data directory, but it must fail on blocking production conditions such as unavailable PostgreSQL, missing required model-profile configuration, missing production internal token, or missing crawl user-agent contact when crawl mode is enabled.

The worker uses the same shared runtime preflight before entering its job loop. Crawl mode still requires `SEC_EDGAR_USER_AGENT` with a contact email or URL.

## Volumes

- `postgres_data` named volume for PostgreSQL.
- `./data:/app/data` ignored bind mount for raw files and exports.
