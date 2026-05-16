#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_FIXTURE_PATH="${AI_INFRA_FUND_FIXTURE_BRIEF_PATH:-${PROJECT_ROOT}/docs/mock_data/situational_awareness_brief.example.json}"
CONTAINER_FIXTURE_PATH="/app/docs/mock_data/$(basename "${HOST_FIXTURE_PATH}")"

cd "${PROJECT_ROOT}"
docker compose build migrate worker
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm \
  -v "${PROJECT_ROOT}/docs:/app/docs:ro" \
  -e "AI_INFRA_FUND_FIXTURE_BRIEF_PATH=${CONTAINER_FIXTURE_PATH}" \
  worker python -m ai_infra_fund_worker.fixture_advisory_run
