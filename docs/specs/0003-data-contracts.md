# 0003 Data Contracts

## Purpose

Define the initial contract surface for Phase 1 implementation.

## Required Contracts

- `Position`
- `TradeEntry`
- `TradeJournal`
- `UniverseMember`
- `DatasetSnapshot`
- `EvidenceItem`
- `EvidenceClaim`
- `FeatureSet`
- `ModelRun`
- `SignalBundle`
- `TargetWeights`
- `ImplementationEstimate`
- `BacktestRun`
- `ModelInventoryEntry`
- `RecommendationArtifact`
- `RecommendationAudit`
- `IncidentRecord`
- `DataQualityCheck`
- `RunArtifact`

## Contract Rules

- IDs must be stable and audit-friendly.
- Source-derived records must include `content_hash`.
- Point-in-time records must include `as_of`, `available_at`, or equivalent.
- Recommendation artifacts must link to evidence, model runs, signals, and target weights.
- Portfolio holdings are relational facts, not vector-only records.
- Model outputs must be validated before persistence.
