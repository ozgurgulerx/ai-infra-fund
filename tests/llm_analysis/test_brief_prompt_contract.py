from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROMPT_PACK_PATH = ROOT / "docs" / "LLM_ANALYST_PROMPT_PACK.md"


class BriefPromptContractTests(unittest.TestCase):
    def test_brief_synthesizer_requires_ticker_specific_evidence_linked_implications(self) -> None:
        body = _role_section(PROMPT_PACK_PATH.read_text(encoding="utf-8"), "brief_synthesizer")

        required_phrases = (
            "advisory-only",
            "ticker_implications",
            "at least five ticker implications",
            "evidence_ids must be non-empty",
            "claim-level evidence IDs must be a subset of top-level evidence_ids",
            "invalidation_signal",
            "supported_claim",
            "weak_inference",
            "monitor_only_hypothesis",
            "review-required",
        )
        missing = [phrase for phrase in required_phrases if phrase not in body]

        self.assertEqual([], missing)


def _role_section(text: str, role_name: str) -> str:
    match = re.search(
        rf"^## Role: `{re.escape(role_name)}`\n(?P<body>.*?)(?=^## Role: |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else ""


if __name__ == "__main__":
    unittest.main()
