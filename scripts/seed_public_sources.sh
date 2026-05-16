#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${PROJECT_ROOT}"
docker compose build migrate worker
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm \
  -e AI_INFRA_FUND_WATCHLIST_PATH=/app/config/ai_equity_watchlist.yaml \
  -e AI_INFRA_FUND_SOURCE_REGISTRY_PATH=/app/config/source_registry.yaml \
  worker python -m ai_infra_fund_worker.crawl seed
