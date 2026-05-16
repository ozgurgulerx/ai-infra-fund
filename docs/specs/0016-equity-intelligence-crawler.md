# 0016 Equity Intelligence Crawler

## Purpose

Define the advisory-only crawler for AI equity intelligence. The crawler monitors configured public sources, detects macro, micro, thematic, company, financial, and segment-level changes, materializes provenance-backed evidence, and emits `SourceSignal` and `MarketEvent` objects for downstream advisory analysis.

The crawler exists to support the AI Infrastructure Trading Advisory Workstation. It can support `TradingAdvisory` candidate updates through evidence-backed signals, but it must not create live market actions, broker outputs, order outputs, automated trading decisions, or execution surfaces.

The crawler is a configured public-source evidence pipeline, not a general internet crawler, private-document crawler, paid-research scraper, broker integration, order-generation system, or execution/trading-action system.

## Output Flow

```text
SourceFrontier
-> SourceSignal
-> EvidenceItem
-> MarketEvent
-> SegmentImpact
-> TradingAdvisory candidate update
```

Output ownership:

- `SourceFrontier` records where configured public sources should be monitored.
- `SourceSignal` records a detected public-source change that may deserve materialization.
- `EvidenceItem` records provenance-backed source evidence.
- `MarketEvent` records a validated AI infrastructure catalyst.
- `SegmentImpact` maps catalyst effects across the AI infrastructure stack.
- `TradingAdvisory candidate update` is a reviewable advisory input, not an action, order, execution instruction, or automated trade decision.

## Source Of Truth

The crawler universe is config-driven:

- `config/ai_equity_watchlist.yaml` owns ticker, company name, themes, sector tags, optional source URLs, and priority.
- Business logic must load and validate that config instead of hard-coding watched companies.
- Local user files are outside the public-source crawler. If local research ingestion exists elsewhere, it must validate files before evidence materialization and must not reuse the public crawler as a private-document crawler.

## Advisory Boundary

Allowed:

- monitor configured public sources
- crawl configured public company, investor-relations, public filing, public technical, macro, policy, sector, and public news sources
- classify sources into data classes
- detect macro, micro, thematic, company, financial, and segment-level changes
- extract source signals, claims, typed events, timestamps, and evidence spans
- materialize evidence items, chunks, claims, and run artifacts
- raise risk, thesis, refresh, source-signal, or review events for advisory workflows
- support `TradingAdvisory` candidate updates with provenance and review gates

Forbidden:

- crawling arbitrary internet sources without watchlist or source-registry configuration
- scraping paid reports
- crawling private documents, local file trees, email inboxes, cloud drives, data rooms, or account portals
- ingesting sensitive private financial documents
- credentials for financial accounts or venues
- private account forms, account-transfer PDFs, or other sensitive local documents as evidence
- broker, order, route, fill, execution, or automated trading outputs
- any live market action endpoint or UI control
- any execution/trading action
- using LLM output to produce deterministic scores, constraints, or target weights directly

## Source Frontier

The crawler uses a source frontier adapted from the startup-analysis onboarding frontier pattern.

Each frontier target is derived from a watchlist entry plus a source kind:

| Source kind | Examples | Default data class |
| --- | --- | --- |
| company_home | configured company product and platform pages | public_evidence |
| company_investor_relations | company IR sites, earnings releases, presentations, investor days, transcripts, filings links | public_evidence |
| sec_filings | SEC filings, 10-K, 10-Q, 8-K, proxy, Form 4, 13F, and other public SEC pages | public_evidence |
| technical_docs | product docs, benchmark pages, architecture notes | public_evidence |
| earnings_releases_transcripts | earnings releases, call transcripts, prepared remarks, and public Q&A summaries | public_evidence |
| hyperscaler_capex_commentary | public capex guidance, cloud capacity commentary, and datacenter investment remarks | public_evidence |
| semiconductor_supply_chain_news | public supply-chain, substrate, equipment, fab, and packaging capacity news | public_evidence |
| hbm_memory_news | public HBM, memory, DRAM, memory pricing, qualification, and capacity updates | public_evidence |
| cowos_advanced_packaging_news | public CoWoS, advanced packaging, interposer, and substrate capacity updates | public_evidence |
| datacenter_leasing_power_contracts | public leases, campus announcements, PPAs, interconnection updates, and power contracts | public_evidence |
| utility_load_growth_guidance | utility earnings, load-growth guidance, grid capex, and interconnection queue commentary | public_evidence |
| export_controls_geopolitical_policy | public export-control, sanctions, sovereign AI, national-security, and geopolitical policy updates | public_evidence |
| macro_rates_liquidity_commentary | public rates, liquidity, credit, risk appetite, and market-structure commentary | public_market_data |
| public_sentiment_news_flow | public articles, reputable news flow, public sentiment summaries, and press releases | public_evidence |

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

The frontier must not discover or crawl arbitrary internet sources outside configured watchlist entries, source registry records, or explicit approved public-source categories. Search-engine expansion is allowed only when it produces candidate URLs for human or policy approval before crawl scheduling.

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

The crawler emits `SourceSignal` and typed `MarketEvent` records from public evidence. They are advisory signals, not actions.

`SourceSignal` records should include:

- `source_signal_id`
- `frontier_url_id`
- `source_kind`
- `ticker`
- `company`
- `detected_at`
- `signal_type`
- `summary`
- `source_url`
- `content_hash`
- `data_class`
- `review_status`
- `evidence_candidate_id` when materialized

`SourceSignal` records are created only from configured public sources. A signal is not usable downstream until it links to an `EvidenceItem` or is explicitly rejected during review.

Initial source signal types:

- `new_public_document`
- `changed_public_document`
- `earnings_or_transcript_update`
- `filing_update`
- `capex_commentary_change`
- `supply_chain_signal`
- `hbm_memory_signal`
- `advanced_packaging_signal`
- `datacenter_or_power_signal`
- `utility_load_growth_signal`
- `export_control_or_policy_signal`
- `macro_liquidity_signal`
- `public_sentiment_signal`

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
- `macro_liquidity_signal`
- `valuation_context_signal`

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

`TradingAdvisory` candidate updates may reference crawler outputs only after evidence materialization and review gating. They must cite `EvidenceItem`, `MarketEvent`, and `SegmentImpact` records. They must never contain broker, order, route, fill, execution, automated-trading, or live-market-action instructions.

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

Private local research files are not crawler inputs. If a separate manual-ingestion path validates local research before materialization, sensitive Schwab, account-transfer, or routing-number PDFs are quarantined and must not become evidence items.

Paid reports, licensed research, private financial documents, broker statements, account exports, tax documents, and other sensitive private documents must not be crawled, scraped, or materialized by the public-source crawler.

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
- SourceSignals are created only from configured public sources.
- MarketEvents and TradingAdvisory candidate updates link back to evidence IDs.
- Refresh jobs and leases support crash recovery and bounded retry.
- Typed events include source evidence IDs and model run IDs when model-assisted extraction is used.
- The crawler never emits broker, order, route, fill, execution, automated-trading, or live-market-action outputs.
- Architecture policy tests continue to pass.
