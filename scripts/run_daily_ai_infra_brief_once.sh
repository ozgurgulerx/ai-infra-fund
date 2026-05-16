#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${PROJECT_ROOT}"
docker compose build migrate worker
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm worker python -m ai_infra_fund_worker.daily_ai_infra_brief_run
