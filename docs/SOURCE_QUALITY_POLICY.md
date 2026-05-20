# Source Quality Policy

The public-source crawler exists only to monitor configured AI infrastructure equity sources and materialize provenance-backed evidence for advisory analysis.

## Source Tiers

| Tier | Use | Examples |
| --- | --- | --- |
| `tier_0_primary` | Primary issuer, regulator, government, or canonical data source. | SEC EDGAR, company IR, EIA, FRED, Stooq. |
| `tier_1_specialist` | Specialist technical or sector source used for catalyst context. | SemiAnalysis public metadata, Semiconductor Engineering, Data Center Dynamics, Epoch AI. |
| `tier_2_news_api` | Broad public news or market-data API used for monitoring and cross-checks. | GDELT DOC 2.0, Finnhub company news. |
| `tier_3_social_attention` | Public attention signal only. It cannot independently drive advisory labels. | Public social/news attention feeds. |

## Rules

- Sources must be declared in `config/source_registry.yaml`.
- Frontier URLs must be derived from the source registry and `config/ai_equity_watchlist.yaml`.
- The crawler must not crawl arbitrary internet URLs, private files, account portals, paid reports, broker documents, email, cloud drives, or local folders.
- Paid, paywalled, or licensed sources are metadata/excerpt-only unless explicitly reviewed and configured otherwise.
- Optional-secret providers are skipped when their secret is missing. The skip reason must be logged and must not block public URL seeding.
- Public endpoints that are robots-blocked, rate-limited, or unstable under the
  approved HTTP-only crawler must be repaired to a crawlable endpoint or marked
  `crawl_enabled: false` with a clear `disabled_reason`. Disabled sources remain
  visible in source metadata but must not seed new frontier or queue rows.
- Stored frontier URLs must not include API keys, tokens, passwords, or other credentials.
- Every source record must preserve `source_id`, `tier`, `source_kind`, `data_class`, `trust_weight`, `license_label`, and `refresh_interval_minutes`.
- `tier_3_social_attention` sources can raise attention signals only; downstream advisory artifacts still require evidence, deterministic checks, and risk/invalidation review.

## Source Access Decisions

Candidate sources from external source maps that cannot be safely activated
must be saved in `config/source_access_decisions.yaml`. This file is the
machine-readable holding area for public-but-not-ready sources, including:

- optional public API keys that need cloud secret approval,
- public URLs that returned `403`, timeout, DNS, or unstable endpoint results,
- public portals that require a typed provider rather than generic crawling,
- broad global/thematic pages that need explicit ticker/segment mapping before
  they can enter the frontier,
- low-value static homepages where a narrower endpoint should be selected.

Access-decision entries must use `crawl_enabled: false` and must not seed
`evidence.source_registry`, `evidence.source_frontier_urls`, or
`evidence.crawl_frontier_queue`. Moving one of these entries into the active
registry requires a future source-specific task with validation evidence.

## Restricted Inference Sources

Some useful AI industrial mobilisation information sources require an account,
API key, paid subscription, licensed data agreement, or terms review. These
sources must be saved in `config/restricted_inference_sources.yaml`, not in
`config/source_registry.yaml`.

Restricted sources are planning metadata only:

- `crawl_enabled` must be `false`.
- `default_action` must be `do_not_crawl`.
- no secrets, tokens, passwords, or credential values may be stored.
- optional `secret_env_var` names may document a future integration requirement,
  but secret values must remain outside Git and outside crawl logs.
- restricted sources must not seed `evidence.source_registry`,
  `evidence.source_frontier_urls`, or `evidence.crawl_frontier_queue`.

Moving a restricted source into the active crawler requires a future explicit
task that reviews licensing, rate limits, auth, source policy, and data class.
Until then, restricted URLs may inform human planning only and must not be
materialized as crawl evidence.

## Runtime Source State

Crawler runtime state is policy state, not a permission to expand crawling. It may track:

- consecutive failures,
- recent block indicators,
- last HTTP status,
- robots disallow,
- `backoff_until`,
- `blocked_until`,
- `requires_key`,
- `render_strategy = http_only | playwright_required | blocked`,
- `crawl_allowed`,
- source tier/trust metadata.

`render_strategy` is advisory metadata only in v1. The runtime remains `http_only`; Playwright/browser fallback, proxy escalation, and stealth crawling are disabled unless a future task explicitly enables them for a source-registry-approved public source.

Successful and `304 not modified` crawls must schedule a future recrawl using `refresh_interval_minutes`. `429`, `403`, robots-disallowed, and timeout failures must back off and must not spin hot.

## Advisory Boundary

Source monitoring may create `SourceSignal`, `EvidenceItem`, `MarketEvent`, and downstream advisory candidates. It must not create broker records, order records, execution instructions, live market actions, automated trading loops, or execution UI state.
