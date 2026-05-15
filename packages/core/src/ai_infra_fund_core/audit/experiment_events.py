"""Pure experiment-event helpers.

Emits structured audit events from the deterministic advisory pipeline.
This module is I/O free; persistence belongs to the worker via a
``PostgresEventSink`` adapter so ``packages/core`` stays free of database
coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from ai_infra_fund_core.contracts.common import (
    canonicalize,
    require_aware_datetime,
    require_text,
    stable_hash_payload,
)


EVENT_KINDS: tuple[str, ...] = (
    "signal_computed",
    "weights_generated",
    "recommendation_issued",
    "backtest_started",
    "backtest_completed",
    "shadow_comparison_recorded",
    "price_disagreement",
)

EVENT_SEVERITIES: tuple[str, ...] = ("info", "warn", "error")

EVENT_ID_PREFIX = "audit-evt-"


@dataclass(frozen=True, slots=True)
class ExperimentEvent:
    event_id: str
    kind: str
    run_id: str | None
    severity: str
    payload: Mapping[str, Any]
    occurred_at: datetime


def build_event(
    *,
    kind: str,
    run_id: str | None,
    payload: Mapping[str, Any],
    occurred_at: datetime,
    severity: str = "info",
) -> ExperimentEvent:
    normalized_kind = require_text(kind, "kind")
    if normalized_kind not in EVENT_KINDS:
        allowed = ", ".join(EVENT_KINDS)
        raise ValueError(f"kind must be one of {allowed}; got {normalized_kind!r}")

    normalized_severity = require_text(severity, "severity")
    if normalized_severity not in EVENT_SEVERITIES:
        allowed = ", ".join(EVENT_SEVERITIES)
        raise ValueError(
            f"severity must be one of {allowed}; got {normalized_severity!r}"
        )

    aware_at = require_aware_datetime(occurred_at, "occurred_at")
    normalized_run_id = run_id if run_id is None else require_text(run_id, "run_id")
    canonical_payload = dict(canonicalize(dict(payload)))

    digest_seed: dict[str, Any] = {
        "kind": normalized_kind,
        "run_id": normalized_run_id,
        "occurred_at": aware_at.isoformat(),
        "payload": canonical_payload,
    }
    digest = stable_hash_payload(digest_seed)[:24]

    return ExperimentEvent(
        event_id=f"{EVENT_ID_PREFIX}{digest}",
        kind=normalized_kind,
        run_id=normalized_run_id,
        severity=normalized_severity,
        payload=canonical_payload,
        occurred_at=aware_at,
    )


EventSink = Any  # callable: (ExperimentEvent) -> None — declared loosely on purpose.


__all__ = [
    "EVENT_ID_PREFIX",
    "EVENT_KINDS",
    "EVENT_SEVERITIES",
    "EventSink",
    "ExperimentEvent",
    "build_event",
]
