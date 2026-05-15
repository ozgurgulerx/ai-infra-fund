from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol
import json


class Cursor(Protocol):
    description: object

    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...

    def fetchall(self) -> list[object]: ...


class Connection(Protocol):
    def cursor(self) -> object: ...


EVIDENCE_SUMMARY_SQL = """
WITH item_counts AS (
    SELECT COUNT(*) AS total_items
    FROM evidence.evidence_items
),
chunk_counts AS (
    SELECT COUNT(*) AS total_chunks
    FROM evidence.evidence_chunks
),
claim_counts AS (
    SELECT COUNT(*) AS total_claims
    FROM evidence.evidence_claims
),
items_by_data_class AS (
    SELECT COALESCE(jsonb_object_agg(data_class, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT data_class, COUNT(*) AS total_count
        FROM evidence.evidence_items
        GROUP BY data_class
    ) AS grouped_items
),
created_rows AS (
    SELECT created_at FROM evidence.evidence_items
    UNION ALL
    SELECT created_at FROM evidence.evidence_chunks
    UNION ALL
    SELECT created_at FROM evidence.evidence_claims
)
SELECT
    item_counts.total_items,
    chunk_counts.total_chunks,
    claim_counts.total_claims,
    items_by_data_class.counts AS items_by_data_class,
    (SELECT MAX(ingested_at) FROM evidence.evidence_items) AS latest_ingested_at,
    (SELECT MAX(created_at) FROM created_rows) AS latest_created_at
FROM item_counts, chunk_counts, claim_counts, items_by_data_class;
"""


RECOMMENDATION_SUMMARY_SQL = """
WITH artifact_counts AS (
    SELECT COUNT(*) AS total_recommendations
    FROM recommendations.recommendation_artifacts
),
audit_counts AS (
    SELECT
        COUNT(*) AS total_audits,
        COUNT(*) FILTER (WHERE schema_valid IS TRUE) AS schema_valid_audits,
        COUNT(*) FILTER (WHERE schema_valid IS FALSE) AS schema_invalid_audits
    FROM recommendations.recommendation_audits
),
created_rows AS (
    SELECT created_at FROM recommendations.recommendation_artifacts
    UNION ALL
    SELECT created_at FROM recommendations.recommendation_audits
)
SELECT
    artifact_counts.total_recommendations,
    audit_counts.total_audits,
    audit_counts.schema_valid_audits,
    audit_counts.schema_invalid_audits,
    (SELECT MAX(created_at) FROM created_rows) AS latest_created_at
FROM artifact_counts, audit_counts;
"""


MODEL_RUN_SUMMARY_SQL = """
WITH run_counts AS (
    SELECT COUNT(*) AS total_model_runs
    FROM audit.model_runs
),
runs_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM audit.model_runs
        GROUP BY status
    ) AS grouped_runs
)
SELECT
    run_counts.total_model_runs,
    runs_by_status.counts AS runs_by_status,
    (SELECT MAX(created_at) FROM audit.model_runs) AS latest_created_at
FROM run_counts, runs_by_status;
"""


EVALUATION_SUMMARY_SQL = """
WITH backtest_counts AS (
    SELECT COUNT(*) AS total_backtest_runs
    FROM audit.backtest_runs
),
backtest_runs_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM audit.backtest_runs
        GROUP BY status
    ) AS grouped_backtests
),
artifact_counts AS (
    SELECT COUNT(*) AS total_run_artifacts
    FROM audit.run_artifacts
),
run_artifacts_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM audit.run_artifacts
        GROUP BY status
    ) AS grouped_artifacts
),
created_rows AS (
    SELECT created_at FROM audit.backtest_runs
    UNION ALL
    SELECT created_at FROM audit.run_artifacts
)
SELECT
    backtest_counts.total_backtest_runs,
    backtest_runs_by_status.counts AS backtest_runs_by_status,
    artifact_counts.total_run_artifacts,
    run_artifacts_by_status.counts AS run_artifacts_by_status,
    (SELECT MAX(created_at) FROM created_rows) AS latest_created_at
FROM backtest_counts, backtest_runs_by_status, artifact_counts, run_artifacts_by_status;
"""


DATA_QUALITY_SUMMARY_SQL = """
WITH check_counts AS (
    SELECT COUNT(*) AS total_checks
    FROM governance.data_quality_checks
),
checks_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM governance.data_quality_checks
        GROUP BY status
    ) AS grouped_statuses
),
checks_by_severity AS (
    SELECT COALESCE(jsonb_object_agg(severity, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT severity, COUNT(*) AS total_count
        FROM governance.data_quality_checks
        GROUP BY severity
    ) AS grouped_severities
)
SELECT
    check_counts.total_checks,
    checks_by_status.counts AS checks_by_status,
    checks_by_severity.counts AS checks_by_severity,
    (SELECT MAX(checked_at) FROM governance.data_quality_checks) AS latest_checked_at,
    (SELECT MAX(created_at) FROM governance.data_quality_checks) AS latest_created_at
FROM check_counts, checks_by_status, checks_by_severity;
"""


INCIDENT_SUMMARY_SQL = """
WITH incident_counts AS (
    SELECT
        COUNT(*) AS total_incidents,
        COUNT(*) FILTER (WHERE resolved_at IS NULL) AS open_incidents
    FROM governance.incident_records
),
incidents_by_severity AS (
    SELECT COALESCE(jsonb_object_agg(severity, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT severity, COUNT(*) AS total_count
        FROM governance.incident_records
        GROUP BY severity
    ) AS grouped_severities
),
incidents_by_freeze_status AS (
    SELECT COALESCE(jsonb_object_agg(freeze_status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT freeze_status, COUNT(*) AS total_count
        FROM governance.incident_records
        GROUP BY freeze_status
    ) AS grouped_freeze_statuses
)
SELECT
    incident_counts.total_incidents,
    incidents_by_severity.counts AS incidents_by_severity,
    incidents_by_freeze_status.counts AS incidents_by_freeze_status,
    incident_counts.open_incidents,
    (SELECT MAX(created_at) FROM governance.incident_records) AS latest_created_at
FROM incident_counts, incidents_by_severity, incidents_by_freeze_status;
"""


WATCHLIST_SUMMARY_SQL = """
WITH member_counts AS (
    SELECT COUNT(*) AS total_members
    FROM core.universe_members
),
members_by_status AS (
    SELECT COALESCE(jsonb_object_agg(watchlist_status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT COALESCE(watchlist_status, 'unspecified') AS watchlist_status, COUNT(*) AS total_count
        FROM core.universe_members
        GROUP BY COALESCE(watchlist_status, 'unspecified')
    ) AS grouped_members
)
SELECT
    member_counts.total_members,
    members_by_status.counts AS by_watchlist_status,
    (SELECT MAX(updated_at) FROM core.universe_members) AS latest_updated_at
FROM member_counts, members_by_status;
"""


WATCHLIST_MEMBERS_SQL = """
SELECT
    ticker,
    name,
    theme,
    role,
    watchlist_status,
    max_weight,
    liquidity_floor,
    thesis_source,
    updated_at
FROM core.universe_members
ORDER BY updated_at DESC, ticker ASC
LIMIT %s;
"""


CRAWL_FRONTIER_HEALTH_SQL = """
SELECT
    dataset_name,
    source,
    MAX(retrieved_at) AS latest_retrieved_at,
    MAX(available_at) AS latest_available_at,
    MAX(effective_at) AS latest_effective_at,
    MAX(created_at) AS latest_created_at,
    COUNT(*) AS snapshot_count,
    COALESCE(SUM(row_count), 0) AS row_count
FROM audit.data_snapshots
GROUP BY dataset_name, source
ORDER BY MAX(available_at) DESC, dataset_name ASC, source ASC
LIMIT 25;
"""


LATEST_EQUITY_EVENTS_SQL = """
SELECT
    evidence_id,
    source_uri,
    source_type,
    title,
    publisher,
    published_at,
    ingested_at,
    data_class,
    tickers,
    themes,
    summary
FROM evidence.evidence_items
WHERE data_class IN ('public_market_data', 'public_evidence')
    AND cardinality(tickers) > 0
ORDER BY COALESCE(published_at, ingested_at, created_at) DESC, evidence_id ASC
LIMIT %s;
"""


LATEST_SIGNAL_SNAPSHOTS_SQL = """
SELECT DISTINCT ON (ticker)
    signal_bundle_id,
    ticker,
    as_of,
    strategic_thesis_score,
    tactical_technical_score,
    forward_indicator_score,
    portfolio_risk_score,
    formula_versions,
    input_snapshot_hash,
    created_at
FROM signals.signal_bundles
ORDER BY ticker ASC, as_of DESC, created_at DESC
LIMIT %s;
"""


LATEST_ADVISORY_RUN_SQL = """
SELECT
    run_id,
    run_type,
    started_at,
    completed_at,
    artifact_uri,
    status,
    error_summary,
    created_at
FROM audit.run_artifacts
WHERE run_type IN (%s, %s, %s)
ORDER BY started_at DESC, created_at DESC
LIMIT 1;
"""


TICKER_WATCHLIST_SQL = """
SELECT
    ticker,
    name,
    theme,
    role,
    watchlist_status,
    max_weight,
    liquidity_floor,
    thesis_source,
    updated_at
FROM core.universe_members
WHERE UPPER(ticker) = UPPER(%s)
LIMIT 1;
"""


TICKER_SIGNAL_SQL = """
SELECT
    signal_bundle_id,
    ticker,
    as_of,
    strategic_thesis_score,
    tactical_technical_score,
    forward_indicator_score,
    portfolio_risk_score,
    formula_versions,
    input_snapshot_hash,
    created_at
FROM signals.signal_bundles
WHERE UPPER(ticker) = UPPER(%s)
ORDER BY as_of DESC, created_at DESC
LIMIT 1;
"""


TICKER_RECOMMENDATION_SQL = """
SELECT
    recommendation_id,
    ticker_or_portfolio,
    advisory_label,
    action,
    horizon,
    target_weights_id,
    signal_bundle_id,
    evidence_ids,
    model_run_ids,
    created_at
FROM recommendations.recommendation_artifacts
WHERE UPPER(ticker_or_portfolio) = UPPER(%s)
ORDER BY created_at DESC
LIMIT 1;
"""


TICKER_EVIDENCE_EVENTS_SQL = """
SELECT
    evidence_id,
    source_uri,
    source_type,
    title,
    publisher,
    published_at,
    ingested_at,
    data_class,
    tickers,
    themes,
    summary
FROM evidence.evidence_items
WHERE tickers @> ARRAY[%s]::text[]
ORDER BY COALESCE(published_at, ingested_at, created_at) DESC, evidence_id ASC
LIMIT %s;
"""


LATEST_PORTFOLIO_SNAPSHOTS_SQL = """
SELECT
    snapshot_id,
    as_of,
    cash_value,
    total_market_value,
    source
FROM core.portfolio_snapshots
ORDER BY as_of DESC, created_at DESC, snapshot_id DESC
LIMIT 2;
"""


PORTFOLIO_SNAPSHOT_POSITIONS_SQL = """
SELECT
    ticker,
    quantity,
    market_price,
    market_value,
    portfolio_weight,
    unrealized_pnl
FROM core.portfolio_snapshot_positions
WHERE snapshot_id = %s::uuid
ORDER BY ticker ASC;
"""


LATEST_RECOMMENDATIONS_SQL = """
SELECT
    artifact.recommendation_id,
    artifact.ticker_or_portfolio,
    artifact.action,
    artifact.horizon,
    artifact.advisory_label,
    artifact.signal_bundle_id,
    artifact.target_weights_id,
    COALESCE(cardinality(artifact.evidence_ids), 0) AS evidence_count,
    COALESCE(cardinality(artifact.model_run_ids), 0) AS model_run_count,
    artifact.created_at,
    COALESCE(audit.schema_valid, false) AS schema_valid
FROM recommendations.recommendation_artifacts AS artifact
LEFT JOIN recommendations.recommendation_audits AS audit
    ON audit.recommendation_id = artifact.recommendation_id
ORDER BY artifact.created_at DESC, artifact.recommendation_id DESC
LIMIT %s;
"""


class DashboardRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_status_overview(self) -> dict[str, object]:
        return self.overview()

    def get_status_modules(self) -> dict[str, object]:
        evidence = self.evidence_summary()
        recommendations = self.recommendation_summary()
        model_runs = self.model_run_summary()
        evaluations = self.evaluation_summary()
        data_quality = self.data_quality_summary()
        incidents = self.incident_summary()
        return {
            "modules": [
                _module_summary(
                    "data-plane",
                    status="available",
                    source_label="PostgreSQL dashboard repository",
                    detail="Dashboard summary queries reached the canonical PostgreSQL data spine.",
                    visible_value="DB summaries available",
                ),
                _module_summary(
                    "evidence-plane",
                    status=str(evidence.get("status", "empty")),
                    source_label="PostgreSQL evidence summary",
                    detail=(
                        f"{_int(evidence.get('total_items'))} items, "
                        f"{_int(evidence.get('total_chunks'))} chunks, "
                        f"{_int(evidence.get('total_claims'))} claims."
                    ),
                    visible_value=f"{_int(evidence.get('total_items'))} evidence items",
                ),
                _module_summary(
                    "recommendation-artifacts",
                    status=str(recommendations.get("status", "empty")),
                    source_label="PostgreSQL recommendation summary",
                    detail=(
                        f"{_int(recommendations.get('total_recommendations'))} artifacts, "
                        f"{_int(recommendations.get('total_audits'))} audits."
                    ),
                    visible_value=f"{_int(recommendations.get('total_recommendations'))} artifacts",
                ),
                _module_summary(
                    "model-router",
                    status=str(model_runs.get("status", "empty")),
                    source_label="PostgreSQL ModelRun summary",
                    detail=f"{_int(model_runs.get('total_model_runs'))} audited model runs.",
                    visible_value=f"{_int(model_runs.get('total_model_runs'))} model runs",
                ),
                _module_summary(
                    "evaluation-harness",
                    status=str(evaluations.get("status", "empty")),
                    source_label="PostgreSQL evaluation summary",
                    detail=(
                        f"{_int(evaluations.get('total_backtest_runs'))} backtests, "
                        f"{_int(evaluations.get('total_run_artifacts'))} run artifacts."
                    ),
                    visible_value=f"{_int(evaluations.get('total_backtest_runs'))} backtests",
                ),
                _module_summary(
                    "data-quality",
                    status=str(data_quality.get("status", "empty")),
                    source_label="PostgreSQL data-quality summary",
                    detail=f"{_int(data_quality.get('total_checks'))} data-quality checks.",
                    visible_value=f"{_int(data_quality.get('total_checks'))} checks",
                ),
                _module_summary(
                    "incidents",
                    status=str(incidents.get("status", "empty")),
                    source_label="PostgreSQL incident summary",
                    detail=(
                        f"{_int(incidents.get('open_incidents'))} open incidents, "
                        f"{_int(incidents.get('total_incidents'))} total."
                    ),
                    visible_value=f"{_int(incidents.get('open_incidents'))} open incidents",
                ),
            ]
        }

    def get_evidence_summary(self) -> dict[str, object]:
        return self.evidence_summary()

    def get_recommendation_summary(self) -> dict[str, object]:
        return self.recommendation_summary()

    def get_evaluation_summary(self) -> dict[str, object]:
        return self.evaluation_summary()

    def get_model_run_summary(self) -> dict[str, object]:
        return self.model_run_summary()

    def get_data_quality_summary(self) -> dict[str, object]:
        return self.data_quality_summary()

    def get_incident_summary(self) -> dict[str, object]:
        return self.incident_summary()

    def get_watchlist_summary(self) -> dict[str, object]:
        return self.watchlist_summary()

    def get_crawl_frontier_health(self) -> dict[str, object]:
        return self.crawl_frontier_health()

    def get_latest_equity_events(self) -> dict[str, object]:
        return self.latest_equity_events()

    def get_latest_signal_snapshots(self) -> dict[str, object]:
        return self.latest_signal_snapshots()

    def get_latest_advisory_run(self) -> dict[str, object]:
        return self.latest_advisory_run()

    def get_ticker_intelligence_summary(self, ticker: str) -> dict[str, object]:
        return self.ticker_intelligence_summary(ticker)

    def get_portfolio_summary(self) -> dict[str, object]:
        return self.portfolio_summary()

    def get_latest_recommendations(self, limit: int = 10) -> dict[str, object]:
        return self.latest_recommendations(limit)

    def evidence_summary(self) -> dict[str, object]:
        row = self._fetch_one(EVIDENCE_SUMMARY_SQL)
        total_items = _int(row.get("total_items"))
        total_chunks = _int(row.get("total_chunks"))
        total_claims = _int(row.get("total_claims"))
        return {
            "status": _status(total_items + total_chunks + total_claims),
            "total_items": total_items,
            "total_chunks": total_chunks,
            "total_claims": total_claims,
            "items_by_data_class": _count_map(row.get("items_by_data_class")),
            "latest_ingested_at": _iso_or_none(row.get("latest_ingested_at")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def recommendation_summary(self) -> dict[str, object]:
        row = self._fetch_one(RECOMMENDATION_SUMMARY_SQL)
        total_recommendations = _int(row.get("total_recommendations"))
        total_audits = _int(row.get("total_audits"))
        return {
            "status": _status(total_recommendations + total_audits),
            "total_recommendations": total_recommendations,
            "total_audits": total_audits,
            "schema_valid_audits": _int(row.get("schema_valid_audits")),
            "schema_invalid_audits": _int(row.get("schema_invalid_audits")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def model_run_summary(self) -> dict[str, object]:
        row = self._fetch_one(MODEL_RUN_SUMMARY_SQL)
        total_model_runs = _int(row.get("total_model_runs"))
        return {
            "status": _status(total_model_runs),
            "total_model_runs": total_model_runs,
            "runs_by_status": _count_map(row.get("runs_by_status")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def evaluation_summary(self) -> dict[str, object]:
        row = self._fetch_one(EVALUATION_SUMMARY_SQL)
        total_backtest_runs = _int(row.get("total_backtest_runs"))
        total_run_artifacts = _int(row.get("total_run_artifacts"))
        return {
            "status": _status(total_backtest_runs + total_run_artifacts),
            "total_backtest_runs": total_backtest_runs,
            "backtest_runs_by_status": _count_map(row.get("backtest_runs_by_status")),
            "total_run_artifacts": total_run_artifacts,
            "run_artifacts_by_status": _count_map(row.get("run_artifacts_by_status")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def data_quality_summary(self) -> dict[str, object]:
        row = self._fetch_one(DATA_QUALITY_SUMMARY_SQL)
        total_checks = _int(row.get("total_checks"))
        return {
            "status": _status(total_checks),
            "total_checks": total_checks,
            "checks_by_status": _count_map(row.get("checks_by_status")),
            "checks_by_severity": _count_map(row.get("checks_by_severity")),
            "latest_checked_at": _iso_or_none(row.get("latest_checked_at")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def incident_summary(self) -> dict[str, object]:
        row = self._fetch_one(INCIDENT_SUMMARY_SQL)
        total_incidents = _int(row.get("total_incidents"))
        open_incidents = _int(row.get("open_incidents"))
        return {
            "status": "degraded" if open_incidents > 0 else _status(total_incidents),
            "total_incidents": total_incidents,
            "incidents_by_severity": _count_map(row.get("incidents_by_severity")),
            "incidents_by_freeze_status": _count_map(
                row.get("incidents_by_freeze_status")
            ),
            "open_incidents": open_incidents,
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def watchlist_summary(self) -> dict[str, object]:
        row = self._fetch_one(WATCHLIST_SUMMARY_SQL)
        members = [
            _watchlist_member_payload(member)
            for member in self._fetch_many(WATCHLIST_MEMBERS_SQL, (25,))
        ]
        total_members = _int(row.get("total_members"))
        return {
            "status": _status(total_members),
            "total_members": total_members,
            "by_watchlist_status": _count_map(row.get("by_watchlist_status")),
            "latest_updated_at": _iso_or_none(row.get("latest_updated_at")),
            "members": members,
        }

    def crawl_frontier_health(self) -> dict[str, object]:
        rows = self._fetch_many(CRAWL_FRONTIER_HEALTH_SQL)
        datasets = [_crawl_frontier_payload(row) for row in rows]
        latest_available_at = _latest_iso(
            row.get("latest_available_at") for row in rows
        )
        return {
            "status": _status(len(datasets)),
            "total_datasets": len(datasets),
            "latest_available_at": latest_available_at,
            "datasets": datasets,
        }

    def latest_equity_events(self, limit: int = 10) -> dict[str, object]:
        rows = self._fetch_many(LATEST_EQUITY_EVENTS_SQL, (limit,))
        events = [_equity_event_payload(row) for row in rows]
        return {
            "status": _status(len(events)),
            "events": events,
        }

    def latest_signal_snapshots(self, limit: int = 10) -> dict[str, object]:
        rows = self._fetch_many(LATEST_SIGNAL_SNAPSHOTS_SQL, (limit,))
        snapshots = [_signal_snapshot_payload(row) for row in rows]
        return {
            "status": _status(len(snapshots)),
            "snapshots": snapshots,
        }

    def latest_advisory_run(self) -> dict[str, object]:
        row = self._fetch_one(
            LATEST_ADVISORY_RUN_SQL,
            ("local_advisory", "advisory_demo", "controlled_advisory_run"),
        )
        if not row:
            return {
                "status": "empty",
                "advisory_label": "advisory_only",
                "detail": "No local advisory run has been produced.",
            }
        return {
            "status": "available",
            "advisory_label": "advisory_only",
            "run_id": row.get("run_id"),
            "run_type": row.get("run_type"),
            "started_at": _iso_or_none(row.get("started_at")),
            "completed_at": _iso_or_none(row.get("completed_at")),
            "artifact_uri": row.get("artifact_uri"),
            "run_status": row.get("status"),
            "error_summary": row.get("error_summary"),
            "created_at": _iso_or_none(row.get("created_at")),
        }

    def portfolio_summary(self) -> dict[str, object]:
        snapshot_rows = self._fetch_many(LATEST_PORTFOLIO_SNAPSHOTS_SQL)
        if not snapshot_rows:
            return {
                "status": "empty",
                "advisory_label": "advisory_only",
                "snapshot_id": None,
                "as_of": None,
                "total_market_value": None,
                "cash_value": None,
                "previous_total_market_value": None,
                "day_delta_pct": None,
                "positions": [],
            }
        latest = snapshot_rows[0]
        previous = snapshot_rows[1] if len(snapshot_rows) > 1 else None
        latest_total = _decimal_or_none(latest.get("total_market_value"))
        previous_total = (
            _decimal_or_none(previous.get("total_market_value")) if previous else None
        )
        day_delta_pct: float | None = None
        if latest_total is not None and previous_total not in (None, 0):
            day_delta_pct = float((latest_total - previous_total) / previous_total)
        positions_rows = self._fetch_many(
            PORTFOLIO_SNAPSHOT_POSITIONS_SQL,
            (str(latest.get("snapshot_id")),),
        )
        positions = [_portfolio_position_payload(row) for row in positions_rows]
        return {
            "status": "available",
            "advisory_label": "advisory_only",
            "snapshot_id": str(latest.get("snapshot_id"))
            if latest.get("snapshot_id")
            else None,
            "as_of": _iso_or_none(latest.get("as_of")),
            "total_market_value": _decimal_text(latest.get("total_market_value")),
            "cash_value": _decimal_text(latest.get("cash_value")),
            "previous_total_market_value": (
                _decimal_text(previous.get("total_market_value")) if previous else None
            ),
            "day_delta_pct": day_delta_pct,
            "source": latest.get("source"),
            "positions": positions,
        }

    def latest_recommendations(self, limit: int = 10) -> dict[str, object]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        rows = self._fetch_many(LATEST_RECOMMENDATIONS_SQL, (limit,))
        items = [_recommendation_summary_payload(row) for row in rows]
        return {
            "status": _status(len(items)),
            "advisory_label": "advisory_only",
            "items": items,
        }

    def ticker_intelligence_summary(self, ticker: str) -> dict[str, object]:
        normalized_ticker = ticker.upper()
        watchlist = self._fetch_one(TICKER_WATCHLIST_SQL, (normalized_ticker,))
        signal = self._fetch_one(TICKER_SIGNAL_SQL, (normalized_ticker,))
        recommendation = self._fetch_one(
            TICKER_RECOMMENDATION_SQL, (normalized_ticker,)
        )
        events = self._fetch_many(TICKER_EVIDENCE_EVENTS_SQL, (normalized_ticker, 5))
        available_sections = sum(
            1 for section in (watchlist, signal, recommendation, events) if section
        )
        return {
            "status": _status(available_sections),
            "ticker": normalized_ticker,
            "watchlist": _watchlist_member_payload(watchlist) if watchlist else None,
            "latest_scores": _signal_snapshot_payload(signal) if signal else None,
            "latest_recommendation": _recommendation_trace_payload(recommendation)
            if recommendation
            else None,
            "latest_events": [_equity_event_payload(row) for row in events],
        }

    def overview(self) -> dict[str, object]:
        evidence = self.evidence_summary()
        recommendations = self.recommendation_summary()
        model_runs = self.model_run_summary()
        evaluations = self.evaluation_summary()
        data_quality = self.data_quality_summary()
        incidents = self.incident_summary()
        sections = (
            evidence,
            recommendations,
            model_runs,
            evaluations,
            data_quality,
            incidents,
        )
        return {
            "status": _overview_status(sections),
            "evidence": evidence,
            "recommendations": recommendations,
            "model_runs": model_runs,
            "evaluations": evaluations,
            "data_quality": data_quality,
            "incidents": incidents,
        }

    def _fetch_one(
        self,
        statement: str,
        params: tuple[object, ...] | None = None,
    ) -> dict[str, object]:
        rows = self._fetch_many(statement, params)
        if not rows:
            return {}
        return rows[0]

    def _fetch_many(
        self,
        statement: str,
        params: tuple[object, ...] | None = None,
    ) -> list[dict[str, object]]:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, params or ())
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        return [_row_to_dict(row, column_names) for row in rows]


def _overview_status(sections: tuple[dict[str, object], ...]) -> str:
    statuses = tuple(str(section.get("status", "empty")) for section in sections)
    if "degraded" in statuses:
        return "degraded"
    if any(status == "available" for status in statuses):
        return "available"
    return "empty"


def _module_summary(
    module_id: str,
    *,
    status: str,
    source_label: str,
    detail: str,
    visible_value: str,
) -> dict[str, object]:
    return {
        "id": module_id,
        "status": status,
        "source_type": "run_artifact",
        "source_label": source_label,
        "detail": detail,
        "visible_value": visible_value,
    }


def _watchlist_member_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "ticker": row.get("ticker"),
        "name": row.get("name"),
        "theme": row.get("theme"),
        "role": row.get("role"),
        "watchlist_status": row.get("watchlist_status"),
        "max_weight": _decimal_text(row.get("max_weight")),
        "liquidity_floor": _decimal_text(row.get("liquidity_floor")),
        "thesis_source": row.get("thesis_source"),
        "updated_at": _iso_or_none(row.get("updated_at")),
    }


def _crawl_frontier_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "dataset_name": row.get("dataset_name"),
        "source": row.get("source"),
        "latest_retrieved_at": _iso_or_none(row.get("latest_retrieved_at")),
        "latest_available_at": _iso_or_none(row.get("latest_available_at")),
        "latest_effective_at": _iso_or_none(row.get("latest_effective_at")),
        "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        "snapshot_count": _int(row.get("snapshot_count")),
        "row_count": _int(row.get("row_count")),
    }


def _equity_event_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "evidence_id": row.get("evidence_id"),
        "source_uri": row.get("source_uri"),
        "source_type": row.get("source_type"),
        "title": row.get("title"),
        "publisher": row.get("publisher"),
        "published_at": _iso_or_none(row.get("published_at")),
        "ingested_at": _iso_or_none(row.get("ingested_at")),
        "data_class": row.get("data_class"),
        "tickers": _text_list(row.get("tickers")),
        "themes": _text_list(row.get("themes")),
        "summary": row.get("summary"),
    }


def _signal_snapshot_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "signal_bundle_id": row.get("signal_bundle_id"),
        "ticker": row.get("ticker"),
        "as_of": _iso_or_none(row.get("as_of")),
        "sentiment_score": _decimal_text(row.get("forward_indicator_score")),
        "technical_score": _decimal_text(row.get("tactical_technical_score")),
        "fundamental_score": _decimal_text(row.get("strategic_thesis_score")),
        "portfolio_risk_score": _decimal_text(row.get("portfolio_risk_score")),
        "formula_versions": _json_value(row.get("formula_versions")),
        "input_snapshot_hash": row.get("input_snapshot_hash"),
        "created_at": _iso_or_none(row.get("created_at")),
    }


def _recommendation_trace_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "recommendation_id": row.get("recommendation_id"),
        "ticker_or_portfolio": row.get("ticker_or_portfolio"),
        "advisory_label": row.get("advisory_label"),
        "action": row.get("action"),
        "horizon": row.get("horizon"),
        "target_weights_id": row.get("target_weights_id"),
        "signal_bundle_id": row.get("signal_bundle_id"),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "model_run_ids": _text_list(row.get("model_run_ids")),
        "created_at": _iso_or_none(row.get("created_at")),
    }


def _portfolio_position_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "ticker": row.get("ticker"),
        "quantity": _decimal_text(row.get("quantity")),
        "market_price": _decimal_text(row.get("market_price")),
        "market_value": _decimal_text(row.get("market_value")),
        "portfolio_weight": _decimal_text(row.get("portfolio_weight")),
        "unrealized_pnl": _decimal_text(row.get("unrealized_pnl")),
    }


def _recommendation_summary_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "recommendation_id": row.get("recommendation_id"),
        "ticker_or_portfolio": row.get("ticker_or_portfolio"),
        "action": row.get("action"),
        "horizon": row.get("horizon"),
        "advisory_label": row.get("advisory_label"),
        "signal_bundle_id": row.get("signal_bundle_id"),
        "target_weights_id": row.get("target_weights_id"),
        "evidence_count": _int(row.get("evidence_count")),
        "model_run_count": _int(row.get("model_run_count")),
        "schema_valid": bool(row.get("schema_valid")),
        "created_at": _iso_or_none(row.get("created_at")),
    }


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _status(total_count: int) -> str:
    if total_count <= 0:
        return "empty"
    return "available"


def _int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _count_map(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _int(count) for key, count in value.items() if key is not None}


def _json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def _text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, tuple | list):
        return [str(item) for item in value]
    return [str(value)]


def _decimal_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _latest_iso(values: object) -> str | None:
    latest: str | None = None
    for value in values:  # type: ignore[assignment]
        current = _iso_or_none(value)
        if current is not None and (latest is None or current > latest):
            latest = current
    return latest


def _iso_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


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


__all__ = ["DashboardRepository"]
