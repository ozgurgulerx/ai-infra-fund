from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from ai_infra_fund_api.repositories.equity_intelligence import (
    EquityIntelligenceRepository,
)
from ai_infra_fund_core.equity_intelligence.capture import LocalCaptureStore
from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy
from ai_infra_fund_core.equity_intelligence.research_extractor import (
    StubLLMClaimExtractor,
)

from .scheduler import SchedulerConfig, build_default_fetcher, run_forever
from .seed import seed_watchlist
from .worker_loop import run_crawl_batch


LOGGER = logging.getLogger("ai_infra_fund.worker.crawl.cli")


def _database_url() -> str:
    url = os.environ.get("AI_INFRA_FUND_DATABASE_URL")
    if not url:
        raise SystemExit("AI_INFRA_FUND_DATABASE_URL must be set")
    return url


def _watchlist_path() -> Path:
    explicit = os.environ.get("AI_INFRA_FUND_WATCHLIST_PATH")
    if explicit:
        return Path(explicit)
    return Path(__file__).resolve().parents[5] / "config" / "ai_equity_watchlist.yaml"


def _source_registry_path() -> Path | None:
    explicit = os.environ.get("AI_INFRA_FUND_SOURCE_REGISTRY_PATH")
    if explicit:
        return Path(explicit)
    candidate = Path(__file__).resolve().parents[5] / "config" / "source_registry.yaml"
    return candidate if candidate.exists() else None


def _captures_root() -> Path:
    explicit = os.environ.get("AI_INFRA_FUND_CAPTURES_ROOT")
    if explicit:
        return Path(explicit)
    return Path(os.environ.get("AI_INFRA_FUND_DATA_DIR", "data"))


def _worker_id() -> str:
    return os.environ.get("AI_INFRA_FUND_WORKER_ID") or f"crawl-{uuid.uuid4().hex[:8]}"


def cmd_seed(_args: argparse.Namespace) -> int:
    connection = psycopg.connect(_database_url())
    try:
        report = seed_watchlist(
            connection,
            watchlist_path=_watchlist_path(),
            source_registry_path=_source_registry_path(),
            now=datetime.now(tz=timezone.utc),
        )
    finally:
        connection.close()
    LOGGER.info(
        "watchlist seeded: equities=%d sources=%d frontier_urls=%d queue_items=%d",
        report.watched_equities,
        report.sources,
        report.frontier_urls,
        report.queue_items,
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    user_agent = (os.environ.get("SEC_EDGAR_USER_AGENT") or "").strip()
    if not user_agent:
        raise SystemExit(
            "SEC_EDGAR_USER_AGENT must be set before running the crawler "
            "(e.g. 'AI Infra Fund Research <contact@example.com>')"
        )
    config = SchedulerConfig(
        worker_id=_worker_id(),
        policy=FrontierPolicy(
            batch_size=args.batch_size,
            domain_cap=args.domain_cap,
        ),
        captures_root=_captures_root(),
        user_agent=user_agent,
        idle_sleep_seconds=args.idle_sleep,
    )

    if args.once:
        connection = psycopg.connect(_database_url())
        try:
            now = datetime.now(tz=timezone.utc)
            fetcher = build_default_fetcher(config)
            report = run_crawl_batch(
                connection,
                worker_id=config.worker_id,
                policy=config.policy,
                fetcher=fetcher,
                capture_store=LocalCaptureStore(config.captures_root),
                research_extractor=StubLLMClaimExtractor(),
                now=now,
            )
        finally:
            connection.close()
        LOGGER.info(
            "single batch result: leased=%d succeeded=%d not_modified=%d failed=%d",
            report.leased,
            report.succeeded,
            report.not_modified,
            report.failed,
        )
        return 0

    database_url = _database_url()

    def factory() -> object:
        return psycopg.connect(database_url)

    succeeded = run_forever(factory, config=config, max_loops=args.max_loops)
    LOGGER.info("scheduler exited after total succeeded captures=%d", succeeded)
    return 0


def cmd_reclaim_stale(_args: argparse.Namespace) -> int:
    connection = psycopg.connect(_database_url())
    try:
        repo = EquityIntelligenceRepository(connection)  # type: ignore[arg-type]
        reclaimed = repo.reclaim_stale_leases(now=datetime.now(tz=timezone.utc))
    finally:
        connection.close()
    LOGGER.info("reclaimed %d stale leases", reclaimed)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser(prog="ai_infra_fund_worker.crawl")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "seed", help="Load watchlist YAML into watched_equities + frontier tables"
    )

    p_run = sub.add_parser("run", help="Run the crawl worker loop")
    p_run.add_argument(
        "--once", action="store_true", help="Run a single batch and exit"
    )
    p_run.add_argument("--batch-size", type=int, default=20)
    p_run.add_argument("--domain-cap", type=int, default=2)
    p_run.add_argument("--idle-sleep", type=float, default=30.0)
    p_run.add_argument("--max-loops", type=int, default=None)

    sub.add_parser(
        "reclaim-stale", help="Reclaim leases whose lease_expires_at has passed"
    )

    args = parser.parse_args(argv)
    dispatch = {
        "seed": cmd_seed,
        "run": cmd_run,
        "reclaim-stale": cmd_reclaim_stale,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
