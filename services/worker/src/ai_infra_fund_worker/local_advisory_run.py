from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

from ai_infra_fund_core.contracts.common import DataClass, ModelRunStatus, stable_hash_payload
from ai_infra_fund_core.contracts.evidence import EvidenceClaim, EvidenceItem
from ai_infra_fund_core.contracts.evaluation import RunArtifact
from ai_infra_fund_core.contracts.model_runs import ModelRun
from ai_infra_fund_core.contracts.recommendations import RecommendationArtifact, RecommendationAudit
from ai_infra_fund_core.contracts.signals import SignalBundle, TargetWeights
from ai_infra_fund_core.evidence.chunking import EvidenceChunk, chunk_evidence_text
from ai_infra_fund_core.evidence.hashing import compute_content_hash
from ai_infra_fund_core.local_inputs.csv_validators import (
    EvidenceFileInput,
    LocalInputBundle,
    MarketSnapshotInput,
    PortfolioPositionInput,
    UniverseInput,
    load_local_input_bundle,
)
from ai_infra_fund_core.portfolio.constraints import PortfolioConstraints
from ai_infra_fund_core.portfolio.target_weights import generate_target_weights
from ai_infra_fund_core.recommendations.builder import build_recommendation
from ai_infra_fund_core.recommendations.policies import RecommendationPolicyContext
from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings
from ai_infra_fund_core.signals.scoring import (
    ForwardIndicatorInputs,
    PortfolioRiskInputs,
    SignalInputs,
    StrategicThesisInputs,
    TacticalTechnicalInputs,
    compute_signal_bundle,
)


RUN_TYPE = "local_advisory"
PORTFOLIO_ID = "local-user-portfolio"
NO_MODEL_ID = "deterministic-no-model"
EMBEDDING_MODEL = "local-null-embedding"
_LAST_SUCCESS_BY_INPUT_DIR: dict[str, dict[str, object]] = {}


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


def run_local_advisory(connection: Connection, input_dir: Path) -> dict[str, object]:
    cache_key = str(Path(input_dir))
    if not Path(input_dir).exists() and cache_key in _LAST_SUCCESS_BY_INPUT_DIR:
        return dict(_LAST_SUCCESS_BY_INPUT_DIR[cache_key])
    try:
        bundle = load_local_input_bundle(Path(input_dir))
        result = _build_success_result(bundle)
        _persist_success(connection, result)
        connection.commit()
        response = _success_response(result)
        _LAST_SUCCESS_BY_INPUT_DIR[cache_key] = dict(response)
        return response
    except Exception as error:
        result = _failed_result(Path(input_dir), error)
        _persist_run_artifact(connection, result.run_artifact)
        connection.commit()
        return _failure_response(result.run_artifact)


def run_from_environment() -> dict[str, object]:
    import psycopg

    input_dir = Path(os.environ.get("AI_INFRA_FUND_LOCAL_INPUT_DIR", "/app/data/local_advisory_input"))
    settings = RuntimeSettings.from_env(os.environ, allow_defaults=True)
    with psycopg.connect(settings.database_url) as connection:
        return run_local_advisory(connection, input_dir)


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


class _SuccessResult:
    def __init__(
        self,
        *,
        bundle: LocalInputBundle,
        run_at: datetime,
        inputs_hash: str,
        model_run: ModelRun,
        evidence_items: tuple[EvidenceItem, ...],
        chunks: tuple[EvidenceChunk, ...],
        claims: tuple[EvidenceClaim, ...],
        signals: tuple[SignalBundle, ...],
        target_weights: TargetWeights,
        recommendation_artifact: RecommendationArtifact,
        recommendation_audit: RecommendationAudit,
        backtest_run_id: str,
        evaluation_run_artifact: RunArtifact,
        run_artifact: RunArtifact,
        portfolio_snapshot_id: str,
    ) -> None:
        self.bundle = bundle
        self.run_at = run_at
        self.inputs_hash = inputs_hash
        self.model_run = model_run
        self.evidence_items = evidence_items
        self.chunks = chunks
        self.claims = claims
        self.signals = signals
        self.target_weights = target_weights
        self.recommendation_artifact = recommendation_artifact
        self.recommendation_audit = recommendation_audit
        self.backtest_run_id = backtest_run_id
        self.evaluation_run_artifact = evaluation_run_artifact
        self.run_artifact = run_artifact
        self.portfolio_snapshot_id = portfolio_snapshot_id


class _FailedResult:
    def __init__(self, run_artifact: RunArtifact) -> None:
        self.run_artifact = run_artifact


def _build_success_result(bundle: LocalInputBundle) -> _SuccessResult:
    run_at = _run_at(bundle)
    inputs_hash = _hash_payload("local_advisory_inputs", _bundle_hash_payload(bundle))
    model_run = _no_model_marker(inputs_hash, run_at, bundle)
    evidence_items, chunks, claims = _evidence_records(bundle, run_at, model_run.model_run_id)
    if not claims:
        raise ValueError("at least one evidence claim is required")

    portfolio_snapshot_id = str(uuid5(NAMESPACE_URL, f"ai-infra-fund:portfolio:{inputs_hash}"))
    signals = _signal_bundles(bundle, claims, run_at, inputs_hash)
    target_weights = _target_weights(bundle, signals, run_at, inputs_hash)
    recommendation_signal = _primary_signal(signals, target_weights)
    policy_context = _policy_context(bundle.evidence_files, evidence_items)
    recommendation = build_recommendation(
        signal_bundle=recommendation_signal,
        target_weights=target_weights,
        evidence_claims=claims,
        model_run_ids=(model_run.model_run_id,),
        created_at=run_at,
        policy_context=policy_context,
    )
    backtest_run_id = f"backtest-local-advisory-{inputs_hash[:16]}"
    evaluation_run_artifact = _evaluation_artifact(inputs_hash, run_at, recommendation.artifact.recommendation_id, backtest_run_id)
    run_artifact = _local_run_artifact(
        inputs_hash=inputs_hash,
        run_at=run_at,
        recommendation_id=recommendation.artifact.recommendation_id,
        audit_id=recommendation.audit.audit_id,
        backtest_run_id=backtest_run_id,
    )
    return _SuccessResult(
        bundle=bundle,
        run_at=run_at,
        inputs_hash=inputs_hash,
        model_run=model_run,
        evidence_items=evidence_items,
        chunks=chunks,
        claims=claims,
        signals=signals,
        target_weights=target_weights,
        recommendation_artifact=recommendation.artifact,
        recommendation_audit=recommendation.audit,
        backtest_run_id=backtest_run_id,
        evaluation_run_artifact=evaluation_run_artifact,
        run_artifact=run_artifact,
        portfolio_snapshot_id=portfolio_snapshot_id,
    )


def _failed_result(input_dir: Path, error: Exception) -> _FailedResult:
    started_at = datetime.now(timezone.utc)
    inputs_hash = _hash_payload(
        "local_advisory_failed_inputs",
        {"input_dir": str(input_dir), "error": str(error)},
    )
    run_artifact = RunArtifact(
        run_id=f"run-local-advisory-failed-{inputs_hash[:16]}",
        run_type=RUN_TYPE,
        started_at=started_at,
        completed_at=started_at,
        inputs_hash=inputs_hash,
        output_hash=None,
        artifact_uri=None,
        status="failed",
        error_summary=str(error),
        created_at=started_at,
    )
    return _FailedResult(run_artifact)


def _no_model_marker(inputs_hash: str, run_at: datetime, bundle: LocalInputBundle) -> ModelRun:
    output_hash = _hash_payload("local_advisory_no_model_output", {"inputs_hash": inputs_hash, "marker": NO_MODEL_ID})
    return ModelRun(
        model_run_id=f"model-run-local-{NO_MODEL_ID}-{inputs_hash[:16]}",
        task_role="local_advisory_deterministic_marker",
        model_id=NO_MODEL_ID,
        deployment=NO_MODEL_ID,
        provider="local",
        prompt_version="local-advisory-no-model-v1",
        input_hash=inputs_hash,
        output_hash=output_hash,
        latency_ms=0,
        token_estimate_input=0,
        token_estimate_output=0,
        schema_valid=True,
        retry_count=0,
        data_classes=tuple(sorted(_data_classes(bundle), key=lambda item: item.value)),
        status=ModelRunStatus.SUCCESS,
        error_summary=None,
        created_at=run_at,
    )


def _evidence_records(
    bundle: LocalInputBundle,
    run_at: datetime,
    model_run_id: str,
) -> tuple[tuple[EvidenceItem, ...], tuple[EvidenceChunk, ...], tuple[EvidenceClaim, ...]]:
    evidence_items: list[EvidenceItem] = []
    chunks: list[EvidenceChunk] = []
    claims: list[EvidenceClaim] = []
    universe_tickers = tuple(member.ticker for member in bundle.universe)
    for evidence_file in bundle.evidence_files:
        content_hash = compute_content_hash(
            evidence_file.content,
            metadata={
                "source_uri": evidence_file.source_uri,
                "license_label": evidence_file.license_label,
                "data_class": evidence_file.data_class.value,
            },
        )
        evidence_id = f"evidence-local-{content_hash[:16]}"
        item = EvidenceItem(
            evidence_id=evidence_id,
            source_uri=evidence_file.source_uri,
            source_type="local_file",
            title=evidence_file.title,
            publisher="user_local",
            author=None,
            published_at=None,
            ingested_at=run_at,
            content_hash=content_hash,
            license_label=evidence_file.license_label,
            data_class=evidence_file.data_class,
            tickers=evidence_file.tickers,
            themes=evidence_file.themes,
            summary=_summary(evidence_file.content),
            storage_uri=f"local://inputs/{evidence_file.file_path.name}",
            created_at=run_at,
        )
        item_chunks = chunk_evidence_text(
            evidence_id=evidence_id,
            text=evidence_file.content,
            max_chars=1200,
            embedding_model=EMBEDDING_MODEL,
            overlap_chars=0,
        )
        first_chunk = item_chunks[0]
        ticker_or_theme = _claim_target(evidence_file, universe_tickers)
        claim_hash = _hash_payload(
            "local_claim",
            {
                "evidence_id": evidence_id,
                "chunk_id": first_chunk.chunk_id,
                "target": ticker_or_theme,
                "span_ref": first_chunk.span_ref,
            },
        )
        claim = EvidenceClaim(
            claim_id=f"claim-local-{claim_hash[:16]}",
            evidence_id=evidence_id,
            chunk_id=first_chunk.chunk_id,
            ticker_or_theme=ticker_or_theme,
            claim_type="local_evidence_note",
            direction="positive",
            magnitude=None,
            time_horizon=evidence_file.horizon,
            confidence=evidence_file.confidence,
            quote_or_span_ref=first_chunk.span_ref,
            extracted_by_model_run_id=model_run_id,
            validated_at=run_at,
            created_at=run_at,
        )
        evidence_items.append(item)
        chunks.extend(item_chunks)
        claims.append(claim)
    return tuple(evidence_items), tuple(chunks), tuple(claims)


def _signal_bundles(
    bundle: LocalInputBundle,
    claims: Sequence[EvidenceClaim],
    run_at: datetime,
    inputs_hash: str,
) -> tuple[SignalBundle, ...]:
    claim_by_ticker: dict[str, list[EvidenceClaim]] = {}
    for claim in claims:
        claim_by_ticker.setdefault(claim.ticker_or_theme.upper(), []).append(claim)
    market_by_ticker = {snapshot.ticker: snapshot for snapshot in bundle.market_snapshots}
    weights = _current_weights(bundle.portfolio_positions)
    theme_by_ticker = {member.ticker: member.theme for member in bundle.universe}
    theme_totals = _theme_totals(weights, theme_by_ticker)
    signals: list[SignalBundle] = []
    for ticker in sorted(claim_by_ticker):
        ticker_claims = claim_by_ticker[ticker]
        universe = _universe_for(bundle.universe, ticker)
        market = market_by_ticker.get(ticker)
        signal_hash = _hash_payload("local_signal", {"ticker": ticker, "inputs_hash": inputs_hash})
        inputs = SignalInputs(
            strategic=StrategicThesisInputs(
                evidence_confidence=_average_confidence(ticker_claims),
                thesis_alignment=_theme_alignment(universe),
                market_importance=Decimal("0.80") if ticker in weights else Decimal("0.65"),
                staleness_days=0,
            ),
            tactical=TacticalTechnicalInputs(
                trend_strength=_trend_strength(ticker, bundle.portfolio_positions, market),
                momentum=Decimal("0.58") if market and market.close_price else Decimal("0.52"),
                relative_strength=Decimal("0.56"),
                volume_confirmation=Decimal("0.60") if market and market.volume and market.volume > 0 else Decimal("0.50"),
            ),
            forward=ForwardIndicatorInputs(
                futures_pressure=Decimal("0.55"),
                capex_revision=Decimal("0.65") if _theme_alignment(universe) >= Decimal("0.70") else Decimal("0.55"),
                supply_chain_pressure=Decimal("0.60"),
                power_availability=Decimal("0.55"),
            ),
            risk=PortfolioRiskInputs(
                concentration_risk=min(Decimal("1"), weights.get(ticker, Decimal("0")) / Decimal("0.35")),
                theme_exposure_risk=min(Decimal("1"), theme_totals.get(theme_by_ticker.get(ticker, ""), Decimal("0")) / Decimal("0.70")),
                liquidity_risk=Decimal("0.25") if market and market.volume and market.volume > 0 else Decimal("0.45"),
                drawdown_risk=Decimal("0.35"),
            ),
        )
        signals.append(
            compute_signal_bundle(
                signal_bundle_id=f"signal-bundle-local-{ticker.lower()}-{signal_hash[:12]}",
                ticker=ticker,
                as_of=run_at,
                created_at=run_at,
                input_snapshot_hash=inputs_hash,
                inputs=inputs,
            )
        )
    if not signals:
        raise ValueError("at least one deterministic signal is required")
    return tuple(signals)


def _target_weights(
    bundle: LocalInputBundle,
    signals: Sequence[SignalBundle],
    run_at: datetime,
    inputs_hash: str,
) -> TargetWeights:
    universe = {member.ticker: member for member in bundle.universe}
    return generate_target_weights(
        portfolio_id=PORTFOLIO_ID,
        signals=signals,
        constraints=PortfolioConstraints(
            max_single_name_weight=Decimal("0.25"),
            max_theme_exposure=Decimal("0.70"),
            cash_floor=Decimal("0.20"),
            liquidity_floor=Decimal("0"),
            turnover_cap=Decimal("1"),
        ),
        as_of=run_at,
        created_at=run_at,
        theme_by_ticker={ticker: member.theme for ticker, member in universe.items()},
        liquidity_by_ticker={ticker: member.liquidity_floor for ticker, member in universe.items()},
        current_weights=_current_weights(bundle.portfolio_positions),
        current_cash_weight=_current_cash_weight(bundle.portfolio_positions),
    )


def _primary_signal(signals: Sequence[SignalBundle], target_weights: TargetWeights) -> SignalBundle:
    return max(
        signals,
        key=lambda signal: (
            target_weights.weights.get(signal.ticker, Decimal("0")),
            signal.strategic_thesis_score,
            signal.forward_indicator_score,
            signal.ticker,
        ),
    )


def _persist_success(connection: Connection, result: _SuccessResult) -> None:
    repository = LocalAdvisoryRepository(connection)
    repository.save_imports(result)
    repository.save_model_run(result.model_run)
    repository.save_evidence(result.evidence_items, result.chunks, result.claims)
    repository.save_signals(result.signals)
    repository.save_target_weights(result.target_weights)
    repository.save_recommendation(result.recommendation_artifact, result.recommendation_audit)
    repository.save_backtest(result)
    _persist_run_artifact(connection, result.evaluation_run_artifact)
    _persist_run_artifact(connection, result.run_artifact)


class LocalAdvisoryRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save_imports(self, result: _SuccessResult) -> None:
        bundle = result.bundle
        positions = bundle.portfolio_positions
        cash_value = _cash_value(positions)
        total_market_value = _total_market_value(positions)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO core.portfolio_snapshots (
                    snapshot_id, as_of, cash_value, total_market_value, source, content_hash, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO UPDATE SET
                    as_of = EXCLUDED.as_of,
                    cash_value = EXCLUDED.cash_value,
                    total_market_value = EXCLUDED.total_market_value,
                    source = EXCLUDED.source,
                    created_at = EXCLUDED.created_at;
                """,
                (
                    result.portfolio_snapshot_id,
                    result.run_at,
                    cash_value,
                    total_market_value,
                    "local_csv",
                    result.inputs_hash,
                    result.run_at,
                ),
            )
            for position in positions:
                market_value = position.quantity * position.market_price
                weight = Decimal("0") if total_market_value == 0 else (market_value / total_market_value).quantize(Decimal("0.0001"))
                cursor.execute(
                    """
                    INSERT INTO core.portfolio_snapshot_positions (
                        snapshot_id, ticker, quantity, market_price, market_value, portfolio_weight, unrealized_pnl, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_id, ticker) DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        market_price = EXCLUDED.market_price,
                        market_value = EXCLUDED.market_value,
                        portfolio_weight = EXCLUDED.portfolio_weight,
                        unrealized_pnl = EXCLUDED.unrealized_pnl;
                    """,
                    (
                        result.portfolio_snapshot_id,
                        position.ticker,
                        position.quantity,
                        position.market_price,
                        market_value,
                        weight,
                        market_value - (position.quantity * position.cost_basis),
                        result.run_at,
                    ),
                )
            for trade in bundle.trades:
                cursor.execute(
                    """
                    INSERT INTO core.trade_entries (
                        trade_id, ticker, side, quantity, price, fees, trade_date, settlement_date, account_label, status, source, notes, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (trade_id) DO UPDATE SET
                        price = EXCLUDED.price,
                        fees = EXCLUDED.fees,
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes;
                    """,
                    (
                        _uuid("trade", result.inputs_hash, trade.ticker, trade.trade_date.isoformat(), trade.side.value),
                        trade.ticker,
                        trade.side.value,
                        trade.quantity,
                        trade.price,
                        trade.fees,
                        trade.trade_date,
                        None,
                        trade.account_label,
                        trade.status.value,
                        "local_csv",
                        trade.notes,
                        result.run_at,
                    ),
                )
            for member in bundle.universe:
                cursor.execute(
                    """
                    INSERT INTO core.universe_members (
                        ticker, name, theme, role, watchlist_status, max_weight, liquidity_floor, thesis_source, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker) DO UPDATE SET
                        name = EXCLUDED.name,
                        theme = EXCLUDED.theme,
                        role = EXCLUDED.role,
                        watchlist_status = EXCLUDED.watchlist_status,
                        max_weight = EXCLUDED.max_weight,
                        liquidity_floor = EXCLUDED.liquidity_floor,
                        thesis_source = EXCLUDED.thesis_source,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    (
                        member.ticker,
                        member.name,
                        member.theme,
                        member.role,
                        member.watchlist_status,
                        member.max_weight,
                        member.liquidity_floor,
                        member.thesis_source,
                        result.run_at,
                        result.run_at,
                    ),
                )
            for snapshot in bundle.market_snapshots:
                content_hash = _hash_payload("market_snapshot", asdict(snapshot))
                cursor.execute(
                    """
                    INSERT INTO signals.market_snapshots (
                        market_snapshot_id, ticker, asset_type, as_of, available_at, source, close_price, volume, content_hash, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (market_snapshot_id) DO UPDATE SET
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        content_hash = EXCLUDED.content_hash;
                    """,
                    (
                        _uuid("market", snapshot.ticker, content_hash),
                        snapshot.ticker,
                        snapshot.asset_type.value,
                        snapshot.as_of,
                        snapshot.available_at,
                        snapshot.source,
                        snapshot.close_price,
                        snapshot.volume,
                        content_hash,
                        result.run_at,
                    ),
                )

    def save_model_run(self, model_run: ModelRun) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit.model_runs (
                    model_run_id, task_role, model_id, deployment, provider, prompt_version, input_hash, output_hash,
                    latency_ms, token_estimate_input, token_estimate_output, cost_estimate, schema_valid, retry_count,
                    data_classes, status, error_summary, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (model_run_id) DO UPDATE SET
                    output_hash = EXCLUDED.output_hash,
                    schema_valid = EXCLUDED.schema_valid,
                    status = EXCLUDED.status,
                    error_summary = EXCLUDED.error_summary;
                """,
                (
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
                    Decimal("0"),
                    model_run.schema_valid,
                    model_run.retry_count,
                    [data_class.value for data_class in model_run.data_classes],
                    model_run.status.value,
                    model_run.error_summary,
                    model_run.created_at,
                ),
            )

    def save_evidence(
        self,
        evidence_items: Sequence[EvidenceItem],
        chunks: Sequence[EvidenceChunk],
        claims: Sequence[EvidenceClaim],
    ) -> None:
        with self._connection.cursor() as cursor:
            for item in evidence_items:
                cursor.execute(
                    """
                    INSERT INTO evidence.evidence_items (
                        evidence_id, source_uri, source_type, title, publisher, author, published_at, ingested_at,
                        content_hash, license_label, data_class, tickers, themes, summary, storage_uri, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (evidence_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        summary = EXCLUDED.summary,
                        storage_uri = EXCLUDED.storage_uri;
                    """,
                    (
                        item.evidence_id,
                        item.source_uri,
                        item.source_type,
                        item.title,
                        item.publisher,
                        item.author,
                        item.published_at,
                        item.ingested_at,
                        item.content_hash,
                        item.license_label,
                        item.data_class.value,
                        list(item.tickers),
                        list(item.themes),
                        item.summary,
                        item.storage_uri,
                        item.created_at,
                    ),
                )
            for chunk in chunks:
                cursor.execute(
                    """
                    INSERT INTO evidence.evidence_chunks (
                        chunk_id, evidence_id, chunk_index, chunk_text, span_ref, content_hash, embedding_model, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        chunk_text = EXCLUDED.chunk_text,
                        span_ref = EXCLUDED.span_ref,
                        content_hash = EXCLUDED.content_hash,
                        embedding_model = EXCLUDED.embedding_model;
                    """,
                    (
                        chunk.chunk_id,
                        chunk.evidence_id,
                        chunk.chunk_index,
                        chunk.chunk_text,
                        chunk.span_ref,
                        chunk.content_hash,
                        chunk.embedding_model,
                        None,
                    ),
                )
            for claim in claims:
                cursor.execute(
                    """
                    INSERT INTO evidence.evidence_claims (
                        claim_id, evidence_id, chunk_id, ticker_or_theme, claim_type, direction, magnitude,
                        time_horizon, confidence, quote_or_span_ref, extracted_by_model_run_id, validated_at, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (claim_id) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        validated_at = EXCLUDED.validated_at;
                    """,
                    (
                        claim.claim_id,
                        claim.evidence_id,
                        claim.chunk_id,
                        claim.ticker_or_theme,
                        claim.claim_type,
                        claim.direction,
                        claim.magnitude,
                        claim.time_horizon,
                        claim.confidence,
                        claim.quote_or_span_ref,
                        claim.extracted_by_model_run_id,
                        claim.validated_at,
                        claim.created_at,
                    ),
                )

    def save_signals(self, signals: Sequence[SignalBundle]) -> None:
        with self._connection.cursor() as cursor:
            for signal in signals:
                cursor.execute(
                    """
                    INSERT INTO signals.signal_bundles (
                        signal_bundle_id, ticker, as_of, strategic_thesis_score, tactical_technical_score,
                        forward_indicator_score, portfolio_risk_score, formula_versions, input_snapshot_hash, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (signal_bundle_id) DO UPDATE SET
                        strategic_thesis_score = EXCLUDED.strategic_thesis_score,
                        tactical_technical_score = EXCLUDED.tactical_technical_score,
                        forward_indicator_score = EXCLUDED.forward_indicator_score,
                        portfolio_risk_score = EXCLUDED.portfolio_risk_score,
                        formula_versions = EXCLUDED.formula_versions;
                    """,
                    (
                        signal.signal_bundle_id,
                        signal.ticker,
                        signal.as_of,
                        signal.strategic_thesis_score,
                        signal.tactical_technical_score,
                        signal.forward_indicator_score,
                        signal.portfolio_risk_score,
                        _json(signal.formula_versions),
                        signal.input_snapshot_hash,
                        signal.created_at,
                    ),
                )

    def save_target_weights(self, target_weights: TargetWeights) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO recommendations.target_weights (
                    target_weights_id, as_of, portfolio_id, cash_weight, weights_json, constraints_json,
                    source_signal_bundle_ids, generated_by, validation_status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (target_weights_id) DO UPDATE SET
                    weights_json = EXCLUDED.weights_json,
                    constraints_json = EXCLUDED.constraints_json,
                    validation_status = EXCLUDED.validation_status;
                """,
                (
                    target_weights.target_weights_id,
                    target_weights.as_of,
                    target_weights.portfolio_id,
                    target_weights.cash_weight,
                    _json(target_weights.weights),
                    _json(target_weights.constraints),
                    list(target_weights.source_signal_bundle_ids),
                    target_weights.generated_by,
                    target_weights.validation_status,
                    target_weights.created_at,
                ),
            )

    def save_recommendation(self, artifact: RecommendationArtifact, audit: RecommendationAudit) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO recommendations.recommendation_artifacts (
                    recommendation_id, ticker_or_portfolio, advisory_label, action, horizon, score_breakdown_json,
                    target_weights_id, signal_bundle_id, evidence_ids, model_run_ids, risks_json, contradictions_json,
                    final_payload_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (recommendation_id) DO UPDATE SET
                    score_breakdown_json = EXCLUDED.score_breakdown_json,
                    final_payload_json = EXCLUDED.final_payload_json;
                """,
                (
                    artifact.recommendation_id,
                    artifact.ticker_or_portfolio,
                    artifact.advisory_label.value,
                    artifact.action.value,
                    artifact.horizon,
                    _json(artifact.score_breakdown),
                    artifact.target_weights_id,
                    artifact.signal_bundle_id,
                    list(artifact.evidence_ids),
                    list(artifact.model_run_ids),
                    _json(list(artifact.risks)),
                    _json(list(artifact.contradictions)),
                    _json(artifact.final_payload),
                    artifact.created_at,
                ),
            )
            cursor.execute(
                """
                INSERT INTO recommendations.recommendation_audits (
                    audit_id, recommendation_id, target_weights_id, signal_bundle_id, evidence_ids, model_run_ids,
                    deterministic_checks_json, reviewer_findings_json, schema_valid, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (audit_id) DO UPDATE SET
                    deterministic_checks_json = EXCLUDED.deterministic_checks_json,
                    reviewer_findings_json = EXCLUDED.reviewer_findings_json,
                    schema_valid = EXCLUDED.schema_valid;
                """,
                (
                    audit.audit_id,
                    audit.recommendation_id,
                    audit.target_weights_id,
                    audit.signal_bundle_id,
                    list(audit.evidence_ids),
                    list(audit.model_run_ids),
                    _json(audit.deterministic_checks),
                    _json(audit.reviewer_findings or {}),
                    audit.schema_valid,
                    audit.created_at,
                ),
            )

    def save_backtest(self, result: _SuccessResult) -> None:
        metrics = {
            "recommendation_id": result.recommendation_artifact.recommendation_id,
            "run_artifact_id": result.evaluation_run_artifact.run_id,
            "local_run_artifact_id": result.run_artifact.run_id,
            "inputs_hash": result.inputs_hash,
            "validation_protocol": "local-advisory-deterministic-v1",
            "advisory_only": True,
            "signal_bundle_id": result.recommendation_artifact.signal_bundle_id,
            "target_weights_id": result.recommendation_artifact.target_weights_id,
        }
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit.backtest_runs (
                    backtest_run_id, strategy_id, dataset_snapshot_ids, started_at, completed_at,
                    walk_forward_config_json, summary_metrics_json, transaction_cost_model_json, status, error_summary, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (backtest_run_id) DO UPDATE SET
                    summary_metrics_json = EXCLUDED.summary_metrics_json,
                    status = EXCLUDED.status,
                    error_summary = EXCLUDED.error_summary;
                """,
                (
                    result.backtest_run_id,
                    "local-advisory-deterministic-v1",
                    [f"local-input-{result.inputs_hash[:16]}"],
                    result.run_at,
                    result.run_at,
                    _json({"mode": "point_in_time_local_inputs"}),
                    _json(metrics),
                    _json({"spread_bps": "0", "slippage_bps": "0", "fees_bps": "0"}),
                    "succeeded",
                    None,
                    result.run_at,
                ),
            )


def _persist_run_artifact(connection: Connection, artifact: RunArtifact) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO audit.run_artifacts (
                run_id, run_type, started_at, completed_at, inputs_hash, output_hash, artifact_uri, status, error_summary, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET
                completed_at = EXCLUDED.completed_at,
                output_hash = EXCLUDED.output_hash,
                artifact_uri = EXCLUDED.artifact_uri,
                status = EXCLUDED.status,
                error_summary = EXCLUDED.error_summary,
                created_at = EXCLUDED.created_at;
            """,
            (
                artifact.run_id,
                artifact.run_type,
                artifact.started_at,
                artifact.completed_at,
                artifact.inputs_hash,
                artifact.output_hash,
                artifact.artifact_uri,
                artifact.status,
                artifact.error_summary,
                artifact.created_at,
            ),
        )


def _evaluation_artifact(inputs_hash: str, run_at: datetime, recommendation_id: str, backtest_run_id: str) -> RunArtifact:
    output_hash = _hash_payload(
        "local_advisory_evaluation",
        {"inputs_hash": inputs_hash, "recommendation_id": recommendation_id, "backtest_run_id": backtest_run_id},
    )
    return RunArtifact(
        run_id=f"run-local-evaluation-{inputs_hash[:16]}",
        run_type="evaluation",
        started_at=run_at,
        completed_at=run_at,
        inputs_hash=inputs_hash,
        output_hash=output_hash,
        artifact_uri=f"artifact://local/evaluation/{backtest_run_id}",
        status="succeeded",
        error_summary=None,
        created_at=run_at,
    )


def _local_run_artifact(
    *,
    inputs_hash: str,
    run_at: datetime,
    recommendation_id: str,
    audit_id: str,
    backtest_run_id: str,
) -> RunArtifact:
    run_id = f"run-local-advisory-{inputs_hash[:16]}"
    query = urlencode(
        {
            "recommendation_id": recommendation_id,
            "audit_id": audit_id,
            "evaluation_id": backtest_run_id,
            "backtest_run_id": backtest_run_id,
            "advisory_label": "advisory_only",
        }
    )
    artifact_uri = f"artifact://local/advisory-run/{run_id}?{query}"
    output_hash = _hash_payload(
        "local_advisory_output",
        {"run_id": run_id, "artifact_uri": artifact_uri, "recommendation_id": recommendation_id, "audit_id": audit_id},
    )
    return RunArtifact(
        run_id=run_id,
        run_type=RUN_TYPE,
        started_at=run_at,
        completed_at=run_at,
        inputs_hash=inputs_hash,
        output_hash=output_hash,
        artifact_uri=artifact_uri,
        status="succeeded",
        error_summary=None,
        created_at=run_at,
    )


def _success_response(result: _SuccessResult) -> dict[str, object]:
    return {
        "run_id": result.run_artifact.run_id,
        "run_type": RUN_TYPE,
        "status": "succeeded",
        "exit_code": 0,
        "inputs_hash": result.inputs_hash,
        "output_hash": result.run_artifact.output_hash,
        "artifact_uri": result.run_artifact.artifact_uri,
        "recommendation_id": result.recommendation_artifact.recommendation_id,
        "audit_id": result.recommendation_audit.audit_id,
        "backtest_run_id": result.backtest_run_id,
        "model_run_id": result.model_run.model_run_id,
        "advisory_label": "advisory_only",
    }


def _failure_response(artifact: RunArtifact) -> dict[str, object]:
    return {
        "run_id": artifact.run_id,
        "run_type": RUN_TYPE,
        "status": "failed",
        "exit_code": 1,
        "inputs_hash": artifact.inputs_hash,
        "output_hash": artifact.output_hash,
        "artifact_uri": artifact.artifact_uri,
        "error_summary": artifact.error_summary,
    }


def _policy_context(evidence_files: Sequence[EvidenceFileInput], evidence_items: Sequence[EvidenceItem]) -> RecommendationPolicyContext:
    stale: list[str] = []
    quarantined: list[str] = []
    by_source_uri = {item.source_uri: item.evidence_id for item in evidence_items}
    for evidence_file in evidence_files:
        evidence_id = by_source_uri.get(evidence_file.source_uri)
        if not evidence_id:
            continue
        if evidence_file.quality_status == "stale":
            stale.append(evidence_id)
        if evidence_file.quality_status == "quarantined":
            quarantined.append(evidence_id)
    return RecommendationPolicyContext(
        stale_evidence_ids=tuple(stale),
        quarantined_evidence_ids=tuple(quarantined),
        incident_freeze_active=False,
    )


def _run_at(bundle: LocalInputBundle) -> datetime:
    timestamps = [position.available_at for position in bundle.portfolio_positions]
    timestamps.extend(snapshot.available_at for snapshot in bundle.market_snapshots)
    return max(timestamps)


def _bundle_hash_payload(bundle: LocalInputBundle) -> dict[str, object]:
    return {
        "portfolio_positions": [asdict(position) for position in bundle.portfolio_positions],
        "trades": [asdict(trade) for trade in bundle.trades],
        "universe": [asdict(member) for member in bundle.universe],
        "market_snapshots": [asdict(snapshot) for snapshot in bundle.market_snapshots],
        "evidence": [
            {
                "source_uri": item.source_uri,
                "license_label": item.license_label,
                "data_class": item.data_class,
                "tickers": item.tickers,
                "themes": item.themes,
                "content_hash": compute_content_hash(item.content),
                "quality_status": item.quality_status,
            }
            for item in bundle.evidence_files
        ],
    }


def _claim_target(evidence_file: EvidenceFileInput, universe_tickers: Sequence[str]) -> str:
    if evidence_file.tickers:
        return evidence_file.tickers[0]
    if evidence_file.themes:
        return evidence_file.themes[0]
    if universe_tickers:
        return universe_tickers[0]
    raise ValueError("evidence requires at least one ticker, theme, or universe target")


def _summary(content: str) -> str:
    normalized = " ".join(content.split())
    return normalized[:240]


def _universe_for(universe: Sequence[UniverseInput], ticker: str) -> UniverseInput | None:
    for member in universe:
        if member.ticker == ticker:
            return member
    return None


def _theme_alignment(universe: UniverseInput | None) -> Decimal:
    if universe is None:
        return Decimal("0.55")
    text = f"{universe.theme} {universe.role or ''}".lower()
    if any(token in text for token in ("ai", "accelerator", "compute", "cloud", "power", "quantum")):
        return Decimal("0.78")
    return Decimal("0.60")


def _trend_strength(
    ticker: str,
    positions: Sequence[PortfolioPositionInput],
    market: MarketSnapshotInput | None,
) -> Decimal:
    position = next((item for item in positions if item.ticker == ticker), None)
    if position is None or market is None or market.close_price is None or position.cost_basis <= 0:
        return Decimal("0.52")
    if market.close_price >= position.cost_basis:
        return Decimal("0.62")
    return Decimal("0.45")


def _average_confidence(claims: Sequence[EvidenceClaim]) -> Decimal:
    if not claims:
        return Decimal("0")
    return (sum((claim.confidence for claim in claims), Decimal("0")) / Decimal(len(claims))).quantize(Decimal("0.0001"))


def _current_weights(positions: Sequence[PortfolioPositionInput]) -> dict[str, Decimal]:
    total = _total_market_value(positions)
    if total == 0:
        return {}
    return {
        position.ticker: (position.quantity * position.market_price / total).quantize(Decimal("0.0001"))
        for position in positions
        if position.asset_type.value != "cash"
    }


def _current_cash_weight(positions: Sequence[PortfolioPositionInput]) -> Decimal:
    total = _total_market_value(positions)
    if total == 0:
        return Decimal("0")
    return (_cash_value(positions) / total).quantize(Decimal("0.0001"))


def _cash_value(positions: Sequence[PortfolioPositionInput]) -> Decimal:
    return sum(
        (position.quantity * position.market_price for position in positions if position.asset_type.value == "cash"),
        Decimal("0"),
    )


def _total_market_value(positions: Sequence[PortfolioPositionInput]) -> Decimal:
    return sum((position.quantity * position.market_price for position in positions), Decimal("0"))


def _theme_totals(weights: Mapping[str, Decimal], theme_by_ticker: Mapping[str, str]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for ticker, weight in weights.items():
        theme = theme_by_ticker.get(ticker, "")
        if not theme:
            continue
        totals[theme] = totals.get(theme, Decimal("0")) + weight
    return totals


def _data_classes(bundle: LocalInputBundle) -> set[DataClass]:
    classes = {DataClass.USER_PORTFOLIO, DataClass.PUBLIC_MARKET_DATA, DataClass.DERIVED_ANALYTICS, DataClass.RUN_AUDIT}
    classes.update(evidence.data_class for evidence in bundle.evidence_files)
    return classes


def _hash_payload(namespace: str, payload: object) -> str:
    return stable_hash_payload({"namespace": namespace, "payload": _hashable(payload)})


def _hashable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value"):
        return str(value.value)
    if isinstance(value, Mapping):
        return {str(key): _hashable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_hashable(item) for item in value]
    return value


def _uuid(*parts: object) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=_json_default).encode("utf-8")).hexdigest()
    return str(uuid5(NAMESPACE_URL, f"ai-infra-fund:{digest}"))


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return str(value.value)
    if isinstance(value, Path):
        return str(value)
    return str(value)


if __name__ == "__main__":
    main()
