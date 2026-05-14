# 0005 UI Acceptance

## Purpose

Define the v1 dashboard behavior without implementing the UI in Phase 0.

## UI Principles

- advisory-only
- dense and scan-friendly
- operational control-room feel
- no marketing landing page
- no order-placement controls
- every recommendation links to evidence and audit records

## Required Views

- system status
- portfolio
- local trade journal
- evidence library
- signals
- recommendations
- backtests and evaluation
- model runs
- data quality and incidents

## Acceptance Rules

- Advisory labels must be visible on recommendation screens.
- Module health must come from real tests, policy checks, run artifacts, health checks, or incidents.
- Green status requires passing evidence; planned modules are gray.
- Critical workflows require E2E tests once UI implementation begins.
