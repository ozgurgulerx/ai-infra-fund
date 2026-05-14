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
docker compose build api migrate worker web

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
docker compose exec -T postgres psql \
  -U ai_infra_fund \
  -d ai_infra_fund \
  -v ON_ERROR_STOP=1 \
  -c "SELECT to_regclass('core.watched_equities') AS watched_equities, to_regclass('signals.equity_events') AS equity_events, to_regclass('audit.equity_intelligence_runs') AS equity_intelligence_runs;"
docker compose exec -T postgres psql \
  -U ai_infra_fund \
  -d ai_infra_fund \
  -v ON_ERROR_STOP=1 \
  -c "SELECT column_name FROM information_schema.columns WHERE table_schema = 'signals' AND table_name = 'equity_events' AND column_name IN ('available_at', 'evidence_claim_ids', 'model_run_ids', 'review_status') ORDER BY column_name;"
docker compose exec -T postgres psql \
  -U ai_infra_fund \
  -d ai_infra_fund \
  -v ON_ERROR_STOP=1 \
  -c "INSERT INTO audit.model_runs (model_run_id, task_role, model_id, deployment, provider, prompt_version, input_hash, output_hash, latency_ms, token_estimate_input, token_estimate_output, schema_valid, retry_count, data_classes, status, created_at) VALUES ('smoke-model-run', 'evidence_summary', 'smoke-model', 'smoke-deployment', 'smoke-provider', 'smoke-prompt-v1', repeat('a', 64), repeat('b', 64), 1, 1, 1, true, 0, ARRAY['public_evidence'], 'success', now()) ON CONFLICT (model_run_id) DO NOTHING;"
docker compose exec -T postgres psql \
  -U ai_infra_fund \
  -d ai_infra_fund \
  -v ON_ERROR_STOP=1 \
  -c "DELETE FROM audit.model_runs WHERE model_run_id = 'smoke-model-run';"

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
