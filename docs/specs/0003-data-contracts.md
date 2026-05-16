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
- `MarketEvent`
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

## MarketEvent

`MarketEvent` is a first-class advisory signal contract for catalyst-driven AI infrastructure analysis.

Required fields:

- `event_id`
- `event_type`
- `source_evidence_ids`
- `tickers`
- `companies`
- `themes`
- `catalyst`
- `ai_relevance`
- `direction`
- `time_horizon`
- `confidence`
- `occurred_at`
- `available_at`
- `content_hash`
- `extracted_by_model_run_id`
- `review_status`

## Contract Rules

- IDs must be stable and audit-friendly.
- Source-derived records must include `content_hash`.
- Point-in-time records must include `as_of`, `available_at`, or equivalent.
- Recommendation artifacts must link to evidence, model runs, signals, and target weights.
- Portfolio holdings are relational facts, not vector-only records.
- Model outputs must be validated before persistence.
- MarketEvents must link to evidence.
- Events without provenance cannot influence `SignalBundle`.
- LLMs may extract events only through allowed model routes.
- Deterministic code owns scoring after event extraction.
- MarketEvents are advisory signals, not trading actions.
