"""Worker job dispatcher.

Polls each known queue once. Used by ``main.py`` inside the worker run
loop. Keep the import surface small so unit tests can stub repositories
without standing up Postgres.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_infra_fund_core.runtime.config import RuntimeSettings

from .backtest_orchestrator import (
    BacktestProcessOutcome,
    process_next_backtest,
)


@dataclass(frozen=True, slots=True)
class DispatcherIterationResult:
    backtest: BacktestProcessOutcome
    reclaimed_request_ids: tuple[str, ...]


def run_iteration(
    settings: RuntimeSettings,
    *,
    worker_id: str = "worker-default",
) -> DispatcherIterationResult:
    import psycopg
    from ai_infra_fund_api.repositories.backtest_requests import (
        BacktestRequestRepository,
    )
    from ai_infra_fund_api.repositories.evaluation import (
        EvaluationRepository,
    )

    from .event_sink import PostgresEventSink

    sink = PostgresEventSink(database_url=settings.database_url)

    with psycopg.connect(settings.database_url) as connection:
        request_repository = BacktestRequestRepository(connection)
        evaluation_repository = EvaluationRepository(connection)

        reclaimed = tuple(request_repository.reclaim_expired_leases())
        backtest_outcome = process_next_backtest(
            request_repository=request_repository,
            evaluation_repository=evaluation_repository,
            event_sink=sink,
            worker_id=worker_id,
        )

    return DispatcherIterationResult(
        backtest=backtest_outcome,
        reclaimed_request_ids=reclaimed,
    )


__all__ = ["DispatcherIterationResult", "run_iteration"]
