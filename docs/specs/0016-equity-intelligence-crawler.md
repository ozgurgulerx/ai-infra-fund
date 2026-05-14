# 0016 Equity Intelligence Crawler

## Purpose

Define the advisory-only crawler for AI equity intelligence. The crawler gathers public evidence about configured equity watchlist names, materializes provenance-backed evidence, and emits typed events for downstream advisory analysis. It does not create any live market action surface.

## Source Of Truth

The crawler universe is config-driven:

- `config/ai_equity_watchlist.yaml` owns ticker, company name, themes, sector tags, optional source URLs, and priority.
- Business logic must load and validate that config instead of hard-coding watched companies.
- Local user files remain ignored local inputs until validation classifies them as safe evidence candidates.

## Advisory Boundary

Allowed:

- crawl public company, investor-relations, public filing, public technical, and public news sources
- classify sources into data classes
- extract claims, typed events, timestamps, and evidence spans
- materialize evidence items, chunks, claims, and run artifacts
- raise risk, thesis, refresh, or review events for advisory workflows

Forbidden:

- credentials for financial accounts or venues
- private account forms, account-transfer PDFs, or other sensitive local documents as evidence
- any live market action endpoint or UI control
- using LLM output to produce deterministic scores, constraints, or target weights directly

## Source Frontier

The crawler uses a source frontier adapted from the startup-analysis onboarding frontier pattern.

Each frontier target is derived from a watchlist entry plus a source kind:

| Source kind | Examples | Default data class |
| --- | --- | --- |
| company_home | company product and platform pages | public_evidence |
| investor_relations | earnings releases, presentations, transcripts, filings links | public_evidence |
| filings | SEC or exchange filing pages | public_evidence |
| technical_docs | product docs, benchmark pages, architecture notes | public_evidence |
| public_news | public articles and press releases | public_evidence |

Frontier records should track:

- canonical URL
- ticker and company name
- source kind
- priority inherited from watchlist priority plus event boosts
- last crawl status and timestamps
- next due timestamp
- content hash and ETag/last-modified metadata when available
- failure count and backoff state

The frontier is URL-level state. The watchlist is ticker-level configuration. Refresh jobs are the bridge between them.

## Refresh Jobs

Refresh jobs represent ticker-level urgency and are processed before generic frontier work.

Required fields:

- `refresh_job_id`
- `ticker`
- `reason`
- `priority_boost`
- `requested_at`
- `status`
- `claimed_at`
- `completed_at`
- `error_summary`

Initial reasons:

- `watchlist_seed`
- `earnings_release`
- `filing_update`
- `product_launch`
- `pricing_change`
- `supply_chain_signal`
- `manual_review`

Processing rules:

1. Reset stale processing jobs before claiming new jobs.
2. Resolve the ticker through `config/ai_equity_watchlist.yaml`.
3. Boost matching frontier URLs for that ticker.
4. Seed baseline URLs from the watchlist when no frontier rows exist.
5. Mark jobs completed only after URL-level frontier rows are boosted or seeded.
6. Persist failure summaries without dropping the job history.

## Leases

Crawler workers must claim URL work through leases so multiple workers can run without duplicate processing.

Lease fields:

- `leased_at`
- `lease_owner`
- `lease_expires_at`
- `lease_attempts`

Lease rules:

- workers claim due URLs in bounded batches
- per-domain caps prevent one domain from consuming the whole batch
- stale leases are released before new claims
- failed leased URLs are requeued with exponential backoff
- each crawl attempt writes a run artifact or crawl log row, even when the fetch fails

## Typed Events

The crawler emits typed events from public evidence. Events are advisory signals, not actions.

Initial event types:

- `earnings_guidance_change`
- `capex_signal`
- `ai_product_launch`
- `accelerator_supply_signal`
- `cloud_capacity_signal`
- `customer_adoption_signal`
- `regulatory_or_export_control_signal`
- `partnership_signal`
- `competitive_position_signal`
- `data_center_power_signal`

Each event must include:

- `event_id`
- `event_type`
- `ticker`
- `occurred_at` when available
- `available_at`
- `confidence`
- `evidence_ids`
- `source_url`
- `extracted_by_model_run_id` when an LLM extracts it
- `review_status`

Event extraction may use configured model routes only for allowed data classes. Deterministic code owns final scoring and portfolio constraints.

## Evidence Materialization

Public crawl captures materialize into the existing evidence spine:

1. fetch page or document metadata
2. classify source and data class
3. compute content hash
4. store raw capture metadata locally and in PostgreSQL-owned metadata tables
5. create `EvidenceItem`
6. chunk content with source spans
7. extract claims and typed events with provenance links
8. write run artifacts tying crawler attempt, model run, evidence IDs, and event IDs together

Private local research files must be validated before materialization. Sensitive Schwab, account-transfer, or routing-number PDFs are quarantined and must not become evidence items.

## Storage Ownership

PostgreSQL + pgvector remains the v1 durable store for frontier state, evidence metadata, chunks, claims, typed events, model runs, and audit artifacts.

Raw files and crawl bodies may live on ignored local filesystem paths. PostgreSQL stores metadata, hashes, provenance, and audit links.

## Runtime Jobs

Recommended Phase 10 runtime surfaces:

- `watchlist-seed`: validates the YAML watchlist and creates initial frontier records
- `equity-refresh-jobs`: processes ticker-level refresh requests into URL-level frontier boosts
- `equity-crawl-frontier`: leases due URLs and records captures
- `equity-event-extractor`: turns materialized evidence into typed events
- `equity-evidence-maintenance`: handles retention, stale lease cleanup, and failed-attempt summaries

Each job must be restartable, idempotent where feasible, and observable through run artifacts.

## Acceptance Criteria

- `config/ai_equity_watchlist.yaml` validates without hard-coded company lists in business logic.
- Local CSV/file validators reject missing point-in-time fields, missing evidence provenance, and sensitive Schwab/routing PDFs.
- Public source crawls produce evidence IDs before events are considered usable.
- Refresh jobs and leases support crash recovery and bounded retry.
- Typed events include source evidence IDs and model run IDs when model-assisted extraction is used.
- Architecture policy tests continue to pass.
