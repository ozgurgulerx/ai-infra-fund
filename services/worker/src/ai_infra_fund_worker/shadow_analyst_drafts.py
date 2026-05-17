from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json
from typing import Any, Protocol, Sequence

from ai_infra_fund_core.contracts.model_runs import ModelRun


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...


INSERT_MODEL_RUN_SQL = """
INSERT INTO audit.model_runs (
    model_run_id,
    task_role,
    model_id,
    deployment,
    provider,
    prompt_version,
    input_hash,
    output_hash,
    latency_ms,
    token_estimate_input,
    token_estimate_output,
    cost_estimate,
    schema_valid,
    retry_count,
    data_classes,
    status,
    error_summary,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (model_run_id) DO UPDATE SET
    task_role = EXCLUDED.task_role,
    model_id = EXCLUDED.model_id,
    deployment = EXCLUDED.deployment,
    provider = EXCLUDED.provider,
    prompt_version = EXCLUDED.prompt_version,
    input_hash = EXCLUDED.input_hash,
    output_hash = EXCLUDED.output_hash,
    latency_ms = EXCLUDED.latency_ms,
    token_estimate_input = EXCLUDED.token_estimate_input,
    token_estimate_output = EXCLUDED.token_estimate_output,
    cost_estimate = EXCLUDED.cost_estimate,
    schema_valid = EXCLUDED.schema_valid,
    retry_count = EXCLUDED.retry_count,
    data_classes = EXCLUDED.data_classes,
    status = EXCLUDED.status,
    error_summary = EXCLUDED.error_summary,
    created_at = EXCLUDED.created_at;
"""


UPSERT_SHADOW_ANALYST_DRAFT_SQL = """
INSERT INTO analyst.shadow_analyst_drafts (
    draft_id,
    draft_type,
    scope,
    ticker,
    model_run_id,
    status,
    payload_json,
    evidence_ids,
    validation_errors,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
) ON CONFLICT (draft_id) DO UPDATE SET
    draft_type = EXCLUDED.draft_type,
    scope = EXCLUDED.scope,
    ticker = EXCLUDED.ticker,
    model_run_id = EXCLUDED.model_run_id,
    status = EXCLUDED.status,
    payload_json = EXCLUDED.payload_json,
    evidence_ids = EXCLUDED.evidence_ids,
    validation_errors = EXCLUDED.validation_errors,
    created_at = EXCLUDED.created_at;
"""


class ShadowAnalystModelRunRecorder:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save(self, model_run: ModelRun) -> ModelRun:
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_MODEL_RUN_SQL, _model_run_params(model_run))
        return model_run


class ShadowAnalystDraftRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save_many(
        self,
        drafts: Sequence[object],
        *,
        scope: str,
        ticker: str | None,
        created_at: datetime,
    ) -> tuple[object, ...]:
        saved = tuple(drafts)
        with self._connection.cursor() as cursor:
            for draft in saved:
                cursor.execute(
                    UPSERT_SHADOW_ANALYST_DRAFT_SQL,
                    _draft_params(
                        draft,
                        scope=scope,
                        ticker=ticker,
                        created_at=created_at,
                    ),
                )
        return saved

    def save_status(
        self,
        *,
        draft_id: str,
        draft_type: str,
        scope: str,
        ticker: str | None,
        model_run_id: str,
        status: str,
        payload: dict[str, object],
        evidence_ids: Sequence[str],
        validation_errors: Sequence[str],
        created_at: datetime,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                UPSERT_SHADOW_ANALYST_DRAFT_SQL,
                (
                    draft_id,
                    draft_type,
                    scope,
                    ticker,
                    model_run_id,
                    status,
                    _json({**payload, "can_publish_directly": False}),
                    list(evidence_ids),
                    list(validation_errors),
                    created_at,
                ),
            )


class BoundShadowAnalystDraftRecorder:
    def __init__(
        self,
        repository: ShadowAnalystDraftRepository,
        *,
        scope: str,
        ticker: str | None,
        created_at: datetime,
    ) -> None:
        self._repository = repository
        self._scope = scope
        self._ticker = ticker
        self._created_at = created_at

    def save_many(self, drafts: Sequence[object]) -> tuple[object, ...]:
        return self._repository.save_many(
            drafts,
            scope=self._scope,
            ticker=self._ticker,
            created_at=self._created_at,
        )


def _model_run_params(model_run: ModelRun) -> tuple[object, ...]:
    return (
        model_run.model_run_id,
        model_run.task_role,
        model_run.model_id,
        model_run.deployment,
        model_run.provider,
        model_run.prompt_version,
        model_run.input_hash,
        model_run.output_hash,
        model_run.latency_ms,
        model_run.token_estimate_input,
        model_run.token_estimate_output,
        None,
        model_run.schema_valid,
        model_run.retry_count,
        [data_class.value for data_class in model_run.data_classes],
        model_run.status.value,
        model_run.error_summary,
        model_run.created_at,
    )


def _draft_params(
    draft: object,
    *,
    scope: str,
    ticker: str | None,
    created_at: datetime,
) -> tuple[object, ...]:
    draft_id = str(getattr(draft, "draft_id"))
    draft_type = str(getattr(draft, "draft_type"))
    status = getattr(getattr(draft, "review_status"), "value", getattr(draft, "review_status"))
    evidence_ids = list(getattr(draft, "evidence_ids"))
    validation_errors = list(getattr(draft, "rejection_reasons", ()))
    return (
        draft_id,
        draft_type,
        scope,
        ticker,
        str(getattr(draft, "model_run_id")),
        str(status),
        _json(_draft_payload(draft)),
        evidence_ids,
        validation_errors,
        created_at,
    )


def _draft_payload(draft: object) -> dict[str, object]:
    if is_dataclass(draft):
        payload = asdict(draft)
    else:
        payload = dict(getattr(draft, "__dict__", {}))
    payload["can_publish_directly"] = False
    return payload


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return str(value)
