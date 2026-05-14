# 0012 Data Architecture

## Purpose

Define v1 storage ownership.

## Core Rule

PostgreSQL + pgvector is the only v1 database. It owns canonical facts, portfolio records, trade journal, evidence metadata, evidence claims, embeddings, run ledger, model runs, market snapshots, factor rows, signal bundles, target weights, recommendation artifacts, audits, backtest summaries, evaluation results, and local semantic retrieval.

DuckDB + Parquet is future optional analytical scale-out only, not a v1 dependency.

## Raw Files

Raw PDFs, CSVs, downloaded reports, private research files, and exports may live on the ignored local filesystem. PostgreSQL stores metadata, hashes, provenance, and audit links.

## pgvector Use

Use vectors for evidence chunks, claims, thesis nodes, recommendation rationales, and reviewer findings. Do not use vector search as the source of truth for portfolio holdings.

## Required Phase 2 Tables

- portfolio and trade journal tables
- evidence item, chunk, claim, and embedding tables
- model run and run artifact tables
- market snapshot and factor tables
- signal bundle tables
- target weight tables
- recommendation and audit tables
- governance and data-quality tables
