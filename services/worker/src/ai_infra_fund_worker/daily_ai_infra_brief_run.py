from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from typing import Protocol
from urllib.parse import urlencode

from ai_infra_fund_core.model_routing.profiles import load_model_profiles
from ai_infra_fund_core.model_routing.router import ModelRouter
from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings
from ai_infra_fund_core.shadow_analyst import (
    GovernedShadowAnalystPipeline,
    build_daily_analyst_context_bundle,
)

from .daily_ai_infra_brief_sql import (
    EVIDENCE_BY_IDS_SQL,
    LATEST_EQUITY_ASSESSMENTS_SQL,
    LATEST_MARKET_EVENTS_SQL,
    LATEST_OUTCOMES_SQL,
    LATEST_PORTFOLIO_SNAPSHOT_SQL,
    LATEST_RISK_REGIME_SQL,
    LATEST_SEGMENT_IMPACTS_SQL,
    LATEST_SOURCE_SIGNALS_SQL,
    LATEST_TRADE_PLANS_SQL,
    LATEST_VALUATION_CONTEXTS_SQL,
    UPSERT_ANALYST_BRIEF_SQL,
    UPSERT_RUN_ARTIFACT_SQL,
    UPSERT_TRADING_ADVISORY_SQL,
)
from .shadow_analyst_drafts import (
    BoundShadowAnalystDraftRecorder,
    ShadowAnalystDraftRepository,
    ShadowAnalystModelRunRecorder,
)


RUN_TYPE = "daily_ai_infra_brief"
ADVISORY_LABEL = "advisory_only"
MAX_SOURCE_AGE = timedelta(days=7)
ALLOWED_EVIDENCE_DATA_CLASSES = frozenset(
    {
        "public_market_data",
        "public_evidence",
        "derived_analytics",
        "user_portfolio",
        "run_audit",
    }
)


class Cursor(Protocol):
    description: object

    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...

    def fetchall(self) -> list[object]: ...


class Connection(Protocol):
    def cursor(self) -> object: ...

    def commit(self) -> None: ...


def run_daily_ai_infra_brief(
    connection: Connection,
    *,
    run_at: datetime | None = None,
    shadow_model_client: object | None = None,
    model_profiles_path: str = "config/model_profiles.yaml",
) -> dict[str, object]:
    as_of = _aware_datetime(run_at)
    inputs = _fetch_inputs(connection)
    inputs_hash = _hash_payload("daily_ai_infra_brief_inputs", _input_summary(inputs))
    run_id = f"run-daily-ai-infra-brief-{inputs_hash[:16]}"
    shadow_result = _run_shadow_analyst(
        connection,
        inputs=inputs,
        as_of=as_of,
        shadow_model_client=shadow_model_client,
        model_profiles_path=model_profiles_path,
    )

    candidates = _build_candidates(inputs, as_of=as_of, inputs_hash=inputs_hash)
    published = [candidate for candidate in candidates if candidate["publishable"]]
    suppressed = [
        _suppressed_payload(candidate)
        for candidate in candidates
        if not candidate["publishable"]
    ]
    brief = _build_brief(
        inputs=inputs,
        published=published,
        suppressed=suppressed,
        as_of=as_of,
        inputs_hash=inputs_hash,
        shadow_analyst=shadow_result,
    )
    output_hash = _hash_payload(
        "daily_ai_infra_brief_output",
        {
            "brief_id": brief["brief_id"],
            "published_advisory_ids": brief["trading_advisory_ids"],
            "suppressed_candidates": suppressed,
            "shadow_analyst": shadow_result,
        },
    )
    artifact_uri = _artifact_uri(
        run_id=run_id,
        brief_id=str(brief["brief_id"]),
        published_ids=_text_list(brief["trading_advisory_ids"]),
    )

    with connection.cursor() as cursor:
        for advisory in published:
            cursor.execute(UPSERT_TRADING_ADVISORY_SQL, _advisory_params(advisory, as_of))
        cursor.execute(UPSERT_ANALYST_BRIEF_SQL, _brief_params(brief, output_hash, as_of))
        cursor.execute(
            UPSERT_RUN_ARTIFACT_SQL,
            (
                run_id,
                RUN_TYPE,
                as_of,
                as_of,
                inputs_hash,
                output_hash,
                artifact_uri,
                "succeeded",
                None,
                as_of,
            ),
        )
    connection.commit()

    published_ids = _text_list(brief["trading_advisory_ids"])
    return {
        "run_id": run_id,
        "run_type": RUN_TYPE,
        "status": "succeeded",
        "exit_code": 0,
        "advisory_label": ADVISORY_LABEL,
        "brief_id": brief["brief_id"],
        "published_advisory_ids": published_ids,
        "published_advisory_count": len(published_ids),
        "suppressed_candidate_count": len(suppressed),
        "shadow_analyst_status": shadow_result["status"],
        "shadow_draft_count": shadow_result["draft_count"],
        "shadow_model_run_count": shadow_result["model_run_count"],
        "inputs_hash": inputs_hash,
        "output_hash": output_hash,
        "artifact_uri": artifact_uri,
    }


def _fetch_inputs(connection: Connection) -> dict[str, list[dict[str, object]]]:
    inputs = {
        "source_signals": _fetch_many(connection, LATEST_SOURCE_SIGNALS_SQL, (25,)),
        "market_events": _fetch_many(connection, LATEST_MARKET_EVENTS_SQL, (25,)),
        "segment_impacts": _fetch_many(connection, LATEST_SEGMENT_IMPACTS_SQL, (50,)),
        "equity_assessments": _fetch_many(
            connection, LATEST_EQUITY_ASSESSMENTS_SQL, (50,)
        ),
        "valuation_contexts": _fetch_many(
            connection, LATEST_VALUATION_CONTEXTS_SQL, (50,)
        ),
        "risk_regime_updates": _fetch_many(connection, LATEST_RISK_REGIME_SQL, (25,)),
        "trade_plans": _fetch_many(connection, LATEST_TRADE_PLANS_SQL, (50,)),
        "portfolio_snapshots": _fetch_many(
            connection, LATEST_PORTFOLIO_SNAPSHOT_SQL, ()
        ),
        "outcomes": _fetch_many(connection, LATEST_OUTCOMES_SQL, (25,)),
    }
    evidence_ids = _collect_evidence_ids(inputs)
    inputs["evidence_items"] = _fetch_many(
        connection, EVIDENCE_BY_IDS_SQL, (evidence_ids,)
    )
    return inputs


class UnavailableShadowAnalystModelClient:
    def generate_structured(
        self,
        *,
        route: object,
        bundle: object,
        output_schema: str,
    ) -> Mapping[str, object]:
        raise RuntimeError("shadow analyst model client unavailable")


def _run_shadow_analyst(
    connection: Connection,
    *,
    inputs: Mapping[str, list[dict[str, object]]],
    as_of: datetime,
    shadow_model_client: object | None,
    model_profiles_path: str,
) -> dict[str, object]:
    bundle = build_daily_analyst_context_bundle(
        _shadow_context_rows(inputs),
        as_of=as_of,
    )
    draft_repository = ShadowAnalystDraftRepository(connection)
    pipeline = GovernedShadowAnalystPipeline(
        router=ModelRouter(load_model_profiles(model_profiles_path)),
        model_client=shadow_model_client or UnavailableShadowAnalystModelClient(),
        model_run_recorder=ShadowAnalystModelRunRecorder(connection),
        draft_recorder=BoundShadowAnalystDraftRecorder(
            draft_repository,
            scope=bundle.scope.value,
            ticker=bundle.ticker,
            created_at=as_of,
        ),
        now=lambda: as_of,
    )
    result = pipeline.run(bundle)
    draft_count = len(result.drafts)
    if not result.drafts:
        status = (
            result.status
            if result.status in {"fallback", "denied"}
            else "fallback"
        )
        model_run_id = (
            result.model_runs[0].model_run_id
            if result.model_runs
            else f"model-run-shadow-{status}-{bundle.content_hash[:16]}"
        )
        draft_repository.save_status(
            draft_id=f"draft-shadow-analyst-{status}-{bundle.content_hash[:16]}",
            draft_type=(
                "ShadowAnalystDenied"
                if status == "denied"
                else "ShadowAnalystFallback"
            ),
            scope=bundle.scope.value,
            ticker=bundle.ticker,
            model_run_id=model_run_id,
            status=status,
            payload={
                "bundle_id": bundle.bundle_id,
                "status": result.status,
                "fallback_used": result.fallback_used,
                "model_run_ids": [run.model_run_id for run in result.model_runs],
                "raw_drafts_published": False,
            },
            evidence_ids=bundle.evidence_ids,
            validation_errors=result.rejection_reasons
            or ("shadow analyst draft generation unavailable",),
            created_at=as_of,
        )
        draft_count = 1

    rejected_count = sum(
        1
        for draft in result.drafts
        if str(getattr(getattr(draft, "review_status", ""), "value", "")) == "rejected"
        or str(getattr(draft, "review_status", "")) == "rejected"
    )
    return {
        "status": result.status,
        "bundle_id": bundle.bundle_id,
        "draft_count": draft_count,
        "review_required_count": max(0, len(result.drafts) - rejected_count),
        "rejected_count": rejected_count,
        "model_run_count": len(result.model_runs),
        "model_run_ids": [run.model_run_id for run in result.model_runs],
        "fallback_used": result.fallback_used,
        "validation_error_count": len(result.rejection_reasons),
        "raw_drafts_published": False,
    }


def _shadow_context_rows(
    inputs: Mapping[str, list[dict[str, object]]],
) -> dict[str, list[dict[str, object]]]:
    return {
        "source_signals": list(inputs.get("source_signals", ())),
        "evidence_items": list(inputs.get("evidence_items", ())),
        "market_events": list(inputs.get("market_events", ())),
        "segment_impacts": list(inputs.get("segment_impacts", ())),
        "equity_impact_assessments": list(inputs.get("equity_assessments", ())),
        "valuation_contexts": list(inputs.get("valuation_contexts", ())),
        "risk_regime_updates": list(inputs.get("risk_regime_updates", ())),
        "portfolio_exposures": list(inputs.get("portfolio_snapshots", ())),
        "prior_advisories": [],
        "outcome_journal_entries": list(inputs.get("outcomes", ())),
    }


def _fetch_many(
    connection: Connection,
    statement: str,
    params: tuple[object, ...],
) -> list[dict[str, object]]:
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        rows = cursor.fetchall()
        column_names = _column_names(cursor.description)
    return [_row_to_dict(row, column_names) for row in rows]


def _build_candidates(
    inputs: Mapping[str, list[dict[str, object]]],
    *,
    as_of: datetime,
    inputs_hash: str,
) -> list[dict[str, object]]:
    market_events = inputs["market_events"]
    segment_impacts = inputs["segment_impacts"]
    valuations = inputs["valuation_contexts"]
    risk_updates = inputs["risk_regime_updates"]
    trade_plans = inputs["trade_plans"]
    evidence_index = {
        str(item["evidence_id"]): item for item in inputs["evidence_items"]
    }
    candidates: list[dict[str, object]] = []

    for assessment in inputs["equity_assessments"]:
        ticker = str(assessment.get("ticker") or "").upper()
        if not ticker:
            continue
        linked_event_ids = _text_list(assessment.get("linked_event_ids"))
        linked_events = _related_market_events(market_events, ticker, linked_event_ids)
        linked_segments = _related_segments(segment_impacts, ticker, linked_event_ids)
        linked_risks = _related_risks(risk_updates, ticker, linked_event_ids)
        valuation = _latest_for_ticker(valuations, ticker)
        trade_plan = _latest_for_ticker(trade_plans, ticker)
        evidence_ids = _unique_texts(
            _text_list(assessment.get("evidence_ids"))
            + [
                evidence_id
                for collection in (linked_events, linked_segments, linked_risks)
                for row in collection
                for evidence_id in _text_list(row.get("evidence_ids"))
            ]
            + _text_list(valuation.get("evidence_ids") if valuation else None)
            + _text_list(trade_plan.get("evidence_ids") if trade_plan else None)
        )
        model_run_ids = _unique_texts(
            event.get("extracted_by_model_run_id")
            for event in linked_events
            if event.get("extracted_by_model_run_id")
        )
        blocking_reasons = _blocking_reasons(
            assessment=assessment,
            linked_events=linked_events,
            linked_risks=linked_risks,
            evidence_ids=evidence_ids,
            evidence_index=evidence_index,
            as_of=as_of,
        )
        readiness = {
            "publishable": not blocking_reasons,
            "blocking_reasons": blocking_reasons,
            "checks": {
                "evidence_present": "missing_evidence" not in blocking_reasons,
                "source_fresh": "stale_source" not in blocking_reasons,
                "data_class_allowed": "data_class_not_allowed" not in blocking_reasons,
                "risk_contradictions_resolved": "unresolved_risk_contradiction"
                not in blocking_reasons,
                "advisory_only_label_present": True,
                "publication_language_clean": "restricted_language"
                not in blocking_reasons,
            },
        }
        advisory_id = f"advisory-daily-{ticker.lower()}-{inputs_hash[:12]}"
        action = _normalize_action(str(assessment.get("advisory_implication") or "review"))
        candidates.append(
            {
                "advisory_id": advisory_id,
                "ticker": ticker,
                "company": assessment.get("company"),
                "advisory_label": ADVISORY_LABEL,
                "analyst_action": action,
                "advisory_summary": _advisory_summary(
                    ticker=ticker,
                    action=action,
                    assessment=assessment,
                    linked_events=linked_events,
                    linked_risks=linked_risks,
                ),
                "evidence_ids": evidence_ids,
                "model_run_ids": model_run_ids,
                "deterministic_checks": _deterministic_check_ids(readiness),
                "linked_trade_plan_id": (
                    str(trade_plan["trade_plan_id"]) if trade_plan else None
                ),
                "market_event_ids": _unique_texts(
                    event.get("event_id") for event in linked_events
                ),
                "segment_impact_ids": _unique_texts(
                    segment.get("segment_id") for segment in linked_segments
                ),
                "risk_regime_ids": _unique_texts(
                    risk.get("regime_id") for risk in linked_risks
                ),
                "valuation_context_id": (
                    str(valuation["valuation_context_id"]) if valuation else None
                ),
                "risk_flags": _unique_texts(
                    _text_list(assessment.get("risk_flags"))
                    + [
                        flag
                        for risk in linked_risks
                        for flag in (
                            risk.get("risk_type"),
                            risk.get("severity"),
                            risk.get("status"),
                        )
                    ]
                ),
                "readiness": readiness,
                "publishable": not blocking_reasons,
            }
        )
    return candidates


def _build_brief(
    *,
    inputs: Mapping[str, list[dict[str, object]]],
    published: list[dict[str, object]],
    suppressed: list[dict[str, object]],
    as_of: datetime,
    inputs_hash: str,
    shadow_analyst: Mapping[str, object],
) -> dict[str, object]:
    market_event_ids = _unique_texts(
        event.get("event_id") for event in inputs["market_events"]
    )
    segment_impact_ids = _unique_texts(
        segment.get("segment_id") for segment in inputs["segment_impacts"]
    )
    published_ids = _unique_texts(advisory["advisory_id"] for advisory in published)
    model_run_ids = _unique_texts(
        event.get("extracted_by_model_run_id")
        for event in inputs["market_events"]
        if event.get("extracted_by_model_run_id")
    )
    brief_id = f"brief-daily-ai-infra-{as_of:%Y%m%dT%H%M%SZ}-{inputs_hash[:8]}"
    payload = {
        "advisory_label": ADVISORY_LABEL,
        "source_signal_ids": _unique_texts(
            signal.get("signal_id") for signal in inputs["source_signals"]
        ),
        "market_event_ids": market_event_ids,
        "segment_impact_ids": segment_impact_ids,
        "published_advisory_ids": published_ids,
        "suppressed_candidates": suppressed,
        "portfolio_snapshot_id": _first_value(
            inputs["portfolio_snapshots"], "snapshot_id"
        ),
        "open_trade_plan_ids": _unique_texts(
            plan.get("trade_plan_id") for plan in inputs["trade_plans"]
        ),
        "journal_state": {
            "outcome_count": len(inputs["outcomes"]),
            "latest_outcome_ids": _unique_texts(
                outcome.get("outcome_id") for outcome in inputs["outcomes"]
            ),
        },
        "input_counts": {
            name: len(rows)
            for name, rows in inputs.items()
            if name != "evidence_items"
        },
        "readiness_policy": {
            "max_source_age_days": MAX_SOURCE_AGE.days,
            "allowed_evidence_data_classes": sorted(ALLOWED_EVIDENCE_DATA_CLASSES),
            "publication_gate": "deterministic",
        },
        "shadow_analyst": {
            "status": shadow_analyst.get("status"),
            "bundle_id": shadow_analyst.get("bundle_id"),
            "draft_count": shadow_analyst.get("draft_count"),
            "review_required_count": shadow_analyst.get("review_required_count"),
            "rejected_count": shadow_analyst.get("rejected_count"),
            "model_run_count": shadow_analyst.get("model_run_count"),
            "model_run_ids": _text_list(shadow_analyst.get("model_run_ids")),
            "fallback_used": shadow_analyst.get("fallback_used"),
            "validation_error_count": shadow_analyst.get("validation_error_count"),
            "raw_drafts_published": False,
        },
    }
    return {
        "brief_id": brief_id,
        "as_of": as_of,
        "title": "AI Infrastructure Daily Brief",
        "advisory_label": ADVISORY_LABEL,
        "executive_summary": _brief_summary(len(published), len(suppressed)),
        "market_event_ids": market_event_ids,
        "segment_impact_ids": segment_impact_ids,
        "trading_advisory_ids": published_ids,
        "model_run_ids": model_run_ids,
        "payload": payload,
    }


def _advisory_params(
    advisory: Mapping[str, object], as_of: datetime
) -> tuple[object, ...]:
    return (
        advisory["advisory_id"],
        None,
        advisory["ticker"],
        ADVISORY_LABEL,
        advisory["analyst_action"],
        advisory["advisory_summary"],
        _text_list(advisory["evidence_ids"]),
        _text_list(advisory["model_run_ids"]),
        None,
        None,
        _text_list(advisory["deterministic_checks"]),
        advisory.get("linked_trade_plan_id"),
        _json(
            {
                "market_event_ids": _text_list(advisory["market_event_ids"]),
                "segment_impact_ids": _text_list(advisory["segment_impact_ids"]),
                "risk_regime_ids": _text_list(advisory["risk_regime_ids"]),
                "valuation_context_id": advisory.get("valuation_context_id"),
                "risk_flags": _text_list(advisory["risk_flags"]),
                "readiness": advisory["readiness"],
                "advisory_label": ADVISORY_LABEL,
            }
        ),
        as_of,
    )


def _brief_params(
    brief: Mapping[str, object], output_hash: str, as_of: datetime
) -> tuple[object, ...]:
    payload = dict(brief["payload"])  # type: ignore[arg-type]
    payload["output_hash"] = output_hash
    return (
        brief["brief_id"],
        brief["as_of"],
        brief["title"],
        ADVISORY_LABEL,
        brief["executive_summary"],
        _text_list(brief["market_event_ids"]),
        _text_list(brief["segment_impact_ids"]),
        _text_list(brief["trading_advisory_ids"]),
        _text_list(brief["model_run_ids"]),
        _json(payload),
        as_of,
    )


def _blocking_reasons(
    *,
    assessment: Mapping[str, object],
    linked_events: list[dict[str, object]],
    linked_risks: list[dict[str, object]],
    evidence_ids: list[str],
    evidence_index: Mapping[str, Mapping[str, object]],
    as_of: datetime,
) -> list[str]:
    reasons: list[str] = []
    missing_evidence = [
        evidence_id for evidence_id in evidence_ids if evidence_id not in evidence_index
    ]
    if not evidence_ids or missing_evidence:
        reasons.append("missing_evidence")
    if any(
        str(evidence_index[evidence_id].get("data_class"))
        not in ALLOWED_EVIDENCE_DATA_CLASSES
        for evidence_id in evidence_ids
        if evidence_id in evidence_index
    ):
        reasons.append("data_class_not_allowed")
    latest_available_at = _latest_datetime(
        [event.get("available_at") for event in linked_events]
        + [risk.get("available_at") for risk in linked_risks]
    )
    if latest_available_at is None or as_of - latest_available_at > MAX_SOURCE_AGE:
        reasons.append("stale_source")
    if any(_risk_has_contradiction(risk) for risk in linked_risks):
        reasons.append("unresolved_risk_contradiction")
    if _contains_restricted_language(assessment, linked_events, linked_risks):
        reasons.append("restricted_language")
    return reasons


def _suppressed_payload(candidate: Mapping[str, object]) -> dict[str, object]:
    readiness = candidate.get("readiness")
    blocking_reasons = (
        readiness.get("blocking_reasons")
        if isinstance(readiness, Mapping)
        else ()
    )
    return {
        "ticker": candidate.get("ticker"),
        "candidate_advisory_id": candidate.get("advisory_id"),
        "blocking_reasons": _text_list(blocking_reasons),
        "advisory_label": ADVISORY_LABEL,
    }


def _artifact_uri(run_id: str, brief_id: str, published_ids: Sequence[str]) -> str:
    query = urlencode(
        {
            "brief_id": brief_id,
            "published_advisory_count": str(len(published_ids)),
            "advisory_label": ADVISORY_LABEL,
        }
    )
    return f"artifact://daily-ai-infra-brief/{run_id}?{query}"


def _input_summary(
    inputs: Mapping[str, list[dict[str, object]]]
) -> dict[str, object]:
    return {
        name: [_compact_row(row) for row in rows]
        for name, rows in sorted(inputs.items())
    }


def _compact_row(row: Mapping[str, object]) -> dict[str, object]:
    return {
        key: row.get(key)
        for key in sorted(row)
        if key.endswith("_id")
        or key.endswith("_ids")
        or key
        in {
            "ticker",
            "tickers",
            "available_at",
            "as_of",
            "data_class",
            "content_hash",
            "advisory_label",
            "review_status",
            "readiness",
        }
    }


def _advisory_summary(
    *,
    ticker: str,
    action: str,
    assessment: Mapping[str, object],
    linked_events: list[dict[str, object]],
    linked_risks: list[dict[str, object]],
) -> str:
    catalyst = (
        str(linked_events[0].get("catalyst"))
        if linked_events
        else "No fresh catalyst was linked."
    )
    risk_note = (
        str(linked_risks[0].get("summary"))
        if linked_risks
        else "No active risk-regime update was linked."
    )
    assessment_text = str(assessment.get("assessment") or "Assessment unavailable.")
    return (
        f"{ticker} advisory-only {action}: {assessment_text} "
        f"Catalyst: {catalyst} Risk context: {risk_note}"
    )


def _brief_summary(published_count: int, suppressed_count: int) -> str:
    if published_count:
        return (
            f"Published {published_count} advisory-only AI infrastructure update(s); "
            f"{suppressed_count} candidate(s) were suppressed by deterministic gates."
        )
    return (
        "No advisory updates were published; "
        f"{suppressed_count} candidate(s) were suppressed by deterministic gates."
    )


def _deterministic_check_ids(readiness: Mapping[str, object]) -> list[str]:
    checks = readiness.get("checks")
    if not isinstance(checks, Mapping):
        return []
    passed = [str(name) for name, value in checks.items() if value is True]
    if readiness.get("publishable") is True:
        passed.append("deterministic_checks_passed")
    return passed


def _collect_evidence_ids(
    inputs: Mapping[str, list[dict[str, object]]]
) -> list[str]:
    return _unique_texts(
        evidence_id
        for rows in inputs.values()
        for row in rows
        for evidence_id in _text_list(row.get("evidence_ids"))
    )


def _related_market_events(
    market_events: list[dict[str, object]],
    ticker: str,
    linked_event_ids: Sequence[str],
) -> list[dict[str, object]]:
    linked = set(linked_event_ids)
    return [
        event
        for event in market_events
        if str(event.get("event_id")) in linked
        or ticker in {item.upper() for item in _text_list(event.get("tickers"))}
    ]


def _related_segments(
    segments: list[dict[str, object]],
    ticker: str,
    linked_event_ids: Sequence[str],
) -> list[dict[str, object]]:
    linked = set(linked_event_ids)
    return [
        segment
        for segment in segments
        if set(_text_list(segment.get("linked_event_ids"))).intersection(linked)
        or ticker
        in {
            item.upper()
            for item in _text_list(segment.get("primary_tickers"))
            + _text_list(segment.get("second_order_tickers"))
        }
    ]


def _related_risks(
    risks: list[dict[str, object]],
    ticker: str,
    linked_event_ids: Sequence[str],
) -> list[dict[str, object]]:
    linked = set(linked_event_ids)
    return [
        risk
        for risk in risks
        if ticker in {item.upper() for item in _text_list(risk.get("affected_tickers"))}
        or set(_text_list(risk.get("linked_event_ids"))).intersection(linked)
    ]


def _latest_for_ticker(
    rows: list[dict[str, object]],
    ticker: str,
) -> dict[str, object] | None:
    for row in rows:
        if str(row.get("ticker") or "").upper() == ticker:
            return row
    return None


def _risk_has_contradiction(risk: Mapping[str, object]) -> bool:
    combined = " ".join(
        str(risk.get(key) or "").lower() for key in ("status", "summary")
    )
    return "contradiction" in combined and "resolved" not in combined


def _contains_restricted_language(*items: object) -> bool:
    text = json.dumps(items, sort_keys=True, default=str).lower()
    restricted_terms = (
        "start live trading",
        "account credential",
        "direct market action",
    )
    return any(term in text for term in restricted_terms)


def _normalize_action(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if "accumulate" in normalized:
        return "accumulate"
    if "trim" in normalized:
        return "trim"
    if "avoid" in normalized:
        return "avoid"
    if "hold" in normalized:
        return "hold"
    if "exit" in normalized:
        return "exit-candidate"
    if "watch" in normalized:
        return "watch"
    return "review"


def _latest_datetime(values: Iterable[object]) -> datetime | None:
    parsed = [_datetime_or_none(value) for value in values]
    valid = [value for value in parsed if value is not None]
    return max(valid) if valid else None


def _datetime_or_none(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _aware_datetime(value)
    try:
        return _aware_datetime(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None


def _aware_datetime(value: datetime | None) -> datetime:
    candidate = value or datetime.now(timezone.utc)
    if candidate.tzinfo is None or candidate.tzinfo.utcoffset(candidate) is None:
        return candidate.replace(tzinfo=timezone.utc)
    return candidate.astimezone(timezone.utc)


def _column_names(description: object) -> tuple[str, ...]:
    return tuple(_column_name(item) for item in description or ())


def _column_name(item: object) -> str:
    name = getattr(item, "name", None)
    if name is not None:
        return str(name)
    return str(item[0])  # type: ignore[index]


def _row_to_dict(row: object, column_names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(row, Mapping):
        return dict(row)
    return dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]


def _first_value(rows: Sequence[Mapping[str, object]], key: str) -> object | None:
    return rows[0].get(key) if rows else None


def _unique_texts(values: Iterable[object] | object) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    iterable = (
        (values,)
        if isinstance(values, str) or not isinstance(values, Iterable)
        else values
    )
    for value in iterable:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return [str(value)]


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _hash_payload(*parts: object) -> str:
    return hashlib.sha256(_json(parts).encode("utf-8")).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def run_from_environment() -> dict[str, object]:
    import psycopg

    settings = RuntimeSettings.from_env(os.environ, allow_defaults=True)
    with psycopg.connect(settings.database_url) as connection:
        return run_daily_ai_infra_brief(
            connection,
            model_profiles_path=settings.model_profiles_path,
        )


def main() -> None:
    try:
        result = run_from_environment()
    except RuntimeConfigError as error:
        result = {
            "run_type": RUN_TYPE,
            "status": "failed",
            "exit_code": 2,
            "error_summary": str(error),
        }

    print(json.dumps(result, sort_keys=True, default=_json_default))
    exit_code = int(result.get("exit_code", 1))
    if exit_code != 0:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
