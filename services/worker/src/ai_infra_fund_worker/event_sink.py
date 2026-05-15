"""Postgres adapter for emitting experiment events from the worker.

The pure event helpers live in ``ai_infra_fund_core.audit.experiment_events``.
This module is the I/O shell that keeps ``packages/core`` free of any
database driver coupling.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_infra_fund_core.audit.experiment_events import ExperimentEvent


@dataclass(frozen=True, slots=True)
class PostgresEventSink:
    database_url: str

    def __call__(self, event: ExperimentEvent) -> None:
        import psycopg
        from ai_infra_fund_api.repositories.experiment_events import (
            ExperimentEventRepository,
        )

        with psycopg.connect(self.database_url) as connection:
            ExperimentEventRepository(connection).record(event)


__all__ = ["PostgresEventSink"]
