from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

from ai_infra_fund_core.runtime.config import RuntimeSettings


RUN_TYPE = "fixture_advisory"
ADVISORY_LABEL = "advisory_only"


class Cursor(Protocol):
    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...


class Connection(Protocol):
    def cursor(self) -> object: ...

    def commit(self) -> None: ...


UPSERT_MODEL_RUN_SQL = """
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
    schema_valid,
    retry_count,
    data_classes,
    status,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (model_run_id) DO UPDATE SET
    task_role = EXCLUDED.task_role,
    model_id = EXCLUDED.model_id,
    deployment = EXCLUDED.deployment,
    provider = EXCLUDED.provider,
    prompt_version = EXCLUDED.prompt_version,
    input_hash = EXCLUDED.input_hash,
    output_hash = EXCLUDED.output_hash,
    schema_valid = EXCLUDED.schema_valid,
    data_classes = EXCLUDED.data_classes,
    status = EXCLUDED.status,
    created_at = EXCLUDED.created_at;
"""


UPSERT_EVIDENCE_ITEM_SQL = """
INSERT INTO evidence.evidence_items (
    evidence_id,
    source_uri,
    source_type,
    title,
    publisher,
    published_at,
    ingested_at,
    content_hash,
    license_label,
    data_class,
    tickers,
    themes,
    summary,
    storage_uri,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (evidence_id) DO UPDATE SET
    source_uri = EXCLUDED.source_uri,
    source_type = EXCLUDED.source_type,
    title = EXCLUDED.title,
    publisher = EXCLUDED.publisher,
    published_at = EXCLUDED.published_at,
    ingested_at = EXCLUDED.ingested_at,
    content_hash = EXCLUDED.content_hash,
    license_label = EXCLUDED.license_label,
    data_class = EXCLUDED.data_class,
    tickers = EXCLUDED.tickers,
    themes = EXCLUDED.themes,
    summary = EXCLUDED.summary,
    storage_uri = EXCLUDED.storage_uri,
    created_at = EXCLUDED.created_at;
"""


UPSERT_SOURCE_SIGNAL_SQL = """
INSERT INTO analyst.source_signals (
    signal_id,
    source_type,
    signal_category,
    title,
    observed_at,
    available_at,
    tickers,
    themes,
    evidence_ids,
    derived_market_event_ids,
    confidence,
    review_status,
    content_hash,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (signal_id) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    signal_category = EXCLUDED.signal_category,
    title = EXCLUDED.title,
    observed_at = EXCLUDED.observed_at,
    available_at = EXCLUDED.available_at,
    tickers = EXCLUDED.tickers,
    themes = EXCLUDED.themes,
    evidence_ids = EXCLUDED.evidence_ids,
    derived_market_event_ids = EXCLUDED.derived_market_event_ids,
    confidence = EXCLUDED.confidence,
    review_status = EXCLUDED.review_status,
    content_hash = EXCLUDED.content_hash,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_MARKET_EVENT_SQL = """
INSERT INTO analyst.market_events (
    event_id,
    event_type,
    source_signal_ids,
    evidence_ids,
    tickers,
    companies,
    themes,
    catalyst,
    ai_relevance,
    direction,
    time_horizon,
    confidence,
    occurred_at,
    available_at,
    content_hash,
    extracted_by_model_run_id,
    review_status,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (event_id) DO UPDATE SET
    event_type = EXCLUDED.event_type,
    source_signal_ids = EXCLUDED.source_signal_ids,
    evidence_ids = EXCLUDED.evidence_ids,
    tickers = EXCLUDED.tickers,
    companies = EXCLUDED.companies,
    themes = EXCLUDED.themes,
    catalyst = EXCLUDED.catalyst,
    ai_relevance = EXCLUDED.ai_relevance,
    direction = EXCLUDED.direction,
    time_horizon = EXCLUDED.time_horizon,
    confidence = EXCLUDED.confidence,
    occurred_at = EXCLUDED.occurred_at,
    available_at = EXCLUDED.available_at,
    content_hash = EXCLUDED.content_hash,
    extracted_by_model_run_id = EXCLUDED.extracted_by_model_run_id,
    review_status = EXCLUDED.review_status,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_SEGMENT_IMPACT_SQL = """
INSERT INTO analyst.segment_impacts (
    segment_id,
    segment_name,
    primary_tickers,
    second_order_tickers,
    linked_event_ids,
    impact_direction,
    impact_summary,
    evidence_ids,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (segment_id) DO UPDATE SET
    segment_name = EXCLUDED.segment_name,
    primary_tickers = EXCLUDED.primary_tickers,
    second_order_tickers = EXCLUDED.second_order_tickers,
    linked_event_ids = EXCLUDED.linked_event_ids,
    impact_direction = EXCLUDED.impact_direction,
    impact_summary = EXCLUDED.impact_summary,
    evidence_ids = EXCLUDED.evidence_ids,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_EQUITY_ASSESSMENT_SQL = """
INSERT INTO analyst.equity_impact_assessments (
    assessment_id,
    ticker,
    company,
    linked_event_ids,
    assessment,
    watch_items,
    advisory_implication,
    risk_flags,
    invalidation,
    evidence_ids,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (assessment_id) DO UPDATE SET
    ticker = EXCLUDED.ticker,
    company = EXCLUDED.company,
    linked_event_ids = EXCLUDED.linked_event_ids,
    assessment = EXCLUDED.assessment,
    watch_items = EXCLUDED.watch_items,
    advisory_implication = EXCLUDED.advisory_implication,
    risk_flags = EXCLUDED.risk_flags,
    invalidation = EXCLUDED.invalidation,
    evidence_ids = EXCLUDED.evidence_ids,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_VALUATION_CONTEXT_SQL = """
INSERT INTO analyst.valuation_contexts (
    valuation_context_id,
    ticker,
    valuation_state,
    forward_pe,
    ev_sales,
    assumptions,
    risk_flags,
    evidence_ids,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (valuation_context_id) DO UPDATE SET
    ticker = EXCLUDED.ticker,
    valuation_state = EXCLUDED.valuation_state,
    forward_pe = EXCLUDED.forward_pe,
    ev_sales = EXCLUDED.ev_sales,
    assumptions = EXCLUDED.assumptions,
    risk_flags = EXCLUDED.risk_flags,
    evidence_ids = EXCLUDED.evidence_ids,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_MACRO_REGIME_SQL = """
INSERT INTO analyst.macro_regime_snapshots (
    regime_id,
    risk_type,
    status,
    linked_event_ids,
    evidence_ids,
    summary,
    portfolio_monitoring_note,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (regime_id) DO UPDATE SET
    risk_type = EXCLUDED.risk_type,
    status = EXCLUDED.status,
    linked_event_ids = EXCLUDED.linked_event_ids,
    evidence_ids = EXCLUDED.evidence_ids,
    summary = EXCLUDED.summary,
    portfolio_monitoring_note = EXCLUDED.portfolio_monitoring_note,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_TRADING_ADVISORY_SQL = """
INSERT INTO analyst.trading_advisories (
    advisory_id,
    recommendation_artifact_id,
    ticker,
    advisory_label,
    analyst_action,
    advisory_summary,
    evidence_ids,
    model_run_ids,
    signal_bundle_id,
    target_weights_id,
    deterministic_checks,
    linked_trade_plan_id,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (advisory_id) DO UPDATE SET
    recommendation_artifact_id = EXCLUDED.recommendation_artifact_id,
    ticker = EXCLUDED.ticker,
    advisory_label = EXCLUDED.advisory_label,
    analyst_action = EXCLUDED.analyst_action,
    advisory_summary = EXCLUDED.advisory_summary,
    evidence_ids = EXCLUDED.evidence_ids,
    model_run_ids = EXCLUDED.model_run_ids,
    signal_bundle_id = EXCLUDED.signal_bundle_id,
    target_weights_id = EXCLUDED.target_weights_id,
    deterministic_checks = EXCLUDED.deterministic_checks,
    linked_trade_plan_id = EXCLUDED.linked_trade_plan_id,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_ANALYST_BRIEF_SQL = """
INSERT INTO analyst.analyst_briefs (
    brief_id,
    as_of,
    title,
    advisory_label,
    executive_summary,
    market_event_ids,
    segment_impact_ids,
    trading_advisory_ids,
    model_run_ids,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (brief_id) DO UPDATE SET
    as_of = EXCLUDED.as_of,
    title = EXCLUDED.title,
    advisory_label = EXCLUDED.advisory_label,
    executive_summary = EXCLUDED.executive_summary,
    market_event_ids = EXCLUDED.market_event_ids,
    segment_impact_ids = EXCLUDED.segment_impact_ids,
    trading_advisory_ids = EXCLUDED.trading_advisory_ids,
    model_run_ids = EXCLUDED.model_run_ids,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_RUN_ARTIFACT_SQL = """
INSERT INTO audit.run_artifacts (
    run_id,
    run_type,
    started_at,
    completed_at,
    inputs_hash,
    output_hash,
    artifact_uri,
    status,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (run_id) DO UPDATE SET
    run_type = EXCLUDED.run_type,
    started_at = EXCLUDED.started_at,
    completed_at = EXCLUDED.completed_at,
    inputs_hash = EXCLUDED.inputs_hash,
    output_hash = EXCLUDED.output_hash,
    artifact_uri = EXCLUDED.artifact_uri,
    status = EXCLUDED.status,
    created_at = EXCLUDED.created_at;
"""


def seed_fixture_advisory_run(
    connection: Connection,
    fixture_path: Path | str,
) -> dict[str, object]:
    path = Path(fixture_path)
    fixture = json.loads(path.read_text(encoding="utf-8"))
    fixture_hash = _file_hash(path)
    as_of = _parse_datetime(str(fixture["as_of"]))
    run_id = f"run-fixture-advisory-{fixture_hash[:16]}"

    with connection.cursor() as cursor:
        _persist_model_runs(cursor, fixture, fixture_hash, as_of)
        _persist_evidence_items(cursor, fixture, as_of)
        _persist_source_signals(cursor, fixture, as_of)
        _persist_market_events(cursor, fixture, as_of)
        _persist_segment_impacts(cursor, fixture, as_of)
        _persist_equity_assessments(cursor, fixture, as_of)
        _persist_valuation_contexts(cursor, fixture, as_of)
        _persist_macro_regime(cursor, fixture, as_of)
        _persist_trading_advisories(cursor, fixture, as_of)
        _persist_analyst_brief(cursor, fixture, as_of)
        cursor.execute(
            UPSERT_RUN_ARTIFACT_SQL,
            (
                run_id,
                RUN_TYPE,
                as_of,
                as_of,
                fixture_hash,
                _hash_payload("fixture_advisory_output", fixture.get("AnalystBrief", {})),
                f"artifact://fixture-advisory?brief_id={fixture['AnalystBrief']['brief_id']}&advisory_label={ADVISORY_LABEL}",
                "succeeded",
                as_of,
            ),
        )
    connection.commit()

    return {
        "run_id": run_id,
        "run_type": RUN_TYPE,
        "status": "succeeded",
        "advisory_label": ADVISORY_LABEL,
        "source_signal_count": len(fixture.get("source_signals", ())),
        "market_event_count": len(fixture.get("market_events", ())),
        "trading_advisory_count": len(fixture.get("trading_advisories", ())),
    }


def _persist_model_runs(cursor: Cursor, fixture: dict[str, object], fixture_hash: str, as_of: datetime) -> None:
    for model_run in _list(fixture.get("model_runs")):
        model_run_id = str(model_run["model_run_id"])
        cursor.execute(
            UPSERT_MODEL_RUN_SQL,
            (
                model_run_id,
                str(model_run.get("task") or "fixture_advisory_review"),
                str(model_run.get("profile") or "fixture_profile"),
                str(model_run.get("profile") or "fixture_profile"),
                "fixture",
                "fixture-advisory-v1",
                fixture_hash,
                _hash_payload("fixture_model_run", model_run),
                0,
                0,
                0,
                True,
                0,
                [str(model_run.get("data_class") or "public_evidence")],
                "success",
                _parse_datetime(str(model_run.get("created_at") or as_of.isoformat())),
            ),
        )


def _persist_evidence_items(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for item in _list(fixture.get("evidence_items")):
        evidence_id = str(item["evidence_id"])
        cursor.execute(
            UPSERT_EVIDENCE_ITEM_SQL,
            (
                evidence_id,
                f"mock://ai-infra-fund/evidence/{evidence_id}",
                str(item.get("source_type") or "mock_public_evidence"),
                str(item.get("source_title") or evidence_id),
                str(item.get("publisher") or "mock_public_fixture"),
                _parse_datetime(str(item.get("captured_at") or as_of.isoformat())),
                as_of,
                _content_hash(item, evidence_id),
                "mock_public",
                "public_evidence",
                _text_list(item.get("tickers")),
                _text_list(item.get("themes")),
                str(item.get("claim_summary") or ""),
                f"fixture://situational-awareness/{evidence_id}",
                as_of,
            ),
        )


def _persist_source_signals(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for signal in _list(fixture.get("source_signals")):
        signal_id = str(signal["signal_id"])
        observed_at = _parse_datetime(str(signal.get("observed_at") or as_of.isoformat()))
        cursor.execute(
            UPSERT_SOURCE_SIGNAL_SQL,
            (
                signal_id,
                str(signal.get("source_type") or "fixture_source"),
                str(signal.get("signal_category") or "fixture_signal"),
                str(signal.get("title") or signal_id),
                observed_at,
                observed_at,
                _text_list(signal.get("tickers")),
                _text_list(signal.get("themes")),
                _required_text_list(signal.get("evidence_ids"), "source signal evidence_ids"),
                _text_list(signal.get("derived_market_event_ids")),
                str(signal.get("confidence") or "medium"),
                str(signal.get("review_status") or "reviewed"),
                _hash_payload("source_signal", signal),
                _json(signal),
                as_of,
            ),
        )


def _persist_market_events(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for event in _list(fixture.get("market_events")):
        event_id = str(event["event_id"])
        cursor.execute(
            UPSERT_MARKET_EVENT_SQL,
            (
                event_id,
                str(event.get("event_type") or "fixture_event"),
                _text_list(event.get("source_signal_ids")),
                _required_text_list(event.get("evidence_ids"), "market event evidence_ids"),
                _text_list(event.get("tickers")),
                _text_list(event.get("companies")),
                _text_list(event.get("themes")),
                str(event.get("catalyst") or event_id),
                str(event.get("ai_relevance") or "AI infrastructure relevance under review."),
                str(event.get("direction") or "mixed"),
                str(event.get("time_horizon") or "medium_term"),
                str(event.get("confidence") or "medium"),
                _parse_datetime(str(event.get("occurred_at") or as_of.isoformat())),
                _parse_datetime(str(event.get("available_at") or as_of.isoformat())),
                _content_hash(event, event_id),
                _optional_text(event.get("extracted_by_model_run_id")),
                str(event.get("review_status") or "reviewed"),
                _json(event),
                as_of,
            ),
        )


def _persist_segment_impacts(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for segment in _list(fixture.get("segment_impacts")):
        cursor.execute(
            UPSERT_SEGMENT_IMPACT_SQL,
            (
                str(segment["segment_id"]),
                str(segment.get("segment_name") or segment["segment_id"]),
                _text_list(segment.get("primary_tickers")),
                _text_list(
                    segment.get("second_order_tickers")
                    or segment.get("derivative_tickers")
                ),
                _required_text_list(segment.get("linked_event_ids"), "segment linked_event_ids"),
                str(segment.get("impact_direction") or "mixed"),
                str(segment.get("impact_summary") or ""),
                _required_text_list(segment.get("evidence_ids"), "segment evidence_ids"),
                _json(segment),
                as_of,
            ),
        )


def _persist_equity_assessments(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for assessment in _list(fixture.get("equity_impact_assessments")):
        cursor.execute(
            UPSERT_EQUITY_ASSESSMENT_SQL,
            (
                str(assessment["assessment_id"]),
                str(assessment["ticker"]).upper(),
                str(assessment.get("company") or assessment["ticker"]),
                _required_text_list(assessment.get("linked_event_ids"), "assessment linked_event_ids"),
                str(assessment.get("assessment") or ""),
                _text_list(assessment.get("watch_items")),
                str(assessment.get("advisory_implication") or "review"),
                _text_list(assessment.get("risk_flags")),
                str(
                    assessment.get("invalidation_condition")
                    or "Invalidate if supporting catalyst evidence weakens."
                ),
                _required_text_list(assessment.get("evidence_ids"), "assessment evidence_ids"),
                _json(assessment),
                as_of,
            ),
        )


def _persist_valuation_contexts(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for valuation in _list(fixture.get("valuation_contexts")):
        cursor.execute(
            UPSERT_VALUATION_CONTEXT_SQL,
            (
                str(valuation["valuation_context_id"]),
                str(valuation["ticker"]).upper(),
                str(valuation.get("valuation_state") or "review"),
                _optional_text(valuation.get("forward_pe_mock")),
                _optional_text(valuation.get("ev_sales_mock")),
                _text_list(valuation.get("assumptions")),
                _text_list(valuation.get("risk_flags")),
                _required_text_list(valuation.get("evidence_ids"), "valuation evidence_ids"),
                _json(valuation),
                as_of,
            ),
        )


def _persist_macro_regime(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for regime in _list(fixture.get("risk_regime_updates")):
        cursor.execute(
            UPSERT_MACRO_REGIME_SQL,
            (
                str(regime["regime_id"]),
                str(regime.get("risk_type") or "macro_regime"),
                str(regime.get("status") or "review"),
                _text_list(regime.get("linked_event_ids")),
                _required_text_list(regime.get("evidence_ids"), "risk regime evidence_ids"),
                str(regime.get("summary") or ""),
                str(regime.get("portfolio_monitoring_note") or ""),
                _json(regime),
                as_of,
            ),
        )


def _persist_trading_advisories(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    for advisory in _list(fixture.get("trading_advisories")):
        cursor.execute(
            UPSERT_TRADING_ADVISORY_SQL,
            (
                str(advisory["advisory_id"]),
                _optional_text(advisory.get("recommendation_artifact_id")),
                str(advisory["ticker"]).upper(),
                ADVISORY_LABEL,
                _normalize_action(str(advisory.get("advisory_label") or "review")),
                str(advisory.get("advisory_summary") or ""),
                _required_text_list(advisory.get("evidence_ids"), "trading advisory evidence_ids"),
                _text_list(advisory.get("model_run_ids")),
                _optional_text(advisory.get("signal_bundle_id")),
                _optional_text(advisory.get("target_weights_id")),
                _text_list(advisory.get("deterministic_checks")),
                _optional_text(advisory.get("linked_trade_plan_id")),
                _json(advisory),
                as_of,
            ),
        )


def _persist_analyst_brief(cursor: Cursor, fixture: dict[str, object], as_of: datetime) -> None:
    brief = dict(fixture["AnalystBrief"])  # type: ignore[arg-type]
    cursor.execute(
        UPSERT_ANALYST_BRIEF_SQL,
        (
            str(brief["brief_id"]),
            _parse_datetime(str(brief.get("as_of") or as_of.isoformat())),
            str(brief.get("title") or "AI Infrastructure Analyst Brief"),
            ADVISORY_LABEL,
            str(brief.get("executive_summary") or ""),
            [str(event["event_id"]) for event in _list(fixture.get("market_events"))],
            [str(segment["segment_id"]) for segment in _list(fixture.get("segment_impacts"))],
            [
                str(advisory["advisory_id"])
                for advisory in _list(fixture.get("trading_advisories"))
            ],
            [
                str(model_run["model_run_id"])
                for model_run in _list(fixture.get("model_runs"))
            ],
            _json(brief),
            as_of,
        ),
    )


def run_from_environment() -> dict[str, object]:
    import psycopg

    fixture_path = Path(
        os.environ.get(
            "AI_INFRA_FUND_FIXTURE_BRIEF_PATH",
            "/app/docs/mock_data/situational_awareness_brief.example.json",
        )
    )
    settings = RuntimeSettings.from_env(os.environ, allow_defaults=True)
    with psycopg.connect(settings.database_url) as connection:
        return seed_fixture_advisory_run(connection, fixture_path)


def main() -> None:
    result = run_from_environment()
    print(json.dumps(result, sort_keys=True, default=str))


def _normalize_action(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    return normalized if normalized in {"watch", "accumulate", "hold", "trim", "avoid", "review", "exit-candidate"} else "review"


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _content_hash(payload: dict[str, object], fallback: str) -> str:
    value = payload.get("content_hash")
    return str(value) if value else _hash_payload("content_hash", payload, fallback)


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_payload(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _required_text_list(value: object, field_name: str) -> list[str]:
    values = _text_list(value)
    if not values:
        raise ValueError(f"{field_name} is required")
    return values


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


if __name__ == "__main__":
    main()
