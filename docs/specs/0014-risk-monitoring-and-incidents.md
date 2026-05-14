# 0014 Risk Monitoring And Incidents

## Purpose

Define operational risk tracking.

## Required Records

- data-quality checks
- stale evidence alerts
- model routing failures
- schema validation failures
- recommendation policy violations
- incident records

## Incident Rules

- Critical financial-safety failures freeze recommendation publication.
- Missing evidence provenance blocks claim creation.
- Model failures must be recorded and routed through fallback policy.
- Private data policy violations are critical incidents.
