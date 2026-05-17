from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Mapping, Protocol
from urllib import parse, request

from ai_infra_fund_core.contracts.common import canonicalize
from ai_infra_fund_core.model_routing.router import ResolvedModelRoute
from ai_infra_fund_core.shadow_analyst.bundles import AnalystContextBundle


DEFAULT_AZURE_API_VERSION = "2024-10-21"
DEFAULT_AZURE_AUTH_MODE = "api_key"
DEFAULT_AZURE_TOKEN_RESOURCE = "https://cognitiveservices.azure.com/"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 45.0

AZURE_AI_FOUNDRY_ENDPOINT_TYPE = "azure_ai_foundry"
LOCAL_ENDPOINT_TYPE = "local"
OLLAMA_PROVIDER = "ollama"

SHADOW_ANALYST_SECTION_BY_ROLE = {
    "segment_impact_analysis": ("segment_impacts",),
    "equity_impact_assessment": ("equity_impact_assessments",),
    "valuation_context_analysis": ("valuation_contexts",),
    "risk_regime_analysis": ("risk_regime_updates",),
    "trading_advisory_draft": ("trading_advisories",),
    "analyst_brief_draft": ("analyst_briefs",),
    "evidence_summary": (
        "segment_impacts",
        "equity_impact_assessments",
        "valuation_contexts",
        "risk_regime_updates",
        "trading_advisories",
        "analyst_briefs",
    ),
}


class ModelClientConfigurationError(RuntimeError):
    """Raised when a configured model route cannot be called safely."""


class ModelClientResponseError(RuntimeError):
    """Raised when a model provider returns an unusable structured response."""


class JsonHttpTransport(Protocol):
    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        ...


class BearerTokenProvider(Protocol):
    def get_token(
        self,
        *,
        resource: str,
        client_id: str | None,
        timeout_seconds: float,
    ) -> str:
        ...


@dataclass(frozen=True, slots=True)
class ConfiguredModelClientSettings:
    azure_endpoint: str | None
    azure_api_key: str | None
    azure_api_version: str = DEFAULT_AZURE_API_VERSION
    azure_auth_mode: str = DEFAULT_AZURE_AUTH_MODE
    azure_token_resource: str = DEFAULT_AZURE_TOKEN_RESOURCE
    azure_managed_identity_client_id: str | None = None
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_environment(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "ConfiguredModelClientSettings":
        source = env if env is not None else os.environ
        return cls(
            azure_endpoint=_optional_text(source.get("AZURE_AI_FOUNDRY_ENDPOINT")),
            azure_api_key=_optional_text(source.get("AZURE_AI_FOUNDRY_API_KEY")),
            azure_api_version=_optional_text(source.get("AZURE_AI_FOUNDRY_API_VERSION"))
            or DEFAULT_AZURE_API_VERSION,
            azure_auth_mode=(
                _optional_text(source.get("AZURE_AI_FOUNDRY_AUTH_MODE"))
                or DEFAULT_AZURE_AUTH_MODE
            ).lower(),
            azure_token_resource=(
                _optional_text(source.get("AZURE_AI_FOUNDRY_TOKEN_RESOURCE"))
                or DEFAULT_AZURE_TOKEN_RESOURCE
            ),
            azure_managed_identity_client_id=_optional_text(
                source.get("AZURE_AI_FOUNDRY_MANAGED_IDENTITY_CLIENT_ID")
            )
            or _optional_text(source.get("AZURE_CLIENT_ID")),
            ollama_base_url=_optional_text(source.get("OLLAMA_BASE_URL"))
            or DEFAULT_OLLAMA_BASE_URL,
            timeout_seconds=_timeout_seconds(
                source.get("AI_INFRA_FUND_MODEL_HTTP_TIMEOUT_SECONDS")
            ),
        )


class ConfiguredModelClient:
    def __init__(
        self,
        *,
        settings: ConfiguredModelClientSettings,
        transport: JsonHttpTransport | None = None,
        token_provider: BearerTokenProvider | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport or UrllibJsonTransport()
        self._token_provider = token_provider or ImdsBearerTokenProvider()

    @classmethod
    def from_environment(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        transport: JsonHttpTransport | None = None,
        token_provider: BearerTokenProvider | None = None,
    ) -> "ConfiguredModelClient":
        return cls(
            settings=ConfiguredModelClientSettings.from_environment(env),
            transport=transport,
            token_provider=token_provider,
        )

    def generate_structured(
        self,
        *,
        route: ResolvedModelRoute,
        bundle: AnalystContextBundle,
        output_schema: str,
    ) -> Mapping[str, object]:
        if not route.profile.structured_output_support:
            raise ModelClientConfigurationError(
                f"route {route.task_role} does not support structured output"
            )

        if route.profile.endpoint_type == AZURE_AI_FOUNDRY_ENDPOINT_TYPE:
            response = self._post_azure_chat(
                route=route,
                bundle=bundle,
                output_schema=output_schema,
            )
        elif (
            route.profile.endpoint_type == LOCAL_ENDPOINT_TYPE
            and route.profile.provider == OLLAMA_PROVIDER
        ):
            response = self._post_ollama_chat(
                route=route,
                bundle=bundle,
                output_schema=output_schema,
            )
        else:
            raise ModelClientConfigurationError(
                f"unsupported endpoint type for route {route.task_role}: {route.profile.endpoint_type}"
            )

        return _extract_structured_response(response)

    def _post_azure_chat(
        self,
        *,
        route: ResolvedModelRoute,
        bundle: AnalystContextBundle,
        output_schema: str,
    ) -> Mapping[str, object]:
        endpoint = _optional_text(self._settings.azure_endpoint)
        if endpoint is None:
            raise ModelClientConfigurationError("Azure model endpoint is not configured")

        deployment = parse.quote(route.profile.deployment, safe="")
        api_version = parse.quote(self._settings.azure_api_version, safe="")
        url = (
            f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={api_version}"
        )
        payload: dict[str, object] = {
            "messages": _messages(route=route, bundle=bundle, output_schema=output_schema),
            "response_format": {"type": "json_object"},
        }
        if route.profile.reasoning_effort is not None:
            payload["reasoning_effort"] = route.profile.reasoning_effort

        return self._transport.post_json(
            url=url,
            headers=self._azure_headers(),
            payload=payload,
            timeout_seconds=self._settings.timeout_seconds,
        )

    def _azure_headers(self) -> dict[str, str]:
        auth_mode = _optional_text(self._settings.azure_auth_mode) or DEFAULT_AZURE_AUTH_MODE
        if auth_mode == "api_key":
            credential = _optional_text(self._settings.azure_api_key)
            if credential is None:
                raise ModelClientConfigurationError("Azure model credential is not configured")
            return {
                "Content-Type": "application/json",
                "api-key": credential,
            }
        if auth_mode == "managed_identity":
            token = self._token_provider.get_token(
                resource=self._settings.azure_token_resource,
                client_id=self._settings.azure_managed_identity_client_id,
                timeout_seconds=self._settings.timeout_seconds,
            )
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
        raise ModelClientConfigurationError(f"unsupported Azure auth mode: {auth_mode}")

    def _post_ollama_chat(
        self,
        *,
        route: ResolvedModelRoute,
        bundle: AnalystContextBundle,
        output_schema: str,
    ) -> Mapping[str, object]:
        base_url = _optional_text(self._settings.ollama_base_url)
        if base_url is None:
            raise ModelClientConfigurationError("Ollama base URL is not configured")
        return self._transport.post_json(
            url=f"{base_url.rstrip('/')}/api/chat",
            headers={"Content-Type": "application/json"},
            payload={
                "model": route.profile.deployment,
                "messages": _messages(route=route, bundle=bundle, output_schema=output_schema),
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout_seconds=self._settings.timeout_seconds,
        )


class UrllibJsonTransport:
    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        req = request.Request(url, data=encoded, headers=headers, method="POST")
        with request.urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        decoded = json.loads(body)
        if not isinstance(decoded, Mapping):
            raise ModelClientResponseError("model response must be a JSON object")
        return decoded


class ImdsBearerTokenProvider:
    def get_token(
        self,
        *,
        resource: str,
        client_id: str | None,
        timeout_seconds: float,
    ) -> str:
        params: dict[str, str] = {
            "api-version": "2018-02-01",
            "resource": resource,
        }
        if client_id:
            params["client_id"] = client_id
        token_url = (
            "http://169.254.169.254/metadata/identity/oauth2/token?"
            + parse.urlencode(params)
        )
        req = request.Request(token_url, headers={"Metadata": "true"}, method="GET")
        with request.urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        decoded = json.loads(body)
        if not isinstance(decoded, Mapping):
            raise ModelClientResponseError("managed identity token response must be a JSON object")
        token = _optional_text(decoded.get("access_token"))
        if token is None:
            raise ModelClientResponseError("managed identity token response did not include an access token")
        return token


def _messages(
    *,
    route: ResolvedModelRoute,
    bundle: AnalystContextBundle,
    output_schema: str,
) -> list[dict[str, str]]:
    sections = SHADOW_ANALYST_SECTION_BY_ROLE.get(
        route.task_role,
        SHADOW_ANALYST_SECTION_BY_ROLE["evidence_summary"],
    )
    system = (
        "You are a governed AI infrastructure trading analyst. "
        "Return only valid JSON for review-required shadow analyst drafts. "
        "Do not produce broker, order, execution, accounting, PnL, target-weight, "
        "or deterministic risk outputs. Every material claim must reference supplied evidence IDs. "
        "Expose decision rationale and the supplied context used for trust, but do not reveal hidden chain-of-thought."
    )
    user_payload = {
        "task_role": route.task_role,
        "output_schema": output_schema,
        "required_top_level_sections": sections,
        "format_rules": (
            "Return a single JSON object using exactly the required_top_level_sections. "
            "Do not emit title, key_claims, brief_id, review_required, tickers_mentioned, "
            "recommended_next_checks, implications_for_portfolio, or near_term_triggers_to_watch. "
            "Do not invent IDs. evidence_ids must be a non-empty subset of supplied evidence_ids. "
            "context_used must be a non-empty subset of supplied evidence_ids or object_ids. "
            "Analyst brief wording must explicitly state advisory-only framing. "
            "For analyst_briefs, ticker_implications evidence_ids and material_claims evidence_ids "
            "must be non-empty subsets of the same top-level evidence_ids."
        ),
        "exact_output_contract": _exact_output_contract(sections),
        "scope": bundle.scope.value,
        "ticker": bundle.ticker,
        "as_of": bundle.as_of,
        "evidence_ids": bundle.evidence_ids,
        "object_ids": bundle.object_ids,
        "data_classes": tuple(data_class.value for data_class in bundle.data_classes),
        "context_rows": bundle.rows,
        "draft_contract": {
            "review_status": "review_required",
            "can_publish_directly": False,
            "material_claims": "Each material claim requires evidence_ids drawn from evidence_ids.",
            "trust_fields": {
                "trading_advisories": "Each item must include rationale and context_used.",
                "analyst_briefs": (
                    "Each item must include decision_rationale, context_used, supported_claim, "
                    "weak_inference, monitor_only_hypothesis, and ticker_implications with "
                    "invalidation_signal and evidence_ids."
                ),
                "context_used": "Use only supplied evidence_ids or object_ids.",
            },
        },
    }
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(canonicalize(user_payload), sort_keys=True),
        },
    ]


def _exact_output_contract(sections: tuple[str, ...]) -> dict[str, object]:
    base = {
        "evidence_ids": ["one or more IDs from supplied evidence_ids"],
        "material_claims": [
            {
                "claim": "plain-text material claim",
                "evidence_ids": ["one or more IDs from supplied evidence_ids"],
            }
        ],
        "payload": {"summary": "non-empty review notes only"},
    }
    contracts: dict[str, object] = {}
    if "segment_impacts" in sections:
        contracts["segment_impacts"] = [
            {
                **base,
                "segment_name": "AI infrastructure segment name",
                "linked_event_ids": ["IDs from supplied object_ids"],
                "first_order_tickers": ["ticker"],
                "second_order_tickers": ["ticker"],
            }
        ]
    if "equity_impact_assessments" in sections:
        contracts["equity_impact_assessments"] = [
            {
                **base,
                "ticker": "ticker",
                "assessment": "concise assessment",
                "bull_case": "evidence-linked bull case",
                "bear_case": "evidence-linked bear case",
                "risk_flags": ["risk flag"],
                "invalidation_condition": "falsifiable invalidation condition",
            }
        ]
    if "valuation_contexts" in sections:
        contracts["valuation_contexts"] = [
            {
                **base,
                "ticker": "ticker",
                "valuation_summary": "valuation context summary",
            }
        ]
    if "risk_regime_updates" in sections:
        contracts["risk_regime_updates"] = [
            {
                **base,
                "risk_type": "risk type",
                "affected_tickers": ["ticker"],
                "summary": "risk regime summary",
            }
        ]
    if "trading_advisories" in sections:
        contracts["trading_advisories"] = [
            {
                **base,
                "ticker": "ticker",
                "analyst_action": "watch | accumulate | hold | trim | avoid",
                "rationale": "decision rationale for trust",
                "context_used": ["IDs from supplied evidence_ids or object_ids"],
                "market_event_ids": ["IDs from supplied object_ids"],
            }
        ]
    if "analyst_briefs" in sections:
        contracts["analyst_briefs"] = [
            {
                **base,
                "headline": "brief headline",
                "summary": "brief summary",
                "decision_rationale": "why this brief matters and what decision it informs",
                "context_used": ["IDs from supplied evidence_ids or object_ids"],
                "supported_claim": "evidence-backed claim supported by supplied evidence_ids",
                "weak_inference": "clearly labeled inference that requires monitoring",
                "monitor_only_hypothesis": "watch-only hypothesis that is not publication-ready",
                "ticker_implications": [
                    {
                        "ticker": "ticker from supplied context",
                        "theme_or_segment": "AI infrastructure theme or segment",
                        "direction": "positive | negative | mixed | neutral",
                        "confidence_delta": "plain-text confidence change, not a score",
                        "time_horizon": "short | medium | long or comparable text",
                        "what_changed": "ticker-specific catalyst or update",
                        "why_it_matters": "ticker-specific implication",
                        "risk_flags": ["risk flag"],
                        "invalidation_signal": "falsifiable monitor that would weaken the implication",
                        "evidence_ids": ["one or more IDs from top-level evidence_ids"],
                        "advisory_stance": "watch | accumulate | hold | trim | avoid | exit-candidate | review",
                    }
                ],
            }
        ]
    return contracts


def _extract_structured_response(response: Mapping[str, object]) -> Mapping[str, object]:
    if _looks_like_shadow_payload(response):
        return response

    content = _chat_content(response)
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ModelClientResponseError("model response content is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ModelClientResponseError("model response content must decode to a JSON object")
    return decoded


def _chat_content(response: Mapping[str, object]) -> str:
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content

    message = response.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

    content = response.get("content")
    if isinstance(content, str) and content.strip():
        return content

    raise ModelClientResponseError("model response did not include JSON message content")


def _looks_like_shadow_payload(response: Mapping[str, object]) -> bool:
    return any(section in response for section in SHADOW_ANALYST_SECTION_BY_ROLE["evidence_summary"])


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _timeout_seconds(value: object) -> float:
    if value is None or not str(value).strip():
        return DEFAULT_TIMEOUT_SECONDS
    try:
        parsed = float(str(value))
    except ValueError as exc:
        raise ModelClientConfigurationError(
            "model HTTP timeout must be a positive number"
        ) from exc
    if parsed <= 0:
        raise ModelClientConfigurationError("model HTTP timeout must be positive")
    return parsed
