# 0015 Containerized Deployment

## Purpose

Define the v1 portable runtime boundary.

## Core Rule

V1 runs through Docker Compose with separate `web`, `api`, `worker`, `postgres`, and `migrate` services.

PostgreSQL + pgvector remains the only v1 database. DuckDB + Parquet is future optional analytical scale-out only, not a v1 dependency.

## Service Responsibilities

- `web`: Next.js frontend; no direct database access.
- `api`: FastAPI-compatible backend boundary; validates inputs and reads/writes through application services.
- `worker`: ingestion, embeddings, deterministic scoring, backtests, and scheduled runs.
- `postgres`: PostgreSQL + pgvector with named volume.
- `migrate`: one-shot migration container.

## Configuration

All configuration comes from environment variables. Secrets must not be committed.

Use Compose service names for internal networking. Do not hard-code `localhost` inside service code.

## Volumes

- `postgres_data` named volume for PostgreSQL.
- `./data:/app/data` ignored bind mount for raw files and exports.
