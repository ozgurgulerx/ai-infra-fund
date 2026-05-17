from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_core.contracts.common import DataClass, ModelRunStatus  # noqa: E402
from ai_infra_fund_core.model_routing.client import (  # noqa: E402
    ConfiguredModelClient,
    ConfiguredModelClientSettings,
)
from ai_infra_fund_core.model_routing.profiles import ModelProfileCatalog  # noqa: E402
from ai_infra_fund_core.model_routing.router import ModelRouter  # noqa: E402
from ai_infra_fund_core.shadow_analyst import (  # noqa: E402
    GovernedShadowAnalystPipeline,
    build_daily_analyst_context_bundle,
)
from ai_infra_fund_worker.daily_ai_infra_brief_run import (  # noqa: E402
    UnavailableShadowAnalystModelClient,
    SHADOW_ANALYST_MODE_ENV,
    _shadow_model_client_from_environment,
)


NOW = datetime(2026, 5, 17, 9, 0, tzinfo=timezone.utc)


class ShadowAnalystRealModelClientIntegrationTests(unittest.TestCase):
    def test_real_model_client_failure_is_audited_and_falls_back(self) -> None:
        bundle = build_daily_analyst_context_bundle(_context_rows(), as_of=NOW)
        recorder = RecordingModelRunRecorder()

        result = GovernedShadowAnalystPipeline(
            router=ModelRouter(_catalog()),
            model_client=ConfiguredModelClient.from_environment({}),
            model_run_recorder=recorder,
            now=lambda: NOW,
            task_role="segment_impact_analysis",
        ).run(bundle)

        self.assertEqual("fallback", result.status)
        self.assertTrue(result.fallback_used)
        self.assertEqual(1, len(recorder.records))
        self.assertEqual(ModelRunStatus.FAILURE, recorder.records[0].status)
        self.assertEqual("segment_impact_analysis", recorder.records[0].task_role)
        self.assertIn("azure", recorder.records[0].error_summary.lower())

    def test_private_research_is_denied_before_real_model_client_call(self) -> None:
        bundle = build_daily_analyst_context_bundle(
            _context_rows(data_class="private_research"),
            as_of=NOW,
        )
        recorder = RecordingModelRunRecorder()

        result = GovernedShadowAnalystPipeline(
            router=ModelRouter(_catalog()),
            model_client=ConfiguredModelClient.from_environment({}),
            model_run_recorder=recorder,
            now=lambda: NOW,
            task_role="segment_impact_analysis",
        ).run(bundle)

        self.assertEqual("denied", result.status)
        self.assertTrue(result.fallback_used)
        self.assertEqual(ModelRunStatus.DENIED, recorder.records[0].status)
        self.assertIn("private_research", recorder.records[0].error_summary or "")

    def test_configured_real_client_success_is_audited_as_review_required_draft(self) -> None:
        bundle = build_daily_analyst_context_bundle(_context_rows(), as_of=NOW)
        recorder = RecordingModelRunRecorder()
        draft_recorder = RecordingDraftRecorder()
        transport = RecordingTransport(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "analyst_briefs": [
                                        {
                                            "evidence_ids": ["evidence-1"],
                                            "material_claims": [
                                                {
                                                    "claim": "AI capex evidence remains review-only.",
                                                    "evidence_ids": ["evidence-1"],
                                                }
                                            ],
                                            "payload": {"summary": "Draft only."},
                                            "headline": "AI infrastructure brief draft",
                                            "summary": "Public evidence supports analyst review.",
                                            "decision_rationale": "The draft ties public evidence to a review-required analyst brief.",
                                            "context_used": [
                                                "evidence-1",
                                                "source-signal-1",
                                                "market-event-1",
                                            ],
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            }
        )

        result = GovernedShadowAnalystPipeline(
            router=ModelRouter(_catalog()),
            model_client=ConfiguredModelClient(
                settings=ConfiguredModelClientSettings(
                    azure_endpoint="https://example.openai.azure.com",
                    azure_api_key="test-secret",
                    azure_api_version="2024-10-21",
                    ollama_base_url="http://localhost:11434",
                    timeout_seconds=3,
                ),
                transport=transport,
            ),
            model_run_recorder=recorder,
            draft_recorder=draft_recorder,
            now=lambda: NOW,
            task_role="analyst_brief_draft",
        ).run(bundle)

        self.assertEqual("review_required", result.status)
        self.assertFalse(result.fallback_used)
        self.assertEqual(1, len(recorder.records))
        self.assertEqual(ModelRunStatus.SUCCESS, recorder.records[0].status)
        self.assertEqual("analyst_brief_draft", recorder.records[0].task_role)
        self.assertEqual(1, len(draft_recorder.records))
        self.assertEqual("AnalystBriefDraft", draft_recorder.records[0].draft_type)
        self.assertEqual(
            recorder.records[0].model_run_id,
            draft_recorder.records[0].model_run_id,
        )
        self.assertFalse(draft_recorder.records[0].can_publish_directly)
        self.assertEqual(1, len(transport.calls))

    def test_daily_worker_enables_real_client_only_when_env_requests_it(self) -> None:
        defaulted = _shadow_model_client_from_environment({})
        fallback = _shadow_model_client_from_environment(
            {SHADOW_ANALYST_MODE_ENV: "fallback"}
        )
        disabled = _shadow_model_client_from_environment(
            {SHADOW_ANALYST_MODE_ENV: "disabled"}
        )
        enabled = _shadow_model_client_from_environment(
            {SHADOW_ANALYST_MODE_ENV: "real"}
        )

        self.assertIsInstance(defaulted, UnavailableShadowAnalystModelClient)
        self.assertIsInstance(fallback, UnavailableShadowAnalystModelClient)
        self.assertIsInstance(disabled, UnavailableShadowAnalystModelClient)
        self.assertIsInstance(enabled, ConfiguredModelClient)

    def test_legacy_worker_env_flag_remains_real_mode_compatibility_alias(self) -> None:
        enabled = _shadow_model_client_from_environment(
            {"AI_INFRA_FUND_SHADOW_ANALYST_MODEL_CLIENT": "real"}
        )

        self.assertIsInstance(enabled, ConfiguredModelClient)


class RecordingModelRunRecorder:
    def __init__(self) -> None:
        self.records = []

    def save(self, run: object) -> object:
        self.records.append(run)
        return run


class RecordingDraftRecorder:
    def __init__(self) -> None:
        self.records = []

    def save_many(self, drafts: object) -> object:
        self.records.extend(drafts)
        return drafts


class RecordingTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


def _catalog() -> ModelProfileCatalog:
    return ModelProfileCatalog.from_mapping(
        {
            "version": 1,
            "models": {
                "test_profile": {
                    "model_id": "test-model",
                    "deployment": "test-deployment",
                    "provider": "azure_foundry",
                    "endpoint_type": "azure_ai_foundry",
                    "task_roles": ["evidence_summary"],
                    "quota_rpm": None,
                    "quota_tpm": None,
                    "cost_class": "test",
                    "max_context": "unknown",
                    "privacy_class": "cloud",
                    "allowed_data_classes": [
                        DataClass.PUBLIC_EVIDENCE.value,
                        DataClass.DERIVED_ANALYTICS.value,
                    ],
                    "fallback_chain": [],
                    "structured_output_support": True,
                    "notes": "Test profile.",
                }
            },
        }
    )


def _context_rows(*, data_class: str = "public_evidence") -> dict[str, tuple[dict[str, object], ...]]:
    return {
        "evidence_items": (
            {
                "evidence_id": "evidence-1",
                "data_class": data_class,
                "summary": "AI capex evidence.",
                "content_hash": "a" * 64,
            },
        ),
        "source_signals": (
            {
                "signal_id": "source-signal-1",
                "evidence_id": "evidence-1",
                "data_class": data_class,
                "tickers": ("NVDA",),
            },
        ),
        "market_events": (
            {
                "event_id": "market-event-1",
                "evidence_ids": ("evidence-1",),
                "tickers": ("NVDA",),
            },
        ),
    }


if __name__ == "__main__":
    unittest.main()
