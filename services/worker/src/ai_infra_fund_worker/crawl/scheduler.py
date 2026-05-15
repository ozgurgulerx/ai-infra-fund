from __future__ import annotations

import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ai_infra_fund_api.repositories.equity_intelligence import (
    EquityIntelligenceRepository,
)
from ai_infra_fund_core.equity_intelligence.capture import LocalCaptureStore
from ai_infra_fund_core.equity_intelligence.fetcher import (
    DomainThrottle,
    HttpFetcher,
    RobotsCache,
)
from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy
from ai_infra_fund_core.equity_intelligence.research_extractor import (
    StubLLMClaimExtractor,
)

from .worker_loop import CrawlBatchReport, Fetcher, run_crawl_batch


LOGGER = logging.getLogger("ai_infra_fund.worker.crawl")


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    """Crawl scheduler config.

    ``user_agent`` is required because SEC EDGAR (and other publishers) require
    a real contact in the UA. The host crawler may route ``data.sec.gov`` URLs,
    so a generic UA can get the whole worker rate-limited or blocked. We
    enforce that the UA contains either an email (``@``) or a URL (``http``).
    """

    worker_id: str
    policy: FrontierPolicy
    captures_root: Path
    user_agent: str
    idle_sleep_seconds: float = 30.0
    stale_lease_check_every: int = 10  # loops
    request_timeout: float = 10.0
    domain_min_delay: float = 2.0

    def __post_init__(self) -> None:
        ua = self.user_agent.strip()
        if not ua:
            raise ValueError(
                "SchedulerConfig.user_agent is required (set SEC_EDGAR_USER_AGENT)"
            )
        if "@" not in ua and "http" not in ua.lower():
            raise ValueError(
                "SchedulerConfig.user_agent must contain a contact email or URL "
                "to comply with SEC EDGAR fair-use policy"
            )


def build_default_fetcher(config: SchedulerConfig) -> HttpFetcher:
    import httpx  # imported lazily so unit tests can inject fakes without httpx setup

    client = httpx.Client(
        headers={"User-Agent": config.user_agent},
        timeout=config.request_timeout,
        follow_redirects=True,
    )
    return HttpFetcher(
        client=client,
        user_agent=config.user_agent,
        robots_cache=RobotsCache(client=client, user_agent=config.user_agent),
        domain_throttle=DomainThrottle(min_delay_seconds=config.domain_min_delay),
    )


def run_forever(
    connection_factory: Callable[[], object],
    *,
    config: SchedulerConfig,
    fetcher: Fetcher | None = None,
    max_loops: int | None = None,
) -> int:
    """Long-running crawl loop. Returns total successful captures emitted."""
    stop = {"signal": False}

    def _handle(_signum: int, _frame: object) -> None:
        LOGGER.info("crawl scheduler stopping on signal")
        stop["signal"] = True

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)

    loops = 0
    total_succeeded = 0
    config.captures_root.mkdir(parents=True, exist_ok=True)
    capture_store = LocalCaptureStore(config.captures_root)
    research_extractor = StubLLMClaimExtractor()
    active_fetcher = fetcher or build_default_fetcher(config)

    try:
        while not stop["signal"]:
            loops += 1
            if max_loops is not None and loops > max_loops:
                break

            if loops % config.stale_lease_check_every == 1:
                _reclaim_stale(connection_factory)

            connection = connection_factory()
            try:
                now = datetime.now(tz=timezone.utc)
                report = run_crawl_batch(
                    connection,
                    worker_id=config.worker_id,
                    policy=config.policy,
                    fetcher=active_fetcher,
                    capture_store=capture_store,
                    research_extractor=research_extractor,
                    now=now,
                )
            finally:
                close = getattr(connection, "close", None)
                if callable(close):
                    close()

            total_succeeded += report.succeeded
            LOGGER.info(
                "crawl batch leased=%d succeeded=%d not_modified=%d failed=%d",
                report.leased,
                report.succeeded,
                report.not_modified,
                report.failed,
            )

            if report.leased == 0:
                time.sleep(config.idle_sleep_seconds)
    finally:
        if fetcher is None:
            close_fetcher = getattr(active_fetcher, "close", None)
            if callable(close_fetcher):
                close_fetcher()

    LOGGER.info(
        "crawl scheduler exited after %d loops (succeeded=%d)", loops, total_succeeded
    )
    return total_succeeded


def _reclaim_stale(connection_factory: Callable[[], object]) -> int:
    connection = connection_factory()
    try:
        repo = EquityIntelligenceRepository(connection)  # type: ignore[arg-type]
        reclaimed = repo.reclaim_stale_leases(now=datetime.now(tz=timezone.utc))
        if reclaimed:
            LOGGER.info("reclaimed %d stale leases", reclaimed)
        return reclaimed
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()


__all__ = [
    "CrawlBatchReport",
    "SchedulerConfig",
    "build_default_fetcher",
    "run_forever",
]
