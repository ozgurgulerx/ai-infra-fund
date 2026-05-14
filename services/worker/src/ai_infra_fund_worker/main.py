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
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


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
    LOGGER.info("worker startup: environment=%s data_dir=%s", settings.environment, settings.data_dir)
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

    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    LOGGER.info("worker running")
    while running:
        time.sleep(int(os.getenv("WORKER_IDLE_SECONDS", "30")))
    LOGGER.info("worker shutdown complete")


if __name__ == "__main__":
    main()
