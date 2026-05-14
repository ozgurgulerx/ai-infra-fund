from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from importlib import import_module
import ast
import inspect
from pathlib import Path
import re
import sys
import unittest
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import (  # noqa: E402
    AdvisoryLabel,
    DataQualityStatus,
    RecommendationAction,
)
from ai_infra_fund_core.contracts.evidence import EvidenceClaim  # noqa: E402
from ai_infra_fund_core.contracts.recommendations import RecommendationArtifact  # noqa: E402
from ai_infra_fund_core.contracts.signals import SignalBundle, TargetWeights  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)

EXPECTED_PUBLICATION_MODULES = (
    "ai_infra_fund_core.recommendations",
    "ai_infra_fund_core.recommendations.publication",
    "ai_infra_fund_core.recommendations.builder",
    "ai_infra_fund_core.recommendations.policy",
    "ai_infra_fund_core.recommendation",
)

EXPECTED_PUBLICATION_FUNCTIONS = (
    "build_recommendation",
    "build_recommendation_artifact",
    "evaluate_recommendation_publication",
    "evaluate_publication_policy",
    "should_publish_recommendation",
    "validate_recommendation_publication",
)

EXPECTED_PUBLICATION_CLASSES = (
    "RecommendationPublicationPolicy",
    "RecommendationPublisher",
    "RecommendationBuilder",
)

PUBLICATION_METHODS = (
    "evaluate",
    "should_publish",
    "validate",
    "build",
    "publish",
    "publication_decision",
)

FORBIDDEN_MODEL_CLIENT_IMPORT_ROOTS = {
    "anthropic",
    "azure",
    "boto3",
    "cohere",
    "mistralai",
    "openai",
    "vertexai",
}

FORBIDDEN_EXECUTION_PATTERNS = (
    r"\bplace_order\b",
    r"\bsubmit_order\b",
    r"\bexecute_order\b",
    r"\bbroker_client\b",
    r"\bbrokerage\b",
    r"\blive_order\b",
    r"\border_execution\b",
    r"\border_router\b",
    r"\border_placement\b",
)

PRODUCTION_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".sql",
    ".yaml",
    ".yml",
}

IGNORED_SOURCE_PARTS = {"node_modules", ".next", "__pycache__"}


@dataclass(frozen=True, slots=True)
class PublicationFixture:
    evidence_ids: tuple[str, ...] = ("evidence-1",)
    model_run_ids: tuple[str, ...] = ("model-run-1",)
    signal_bundle_id: str | None = "signal-bundle-1"
    target_weights_id: str | None = "target-weights-1"
    data_quality_statuses: tuple[DataQualityStatus, ...] = (DataQualityStatus.PASS,)
    incident_freeze_statuses: tuple[str, ...] = ("open",)
    license_statuses: tuple[str, ...] = ("licensed",)
    model_approval_statuses: tuple[str, ...] = ("approved",)


@dataclass(frozen=True, slots=True)
class PublicationEvaluator:
    label: str
    module: Any
    call: Callable[[PublicationFixture], Any]


class Phase6RecommendationPolicyIntegrationTests(unittest.TestCase):
    def test_deterministic_recommendation_modules_do_not_import_model_clients(self) -> None:
        module_paths = _recommendation_module_paths()
        if not module_paths:
            self.fail(
                "Coordination needed: expected a deterministic recommendation module under "
                "ai_infra_fund_core.recommendations* so policy tests can verify it does not import "
                "cloud model clients."
            )

        offenders: list[str] = []
        for path in module_paths:
            for import_root in _import_roots(path):
                if import_root in FORBIDDEN_MODEL_CLIENT_IMPORT_ROOTS:
                    offenders.append(f"{path.relative_to(ROOT)} imports {import_root}")

        self.assertEqual([], offenders)

    def test_no_broker_or_live_order_execution_surface_exists(self) -> None:
        offenders: list[str] = []
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_EXECUTION_PATTERNS]

        for path in _production_text_files():
            relative_path = path.relative_to(ROOT).as_posix()
            searchable = f"{relative_path}\n{path.read_text(encoding='utf-8', errors='ignore')}"
            for pattern in compiled_patterns:
                if pattern.search(searchable):
                    offenders.append(f"{relative_path} matches {pattern.pattern}")

        self.assertEqual([], offenders)

    def test_recommendation_artifact_requires_advisory_audit_linkage(self) -> None:
        artifact = recommendation_artifact()

        self.assertEqual(AdvisoryLabel.ADVISORY_ONLY, artifact.advisory_label)
        self.assertEqual(("evidence-1",), artifact.evidence_ids)
        self.assertEqual(("model-run-1",), artifact.model_run_ids)
        self.assertEqual("signal-bundle-1", artifact.signal_bundle_id)
        self.assertEqual("target-weights-1", artifact.target_weights_id)

        required_link_cases = {
            "advisory_label": {"advisory_label": ""},
            "evidence_ids": {"evidence_ids": ()},
            "model_run_ids": {"model_run_ids": ()},
            "signal_bundle_id": {"signal_bundle_id": ""},
            "target_weights_id": {"target_weights_id": ""},
        }
        for field_name, overrides in required_link_cases.items():
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValueError):
                    recommendation_artifact(**overrides)

    def test_target_weights_cannot_be_created_from_raw_llm_output(self) -> None:
        with self.assertRaises(ValueError):
            TargetWeights.from_raw_llm_output({"NVDA": 0.50, "MSFT": 0.25})

        for generator in ("llm", "LLM", "raw_llm", "cloud_model", "model_output"):
            with self.subTest(generator=generator):
                with self.assertRaises(ValueError):
                    target_weights(generated_by=generator)

    def test_publication_policy_allows_only_complete_clean_inputs(self) -> None:
        evaluator = _find_publication_evaluator(self)

        allowed = _invoke_publication_evaluator(evaluator, PublicationFixture())
        self.assertTrue(
            _allows_publication(allowed),
            f"{evaluator.label} should allow publication when required links are present and inputs are clean.",
        )

        suppressed_cases = {
            "missing_evidence_ids": PublicationFixture(evidence_ids=()),
            "missing_model_run_ids": PublicationFixture(model_run_ids=()),
            "missing_signal_bundle_id": PublicationFixture(signal_bundle_id=None),
            "missing_target_weights_id": PublicationFixture(target_weights_id=None),
            "stale_input": PublicationFixture(data_quality_statuses=(DataQualityStatus.STALE,)),
            "quarantined_input": PublicationFixture(data_quality_statuses=(DataQualityStatus.QUARANTINED,)),
            "incident_frozen_input": PublicationFixture(incident_freeze_statuses=("frozen",)),
        }
        for scenario, fixture in suppressed_cases.items():
            with self.subTest(scenario=scenario):
                try:
                    decision = _invoke_publication_evaluator(evaluator, fixture)
                except ValueError:
                    continue
                self.assertTrue(
                    _suppresses_publication(decision),
                    f"{evaluator.label} must suppress publication for {scenario}.",
                )


def recommendation_artifact(**overrides: object) -> RecommendationArtifact:
    data = {
        "recommendation_id": "recommendation-1",
        "ticker_or_portfolio": "NVDA",
        "advisory_label": AdvisoryLabel.ADVISORY_ONLY,
        "action": RecommendationAction.ACCUMULATE,
        "horizon": "12m",
        "score_breakdown": {"combined_attractiveness_score": "0.81"},
        "target_weights_id": "target-weights-1",
        "evidence_ids": ("evidence-1",),
        "model_run_ids": ("model-run-1",),
        "signal_bundle_id": "signal-bundle-1",
        "risks": ("supply concentration",),
        "contradictions": (),
        "final_payload": {"label": "advisory_only", "rationale": "deterministic policy fixture"},
        "created_at": NOW,
    }
    data.update(overrides)
    return RecommendationArtifact(**data)


def target_weights(**overrides: object) -> TargetWeights:
    data = {
        "target_weights_id": "target-weights-1",
        "as_of": NOW,
        "portfolio_id": "portfolio-1",
        "cash_weight": Decimal("0.60"),
        "weights": {"NVDA": Decimal("0.40")},
        "constraints": {"cash_floor": "0.10", "max_single_name_weight": "0.40"},
        "source_signal_bundle_ids": ("signal-bundle-1",),
        "generated_by": "deterministic_portfolio_engine.v1",
        "validation_status": "validated",
        "created_at": NOW,
    }
    data.update(overrides)
    return TargetWeights(**data)


def signal_bundle(**overrides: object) -> SignalBundle:
    data = {
        "signal_bundle_id": "signal-bundle-1",
        "ticker": "NVDA",
        "as_of": NOW,
        "strategic_thesis_score": Decimal("0.80"),
        "tactical_technical_score": Decimal("0.60"),
        "forward_indicator_score": Decimal("0.50"),
        "portfolio_risk_score": Decimal("0.30"),
        "formula_versions": {"test": "v1"},
        "input_snapshot_hash": "a" * 64,
        "created_at": NOW,
    }
    data.update(overrides)
    return SignalBundle(**data)


def evidence_claim(**overrides: object) -> EvidenceClaim:
    data = {
        "claim_id": "claim-1",
        "evidence_id": "evidence-1",
        "chunk_id": "chunk-1",
        "ticker_or_theme": "NVDA",
        "claim_type": "supply_constraint",
        "direction": "positive",
        "magnitude": Decimal("0.40"),
        "time_horizon": "12m",
        "confidence": Decimal("0.80"),
        "quote_or_span_ref": "p1:l2-l5",
        "extracted_by_model_run_id": "model-run-1",
        "validated_at": NOW,
        "created_at": NOW,
    }
    data.update(overrides)
    return EvidenceClaim(**data)


def _recommendation_module_paths() -> list[Path]:
    package_root = CORE_SRC / "ai_infra_fund_core"
    if not package_root.exists():
        return []

    paths: set[Path] = set()
    for path in package_root.rglob("*.py"):
        relative_parts = path.relative_to(package_root).parts
        if relative_parts == ("contracts", "recommendations.py"):
            continue
        if "recommendations" in relative_parts or "recommendation" in path.stem:
            paths.add(path)
    return sorted(paths)


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])
    return roots


def _production_text_files() -> list[Path]:
    files: list[Path] = []
    for root_name in ("apps", "services", "packages"):
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in PRODUCTION_SUFFIXES:
                continue
            if any(part in IGNORED_SOURCE_PARTS for part in path.relative_to(ROOT).parts):
                continue
            files.append(path)
    return files


def _find_publication_evaluator(test_case: unittest.TestCase) -> PublicationEvaluator:
    imported_modules: list[Any] = []
    import_errors: list[str] = []
    for module_name in EXPECTED_PUBLICATION_MODULES:
        try:
            imported_modules.append(import_module(module_name))
        except ModuleNotFoundError as exc:
            import_errors.append(f"{module_name}: {exc}")

    for module in imported_modules:
        for function_name in EXPECTED_PUBLICATION_FUNCTIONS:
            function = getattr(module, function_name, None)
            if callable(function):
                return PublicationEvaluator(f"{module.__name__}.{function_name}", module, function)

        for class_name in EXPECTED_PUBLICATION_CLASSES:
            cls = getattr(module, class_name, None)
            if cls is None:
                continue
            try:
                instance = cls()
            except TypeError:
                continue
            for method_name in PUBLICATION_METHODS:
                method = getattr(instance, method_name, None)
                if callable(method):
                    return PublicationEvaluator(f"{module.__name__}.{class_name}.{method_name}", module, method)

    test_case.fail(
        "Coordination needed: expose a Phase 6 publication policy public symbol. Expected one of "
        f"{EXPECTED_PUBLICATION_FUNCTIONS} or {EXPECTED_PUBLICATION_CLASSES} in one of "
        f"{EXPECTED_PUBLICATION_MODULES}. Import attempts: {import_errors}"
    )
    raise AssertionError("unreachable")


def _invoke_publication_evaluator(evaluator: PublicationEvaluator, fixture: PublicationFixture) -> Any:
    kwargs = {
        "evidence_ids": fixture.evidence_ids,
        "model_run_ids": fixture.model_run_ids,
        "signal_bundle_id": fixture.signal_bundle_id,
        "target_weights_id": fixture.target_weights_id,
        "data_quality_statuses": fixture.data_quality_statuses,
        "data_quality_checks": fixture.data_quality_statuses,
        "incident_freeze_statuses": fixture.incident_freeze_statuses,
        "incident_statuses": fixture.incident_freeze_statuses,
        "license_statuses": fixture.license_statuses,
        "model_approval_statuses": fixture.model_approval_statuses,
        "deterministic_checks": _deterministic_checks_input(fixture),
        "signal_bundle": _signal_bundle_input(fixture),
        "target_weights": _target_weights_input(fixture),
        "evidence_claims": _evidence_claim_inputs(fixture),
        "created_at": NOW,
        "policy_context": _policy_context_input(evaluator, fixture),
        "artifact": recommendation_artifact(
            evidence_ids=fixture.evidence_ids or ("placeholder-evidence",),
            model_run_ids=fixture.model_run_ids or ("placeholder-model-run",),
            signal_bundle_id=fixture.signal_bundle_id or "placeholder-signal-bundle",
            target_weights_id=fixture.target_weights_id or "placeholder-target-weights",
        ),
        "publication_input": fixture,
        "inputs": fixture,
        "context": fixture,
    }

    signature = inspect.signature(evaluator.call)
    parameters = signature.parameters
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return evaluator.call(**kwargs)

    accepted_kwargs = {
        name: value
        for name, value in kwargs.items()
        if name in parameters
        and parameters[name].kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    if accepted_kwargs:
        return evaluator.call(**accepted_kwargs)

    positional_parameters = [
        parameter
        for parameter in parameters.values()
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional_parameters) == 1:
        return evaluator.call(fixture)

    return evaluator.call()


def _signal_bundle_input(fixture: PublicationFixture) -> SignalBundle | dict[str, object]:
    if fixture.signal_bundle_id:
        return signal_bundle(signal_bundle_id=fixture.signal_bundle_id)
    return {
        "signal_bundle_id": "",
        "ticker": "NVDA",
        "as_of": NOW,
        "strategic_thesis_score": Decimal("0.80"),
        "tactical_technical_score": Decimal("0.60"),
        "forward_indicator_score": Decimal("0.50"),
        "portfolio_risk_score": Decimal("0.30"),
        "formula_versions": {"test": "v1"},
        "input_snapshot_hash": "a" * 64,
        "created_at": NOW,
    }


def _target_weights_input(fixture: PublicationFixture) -> TargetWeights | dict[str, object]:
    if fixture.target_weights_id:
        return target_weights(target_weights_id=fixture.target_weights_id)
    return {
        "target_weights_id": "",
        "as_of": NOW,
        "portfolio_id": "portfolio-1",
        "cash_weight": Decimal("0.60"),
        "weights": {"NVDA": Decimal("0.40")},
        "constraints": {"cash_floor": "0.10", "max_single_name_weight": "0.40"},
        "source_signal_bundle_ids": ("signal-bundle-1",),
        "generated_by": "deterministic_portfolio_engine.v1",
        "validation_status": "validated",
        "created_at": NOW,
    }


def _evidence_claim_inputs(fixture: PublicationFixture) -> tuple[EvidenceClaim, ...]:
    return tuple(
        evidence_claim(claim_id=f"claim-{index}", evidence_id=evidence_id)
        for index, evidence_id in enumerate(fixture.evidence_ids, start=1)
    )


def _policy_context_input(evaluator: PublicationEvaluator, fixture: PublicationFixture) -> object:
    context_cls = getattr(evaluator.module, "RecommendationPolicyContext", None)
    if context_cls is None:
        return fixture

    context_kwargs = {
        "stale_evidence_ids": fixture.evidence_ids
        if DataQualityStatus.STALE in fixture.data_quality_statuses
        else (),
        "quarantined_evidence_ids": fixture.evidence_ids
        if DataQualityStatus.QUARANTINED in fixture.data_quality_statuses
        else (),
        "incident_freeze_active": "frozen" in fixture.incident_freeze_statuses,
    }
    signature = inspect.signature(context_cls)
    accepted_context_kwargs = {
        name: value
        for name, value in context_kwargs.items()
        if name in signature.parameters
    }
    return context_cls(**accepted_context_kwargs)


def _deterministic_checks_input(fixture: PublicationFixture) -> dict[str, object]:
    return {
        "advisory_only": True,
        "signal_bundle_id_present": bool(fixture.signal_bundle_id),
        "target_weights_id_present": bool(fixture.target_weights_id),
        "evidence_ids_present": bool(fixture.evidence_ids),
        "model_run_ids_present": bool(fixture.model_run_ids),
        "target_weights_generated_by_deterministic": bool(fixture.target_weights_id),
        "target_weights_validated": bool(fixture.target_weights_id),
        "source_signal_bundle_linked": bool(fixture.signal_bundle_id and fixture.target_weights_id),
        "target_weights_sum_valid": bool(fixture.target_weights_id),
        "evidence_covers_signal": bool(fixture.evidence_ids),
        "stale_evidence_ids": fixture.evidence_ids
        if DataQualityStatus.STALE in fixture.data_quality_statuses
        else (),
        "quarantined_evidence_ids": fixture.evidence_ids
        if DataQualityStatus.QUARANTINED in fixture.data_quality_statuses
        else (),
        "incident_freeze_active": "frozen" in fixture.incident_freeze_statuses,
    }


def _allows_publication(decision: Any) -> bool:
    if isinstance(decision, RecommendationArtifact):
        return True
    if isinstance(decision, bool):
        return decision
    if decision is None:
        return False

    suppressed = _lookup_decision_field(decision, ("suppressed", "is_suppressed", "blocked", "is_blocked"))
    if suppressed is not None:
        return not bool(suppressed)

    allowed = _lookup_decision_field(
        decision,
        ("allowed", "is_allowed", "can_publish", "should_publish", "publish", "published", "ok"),
    )
    if allowed is not None:
        return bool(allowed)

    if isinstance(decision, tuple) and decision and isinstance(decision[0], bool):
        return decision[0]

    raise AssertionError(
        "Publication decision must return a RecommendationArtifact, bool, None, tuple(bool, ...), "
        "or expose an allowed/suppressed decision field."
    )


def _suppresses_publication(decision: Any) -> bool:
    if decision is None:
        return True
    return not _allows_publication(decision)


def _lookup_decision_field(decision: Any, names: tuple[str, ...]) -> Any | None:
    if isinstance(decision, Mapping):
        for name in names:
            if name in decision:
                return decision[name]
        return None

    for name in names:
        if hasattr(decision, name):
            return getattr(decision, name)
    return None


if __name__ == "__main__":
    unittest.main()
