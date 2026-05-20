# Crawl Runtime Delta

## Reference Inspected

Startup-analysis crawl runtime files reviewed:

- `packages/analysis/src/crawl_runtime/README.md`
- `packages/analysis/src/crawl_runtime/frontier.py`
- `packages/analysis/src/crawl_runtime/scrapy_runtime.py`
- `packages/analysis/src/crawl_runtime/run_spider.py`
- `packages/analysis/src/crawl_runtime/worker.py`
- `packages/analysis/src/crawl_runtime/unblock_provider.py`
- `infrastructure/vm-cron/jobs/crawl-frontier.sh`

## Queue Model Chosen

`evidence.source_frontier_urls` remains the authoritative v1 crawl queue for ai-infra-fund. The existing worker already leases from that table, evidence lineage points back to `frontier_url_id`, and the stricter source policy is stored on those rows.

`evidence.crawl_frontier_queue` is kept as a synchronized operational mirror for dashboards, smoke checks, and future migration. It must not diverge from the authoritative `source_frontier_urls` lifecycle.

## Runtime Delta

Startup-analysis uses recurring queue rows: successful, unchanged, and failed crawls all release the row back into a future due state. ai-infra-fund previously marked successful rows `captured`, which made the crawler idle once initial URLs were exhausted.

The ai-infra-fund runtime now follows the recurring model:

- success -> `status=queued`, `attempt_count=0`, future `next_attempt_at`
- `304 not modified` -> `status=queued`, future `next_attempt_at`
- generic failure -> `status=retry` with exponential backoff until max attempts
- `429` -> long rate-limit backoff
- `403` / robots disallow -> blocked metadata plus long backoff/no hot loop
- reseeding reactivates captured rows but does not hot-loop skipped/failed rows

Refresh cadence comes from `config/source_registry.yaml` `refresh_interval_minutes`; deterministic fallback intervals are used only when a source lacks registry cadence.

## Deployment Delta

Startup-analysis runs a VM cron job every 30 minutes. ai-infra-fund uses the equivalent AKS `CronJob`:

- `ai-infra-fund-crawl-frontier`
- schedule: `*/30 * * * *`
- command: `python -m ai_infra_fund_worker.crawl run --once`
- concurrency policy: `Forbid`

The long-running worker mode remains available and safe, but the scheduled job guarantees forward progress even if the long-running worker sits idle between due windows.

## Source Policy Differences

Copied/adapted:

- due-row leasing and stale lease recovery
- recurring release after success or not-modified
- retry/backoff semantics
- source/domain policy metadata
- fail-fast schema verification
- one-shot and runtime smoke scripts

Intentionally not copied:

- arbitrary same-site internal link discovery
- startup website common-path expansion
- broad sitemap expansion
- Browserless/stealth/proxy escalation by default
- paid/private/paywalled scraping
- private document ingestion
- any source outside `config/source_registry.yaml`

Optional render fallback remains a future-compatible concept only through `render_strategy = http_only | playwright_required | blocked`; v1 defaults to `http_only` and does not enable Playwright/browser fallback.

## Risks

- Some provider failures may remain in `failed` until explicit operator review or future source-state tooling.
- The queue mirror can still drift if future code updates one table without the synchronized repository methods.
- Real web changes may produce `not_modified` or provider errors, so operational smoke distinguishes "nothing due yet" from "frontier broken".

## Validation

Required local validation:

```bash
./.venv/bin/python -m unittest discover -s tests
python3 -m compileall packages services tests
docker compose config
scripts/seed_public_sources.sh
scripts/crawl_materialization_smoke.sh
scripts/run_crawl_frontier_once.sh
scripts/crawl_runtime_smoke.sh
git diff --check
```

Cloud validation:

```bash
kubectl -n ai-infra-fund get cronjob ai-infra-fund-crawl-frontier
scripts/cloud_crawl_frontier_once.sh
scripts/crawl_runtime_smoke.sh
```
