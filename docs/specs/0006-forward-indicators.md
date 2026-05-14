# 0006 Forward Indicators

## Purpose

Define the future forward-indicator signal lane.

## Inputs

- futures/proxy data
- AI infrastructure supply-chain indicators
- cloud capex signals
- semiconductor demand proxies
- power and data-center constraints
- earnings/news event metadata

## Rules

- Ingestion must preserve source, timestamp, availability, and content hash.
- Signal formulas must be deterministic and versioned.
- No future data may leak into historical runs.
- Forward-indicator scores must be stored as part of `SignalBundle`.

## V1 Boundary

Phase 0 specifies this lane only. Implementation starts after data contracts and PostgreSQL persistence exist.
