from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.model_routing.client import (  # noqa: E402
    ConfiguredModelClient,
    ConfiguredModelClientSettings,
    ModelClientConfigurationError,
)
from ai_infra_fund_core.model_routing.profiles import ModelProfileCatalog  # noqa: E402
from ai_infra_fund_core.model_routing.router import (  # noqa: E402
    ModelRouter,
    SHADOW_ANALYST_TASK_ROLES,
)
from ai_infra_fund_core.shadow_analyst import build_daily_analyst_context_bundle  # noqa: E402


NOW = datetime(2026, 5, 17, 8, 0, tzinfo=timezone.utc)


class ConfiguredModelClientTests(unittest.TestCase):
    def test_azure_foundry_route_uses_configured_deployment_and_parses_json_content(self) -> None:
        transport = RecordingTransport(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "segment_impacts": [
                                        {
                                            "evidence_ids": ["evidence-1"],
                                            "material_claims": [
                                                {
                                                    "claim": "AI capex supports accelerator demand.",
                                                    "evidence_ids": ["evidence-1"],
                                                }
                                            ],
                                            "payload": {"summary": "Review-only draft."},
                                            "segment_name": "accelerators",
                                            "linked_event_ids": ["market-event-1"],
                                            "first_order_tickers": ["NVDA"],
                                            "second_order_tickers": ["TSM"],
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            }
        )
        route = ModelRouter(_catalog()).resolve(
            "segment_impact_analysis",
            data_classes=(DataClass.PUBLIC_EVIDENCE,),
        )
        client = ConfiguredModelClient(
            settings=ConfiguredModelClientSettings(
                azure_endpoint="https://example.openai.azure.com",
                azure_api_key="test-secret",
                azure_api_version="2024-10-21",
                ollama_base_url="http://localhost:11434",
                timeout_seconds=3,
            ),
            transport=transport,
        )

        output = client.generate_structured(
            route=route,
            bundle=_bundle(),
            output_schema="shadow_analyst_drafts_v1",
        )

        self.assertIn("segment_impacts", output)
        self.assertEqual(1, len(transport.calls))
        call = transport.calls[0]
        self.assertEqual("POST", call["method"])
        self.assertIn("/openai/deployments/test-deployment/chat/completions", call["url"])
        self.assertIn("api-version=2024-10-21", call["url"])
        self.assertEqual("test-secret", call["headers"]["api-key"])
        self.assertEqual("application/json", call["headers"]["Content-Type"])
        self.assertEqual({"type": "json_object"}, call["payload"]["response_format"])
        self.assertNotIn("test-model", json.dumps(call["payload"]))

    def test_missing_azure_configuration_fails_before_network_without_leaking_secret(self) -> None:
        transport = RecordingTransport({})
        route = ModelRouter(_catalog()).resolve(
            "analyst_brief_draft",
            data_classes=(DataClass.PUBLIC_EVIDENCE,),
        )
        client = ConfiguredModelClient(
            settings=ConfiguredModelClientSettings(
                azure_endpoint=None,
                azure_api_key=None,
                azure_api_version="2024-10-21",
                ollama_base_url="http://localhost:11434",
                timeout_seconds=3,
            ),
            transport=transport,
        )

        with self.assertRaises(ModelClientConfigurationError) as raised:
            client.generate_structured(
                route=route,
                bundle=_bundle(),
                output_schema="shadow_analyst_drafts_v1",
            )

        self.assertEqual([], transport.calls)
        self.assertNotIn("api_key", str(raised.exception).lower())
        self.assertIn("azure", str(raised.exception).lower())

    def test_azure_foundry_managed_identity_route_uses_bearer_token(self) -> None:
        transport = RecordingTransport(
            {
                "analyst_briefs": [
                    {
                        "evidence_ids": ["evidence-1"],
                        "material_claims": [
                            {"claim": "Test.", "evidence_ids": ["evidence-1"]}
                        ],
                        "payload": {"summary": "Draft only."},
                        "headline": "Test",
                        "summary": "Test.",
                        "decision_rationale": "Evidence supports a review-required analyst brief.",
                        "context_used": ["evidence-1", "source-signal-1", "market-event-1"],
                    }
                ]
            }
        )
        token_provider = RecordingTokenProvider("test-token")
        route = ModelRouter(_catalog()).resolve(
            "analyst_brief_draft",
            data_classes=(DataClass.PUBLIC_EVIDENCE,),
        )
        client = ConfiguredModelClient(
            settings=ConfiguredModelClientSettings(
                azure_endpoint="https://example.openai.azure.com",
                azure_api_key=None,
                azure_api_version="2024-10-21",
                azure_auth_mode="managed_identity",
                azure_token_resource="https://cognitiveservices.azure.com/",
                azure_managed_identity_client_id="client-id-1",
                ollama_base_url="http://localhost:11434",
                timeout_seconds=3,
            ),
            transport=transport,
            token_provider=token_provider,
        )

        output = client.generate_structured(
            route=route,
            bundle=_bundle(),
            output_schema="shadow_analyst_drafts_v1",
        )

        self.assertIn("analyst_briefs", output)
        call = transport.calls[0]
        self.assertEqual("Bearer test-token", call["headers"]["Authorization"])
        self.assertNotIn("api-key", call["headers"])
        self.assertEqual(
            [("https://cognitiveservices.azure.com/", "client-id-1", 3)],
            token_provider.calls,
        )

    def test_azure_foundry_payload_uses_profile_reasoning_effort_without_temperature(self) -> None:
        transport = RecordingTransport(
            {
                "analyst_briefs": [
                    {
                        "evidence_ids": ["evidence-1"],
                        "material_claims": [
                            {"claim": "Test.", "evidence_ids": ["evidence-1"]}
                        ],
                        "payload": {"summary": "Draft only."},
                        "headline": "Test",
                        "summary": "Test.",
                        "decision_rationale": "Evidence supports a review-required analyst brief.",
                        "context_used": ["evidence-1", "source-signal-1", "market-event-1"],
                    }
                ]
            }
        )
        route = ModelRouter(_catalog(reasoning_effort="high")).resolve(
            "analyst_brief_draft",
            data_classes=(DataClass.PUBLIC_EVIDENCE,),
        )
        client = ConfiguredModelClient(
            settings=ConfiguredModelClientSettings(
                azure_endpoint="https://example.openai.azure.com",
                azure_api_key="test-secret",
                azure_api_version="2024-10-21",
                ollama_base_url="http://localhost:11434",
                timeout_seconds=3,
            ),
            transport=transport,
        )

        client.generate_structured(
            route=route,
            bundle=_bundle(),
            output_schema="shadow_analyst_drafts_v1",
        )

        payload = transport.calls[0]["payload"]
        self.assertEqual("high", payload["reasoning_effort"])
        self.assertNotIn("temperature", payload)

    def test_ollama_local_route_uses_local_chat_endpoint(self) -> None:
        transport = RecordingTransport(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "analyst_briefs": [
                                {
                                    "evidence_ids": ["evidence-1"],
                                    "material_claims": [
                                        {
                                            "claim": "Evidence remains review-only.",
                                            "evidence_ids": ["evidence-1"],
                                        }
                                    ],
                                    "payload": {"summary": "Local draft."},
                                    "headline": "AI infrastructure brief",
                                    "summary": "Review-only summary.",
                                    "decision_rationale": "Evidence supports a local review-required analyst brief.",
                                    "context_used": ["evidence-1", "source-signal-1", "market-event-1"],
                                }
                            ]
                        }
                    )
                }
            }
        )
        route = ModelRouter(_catalog(endpoint_type="local", provider="ollama")).resolve(
            "analyst_brief_draft",
            data_classes=(DataClass.PRIVATE_RESEARCH,),
        )
        client = ConfiguredModelClient(
            settings=ConfiguredModelClientSettings(
                azure_endpoint=None,
                azure_api_key=None,
                azure_api_version="2024-10-21",
                ollama_base_url="http://localhost:11434",
                timeout_seconds=3,
            ),
            transport=transport,
        )

        output = client.generate_structured(
            route=route,
            bundle=_bundle(data_class="private_research"),
            output_schema="shadow_analyst_drafts_v1",
        )

        self.assertIn("analyst_briefs", output)
        call = transport.calls[0]
        self.assertEqual("http://localhost:11434/api/chat", call["url"])
        self.assertEqual("test-deployment", call["payload"]["model"])
        self.assertFalse(call["payload"]["stream"])
        self.assertEqual("json", call["payload"]["format"])

    def test_default_config_routes_shadow_task_roles_without_hard_coded_model_selection(self) -> None:
        catalog = ModelProfileCatalog.from_mapping(_profile_mapping())
        router = ModelRouter(catalog)

        for task_role in SHADOW_ANALYST_TASK_ROLES:
            with self.subTest(task_role=task_role):
                route = router.resolve(task_role, data_classes=(DataClass.PUBLIC_EVIDENCE,))

                self.assertEqual(task_role, route.task_role)
                self.assertEqual("test-deployment", route.profile.deployment)
                self.assertIn("evidence_summary", route.profile.task_roles)


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
                "method": "POST",
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


class RecordingTokenProvider:
    def __init__(self, token: str) -> None:
        self.token = token
        self.calls: list[tuple[str, str | None, float]] = []

    def get_token(
        self,
        *,
        resource: str,
        client_id: str | None,
        timeout_seconds: float,
    ) -> str:
        self.calls.append((resource, client_id, timeout_seconds))
        return self.token


def _catalog(
    *,
    endpoint_type: str = "azure_ai_foundry",
    provider: str = "azure_foundry",
    reasoning_effort: str | None = None,
) -> ModelProfileCatalog:
    return ModelProfileCatalog.from_mapping(
        _profile_mapping(
            endpoint_type=endpoint_type,
            provider=provider,
            reasoning_effort=reasoning_effort,
        )
    )


def _profile_mapping(
    *,
    endpoint_type: str = "azure_ai_foundry",
    provider: str = "azure_foundry",
    reasoning_effort: str | None = None,
) -> dict[str, object]:
    allowed = [DataClass.PUBLIC_EVIDENCE.value, DataClass.DERIVED_ANALYTICS.value]
    if endpoint_type == "local":
        allowed.append(DataClass.PRIVATE_RESEARCH.value)
    profile: dict[str, object] = {
        "model_id": "test-model",
        "deployment": "test-deployment",
        "provider": provider,
        "endpoint_type": endpoint_type,
        "task_roles": ["evidence_summary"],
        "quota_rpm": None,
        "quota_tpm": None,
        "cost_class": "test",
        "max_context": "unknown",
        "privacy_class": "local" if endpoint_type == "local" else "cloud",
        "allowed_data_classes": allowed,
        "fallback_chain": [],
        "structured_output_support": True,
        "notes": "Test profile.",
    }
    if reasoning_effort is not None:
        profile["reasoning_effort"] = reasoning_effort
    return {
        "version": 1,
        "models": {"test_profile": profile},
    }


def _bundle(*, data_class: str = "public_evidence"):
    return build_daily_analyst_context_bundle(
        {
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
        },
        as_of=NOW,
    )


if __name__ == "__main__":
    unittest.main()
