#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRAWL_BATCH_SIZE="${AI_INFRA_FUND_CRAWL_BATCH_SIZE:-20}"
CRAWL_DOMAIN_CAP="${AI_INFRA_FUND_CRAWL_DOMAIN_CAP:-2}"
SEC_USER_AGENT="${SEC_EDGAR_USER_AGENT:-AI Infra Fund Research <ozgur.guler1@gmail.com>}"

cd "${PROJECT_ROOT}"

docker compose build migrate worker
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm \
  -e AI_INFRA_FUND_WATCHLIST_PATH=/app/config/ai_equity_watchlist.yaml \
  -e AI_INFRA_FUND_SOURCE_REGISTRY_PATH=/app/config/source_registry.yaml \
  -e SEC_EDGAR_USER_AGENT="${SEC_USER_AGENT}" \
  worker python -m ai_infra_fund_worker.crawl reclaim-stale
docker compose run --rm \
  -e AI_INFRA_FUND_WATCHLIST_PATH=/app/config/ai_equity_watchlist.yaml \
  -e AI_INFRA_FUND_SOURCE_REGISTRY_PATH=/app/config/source_registry.yaml \
  -e SEC_EDGAR_USER_AGENT="${SEC_USER_AGENT}" \
  worker python -m ai_infra_fund_worker.crawl run --once \
    --batch-size "${CRAWL_BATCH_SIZE}" \
    --domain-cap "${CRAWL_DOMAIN_CAP}"
