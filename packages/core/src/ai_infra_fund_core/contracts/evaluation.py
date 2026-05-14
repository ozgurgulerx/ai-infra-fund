from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .common import (
    normalize_tuple,
    require_aware_datetime,
    require_content_hash,
    require_non_empty_tuple,
    require_text,
)


@dataclass(frozen=True, slots=True)
class BacktestRun:
    backtest_run_id: str
    strategy_id: str
    dataset_snapshot_ids: tuple[str, ...]
    validation_protocol: str
    cost_assumptions: dict[str, Any]
    metrics: dict[str, Any]
    artifact_hash: str
    as_of: datetime
    available_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "backtest_run_id", require_text(self.backtest_run_id, "backtest_run_id"))
        object.__setattr__(self, "strategy_id", require_text(self.strategy_id, "strategy_id"))
        object.__setattr__(
            self,
            "dataset_snapshot_ids",
            require_non_empty_tuple(normalize_tuple(self.dataset_snapshot_ids, "dataset_snapshot_ids"), "dataset_snapshot_ids"),
        )
        object.__setattr__(self, "validation_protocol", require_text(self.validation_protocol, "validation_protocol"))
        if not self.cost_assumptions:
            raise ValueError("cost_assumptions must not be empty")
        if not self.metrics:
            raise ValueError("metrics must not be empty")
        object.__setattr__(self, "artifact_hash", require_content_hash(self.artifact_hash, "artifact_hash"))
        require_aware_datetime(self.as_of, "as_of")
        require_aware_datetime(self.available_at, "available_at")
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class RunArtifact:
    run_id: str
    run_type: str
    started_at: datetime
    completed_at: datetime | None
    inputs_hash: str
    output_hash: str | None
    artifact_uri: str | None
    status: str
    error_summary: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", require_text(self.run_id, "run_id"))
        object.__setattr__(self, "run_type", require_text(self.run_type, "run_type"))
        object.__setattr__(self, "inputs_hash", require_content_hash(self.inputs_hash, "inputs_hash"))
        if self.output_hash is not None:
            object.__setattr__(self, "output_hash", require_content_hash(self.output_hash, "output_hash"))
        object.__setattr__(self, "status", require_text(self.status, "status"))
        require_aware_datetime(self.started_at, "started_at")
        if self.completed_at is not None:
            require_aware_datetime(self.completed_at, "completed_at")
        require_aware_datetime(self.created_at, "created_at")
