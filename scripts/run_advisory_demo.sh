#!/usr/bin/env bash
set -euo pipefail

docker compose build worker
docker compose run --rm worker python -m ai_infra_fund_worker.advisory_run
