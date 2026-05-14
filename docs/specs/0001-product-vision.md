# 0001 Product Vision

## Purpose

Define the product boundary for the AI Infrastructure Fund Control Room.

## Vision

Build a private, local-first, advisory-only research and recommendation system for AI infrastructure, AI ecosystem, and quantum-tech investing.

The system should help ingest evidence, compute deterministic signals, evaluate recommendations, and explain portfolio suggestions. It must not place live orders.

## V1 Scope

- portfolio and universe tracking
- local trade journal for intended and completed manual trades
- evidence ingestion and provenance
- deterministic scoring and target-weight generation
- recommendation artifacts with audit links
- model-assisted extraction, review, and explanation
- backtest and evaluation summaries
- read-only/advisory dashboard

## V1 Non-Goals

- no live broker integration
- no order execution
- no LLM-owned numeric scores or target weights
- no cloud-only database dependency
- no paid-report scraping

## Architecture Summary

- PostgreSQL + pgvector is the v1 data spine.
- DuckDB + Parquet is future optional scale-out only, not a v1 dependency.
- Docker Compose runs `web`, `api`, `worker`, `postgres`, and `migrate`.
- Cloud models may be used only through the model router and data-class policy.
