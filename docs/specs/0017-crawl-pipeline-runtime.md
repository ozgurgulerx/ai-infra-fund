# 0017 — Phase 10 Crawl Pipeline Runtime

Status: **v1 implemented** — deterministic crawl only, deep-research extension point is a stubbed Protocol.

## Purpose

Operationalize the equity-intelligence crawler. The schema, repositories, and pure-function frontier domain (`packages/core/src/ai_infra_fund_core/equity_intelligence/`) already existed; this spec defines the runtime that drives them: watchlist seeding, lease-based fetch loop, deterministic event extraction, and per-attempt audit.

See [0016](0016-equity-intelligence-crawler.md) for the Phase 10 source-of-truth design (forbidden lists, source kinds, data classes). This doc is the **execution layer** on top.

## Source kinds and data classes

V1 treats every watchlist source URL as `source_type=company_ir_press` / `data_class=public_evidence`. The `connectors.py` protocol enumerates `news_rss_public_web`, `sec_filing`, `company_ir_press`, `manual_local_file`, `market_price_snapshot`; those finer kinds are deferred to Phase 10b along with their specific extractors. Per [0013](0013-llm-routing-and-governance.md), no source flagged anything other than `public_evidence` or `public_market_data` is eligible for cloud LLM extraction.

## Fetcher contract

`HttpFetcher.fetch(url, *, etag, last_modified) -> FetchResult` — `packages/core/src/ai_infra_fund_core/equity_intelligence/fetcher.py`.

- Sync `httpx.Client`. No internal retry — failures bubble up so the frontier owns the backoff.
- Sends `If-None-Match` / `If-Modified-Since` when prior values exist (round-tripped via `evidence.source_frontier_urls.metadata_json`).
- `RobotsCache` (TTL 1 h, parser from `urllib.robotparser`) gates every fetch. A blocked host returns `error_summary='robots_disallowed'`. Network failures fetching robots.txt **fall open** (treated as allowed) — robots is advisory when the host is unreachable.
- `DomainThrottle` enforces a per-host minimum delay between requests (default 2 s).
- User-Agent: `ai-infra-fund/<version> (advisory; contact: local-only)`.

## Retry and backoff

Failure path computes the next attempt time inline using the existing `FrontierPolicy` defaults (`batch_size=20`, `domain_cap=2`, `lease_duration=15m`, `max_retries=3`, `backoff_base=5m`):

```
next_attempt_count = current + 1
if next_attempt_count >= max_attempts:
    next_attempt_at = now + 10 years   # effectively blocked
else:
    next_attempt_at = now + backoff_base * (2 ** (next_attempt_count - 1))
```

`record_frontier_failure` in `EquityIntelligenceRepository` transitions the row to `status='retry'` until `attempt_count >= max_attempts`, then `'failed'`.

## Lease semantics

`evidence.source_frontier_urls.LEASE_DUE_FRONTIER_URLS_SQL` uses `FOR UPDATE SKIP LOCKED`, so multiple workers can run in parallel without stepping on each other. Stale leases (`lease_expires_at < now()`) are reclaimed by `EquityIntelligenceRepository.reclaim_stale_leases(now=...)`, called every N loops by the scheduler.

## Per-attempt audit

Every `fetcher.fetch` call writes one row to `evidence.crawl_logs` (migration `0004_phase10_crawl_logs.sql`), recording: `attempt_id`, `frontier_url_id`, `ticker`, `source_id`, `url`, `attempted_at`, `fetch_method` (`http_get` | `http_304` | `error`), `http_status`, `latency_ms`, `bytes_fetched`, `capture_id` (if successful), `error_summary`. Required by 0016 line 111: "each crawl attempt writes a run artifact or crawl log row, even when the fetch fails."

The dashboard endpoint `/internal/dashboard/crawl-activity` aggregates the last 24 hours from this table.

## Capture storage

`LocalCaptureStore` writes bodies to `<root>/captures/<sha[:2]>/<sha>.body` with a `<sha>.meta.json` sidecar containing the response headers. The hash is over the **body content**, so identical payloads dedup naturally and align with the `evidence.source_raw_captures.content_hash UNIQUE` constraint.

Storage URI: `file://captures/<sha[:2]>/<sha>.body` — relative; resolvable from the worker's `data_dir`.

## Event extraction (deterministic)

`extract_events(...)` in `event_extractor.py` classifies captures:

| Input                                                                                       | Resulting event_type   |
| ------------------------------------------------------------------------------------------- | ---------------------- |
| RSS feed → one row per item                                                                 | `news_alert`           |
| HTML title matches `8-K`, `10-Q`, `10-K`, `form 4`, `13f`                                   | `sec_filing_published` |
| HTML title matches `press release`, `earnings`, `quarterly results`, `results`, `announces` | `company_ir_press`     |
| Fallback                                                                                    | `company_ir_press`     |

All emitted with `review_status='deterministic'`, `model_run_ids=[]`, `evidence_claim_ids=[]`. `content_hash` is the SHA-256 of canonical `(ticker, event_type, event_time, summary, salt)`. Re-running on identical inputs produces identical hashes — the `UPSERT_EQUITY_EVENT_SQL ON CONFLICT (content_hash) DO UPDATE` collapses duplicates.

## Deep-research extension point (Phase 10b)

`research_extractor.py` defines:

- `LLMClaimExtractor` Protocol with `extract_claims(*, capture: CaptureContext, model_router) -> ResearchExtractionResult`.
- `StubLLMClaimExtractor` — v1 default. Returns `ResearchExtractionResult(claims=(), model_runs=())`. No network calls.
- `CaptureContext` rejects construction if `data_class` not in `{public_market_data, public_evidence, derived_analytics}`.

A real extractor MUST:

1. Honor the same `data_class` guard before any cloud call.
2. Create a `ModelRun` per call (success or failure).
3. Produce only `EvidenceClaim` records with citations. Never scores, weights, or constraints — those remain deterministic.

## Worker entrypoint

`python -m ai_infra_fund_worker.crawl <subcommand>`:

- `seed` — load `config/ai_equity_watchlist.yaml` into the four crawl tables (idempotent).
- `run --once` — single batch.
- `run --forever` — daemon, with periodic stale-lease reclamation.
- `reclaim-stale` — manual stale-lease reclamation.

The main worker container respects `AI_INFRA_FUND_WORKER_MODE=crawl` to enter the scheduler at process startup.

## Deferred (Phase 10b / later)

- JS rendering (Playwright / Browserless escalation)
- SEC EDGAR-specific filing parsing
- Real LLM claim extractor (Azure OpenAI Responses API, governed by model router)
- Embedding model wiring for `evidence.evidence_chunks.embedding`
- Provider-specific connectors (`news_rss_public_web`, `market_price_snapshot`)
- YAML `--prune` flag on `seed` to deactivate removed tickers
