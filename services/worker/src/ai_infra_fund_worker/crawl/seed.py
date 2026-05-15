from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ai_infra_fund_api.repositories.equity_intelligence import (
    EquityIntelligenceRepository,
)
from ai_infra_fund_core.equity_intelligence.seeder import (
    build_crawl_queue_items,
    build_frontier_url_records,
    build_provider_frontier_urls,
    build_provider_source_records,
    build_source_records,
    build_watched_equity_records,
)
from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist


@dataclass(frozen=True, slots=True)
class SeedReport:
    watched_equities: int
    sources: int
    frontier_urls: int
    queue_items: int


def seed_watchlist(
    connection: object,
    *,
    watchlist_path: Path,
    now: datetime,
) -> SeedReport:
    """Idempotently load the YAML watchlist into the four crawl tables.

    Every upsert is `ON CONFLICT DO UPDATE`, so re-running is safe.
    Does NOT prune tickers removed from the YAML (tracked TODO).
    """
    watchlist = load_ai_equity_watchlist(watchlist_path)
    repository = EquityIntelligenceRepository(connection)  # type: ignore[arg-type]

    watched_records = build_watched_equity_records(watchlist, now=now)
    host_source_records = build_source_records(watchlist, now=now)
    provider_source_records = build_provider_source_records(watchlist, now=now)
    host_frontier_records = build_frontier_url_records(watchlist, now=now)
    provider_frontier_records = build_provider_frontier_urls(watchlist, now=now)
    frontier_records = host_frontier_records + provider_frontier_records
    queue_records = build_crawl_queue_items(frontier_records, now=now)

    for record in watched_records:
        repository.upsert_watched_equity(record)
    for record in host_source_records:
        repository.upsert_source(record)
    for record in provider_source_records:
        repository.upsert_source(record)
    for record in frontier_records:
        repository.upsert_frontier_url(record)
    for record in queue_records:
        repository.upsert_crawl_queue_item(record)

    return SeedReport(
        watched_equities=len(watched_records),
        sources=len(host_source_records) + len(provider_source_records),
        frontier_urls=len(frontier_records),
        queue_items=len(queue_records),
    )


__all__ = ["SeedReport", "seed_watchlist"]
