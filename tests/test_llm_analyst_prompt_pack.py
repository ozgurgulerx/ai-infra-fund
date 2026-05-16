from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PACK_PATH = ROOT / "docs" / "LLM_ANALYST_PROMPT_PACK.md"

REQUIRED_ROLES = [
    "source_signal_monitor",
    "market_event_extractor",
    "segment_mapping_reviewer",
    "fundamental_snapshot_reviewer",
    "valuation_context_analyst",
    "macro_regime_reviewer",
    "equity_thesis_analyst",
    "risk_regime_reviewer",
    "trading_advisory_synthesizer",
    "trade_plan_critic",
    "portfolio_exposure_explainer",
    "brief_synthesizer",
    "outcome_reviewer",
    "llm_note_reviewer",
]

REQUIRED_ROLE_SECTIONS = [
    "Allowed inputs",
    "Allowed outputs",
    "Forbidden outputs",
    "Schema expectations",
    "ModelRun audit requirements",
    "Escalation and fallback",
]

REQUIRED_POLICY_PHRASES = [
    "Every analyst evaluation and decision point must be LLM-mediated",
    "config/model_profiles.yaml",
    "ModelRun",
    "private research is local-only by default",
    "data-class policy",
    "advisory-only",
    "LLMs must not generate final deterministic scores",
    "target weights",
    "constraints",
    "PnL",
    "executable trade instructions",
]

FORBIDDEN_PROMPT_TERMS = [
    "place an order",
    "submit an order",
    "execute a trade",
    "route to broker",
    "broker credentials",
    "order ticket",
    "gpt-",
    "deepseek",
    "kimi",
    "qwen",
    "ollama",
]


def read_prompt_pack() -> str:
    return PROMPT_PACK_PATH.read_text(encoding="utf-8")


def role_section(text: str, role_name: str) -> str:
    match = re.search(
        rf"^## Role: `{re.escape(role_name)}`\n(?P<body>.*?)(?=^## Role: |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else ""


class LlmAnalystPromptPackTests(unittest.TestCase):
    def test_prompt_pack_defines_required_roles(self) -> None:
        text = read_prompt_pack()
        missing = [role for role in REQUIRED_ROLES if f"## Role: `{role}`" not in text]
        self.assertEqual([], missing)

    def test_each_role_has_required_contract_sections(self) -> None:
        text = read_prompt_pack()
        missing: dict[str, list[str]] = {}
        for role in REQUIRED_ROLES:
            body = role_section(text, role)
            self.assertTrue(body, role)
            missing_sections = [
                section for section in REQUIRED_ROLE_SECTIONS if f"### {section}" not in body
            ]
            if missing_sections:
                missing[role] = missing_sections
        self.assertEqual({}, missing)

    def test_pack_states_routing_audit_and_boundary_policies(self) -> None:
        text = read_prompt_pack()
        missing = [phrase for phrase in REQUIRED_POLICY_PHRASES if phrase not in text]
        self.assertEqual([], missing)

    def test_pack_avoids_execution_and_hard_coded_model_language(self) -> None:
        text = read_prompt_pack().lower()
        present = [term for term in FORBIDDEN_PROMPT_TERMS if term in text]
        self.assertEqual([], present)


if __name__ == "__main__":
    unittest.main()
