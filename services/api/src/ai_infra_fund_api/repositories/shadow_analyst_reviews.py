from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import json
from typing import Any, Mapping, Protocol

from ai_infra_fund_core.contracts.common import stable_hash_payload
from ai_infra_fund_core.shadow_analyst.quality import (
    DraftEvidenceReference,
    DraftQualityContext,
    DraftQualityRecommendation,
    build_sanitized_publication_payload,
    evaluate_shadow_analyst_draft,
)


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchone(self) -> object | None:
        ...

    def fetchall(self) -> list[object]:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...


GET_DRAFT_SQL = """
SELECT
    draft_id,
    draft_type,
    scope,
    ticker,
    source_model_run_id,
    status,
    payload_json,
    evidence_ids,
    validation_errors,
    created_at
FROM analyst.shadow_analyst_drafts
WHERE draft_id = %s;
"""


GET_EVIDENCE_SQL = """
SELECT
    evidence_id,
    source_uri,
    title,
    publisher,
    published_at,
    ingested_at,
    content_hash,
    data_class,
    tickers,
    themes,
    summary,
    created_at
FROM evidence.evidence_items
WHERE evidence_id = ANY(%s::text[]);
"""


GET_CONTEXT_OBJECT_IDS_SQL = """
SELECT signal_id
FROM analyst.source_signals
WHERE signal_id = ANY(%s::text[])
UNION
SELECT event_id
FROM analyst.market_events
WHERE event_id = ANY(%s::text[]);
"""


INSERT_REVIEW_SQL = """
INSERT INTO analyst.shadow_analyst_draft_reviews (
    review_id,
    draft_id,
    reviewer,
    decision,
    notes,
    draft_quality_score,
    evaluator_findings,
    blocking_issues,
    non_blocking_warnings,
    recommendation,
    accepted_payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (review_id) DO UPDATE SET
    reviewer = EXCLUDED.reviewer,
    decision = EXCLUDED.decision,
    notes = EXCLUDED.notes,
    draft_quality_score = EXCLUDED.draft_quality_score,
    evaluator_findings = EXCLUDED.evaluator_findings,
    blocking_issues = EXCLUDED.blocking_issues,
    non_blocking_warnings = EXCLUDED.non_blocking_warnings,
    recommendation = EXCLUDED.recommendation,
    accepted_payload_json = EXCLUDED.accepted_payload_json,
    created_at = EXCLUDED.created_at;
"""


UPDATE_DRAFT_STATUS_SQL = """
UPDATE analyst.shadow_analyst_drafts
SET status = %s,
    validation_errors = %s
WHERE draft_id = %s;
"""


ALLOWED_DECISIONS = frozenset(
    {"accepted_for_publication", "rejected", "keep_review_required"}
)


class ShadowAnalystReviewRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def review_draft(
        self,
        *,
        draft_id: str,
        decision: str,
        reviewer: str,
        notes: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> dict[str, object]:
        reviewed_at = reviewed_at or datetime.now(timezone.utc)
        if reviewed_at.tzinfo is None or reviewed_at.tzinfo.utcoffset(reviewed_at) is None:
            raise ValueError("reviewed_at must be timezone-aware")
        clean_decision = _require_choice(decision, "decision", ALLOWED_DECISIONS)
        clean_reviewer = _require_text(reviewer, "reviewer")
        clean_draft_id = _require_text(draft_id, "draft_id")

        with self._connection.cursor() as cursor:
            draft_row = self._load_draft(cursor, clean_draft_id)
            evidence_rows = self._load_evidence(cursor, draft_row["evidence_ids"])
            known_context_ids = self._load_known_context_ids(
                cursor,
                _context_ids(draft_row["payload_json"]),
            )
            draft = _draft_mapping(draft_row)
            context = _quality_context(
                evidence_rows=evidence_rows,
                known_context_ids=known_context_ids,
                as_of=reviewed_at,
            )
            evaluation = evaluate_shadow_analyst_draft(draft, context)
            accepted_payload: dict[str, object] = {}
            if clean_decision == "accepted_for_publication":
                _validate_acceptance(draft_row, evaluation)
                accepted_payload = build_sanitized_publication_payload(
                    draft,
                    evaluation,
                    reviewer=clean_reviewer,
                    accepted_at=reviewed_at,
                )

            draft_status = _draft_status_for_decision(clean_decision)
            review_id = _review_id(clean_draft_id, clean_decision, reviewed_at)
            cursor.execute(
                INSERT_REVIEW_SQL,
                (
                    review_id,
                    clean_draft_id,
                    clean_reviewer,
                    clean_decision,
                    notes,
                    evaluation.draft_quality_score,
                    _json(list(evaluation.evaluator_findings)),
                    list(evaluation.blocking_issues),
                    list(evaluation.non_blocking_warnings),
                    evaluation.recommendation.value,
                    _json(accepted_payload),
                    reviewed_at,
                ),
            )
            cursor.execute(
                UPDATE_DRAFT_STATUS_SQL,
                (
                    draft_status,
                    list(evaluation.blocking_issues),
                    clean_draft_id,
                ),
            )

        return {
            "review_id": review_id,
            "draft_id": clean_draft_id,
            "decision": clean_decision,
            "draft_status": draft_status,
            "draft_quality_score": evaluation.draft_quality_score,
            "evaluator_findings": list(evaluation.evaluator_findings),
            "blocking_issues": list(evaluation.blocking_issues),
            "non_blocking_warnings": list(evaluation.non_blocking_warnings),
            "recommendation": evaluation.recommendation.value,
            "accepted_payload": accepted_payload,
        }

    def _load_draft(self, cursor: Cursor, draft_id: str) -> dict[str, object]:
        cursor.execute(GET_DRAFT_SQL, (draft_id,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError("shadow analyst draft not found")
        return _draft_row_to_mapping(row)

    def _load_evidence(
        self,
        cursor: Cursor,
        evidence_ids: tuple[str, ...],
    ) -> tuple[dict[str, object], ...]:
        cursor.execute(GET_EVIDENCE_SQL, (list(evidence_ids),))
        return tuple(_evidence_row_to_mapping(row) for row in cursor.fetchall())

    def _load_known_context_ids(
        self,
        cursor: Cursor,
        context_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not context_ids:
            return ()
        cursor.execute(GET_CONTEXT_OBJECT_IDS_SQL, (list(context_ids), list(context_ids)))
        return tuple(str(_first_column(row)) for row in cursor.fetchall() if _first_column(row))


def _validate_acceptance(
    draft_row: Mapping[str, object],
    evaluation: object,
) -> None:
    if draft_row["status"] != "review_required":
        raise ValueError("only review_required drafts can be accepted for publication")
    if evaluation.recommendation is not DraftQualityRecommendation.ELIGIBLE_FOR_HUMAN_REVIEW:
        raise ValueError("quality checks did not make draft eligible for human review")
    if evaluation.blocking_issues:
        raise ValueError("draft has blocking quality issues")


def _draft_mapping(draft_row: Mapping[str, object]) -> dict[str, object]:
    payload_json = _mapping(draft_row["payload_json"])
    payload = dict(payload_json)
    payload.setdefault("draft_id", draft_row["draft_id"])
    payload.setdefault("draft_type", draft_row["draft_type"])
    payload.setdefault("evidence_ids", list(draft_row["evidence_ids"]))
    payload.setdefault("model_run_id", draft_row["source_model_run_id"])
    payload.setdefault("review_status", draft_row["status"])
    return payload


def _quality_context(
    *,
    evidence_rows: tuple[dict[str, object], ...],
    known_context_ids: tuple[str, ...],
    as_of: datetime,
) -> DraftQualityContext:
    evidence = tuple(
        DraftEvidenceReference(
            evidence_id=str(row["evidence_id"]),
            text=" ".join(
                str(value)
                for value in (
                    row.get("title"),
                    row.get("publisher"),
                    row.get("summary"),
                    " ".join(_text_tuple(row.get("themes"))),
                    " ".join(_text_tuple(row.get("tickers"))),
                )
                if value
            ),
            available_at=_evidence_available_at(row),
            source_uri=str(row.get("source_uri") or ""),
        )
        for row in evidence_rows
    )
    known_tickers = tuple(
        dict.fromkeys(
            ticker
            for row in evidence_rows
            for ticker in _text_tuple(row.get("tickers"))
        )
    )
    known_segments = tuple(
        dict.fromkeys(
            theme
            for row in evidence_rows
            for theme in _text_tuple(row.get("themes"))
        )
    )
    return DraftQualityContext(
        evidence=evidence,
        known_tickers=known_tickers,
        known_segments=known_segments,
        known_object_ids=known_context_ids,
        as_of=as_of,
        max_evidence_age_days=30,
    )


def _evidence_available_at(row: Mapping[str, object]) -> datetime | None:
    for key in ("published_at", "ingested_at", "created_at"):
        value = row.get(key)
        if isinstance(value, datetime):
            return value
    return None


def _draft_status_for_decision(decision: str) -> str:
    if decision == "accepted_for_publication":
        return "accepted_for_publication"
    if decision == "rejected":
        return "rejected"
    return "review_required"


def _draft_row_to_mapping(row: object) -> dict[str, object]:
    if isinstance(row, Mapping):
        return {
            "draft_id": row["draft_id"],
            "draft_type": row["draft_type"],
            "scope": row["scope"],
            "ticker": row.get("ticker"),
            "source_model_run_id": row["source_model_run_id"],
            "status": row["status"],
            "payload_json": _mapping(row["payload_json"]),
            "evidence_ids": _text_tuple(row["evidence_ids"]),
            "validation_errors": _text_tuple(row["validation_errors"]),
            "created_at": row["created_at"],
        }
    values = tuple(row)  # type: ignore[arg-type]
    return {
        "draft_id": str(values[0]),
        "draft_type": str(values[1]),
        "scope": str(values[2]),
        "ticker": values[3],
        "source_model_run_id": str(values[4]),
        "status": str(values[5]),
        "payload_json": _mapping(values[6]),
        "evidence_ids": _text_tuple(values[7]),
        "validation_errors": _text_tuple(values[8]),
        "created_at": values[9],
    }


def _evidence_row_to_mapping(row: object) -> dict[str, object]:
    if isinstance(row, Mapping):
        return dict(row)
    values = tuple(row)  # type: ignore[arg-type]
    return {
        "evidence_id": str(values[0]),
        "source_uri": str(values[1]),
        "title": values[2],
        "publisher": values[3],
        "published_at": values[4],
        "ingested_at": values[5],
        "content_hash": str(values[6]),
        "data_class": str(values[7]),
        "tickers": _text_tuple(values[8]),
        "themes": _text_tuple(values[9]),
        "summary": values[10],
        "created_at": values[11],
    }


def _context_ids(payload_json: Mapping[str, object]) -> tuple[str, ...]:
    raw_ids = payload_json.get("context_used")
    if raw_ids is None and isinstance(payload_json.get("payload"), Mapping):
        raw_ids = payload_json["payload"].get("context_used")  # type: ignore[index]
    return tuple(item for item in _text_tuple(raw_ids) if not item.startswith("evidence-"))


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        decoded = json.loads(value)
        if isinstance(decoded, Mapping):
            return dict(decoded)
    raise ValueError("payload_json must be a mapping")


def _text_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    return tuple(str(item).strip() for item in value if str(item).strip())  # type: ignore[operator]


def _first_column(row: object) -> object:
    if isinstance(row, Mapping):
        return next(iter(row.values()), None)
    values = tuple(row)  # type: ignore[arg-type]
    return values[0] if values else None


def _require_text(value: str | None, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required")
    return str(value).strip()


def _require_choice(value: str, field_name: str, choices: set[str] | frozenset[str]) -> str:
    clean = _require_text(value, field_name)
    if clean not in choices:
        raise ValueError(f"{field_name} must be one of {sorted(choices)}")
    return clean


def _review_id(draft_id: str, decision: str, reviewed_at: datetime) -> str:
    digest = stable_hash_payload(
        {
            "draft_id": draft_id,
            "decision": decision,
            "reviewed_at": reviewed_at.astimezone(timezone.utc).isoformat(),
        }
    )
    return f"shadow-draft-review-{digest[:20]}"


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
