from __future__ import annotations

import logging
import os
import signal
import time
from typing import Callable, Mapping

from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings
from ai_infra_fund_core.runtime.database import check_database_connection


LOGGER = logging.getLogger("ai_infra_fund.worker")
ConnectionCheck = Callable[[RuntimeSettings], bool]


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )


def load_worker_settings(env: Mapping[str, str] | None = None) -> RuntimeSettings:
    source = os.environ if env is None else env
    try:
        return RuntimeSettings.from_env(source, allow_defaults=False)
    except RuntimeConfigError as error:
        LOGGER.error("worker configuration invalid: %s", error)
        raise SystemExit(2) from error


def run_once(
    settings: RuntimeSettings,
    *,
    connection_check: ConnectionCheck = check_database_connection,
) -> int:
    LOGGER.info(
        "worker startup: environment=%s data_dir=%s",
        settings.environment,
        settings.data_dir,
    )
    if not connection_check(settings):
        LOGGER.error("worker startup failed: database unavailable")
        return 2
    LOGGER.info("worker ready: jobs are stubbed until later phases")
    return 0


def main() -> None:
    configure_logging()
    settings = load_worker_settings()
    status = run_once(settings)
    if status != 0:
        raise SystemExit(status)

    mode = (os.getenv("AI_INFRA_FUND_WORKER_MODE") or "default").lower()
    if mode == "crawl":
        _run_crawl_mode(settings)
        return

    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    LOGGER.info("worker running")
    worker_id = os.getenv("WORKER_ID", "worker-default")
    idle_seconds = int(os.getenv("WORKER_IDLE_SECONDS", "30"))
    while running:
        try:
            from .jobs import run_iteration

            outcome = run_iteration(settings, worker_id=worker_id).backtest
            if outcome.status == "succeeded":
                LOGGER.info(
                    "backtest succeeded request_id=%s run_id=%s",
                    outcome.request_id,
                    outcome.backtest_run_id,
                )
            elif outcome.status == "failed":
                LOGGER.warning(
                    "backtest failed request_id=%s error=%s",
                    outcome.request_id,
                    outcome.error_summary,
                )
        except Exception:  # noqa: BLE001 — log and idle, never crash the loop
            LOGGER.exception("worker iteration failed")
        time.sleep(idle_seconds)
    LOGGER.info("worker shutdown complete")


def _run_crawl_mode(settings: RuntimeSettings) -> None:
    from pathlib import Path

    import psycopg

    from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy

    from .crawl.scheduler import SchedulerConfig, run_forever

    captures_root = Path(
        os.getenv("AI_INFRA_FUND_CAPTURES_ROOT", str(settings.data_dir))
    )
    config = SchedulerConfig(
        worker_id=os.getenv("AI_INFRA_FUND_WORKER_ID") or "crawl-default",
        policy=FrontierPolicy(
            batch_size=int(os.getenv("AI_INFRA_FUND_CRAWL_BATCH_SIZE", "20")),
            domain_cap=int(os.getenv("AI_INFRA_FUND_CRAWL_DOMAIN_CAP", "2")),
        ),
        captures_root=captures_root,
        idle_sleep_seconds=float(os.getenv("AI_INFRA_FUND_CRAWL_IDLE_SECONDS", "30")),
    )

    database_url = settings.database_url

    def factory() -> object:
        return psycopg.connect(database_url)

    LOGGER.info("worker entering crawl mode worker_id=%s", config.worker_id)
    succeeded = run_forever(factory, config=config)
    LOGGER.info("worker crawl mode exited succeeded=%d", succeeded)


if __name__ == "__main__":
    main()
