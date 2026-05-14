#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[compose-smoke] %s\n' "$*"
}

check_url() {
  local url="$1"
  curl --fail --silent --show-error \
    --retry 20 \
    --retry-delay 1 \
    --retry-all-errors \
    "$url"
  printf '\n'
}

on_failure() {
  status=$?
  log "failure detected; recent compose logs follow"
  docker compose logs --no-color --tail=100 || true
  exit "$status"
}

trap on_failure ERR

log "validating compose config"
docker compose config

log "building service images"
docker compose build api worker web

log "starting postgres"
docker compose up -d postgres

log "running migrations"
docker compose run --rm migrate

log "checking pgvector and migrated tables"
docker compose exec -T postgres psql \
  -U ai_infra_fund \
  -d ai_infra_fund \
  -v ON_ERROR_STOP=1 \
  -c "SELECT '[1,0,0]'::vector <=> '[0,1,0]'::vector AS cosine_distance;"
docker compose exec -T postgres psql \
  -U ai_infra_fund \
  -d ai_infra_fund \
  -v ON_ERROR_STOP=1 \
  -c "SELECT to_regclass('evidence.evidence_chunks') AS evidence_chunks, to_regclass('recommendations.recommendation_artifacts') AS recommendation_artifacts;"

log "starting api, worker, and web"
docker compose up -d api worker web

log "checking API health"
check_url http://localhost:8000/health

log "checking API readiness"
check_url http://localhost:8000/ready

log "showing service status"
docker compose ps

log "recent service logs"
docker compose logs --no-color --tail=100

log "compose smoke passed"
