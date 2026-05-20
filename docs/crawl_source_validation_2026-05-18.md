# Crawl Source Validation - 2026-05-18

Purpose: validate each active source in `config/source_registry.yaml` and log
sources that need troubleshooting before expanding the AI industrial
mobilisation inference map.

Scope:

- Active crawl sources only: `config/source_registry.yaml`.
- Restricted/account/key/paid/licensed sources are excluded from crawling and
  tracked separately in `config/restricted_inference_sources.yaml`.
- Validation used one representative URL per active source plus production
  crawl-log history from AKS PostgreSQL.

## Summary

| Status | Count | Meaning |
| --- | ---: | --- |
| OK | 27 | Live probe succeeded under the approved HTTP-only crawler. |
| Deferred | 2 | Public sources remain in registry metadata but are crawl-disabled because the endpoint is currently unstable/rate-limited. |
| Failed | 0 | No active non-key source currently fails representative HTTP-only validation. |
| Skipped | 3 | Source requires a missing API key/secret and is skipped by design. |

## Active Source Results

| Source | Live result | Production history | Notes |
| --- | --- | --- | --- |
| `source_sec_edgar` | OK, HTTP 200 | 68 attempts, 68 captures, 0 errors | Healthy. |
| `source_nvidia_official` | OK, HTTP 200 | 5 attempts, 2 captures, 3 historical errors | Current URL works; historical errors can be monitored. |
| `source_tsmc_ir_monthly_revenue` | OK, HTTP 200 | 3 historical attempts, 0 captures, 3 errors from old blocked URL | Replaced Cloudflare-blocked TSMC investor URL with robots-allowed Taiwan MOPS landing endpoint `https://mops.twse.com.tw/mops/web/index`. |
| `source_eia_electricity` | Skipped | 204 historical attempts, 0 captures, 204 errors | `EIA_API_KEY` missing. Keep skipped until secret/provider config is approved. |
| `source_fred_macro` | Skipped | No current successful active crawl rows observed | `FRED_API_KEY` missing. Keep skipped until secret/provider config is approved. |
| `source_asml_investor_relations` | OK, HTTP 200 | New source-map onboarding | Public company IR source for ASML/lithography catalyst monitoring. |
| `source_semianalysis_public` | Deferred | 170 attempts, 68 captures, 102 historical errors from old search URL | Public RSS feed returned HTTP 429 during expanded validation. Keep metadata-only but crawl-disabled until source-specific rate handling or manual metadata import is approved. |
| `source_semiconductor_engineering` | OK, HTTP 200 | 68 attempts, 68 captures, 0 errors | Healthy. |
| `source_semiwiki` | OK, HTTP 200 | 71 attempts, 62 captures, 9 errors | Current URL works; monitor occasional failures. |
| `source_situational_awareness` | OK, HTTP 200 | New source-map onboarding | Public thesis/reference source; very low-frequency recrawl. |
| `source_datacenter_dynamics` | OK, HTTP 200 RSS | 104 attempts, 2 captures, 102 historical errors | Current RSS URL works; historical errors likely from earlier URL/config behavior. |
| `source_datacenter_knowledge` | OK, HTTP 200 XML | 102 historical attempts, 0 captures, 102 errors from old search URL | Replaced robots-disallowed search path with allowed sitemap `https://www.datacenterknowledge.com/sitemap.xml`. |
| `source_ieee_spectrum_ai_energy` | OK, HTTP 200 | 2 attempts, 2 captures, 0 errors | Healthy. |
| `source_deeplearning_ai_batch` | OK, HTTP 200 | 2 attempts, 2 captures, 0 errors | Healthy. |
| `source_epoch_ai` | OK, HTTP 200 | 2 attempts, 2 captures, 0 errors | Healthy. |
| `source_metr` | OK, HTTP 200 | 2 attempts, 2 captures, 0 errors | Healthy. |
| `source_arxiv_ai_recent` | OK, HTTP 200 | New source-map onboarding | Public AI research velocity source. |
| `source_wipo_ai_trends` | OK, HTTP 200 | New source-map onboarding | Public AI patent/technology-trend reference source; low-frequency recrawl. |
| `source_papers_with_code` | OK, HTTP 200 | New source-map onboarding | Public AI model/research benchmark context source. |
| `source_federal_register_bis_api` | OK, HTTP 200 JSON | New source-map onboarding | Uses public Federal Register API because the HTML agency page redirected to an unblock page. |
| `source_chips_for_america` | OK, HTTP 200 | New source-map onboarding | Public U.S. semiconductor industrial-policy source. |
| `source_us_treasury_interest_rates` | OK, HTTP 200 | New source-map onboarding | Public rates/macro valuation-pressure source. |
| `source_iea_data_statistics` | OK, HTTP 200 | New source-map onboarding | Public metadata-only energy/power context source. |
| `source_darpa_programs` | OK, HTTP 200 | New source-map onboarding | Public defense/frontier-compute program source. |
| `source_defense_innovation_unit` | OK, HTTP 200 | New source-map onboarding | Public defense/AI procurement context source. |
| `source_uspto_open_data` | OK, HTTP 200 | New source-map onboarding | Public metadata-only patent/technical-direction source. |
| `source_g42_ai_infrastructure` | OK, HTTP 200 | New source-map onboarding | Public Gulf sovereign AI infrastructure source. |
| `source_khazna_datacenters` | OK, HTTP 200 | New source-map onboarding | Public Gulf datacenter infrastructure source. |
| `source_gdelt_doc` | Deferred | 84 attempts, 22 captures, 62 errors | GDELT was unstable/rate-limited during validation. It remains documented but `crawl_enabled: false` with `disabled_reason: rate_limited_deferred`, so it no longer seeds or leases frontier rows until a future repair task. |
| `source_finnhub_company_news` | Skipped | No successful active crawl rows observed | `FINNHUB_API_KEY` missing. Keep skipped until secret/provider config is approved. |
| `source_stooq_market_data` | OK, HTTP 200 text/plain | 68 attempts, 68 captures, 0 errors | Healthy, though body is CSV/text and extractor should continue treating it as market-data evidence. |
| `source_public_social_attention` | OK, HTTP 200 | 68 attempts, 68 captures, 0 errors | Healthy metadata-only attention source. |

## Troubleshooting Queue

1. `source_semianalysis_public`
   - Problem: public feed returned HTTP 429 during expanded validation.
   - Current fix: disabled from active crawling with a clear disabled reason; source metadata remains for future repair.
   - Recommended future fix: implement a source-specific connector with conservative cadence, caching, and validation before re-enabling.

2. `source_gdelt_doc`
   - Problem: unstable response/rate behavior and request timeouts during repeated validation.
   - Current fix: disabled from active crawling with a clear disabled reason; source metadata remains for future repair.
   - Recommended future fix: implement a stricter provider-specific connector with durable rate limiting, small themed queries, and cloud validation before re-enabling.

3. Optional-secret providers
   - `source_eia_electricity`: needs `EIA_API_KEY`.
   - `source_fred_macro`: needs `FRED_API_KEY`.
   - `source_finnhub_company_news`: needs `FINNHUB_API_KEY`.
   - Recommended fix: keep skipped until secrets are explicitly configured and provider terms/rate limits are accepted.

## Validation Commands

- Live representative-source probe: `/tmp/validate_ai_infra_sources.py`.
- Production history query: grouped `evidence.crawl_logs` by `source_id`.
- Additional checks:
  - TSMC investor and eMOPS endpoints were rejected by Cloudflare/robots; MOPS landing endpoint validated.
  - Data Center Knowledge search is robots-disallowed; sitemap validated.
  - GDELT follow-up verification timed out or rate-limited, so it is disabled until a future connector repair.
  - Candidate source-map URLs that timed out, returned 403/404, need a typed
    provider, need account/key approval, or need global/thematic fanout support
    are saved in `config/source_access_decisions.yaml`.

## Guardrails

- No restricted source was added to active crawling.
- No paid/private/account/key-gated source was crawled from the restricted list.
- No browser, stealth, proxy, or robots bypass was used.
- No broker/order/execution behavior was introduced.
