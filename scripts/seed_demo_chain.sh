#!/usr/bin/env bash
set -euo pipefail

docker compose build api
docker compose run --rm api python -m ai_infra_fund_api.seed_demo_chain
