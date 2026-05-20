#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_USER="${POSTGRES_USER:-ai_infra_fund}"
POSTGRES_DB="${POSTGRES_DB:-ai_infra_fund}"

cd "${PROJECT_ROOT}"

query_scalar() {
  local sql="$1"
  docker compose exec -T postgres \
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "${sql}" \
    | tr -d '[:space:]'
}

fail() {
  local message="$1"
  printf 'crawl runtime smoke failed: %s\n' "${message}" >&2
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

frontier_count="$(query_scalar "SELECT COUNT(*) FROM evidence.source_frontier_urls;")"
queue_count="$(query_scalar "SELECT COUNT(*) FROM evidence.crawl_frontier_queue;")"
leasable_predicate="status IN ('queued','retry') AND next_attempt_at <= now() AND NOT (COALESCE(last_error_summary, '') IN ('http_403', 'robots_disallowed') OR COALESCE(metadata_json->>'render_strategy', '') = 'blocked' OR COALESCE(metadata_json->>'crawl_allowed', 'true') = 'false')"
due_count="$(query_scalar "SELECT COUNT(*) FROM evidence.source_frontier_urls WHERE ${leasable_predicate};")"
crawl_log_count="$(query_scalar "SELECT COUNT(*) FROM evidence.crawl_logs;")"
capture_count="$(query_scalar "SELECT COUNT(*) FROM evidence.source_raw_captures;")"
evidence_item_count="$(query_scalar "SELECT COUNT(*) FROM evidence.evidence_items;")"
source_signal_count="$(query_scalar "SELECT COUNT(*) FROM analyst.source_signals;")"
market_event_count="$(query_scalar "SELECT COUNT(*) FROM analyst.market_events;")"
future_recrawl_count="$(query_scalar "SELECT COUNT(*) FROM evidence.source_frontier_urls WHERE status = 'queued' AND next_attempt_at > now();")"
hot_blocked_count="$(query_scalar "SELECT COUNT(*) FROM evidence.source_frontier_urls WHERE ${leasable_predicate} AND (last_error_summary IN ('http_403','robots_disallowed') OR metadata_json->>'render_strategy' = 'blocked');")"

require_positive \
  "source_frontier_urls" \
  "${frontier_count}" \
  "source_frontier_urls is empty; run scripts/seed_public_sources.sh"

require_positive \
  "crawl_frontier_queue" \
  "${queue_count}" \
  "crawl_frontier_queue is empty; run scripts/seed_public_sources.sh"

if [[ "${due_count}" -le 0 && "${future_recrawl_count}" -le 0 ]]; then
  fail "frontier seeded but not leased and no future recurring rows exist"
fi

if [[ "${crawl_log_count}" -le 0 ]]; then
  fail "frontier seeded but not leased; crawl_logs is empty"
fi

require_positive \
  "future_recrawl_count" \
  "${future_recrawl_count}" \
  "next_due_at exists after success; no successful/not-modified frontier URL has a future next_attempt_at"

if [[ "${hot_blocked_count}" -gt 0 ]]; then
  fail "failed source does not spin hot; blocked/robots-disallowed source is immediately due"
fi

if [[ "${capture_count}" -le 0 ]]; then
  printf 'crawl runtime smoke warning: leases occurred but no successful source_raw_captures are present yet\n' >&2
fi

if [[ "${evidence_item_count}" -le 0 ]]; then
  printf 'crawl runtime smoke warning: captures written but no EvidenceItems are present yet\n' >&2
fi

if [[ "${source_signal_count}" -le 0 ]]; then
  printf 'crawl runtime smoke warning: evidence item written but no SourceSignals are present yet\n' >&2
fi

if [[ "${market_event_count}" -le 0 ]]; then
  printf 'crawl runtime smoke warning: source signal written but no MarketEvents are present yet\n' >&2
fi

cat <<REPORT
crawl runtime smoke passed:
  source_frontier_urls=${frontier_count}
  crawl_frontier_queue=${queue_count}
  due_source_frontier_urls=${due_count}
  future_recrawl_source_frontier_urls=${future_recrawl_count}
  crawl_logs=${crawl_log_count}
  source_raw_captures=${capture_count}
  evidence_items=${evidence_item_count}
  source_signals=${source_signal_count}
  market_events=${market_event_count}
REPORT
