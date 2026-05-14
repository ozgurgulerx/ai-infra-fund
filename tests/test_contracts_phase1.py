from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import (  # noqa: E402
    AdvisoryLabel,
    AssetType,
    DataClass,
    DataQualityStatus,
    IncidentSeverity,
    ModelRunStatus,
    RecommendationAction,
    TradeSide,
    TradeStatus,
    stable_hash_payload,
)
from ai_infra_fund_core.contracts.evaluation import BacktestRun, RunArtifact  # noqa: E402
from ai_infra_fund_core.contracts.evidence import (  # noqa: E402
    DatasetSnapshot,
    EvidenceClaim,
    EvidenceItem,
    FeatureSet,
)
from ai_infra_fund_core.contracts.governance import (  # noqa: E402
    DataQualityCheck,
    IncidentRecord,
    ModelInventoryEntry,
)
from ai_infra_fund_core.contracts.model_runs import ModelRun  # noqa: E402
from ai_infra_fund_core.contracts.portfolio import (  # noqa: E402
    Position,
    TradeEntry,
    TradeJournal,
    UniverseMember,
)
from ai_infra_fund_core.contracts.recommendations import (  # noqa: E402
    RecommendationArtifact,
    RecommendationAudit,
)
from ai_infra_fund_core.contracts.signals import (  # noqa: E402
    ImplementationEstimate,
    SignalBundle,
    TargetWeights,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 12, 5, tzinfo=timezone.utc)


class Phase1ContractTests(unittest.TestCase):
    def test_all_contracts_are_dataclasses_with_required_ids(self) -> None:
        samples = [
            self.position(),
            self.trade_entry(),
            self.trade_journal(),
            self.universe_member(),
            self.dataset_snapshot(),
            self.evidence_item(),
            self.evidence_claim(),
            self.feature_set(),
            self.model_run(),
            self.signal_bundle(),
            self.target_weights(),
            self.implementation_estimate(),
            self.backtest_run(),
            self.model_inventory_entry(),
            self.recommendation_artifact(),
            self.recommendation_audit(),
            self.incident_record(),
            self.data_quality_check(),
            self.run_artifact(),
        ]

        for sample in samples:
            with self.subTest(contract=type(sample).__name__):
                self.assertTrue(is_dataclass(sample))
                id_fields = [field.name for field in fields(sample) if field.name.endswith("_id")]
                self.assertTrue(id_fields)
                for field_name in id_fields:
                    self.assertIsInstance(getattr(sample, field_name), str)
                    self.assertTrue(getattr(sample, field_name))

    def test_source_derived_records_require_content_hash(self) -> None:
        with self.assertRaises(ValueError):
            self.dataset_snapshot(content_hash="")
        with self.assertRaises(ValueError):
            self.evidence_item(content_hash="")
        with self.assertRaises(ValueError):
            self.feature_set(input_snapshot_hash="")

    def test_point_in_time_records_include_audit_timestamps(self) -> None:
        records = [
            self.dataset_snapshot(),
            self.feature_set(),
            self.signal_bundle(),
            self.target_weights(),
            self.implementation_estimate(),
            self.backtest_run(),
        ]

        for record in records:
            names = {field.name for field in fields(record)}
            self.assertTrue({"as_of", "available_at", "retrieved_at"} & names)

    def test_recommendation_artifact_requires_audit_links(self) -> None:
        artifact = self.recommendation_artifact()

        self.assertEqual(AdvisoryLabel.ADVISORY_ONLY, artifact.advisory_label)
        self.assertEqual(("evidence-1",), artifact.evidence_ids)
        self.assertEqual(("model-run-1",), artifact.model_run_ids)
        self.assertEqual("signal-bundle-1", artifact.signal_bundle_id)
        self.assertEqual("target-weights-1", artifact.target_weights_id)

        with self.assertRaises(ValueError):
            self.recommendation_artifact(evidence_ids=())
        with self.assertRaises(ValueError):
            self.recommendation_artifact(model_run_ids=())
        with self.assertRaises(ValueError):
            self.recommendation_artifact(signal_bundle_id="")
        with self.assertRaises(ValueError):
            self.recommendation_artifact(target_weights_id="")

    def test_target_weights_reject_raw_llm_output(self) -> None:
        with self.assertRaises(ValueError):
            self.target_weights(generated_by="llm")

        with self.assertRaises(ValueError):
            TargetWeights.from_raw_llm_output({"NVDA": 0.5})

    def test_model_run_supports_success_retry_and_failure(self) -> None:
        success = self.model_run(status=ModelRunStatus.SUCCESS, schema_valid=True, retry_count=0)
        retry = self.model_run(
            model_run_id="model-run-retry",
            status=ModelRunStatus.RETRY,
            schema_valid=False,
            retry_count=1,
        )
        failure = self.model_run(
            model_run_id="model-run-failure",
            status=ModelRunStatus.FAILURE,
            output_hash=None,
            schema_valid=False,
            retry_count=2,
            error_summary="schema validation failed",
        )

        for run in (success, retry, failure):
            self.assertTrue(run.prompt_version)
            self.assertTrue(run.input_hash)
            self.assertGreaterEqual(run.retry_count, 0)
            self.assertIn(run.status, set(ModelRunStatus))

    def test_evidence_claim_requires_linkage_and_span(self) -> None:
        claim = self.evidence_claim()

        self.assertEqual("evidence-1", claim.evidence_id)
        self.assertEqual("NVDA", claim.ticker_or_theme)
        self.assertEqual("supply_constraint", claim.claim_type)
        self.assertEqual("12m", claim.time_horizon)
        self.assertEqual("p1:l2-l5", claim.quote_or_span_ref)
        self.assertEqual(Decimal("0.8"), claim.confidence)

        with self.assertRaises(ValueError):
            self.evidence_claim(confidence=Decimal("1.5"))
        with self.assertRaises(ValueError):
            self.evidence_claim(quote_or_span_ref="")

    def test_enums_cover_phase1_contract_values(self) -> None:
        self.assertEqual("public_evidence", DataClass.PUBLIC_EVIDENCE.value)
        self.assertEqual("equity", AssetType.EQUITY.value)
        self.assertEqual("buy", TradeSide.BUY.value)
        self.assertEqual("completed", TradeStatus.COMPLETED.value)
        self.assertEqual("accumulate", RecommendationAction.ACCUMULATE.value)
        self.assertEqual("advisory_only", AdvisoryLabel.ADVISORY_ONLY.value)
        self.assertEqual("success", ModelRunStatus.SUCCESS.value)
        self.assertEqual("high", IncidentSeverity.HIGH.value)
        self.assertEqual("pass", DataQualityStatus.PASS.value)

    def test_stable_hash_payload_is_order_independent(self) -> None:
        left = stable_hash_payload({"ticker": "NVDA", "weights": {"MSFT": 0.2, "NVDA": 0.3}})
        right = stable_hash_payload({"weights": {"NVDA": 0.3, "MSFT": 0.2}, "ticker": "NVDA"})

        self.assertEqual(left, right)
        self.assertEqual(64, len(left))

    def test_contracts_do_not_import_cloud_model_clients_or_execution_surface(self) -> None:
        contract_files = list((CORE_SRC / "ai_infra_fund_core" / "contracts").glob("*.py"))
        self.assertTrue(contract_files)
        forbidden = [
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "place_order",
            "submit_order",
            "broker_client",
            "live_order",
            "order_execution",
        ]

        offenders: list[str] = []
        for path in contract_files:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")
        self.assertEqual([], offenders)

    def position(self, **overrides: object) -> Position:
        data = {
            "position_id": "position-1",
            "ticker": "NVDA",
            "quantity": Decimal("10"),
            "cost_basis": Decimal("1000"),
            "currency": "USD",
            "account_label": "personal",
            "asset_type": AssetType.EQUITY,
            "opened_at": date(2026, 1, 2),
            "notes": "core AI accelerator",
            "source": "manual",
            "created_at": NOW,
            "updated_at": NOW,
        }
        data.update(overrides)
        return Position(**data)

    def trade_entry(self, **overrides: object) -> TradeEntry:
        data = {
            "trade_id": "trade-1",
            "ticker": "NVDA",
            "side": TradeSide.BUY,
            "quantity": Decimal("2"),
            "price": Decimal("225.83"),
            "fees": Decimal("0"),
            "trade_date": date(2026, 5, 14),
            "settlement_date": date(2026, 5, 15),
            "account_label": "personal",
            "status": TradeStatus.COMPLETED,
            "source": "manual",
            "notes": "manual journal entry",
            "created_at": NOW,
        }
        data.update(overrides)
        return TradeEntry(**data)

    def trade_journal(self, **overrides: object) -> TradeJournal:
        data = {
            "journal_id": "trade-journal-1",
            "entries": (self.trade_entry(),),
            "as_of": NOW,
            "created_at": NOW,
        }
        data.update(overrides)
        return TradeJournal(**data)

    def universe_member(self, **overrides: object) -> UniverseMember:
        data = {
            "universe_member_id": "universe-member-1",
            "ticker": "NVDA",
            "name": "NVIDIA",
            "theme": "ai_accelerators",
            "role": "core",
            "watchlist_status": "active",
            "max_weight": Decimal("0.25"),
            "liquidity_floor": Decimal("1000000"),
            "thesis_source": "situational_awareness",
            "created_at": NOW,
            "updated_at": NOW,
        }
        data.update(overrides)
        return UniverseMember(**data)

    def dataset_snapshot(self, **overrides: object) -> DatasetSnapshot:
        data = {
            "snapshot_id": "dataset-snapshot-1",
            "dataset_name": "prices",
            "source": "yfinance",
            "license_label": "public",
            "retrieved_at": NOW,
            "effective_at": NOW,
            "available_at": LATER,
            "storage_uri": "postgres://market_snapshots/dataset-snapshot-1",
            "content_hash": "hash-dataset",
            "schema_version": "v1",
            "row_count": 10,
            "data_class": DataClass.PUBLIC_MARKET_DATA,
            "created_at": NOW,
        }
        data.update(overrides)
        return DatasetSnapshot(**data)

    def evidence_item(self, **overrides: object) -> EvidenceItem:
        data = {
            "evidence_id": "evidence-1",
            "source_uri": "file:///reports/semianalysis.md",
            "source_type": "report",
            "title": "AI Hardware",
            "publisher": "SemiAnalysis",
            "author": None,
            "published_at": NOW,
            "ingested_at": LATER,
            "content_hash": "hash-evidence",
            "license_label": "user_supplied_private",
            "data_class": DataClass.PRIVATE_RESEARCH,
            "tickers": ("NVDA",),
            "themes": ("ai_accelerators",),
            "summary": "HBM and accelerator supply constraints",
            "storage_uri": "local://data/raw/reports/private/report.md",
            "created_at": NOW,
        }
        data.update(overrides)
        return EvidenceItem(**data)

    def evidence_claim(self, **overrides: object) -> EvidenceClaim:
        data = {
            "claim_id": "claim-1",
            "evidence_id": "evidence-1",
            "chunk_id": "chunk-1",
            "ticker_or_theme": "NVDA",
            "claim_type": "supply_constraint",
            "direction": "positive",
            "magnitude": Decimal("0.4"),
            "time_horizon": "12m",
            "confidence": Decimal("0.8"),
            "quote_or_span_ref": "p1:l2-l5",
            "extracted_by_model_run_id": "model-run-1",
            "validated_at": LATER,
            "created_at": NOW,
        }
        data.update(overrides)
        return EvidenceClaim(**data)

    def feature_set(self, **overrides: object) -> FeatureSet:
        data = {
            "feature_set_id": "feature-set-1",
            "dataset_snapshot_ids": ("dataset-snapshot-1",),
            "formula_version": "technical-v1",
            "point_in_time_rule": "available_at <= as_of",
            "owner": "deterministic_signal_engine",
            "as_of": NOW,
            "available_at": LATER,
            "input_snapshot_hash": "hash-feature-inputs",
            "created_at": NOW,
        }
        data.update(overrides)
        return FeatureSet(**data)

    def model_run(self, **overrides: object) -> ModelRun:
        data = {
            "model_run_id": "model-run-1",
            "task_role": "evidence_summary",
            "model_id": "configured-model",
            "deployment": "configured-deployment",
            "provider": "azure_ai_foundry",
            "prompt_version": "evidence-summary-v1",
            "input_hash": "hash-model-input",
            "output_hash": "hash-model-output",
            "latency_ms": 120,
            "token_estimate_input": 100,
            "token_estimate_output": 50,
            "schema_valid": True,
            "retry_count": 0,
            "data_classes": (DataClass.PUBLIC_EVIDENCE,),
            "status": ModelRunStatus.SUCCESS,
            "error_summary": None,
            "created_at": NOW,
        }
        data.update(overrides)
        return ModelRun(**data)

    def signal_bundle(self, **overrides: object) -> SignalBundle:
        data = {
            "signal_bundle_id": "signal-bundle-1",
            "ticker": "NVDA",
            "as_of": NOW,
            "strategic_thesis_score": Decimal("0.8"),
            "tactical_technical_score": Decimal("0.6"),
            "forward_indicator_score": Decimal("0.5"),
            "portfolio_risk_score": Decimal("0.3"),
            "formula_versions": {"strategic": "v1"},
            "input_snapshot_hash": "hash-signal-inputs",
            "created_at": NOW,
        }
        data.update(overrides)
        return SignalBundle(**data)

    def target_weights(self, **overrides: object) -> TargetWeights:
        data = {
            "target_weights_id": "target-weights-1",
            "as_of": NOW,
            "portfolio_id": "portfolio-1",
            "cash_weight": Decimal("0.2"),
            "weights": {"NVDA": Decimal("0.3"), "MSFT": Decimal("0.2")},
            "constraints": {"max_single_name_weight": Decimal("0.35")},
            "source_signal_bundle_ids": ("signal-bundle-1",),
            "generated_by": "deterministic_portfolio_engine",
            "validation_status": "validated",
            "created_at": NOW,
        }
        data.update(overrides)
        return TargetWeights(**data)

    def implementation_estimate(self, **overrides: object) -> ImplementationEstimate:
        data = {
            "implementation_estimate_id": "implementation-estimate-1",
            "ticker_or_portfolio": "NVDA",
            "as_of": NOW,
            "expected_turnover": Decimal("0.05"),
            "spread_cost_bps": Decimal("2.0"),
            "slippage_bps": Decimal("3.0"),
            "participation_rate": Decimal("0.01"),
            "liquidity_limit": Decimal("100000"),
            "implementation_shortfall_bps": Decimal("5.0"),
            "created_at": NOW,
        }
        data.update(overrides)
        return ImplementationEstimate(**data)

    def backtest_run(self, **overrides: object) -> BacktestRun:
        data = {
            "backtest_run_id": "backtest-run-1",
            "strategy_id": "strategy-1",
            "dataset_snapshot_ids": ("dataset-snapshot-1",),
            "validation_protocol": "walk_forward_purged_cv",
            "cost_assumptions": {"spread_bps": 2},
            "metrics": {"sharpe": 1.2},
            "artifact_hash": "hash-backtest-output",
            "as_of": NOW,
            "available_at": LATER,
            "created_at": NOW,
        }
        data.update(overrides)
        return BacktestRun(**data)

    def model_inventory_entry(self, **overrides: object) -> ModelInventoryEntry:
        data = {
            "model_inventory_id": "model-inventory-1",
            "owner": "ozgur",
            "purpose": "evidence summarization",
            "inputs": ("public_evidence",),
            "approval_status": "approved",
            "validation_date": date(2026, 5, 14),
            "retraining_trigger": "schema_failure_rate",
            "retirement_criteria": "poor benchmark performance",
            "created_at": NOW,
        }
        data.update(overrides)
        return ModelInventoryEntry(**data)

    def recommendation_artifact(self, **overrides: object) -> RecommendationArtifact:
        data = {
            "recommendation_id": "recommendation-1",
            "ticker_or_portfolio": "NVDA",
            "advisory_label": AdvisoryLabel.ADVISORY_ONLY,
            "action": RecommendationAction.ACCUMULATE,
            "horizon": "medium_term",
            "score_breakdown": {"strategic_thesis_score": "0.8"},
            "target_weights_id": "target-weights-1",
            "evidence_ids": ("evidence-1",),
            "model_run_ids": ("model-run-1",),
            "signal_bundle_id": "signal-bundle-1",
            "risks": ("valuation",),
            "contradictions": ("supply normalization",),
            "final_payload": {"summary": "Accumulate advisory-only"},
            "created_at": NOW,
        }
        data.update(overrides)
        return RecommendationArtifact(**data)

    def recommendation_audit(self, **overrides: object) -> RecommendationAudit:
        data = {
            "audit_id": "recommendation-audit-1",
            "recommendation_id": "recommendation-1",
            "target_weights_id": "target-weights-1",
            "signal_bundle_id": "signal-bundle-1",
            "evidence_ids": ("evidence-1",),
            "model_run_ids": ("model-run-1",),
            "deterministic_checks": {"constraints_passed": True},
            "reviewer_findings": {"contradictions": 1},
            "schema_valid": True,
            "created_at": NOW,
        }
        data.update(overrides)
        return RecommendationAudit(**data)

    def incident_record(self, **overrides: object) -> IncidentRecord:
        data = {
            "incident_id": "incident-1",
            "severity": IncidentSeverity.HIGH,
            "affected_artifacts": ("recommendation-1",),
            "freeze_status": "frozen",
            "root_cause": "stale data",
            "remediation": "refresh source",
            "reopen_criteria": "freshness check passes",
            "created_at": NOW,
            "resolved_at": None,
        }
        data.update(overrides)
        return IncidentRecord(**data)

    def data_quality_check(self, **overrides: object) -> DataQualityCheck:
        data = {
            "check_id": "data-quality-check-1",
            "dataset_id": "dataset-snapshot-1",
            "check_name": "freshness",
            "status": DataQualityStatus.PASS,
            "severity": IncidentSeverity.LOW,
            "observed_value": "5m",
            "threshold": "1h",
            "checked_at": NOW,
        }
        data.update(overrides)
        return DataQualityCheck(**data)

    def run_artifact(self, **overrides: object) -> RunArtifact:
        data = {
            "run_id": "run-1",
            "run_type": "daily",
            "started_at": NOW,
            "completed_at": LATER,
            "inputs_hash": "hash-run-inputs",
            "output_hash": "hash-run-output",
            "artifact_uri": "postgres://audit/run_artifacts/run-1",
            "status": "succeeded",
            "error_summary": None,
            "created_at": NOW,
        }
        data.update(overrides)
        return RunArtifact(**data)


if __name__ == "__main__":
    unittest.main()
