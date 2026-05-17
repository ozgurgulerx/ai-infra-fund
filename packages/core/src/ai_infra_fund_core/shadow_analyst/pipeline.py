from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence

from ai_infra_fund_core.contracts.common import (
    DataClass,
    ModelRunStatus,
    stable_hash_payload,
)
from ai_infra_fund_core.contracts.model_runs import ModelRun
from ai_infra_fund_core.model_routing.router import ModelRouteDenied, ModelRouter, ResolvedModelRoute

from .bundles import AnalystContextBundle
from .drafts import (
    AnalystBriefDraft,
    DraftReviewStatus,
    EquityImpactAssessmentDraft,
    RejectedAnalystDraft,
    RiskRegimeUpdateDraft,
    SegmentImpactDraft,
    TradingAdvisoryDraft,
    ValuationContextDraft,
    extract_evidence_ids,
    make_material_claims,
    reject_forbidden_payload,
)


DEFAULT_TASK_ROLE = "evidence_summary"
PROMPT_VERSION = "shadow_analyst_drafts_v1"
OUTPUT_SCHEMA = "shadow_analyst_drafts_v1"
UNRESOLVED_ROUTE_VALUE = "unresolved_route"
ROUTER_PROVIDER = "model_router"


class AnalystModelClient(Protocol):
    def generate_structured(
        self,
        *,
        route: ResolvedModelRoute,
        bundle: AnalystContextBundle,
        output_schema: str,
    ) -> Mapping[str, object]: ...


class ModelRunRecorder(Protocol):
    def save(self, run: ModelRun) -> object: ...


class AnalystDraftRecorder(Protocol):
    def save_many(self, drafts: Sequence[object]) -> object: ...


@dataclass(frozen=True, slots=True)
class ShadowAnalystResult:
    bundle_id: str
    status: str
    drafts: tuple[object, ...]
    model_runs: tuple[ModelRun, ...]
    fallback_used: bool
    rejection_reasons: tuple[str, ...]


class GovernedShadowAnalystPipeline:
    def __init__(
        self,
        *,
        router: ModelRouter,
        model_client: AnalystModelClient,
        model_run_recorder: ModelRunRecorder,
        draft_recorder: AnalystDraftRecorder | None = None,
        now: Callable[[], datetime] | None = None,
        task_role: str = DEFAULT_TASK_ROLE,
        allow_private_research: bool = False,
    ) -> None:
        self._router = router
        self._model_client = model_client
        self._model_run_recorder = model_run_recorder
        self._draft_recorder = draft_recorder
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._task_role = task_role
        self._allow_private_research = allow_private_research

    def run(self, bundle: AnalystContextBundle) -> ShadowAnalystResult:
        if DataClass.PRIVATE_RESEARCH in bundle.data_classes and not self._allow_private_research:
            run = self._record_denied_run(
                bundle,
                error_summary="private_research denied for governed shadow analyst cloud route by default",
            )
            return ShadowAnalystResult(
                bundle_id=bundle.bundle_id,
                status="denied",
                drafts=(),
                model_runs=(run,),
                fallback_used=True,
                rejection_reasons=(run.error_summary or "route denied",),
            )

        try:
            route = self._router.resolve(self._task_role, data_classes=bundle.data_classes)
        except ModelRouteDenied as exc:
            run = self._record_denied_run(bundle, error_summary=str(exc))
            return ShadowAnalystResult(
                bundle_id=bundle.bundle_id,
                status="denied",
                drafts=(),
                model_runs=(run,),
                fallback_used=True,
                rejection_reasons=(str(exc),),
            )

        input_token_estimate = _estimate_tokens(_bundle_prompt_material(bundle))
        try:
            output = dict(
                self._model_client.generate_structured(
                    route=route,
                    bundle=bundle,
                    output_schema=OUTPUT_SCHEMA,
                )
            )
        except Exception as exc:  # pragma: no cover - exercised through tests
            run = self._record_profile_run(
                bundle=bundle,
                route=route,
                status=ModelRunStatus.FAILURE,
                output_hash=None,
                output_token_estimate=None,
                input_token_estimate=input_token_estimate,
                schema_valid=False,
                error_summary=str(exc),
            )
            return ShadowAnalystResult(
                bundle_id=bundle.bundle_id,
                status="fallback",
                drafts=(),
                model_runs=(run,),
                fallback_used=True,
                rejection_reasons=(str(exc),),
            )

        output_hash = stable_hash_payload({"output": output})
        model_run_id = _model_run_id("shadow-analyst", bundle.content_hash, output_hash)
        drafts, rejection_reasons = _parse_shadow_output(
            output,
            model_run_id=model_run_id,
            bundle_evidence_ids=bundle.evidence_ids,
        )
        schema_valid = not rejection_reasons
        run = self._record_profile_run(
            bundle=bundle,
            route=route,
            status=ModelRunStatus.SUCCESS if schema_valid else ModelRunStatus.FAILURE,
            output_hash=output_hash,
            output_token_estimate=_estimate_tokens(output),
            input_token_estimate=input_token_estimate,
            schema_valid=schema_valid,
            error_summary=None if schema_valid else "; ".join(rejection_reasons),
            model_run_id=model_run_id,
        )
        self._save_drafts(drafts)
        return ShadowAnalystResult(
            bundle_id=bundle.bundle_id,
            status="review_required" if schema_valid else "rejected",
            drafts=drafts,
            model_runs=(run,),
            fallback_used=False,
            rejection_reasons=rejection_reasons,
        )

    def _save_drafts(self, drafts: Sequence[object]) -> None:
        if self._draft_recorder is not None and drafts:
            self._draft_recorder.save_many(tuple(drafts))

    def _record_denied_run(self, bundle: AnalystContextBundle, *, error_summary: str) -> ModelRun:
        run = ModelRun(
            model_run_id=_model_run_id("shadow-analyst-denied", bundle.content_hash, error_summary),
            task_role=self._task_role,
            model_id=UNRESOLVED_ROUTE_VALUE,
            deployment=UNRESOLVED_ROUTE_VALUE,
            provider=ROUTER_PROVIDER,
            prompt_version=PROMPT_VERSION,
            input_hash=bundle.content_hash,
            output_hash=None,
            latency_ms=None,
            token_estimate_input=_estimate_tokens(_bundle_prompt_material(bundle)),
            token_estimate_output=None,
            schema_valid=False,
            retry_count=0,
            data_classes=bundle.data_classes,
            status=ModelRunStatus.DENIED,
            error_summary=error_summary,
            created_at=self._now(),
        )
        self._model_run_recorder.save(run)
        return run

    def _record_profile_run(
        self,
        *,
        bundle: AnalystContextBundle,
        route: ResolvedModelRoute,
        status: ModelRunStatus,
        output_hash: str | None,
        output_token_estimate: int | None,
        input_token_estimate: int,
        schema_valid: bool,
        error_summary: str | None,
        model_run_id: str | None = None,
    ) -> ModelRun:
        run = ModelRun(
            model_run_id=model_run_id or _model_run_id("shadow-analyst", bundle.content_hash, status.value, error_summary or ""),
            task_role=route.task_role,
            model_id=route.profile.model_id,
            deployment=route.profile.deployment,
            provider=route.profile.provider,
            prompt_version=PROMPT_VERSION,
            input_hash=bundle.content_hash,
            output_hash=output_hash,
            latency_ms=None,
            token_estimate_input=input_token_estimate,
            token_estimate_output=output_token_estimate,
            schema_valid=schema_valid,
            retry_count=0,
            data_classes=bundle.data_classes,
            status=status,
            error_summary=error_summary,
            created_at=self._now(),
        )
        self._model_run_recorder.save(run)
        return run


def _parse_shadow_output(
    output: Mapping[str, object],
    *,
    model_run_id: str,
    bundle_evidence_ids: Sequence[str],
) -> tuple[tuple[object, ...], tuple[str, ...]]:
    specs = (
        ("segment_impacts", "SegmentImpactDraft", SegmentImpactDraft, ("segment_name", "linked_event_ids", "first_order_tickers", "second_order_tickers")),
        (
            "equity_impact_assessments",
            "EquityImpactAssessmentDraft",
            EquityImpactAssessmentDraft,
            ("ticker", "assessment", "bull_case", "bear_case", "risk_flags", "invalidation_condition"),
        ),
        ("valuation_contexts", "ValuationContextDraft", ValuationContextDraft, ("ticker", "valuation_summary")),
        ("risk_regime_updates", "RiskRegimeUpdateDraft", RiskRegimeUpdateDraft, ("risk_type", "affected_tickers", "summary")),
        (
            "trading_advisories",
            "TradingAdvisoryDraft",
            TradingAdvisoryDraft,
            ("ticker", "analyst_action", "rationale", "context_used", "market_event_ids"),
        ),
        (
            "analyst_briefs",
            "AnalystBriefDraft",
            AnalystBriefDraft,
            ("headline", "summary", "decision_rationale", "context_used"),
        ),
    )
    drafts: list[object] = []
    rejection_reasons: list[str] = []
    for section_name, draft_type, draft_class, extra_fields in specs:
        for index, raw_item in enumerate(_iter_mappings(output.get(section_name))):
            draft_id = _draft_id(draft_type, model_run_id, index)
            try:
                reject_forbidden_payload(raw_item)
                evidence_ids = extract_evidence_ids(raw_item)
                unknown = [evidence_id for evidence_id in evidence_ids if evidence_id not in bundle_evidence_ids]
                if unknown:
                    raise ValueError(f"{draft_type} references unknown evidence IDs: {', '.join(unknown)}")
                material_claims = make_material_claims(
                    raw_item.get("material_claims"),
                    allowed_evidence_ids=bundle_evidence_ids,
                )
                payload = raw_item.get("payload")
                if not isinstance(payload, dict):
                    raise ValueError(f"{draft_type} payload must be a mapping")
                kwargs = {
                    "draft_id": draft_id,
                    "draft_type": draft_type,
                    "evidence_ids": evidence_ids,
                    "material_claims": material_claims,
                    "payload": dict(payload),
                    "model_run_id": model_run_id,
                    "review_status": DraftReviewStatus.REVIEW_REQUIRED,
                }
                kwargs.update({field_name: raw_item.get(field_name) for field_name in extra_fields})
                drafts.append(draft_class(**kwargs))
            except ValueError as exc:
                reason = f"{draft_type}[{index}]: {exc}"
                rejection_reasons.append(reason)
                drafts.append(
                    RejectedAnalystDraft(
                        draft_id=draft_id,
                        draft_type=draft_type,
                        evidence_ids=_safe_evidence_ids(raw_item, bundle_evidence_ids),
                        model_run_id=model_run_id,
                        rejection_reasons=(reason,),
                        raw_payload=dict(raw_item),
                    )
                )
    if not drafts:
        rejection_reasons.append("model output produced no draft analyst objects")
    return tuple(drafts), tuple(rejection_reasons)


def _iter_mappings(value: object) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if not isinstance(value, (list, tuple)):
        raise ValueError("model output sections must be mappings or sequences of mappings")
    rows: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("model output section entries must be mappings")
        rows.append(item)
    return tuple(rows)


def _safe_evidence_ids(raw_item: Mapping[str, object], bundle_evidence_ids: Sequence[str]) -> tuple[str, ...]:
    raw_evidence_ids = raw_item.get("evidence_ids")
    if isinstance(raw_evidence_ids, str) and raw_evidence_ids.strip():
        return (raw_evidence_ids.strip(),)
    if isinstance(raw_evidence_ids, (list, tuple)):
        evidence_ids = tuple(str(item).strip() for item in raw_evidence_ids if str(item).strip())
        if evidence_ids:
            return evidence_ids
    if bundle_evidence_ids:
        return (bundle_evidence_ids[0],)
    return ("unlinked-evidence",)


def _bundle_prompt_material(bundle: AnalystContextBundle) -> dict[str, object]:
    return {
        "bundle_id": bundle.bundle_id,
        "scope": bundle.scope.value,
        "ticker": bundle.ticker,
        "evidence_ids": bundle.evidence_ids,
        "object_ids": bundle.object_ids,
        "data_classes": tuple(data_class.value for data_class in bundle.data_classes),
    }


def _estimate_tokens(value: object) -> int:
    text = str(value)
    return max(1, len(text) // 4)


def _model_run_id(*parts: object) -> str:
    digest = stable_hash_payload({"parts": parts})
    return f"model-run-{digest[:24]}"


def _draft_id(draft_type: str, model_run_id: str, index: int) -> str:
    digest = stable_hash_payload({"draft_type": draft_type, "model_run_id": model_run_id, "index": index})
    return f"draft-{draft_type.lower()}-{digest[:16]}"
