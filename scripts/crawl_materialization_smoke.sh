#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_USER="${POSTGRES_USER:-ai_infra_fund}"
POSTGRES_DB="${POSTGRES_DB:-ai_infra_fund}"

cd "${PROJECT_ROOT}"

count_table() {
  local table_name="$1"
  docker compose exec -T postgres \
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT COUNT(*) FROM ${table_name};" \
    | tr -d '[:space:]'
}

fail() {
  local message="$1"
  printf 'crawl materialization smoke failed: %s\n' "${message}" >&2
  exit 1
}

require_positive() {
  local label="$1"
  local value="$2"
  local message="$3"
  if [[ -z "${value}" || "${value}" -le 0 ]]; then
    fail "${message} (${label}=${value:-empty})"
  fi
}

frontier_count="$(count_table evidence.source_frontier_urls)"
queue_count="$(count_table evidence.crawl_frontier_queue)"
crawl_log_count="$(count_table evidence.crawl_logs)"
capture_count="$(count_table evidence.source_raw_captures)"
evidence_item_count="$(count_table evidence.evidence_items)"
source_signal_count="$(count_table analyst.source_signals)"
market_event_count="$(count_table analyst.market_events)"

require_positive \
  "source_frontier_urls" \
  "${frontier_count}" \
  "source_frontier_urls is empty; run scripts/seed_public_sources.sh"

require_positive \
  "crawl_frontier_queue" \
  "${queue_count}" \
  "crawl_queue items are empty; run scripts/seed_public_sources.sh"

if [[ "${crawl_log_count}" -le 0 ]]; then
  fail "frontier seeded but not leased; crawl_logs is empty"
fi

if [[ "${capture_count}" -le 0 ]]; then
  fail "leases acquired but fetch failed; source_raw_captures is empty"
fi

if [[ "${evidence_item_count}" -le 0 ]]; then
  fail "captures written but no evidence item; evidence.evidence_items is empty"
fi

if [[ "${source_signal_count}" -le 0 ]]; then
  fail "evidence item written but no source signal; analyst.source_signals is empty"
fi

if [[ "${market_event_count}" -le 0 ]]; then
  fail "source signal written but no MarketEvent; analyst.market_events is empty"
fi

cat <<REPORT
crawl materialization smoke passed:
  source_frontier_urls=${frontier_count}
  crawl_queue_items=${queue_count}
  crawl_logs=${crawl_log_count}
  source_raw_captures=${capture_count}
  evidence_items=${evidence_item_count}
  source_signals=${source_signal_count}
  market_events=${market_event_count}
REPORT
