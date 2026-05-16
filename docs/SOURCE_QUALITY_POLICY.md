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
- Stored frontier URLs must not include API keys, tokens, passwords, or other credentials.
- Every source record must preserve `source_id`, `tier`, `source_kind`, `data_class`, `trust_weight`, `license_label`, and `refresh_interval_minutes`.
- `tier_3_social_attention` sources can raise attention signals only; downstream advisory artifacts still require evidence, deterministic checks, and risk/invalidation review.

## Advisory Boundary

Source monitoring may create `SourceSignal`, `EvidenceItem`, `MarketEvent`, and downstream advisory candidates. It must not create broker records, order records, execution instructions, live market actions, automated trading loops, or execution UI state.
