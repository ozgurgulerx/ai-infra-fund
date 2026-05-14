#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_INPUT_DIR="${AI_INFRA_FUND_LOCAL_INPUT_DIR:-${PROJECT_ROOT}/data/local_advisory_sample}"
CONTAINER_INPUT_DIR="/app/data/$(basename "${HOST_INPUT_DIR}")"

mkdir -p "${HOST_INPUT_DIR}"

if [[ ! -f "${HOST_INPUT_DIR}/portfolio_positions.csv" ]]; then
  cat > "${HOST_INPUT_DIR}/portfolio_positions.csv" <<'CSV'
ticker,quantity,cost_basis,market_price,currency,asset_type,account_label,as_of,available_at
NVDA,3,200,900,USD,equity,local,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00
MSFT,4,300,410,USD,equity,local,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00
CASH,1000,1,1,USD,cash,local,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00
CSV
fi

if [[ ! -f "${HOST_INPUT_DIR}/trade_journal.csv" ]]; then
  cat > "${HOST_INPUT_DIR}/trade_journal.csv" <<'CSV'
ticker,side,quantity,price,fees,trade_date,status,account_label,notes
NVDA,buy,1,850,0,2026-05-10,completed,local,manual local entry
CSV
fi

if [[ ! -f "${HOST_INPUT_DIR}/universe.csv" ]]; then
  cat > "${HOST_INPUT_DIR}/universe.csv" <<'CSV'
ticker,name,theme,role,watchlist_status,max_weight,liquidity_floor,thesis_source
NVDA,NVIDIA,ai_accelerators,core,active,0.25,0.00,local thesis
MSFT,Microsoft,ai_cloud,core,active,0.25,0.00,local thesis
CSV
fi

if [[ ! -f "${HOST_INPUT_DIR}/market_snapshots.csv" ]]; then
  cat > "${HOST_INPUT_DIR}/market_snapshots.csv" <<'CSV'
ticker,asset_type,as_of,available_at,source,close_price,volume
NVDA,equity,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00,manual,900,1000000
MSFT,equity,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00,manual,410,1200000
CSV
fi

if [[ ! -f "${HOST_INPUT_DIR}/nvda-note.md" ]]; then
  cat > "${HOST_INPUT_DIR}/nvda-note.md" <<'MD'
NVDA accelerator demand remains strong and local evidence supports medium-term AI infrastructure exposure.
MD
fi

if [[ ! -f "${HOST_INPUT_DIR}/evidence_index.csv" ]]; then
  cat > "${HOST_INPUT_DIR}/evidence_index.csv" <<'CSV'
file_path,source_uri,license_label,data_class,tickers,themes,title,confidence,horizon
nvda-note.md,file://local/nvda-note.md,user_private,private_research,NVDA,ai_accelerators,Local AI note,0.80,medium_term
CSV
fi

cd "${PROJECT_ROOT}"
docker compose build worker
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm -e "AI_INFRA_FUND_LOCAL_INPUT_DIR=${CONTAINER_INPUT_DIR}" worker python -m ai_infra_fund_worker.local_advisory_run
