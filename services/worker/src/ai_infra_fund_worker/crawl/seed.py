from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import os
from pathlib import Path

from ai_infra_fund_api.repositories.equity_intelligence import (
    EquityIntelligenceRepository,
)
from ai_infra_fund_core.equity_intelligence.seeder import (
    build_crawl_queue_items,
    build_frontier_url_records,
    build_provider_frontier_urls,
    build_provider_source_records,
    build_source_registry_seed_plan,
    build_source_records,
    build_watched_equity_records,
)
from ai_infra_fund_core.equity_intelligence.source_registry import (
    load_source_registry,
)
from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist


LOGGER = logging.getLogger("ai_infra_fund.worker.crawl.seed")


@dataclass(frozen=True, slots=True)
class SeedReport:
    watched_equities: int
    sources: int
    frontier_urls: int
    queue_items: int
    skipped_sources: tuple[tuple[str, str], ...] = ()


def seed_watchlist(
    connection: object,
    *,
    watchlist_path: Path,
    source_registry_path: Path | None = None,
    now: datetime,
    environ: dict[str, str] | None = None,
) -> SeedReport:
    """Idempotently load configured public sources into crawl tables.

    Every upsert is `ON CONFLICT DO UPDATE`, so re-running is safe.
    Does NOT prune tickers removed from the YAML (tracked TODO).
    """
    watchlist = load_ai_equity_watchlist(watchlist_path)
    repository = EquityIntelligenceRepository(connection)  # type: ignore[arg-type]
    env = os.environ if environ is None else environ

    watched_records = build_watched_equity_records(watchlist, now=now)
    skipped_sources: tuple[tuple[str, str], ...] = ()

    if source_registry_path is not None and source_registry_path.exists():
        registry = load_source_registry(source_registry_path)
        source_plan = build_source_registry_seed_plan(
            watchlist,
            registry,
            now=now,
            environ=dict(env),
        )
        source_records = source_plan.source_records
        frontier_records = source_plan.frontier_url_records
        skipped_sources = tuple(
            (record.source_id, record.reason) for record in source_plan.skipped_sources
        )
        for source_id, reason in skipped_sources:
            LOGGER.info("source_registry source skipped: %s reason=%s", source_id, reason)
    else:
        host_source_records = build_source_records(watchlist, now=now)
        provider_source_records = build_provider_source_records(watchlist, now=now)
        host_frontier_records = build_frontier_url_records(watchlist, now=now)
        provider_frontier_records = build_provider_frontier_urls(watchlist, now=now)
        source_records = host_source_records + provider_source_records
        frontier_records = host_frontier_records + provider_frontier_records

    queue_records = build_crawl_queue_items(frontier_records, now=now)

    for record in watched_records:
        repository.upsert_watched_equity(record)
    for record in source_records:
        repository.upsert_source(record)
    for record in frontier_records:
        repository.upsert_frontier_url(record)
    for record in queue_records:
        repository.upsert_crawl_queue_item(record)

    return SeedReport(
        watched_equities=len(watched_records),
        sources=len(source_records),
        frontier_urls=len(frontier_records),
        queue_items=len(queue_records),
        skipped_sources=skipped_sources,
    )


__all__ = ["SeedReport", "seed_watchlist"]
