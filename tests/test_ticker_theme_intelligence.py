from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "services" / "api" / "src"
WEB_ROOT = ROOT / "apps" / "web"
sys.path.insert(0, str(API_SRC))
sys.path.insert(0, str(ROOT / "tests"))

from test_advisory_workstation_read_model_repository import (  # noqa: E402
    ADVISORY_COLUMNS,
    ASSESSMENT_COLUMNS,
    LLM_NOTE_COLUMNS,
    MARKET_EVENT_COLUMNS,
    RISK_COLUMNS,
    SEGMENT_COLUMNS,
    SOURCE_SIGNAL_COLUMNS,
    TRADE_PLAN_COLUMNS,
    VALUATION_COLUMNS,
    FakeConnection,
    ResultSet,
    equity_assessment_row,
    llm_note_row,
    market_event_row,
    risk_regime_row,
    segment_impact_row,
    source_signal_row,
    trade_plan_row,
    trading_advisory_row,
    valuation_row,
)


def read_web(relative_path: str) -> str:
    return (WEB_ROOT / relative_path).read_text(encoding="utf-8")


class TickerThemeIntelligenceTests(unittest.TestCase):
    def test_backend_workbench_returns_theme_groups_with_advisory_stance_and_trace_links(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        payload = AdvisoryWorkstationRepository(_workbench_connection()).get_ticker_workbench("nvda")

        self.assertEqual("available", payload["status"])
        theme_groups = payload["theme_groups"]
        self.assertTrue(theme_groups)
        first = theme_groups[0]
        self.assertEqual("NVDA", first["ticker"])
        self.assertIn("theme_id", first)
        self.assertIn("why_now", first)
        self.assertIn("what_changed", first)
        self.assertIn("evidence_ids", first)
        self.assertEqual(["evidence-1"], first["evidence_ids"])
        self.assertTrue(first["source_signals"])
        self.assertTrue(first["market_events"])
        self.assertTrue(first["impact_assessments"])
        self.assertTrue(first["llm_notes"])
        self.assertTrue(first["trade_plan_notes"])
        self.assertTrue(first["related_tickers"])
        self.assertTrue(first["risk_flags"])
        self.assertTrue(first["invalidation"])
        self.assertTrue(first["next_watch_items"])
        stance = first["advisory_stance"]
        self.assertEqual("watch", stance["action"])
        self.assertEqual("neutral", stance["tone"])
        self.assertEqual("advisory-1", stance["source_advisory_id"])
        self.assertEqual(["evidence-1"], stance["evidence_ids"])
        self.assertEqual(["model-run-1"], stance["model_run_ids"])
        self.assertEqual(["source_signal_bundle_linked"], stance["deterministic_check_ids"])
        self.assertTrue(stance["advisory_only"])
        related = first["related_tickers"][0]
        self.assertIn("relationship_type", related)
        self.assertIn("reason", related)
        self.assertIn("relevance", first["market_events"][0])

    def test_suppressed_or_stale_advisory_cannot_leak_action_into_theme_stance(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        suppressed_advisory = list(trading_advisory_row())
        suppressed_advisory[-1] = {
            "source": "fixture",
            "readiness": {
                "publishable": False,
                "blocking_reasons": ["stale_source"],
            },
            "freshness": "stale",
        }
        payload = AdvisoryWorkstationRepository(
            _workbench_connection(advisory_row=tuple(suppressed_advisory))
        ).get_ticker_workbench("nvda")

        stance = payload["theme_groups"][0]["advisory_stance"]
        self.assertIn(stance["action"], {"review", "unrated"})
        self.assertIn(stance["freshness"], {"stale", "suppressed"})

    def test_backend_normalizes_json_like_source_display_text(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        payload = AdvisoryWorkstationRepository(
            _workbench_connection(
                source_signal_fixture=_source_signal_row_with_raw_title(),
                market_event_fixture=_market_event_row_with_raw_display_text(),
            )
        ).get_ticker_workbench("ceg")

        first = payload["theme_groups"][0]
        self.assertEqual(
            "Constellation power demand rises for data centers",
            first["why_now"],
        )
        self.assertEqual(
            "CEG nuclear capacity draws AI campus demand",
            first["what_changed"],
        )
        self.assertEqual(
            "CEG nuclear capacity draws AI campus demand",
            first["source_signals"][0]["title"],
        )
        self.assertEqual(
            "Power demand coverage notes nuclear capacity.",
            first["source_signals"][0]["summary"],
        )
        self.assertEqual(
            "Constellation power demand rises for data centers",
            first["market_events"][0]["catalyst"],
        )
        self.assertEqual(
            "Nuclear baseload capacity remains relevant for AI campus power.",
            first["market_events"][0]["ai_relevance"],
        )
        self.assertEqual(["evidence-1"], first["evidence_ids"])
        rendered_values = [
            first["why_now"],
            first["what_changed"],
            first["source_signals"][0]["title"],
            first["source_signals"][0]["summary"],
            first["market_events"][0]["catalyst"],
            first["market_events"][0]["ai_relevance"],
        ]
        for value in rendered_values:
            self.assertNotIn('{"articles"', value)
            self.assertNotIn("url_mobile", value)

    def test_backend_uses_safe_fallback_for_unextractable_raw_provider_payload(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        payload = AdvisoryWorkstationRepository(
            _workbench_connection(
                source_signal_fixture=_source_signal_row_with_unextractable_raw_title(),
                market_event_fixture=(
                    _market_event_row_with_unextractable_raw_display_text()
                ),
            )
        ).get_ticker_workbench("ceg")

        first = payload["theme_groups"][0]
        fallback = "Source captured; summary pending review"
        self.assertEqual(fallback, first["why_now"])
        self.assertEqual(fallback, first["what_changed"])
        self.assertEqual(fallback, first["source_signals"][0]["title"])
        self.assertEqual(fallback, first["source_signals"][0]["summary"])
        self.assertEqual(fallback, first["market_events"][0]["catalyst"])
        self.assertEqual(fallback, first["market_events"][0]["ai_relevance"])
        self.assertEqual(["evidence-1"], first["evidence_ids"])

    def test_ticker_page_uses_live_workbench_data_without_mock_default(self) -> None:
        page = read_web("app/ticker/[ticker]/page.tsx")
        advisory_lib = read_web("lib/advisory/ticker-workbench.ts")

        self.assertIn("readTickerWorkbenchPayload", advisory_lib)
        self.assertIn("/internal/ticker/", advisory_lib)
        self.assertIn("theme_groups", page)
        self.assertNotIn("mockWorkstationData", page)
        self.assertNotIn("mock-workstation-data", page)

    def test_ticker_page_renders_required_tabs_and_advisory_boundaries(self) -> None:
        page = read_web("app/ticker/[ticker]/page.tsx")
        required = [
            "Summary",
            "Themes",
            "News / Events",
            "Notes",
            "Related Tickers",
            "Risks",
            "Evidence",
            "Advisory-only",
            "readiness",
            "suppression",
        ]

        self.assertEqual([], [text for text in required if text not in page])
        forbidden = [
            r">\s*Buy\s*<",
            r">\s*Sell\s*<",
            r">\s*Place\s+Order\s*<",
            r">\s*Submit\s+Order\s*<",
            r">\s*Execute",
            r"broker",
        ]
        offenders = [
            pattern
            for pattern in forbidden
            if re.search(pattern, page, re.IGNORECASE)
        ]
        self.assertEqual([], offenders)


def _workbench_connection(
    *,
    advisory_row: tuple[object, ...] | None = None,
    market_event_fixture: tuple[object, ...] | None = None,
    source_signal_fixture: tuple[object, ...] | None = None,
) -> FakeConnection:
    return FakeConnection(
        [
            ResultSet(
                [source_signal_fixture or source_signal_row()],
                SOURCE_SIGNAL_COLUMNS,
            ),
            ResultSet(
                [market_event_fixture or market_event_row()],
                MARKET_EVENT_COLUMNS,
            ),
            ResultSet([segment_impact_row()], SEGMENT_COLUMNS),
            ResultSet([equity_assessment_row()], ASSESSMENT_COLUMNS),
            ResultSet([valuation_row()], VALUATION_COLUMNS),
            ResultSet([advisory_row or trading_advisory_row()], ADVISORY_COLUMNS),
            ResultSet([trade_plan_row()], TRADE_PLAN_COLUMNS),
            ResultSet([risk_regime_row()], RISK_COLUMNS),
            ResultSet([llm_note_row()], LLM_NOTE_COLUMNS),
        ]
    )


def _source_signal_row_with_raw_title() -> tuple[object, ...]:
    row = list(source_signal_row())
    row[3] = (
        '{"articles":[{"title":"CEG nuclear capacity draws AI campus demand",'
        '"summary":"Power demand coverage notes nuclear capacity.",'
        '"url":"https://example.test/ceg",'
        '"url_mobile":"https://m.example.test/ceg"}]}'
    )
    row[6] = ["CEG"]
    row[7] = ["datacenter power procurement"]
    return tuple(row)


def _market_event_row_with_raw_display_text() -> tuple[object, ...]:
    row = list(market_event_row())
    row[4] = ["CEG"]
    row[5] = ["Constellation Energy"]
    row[6] = ["datacenter power procurement"]
    row[7] = (
        '{"articles":[{"title":"Constellation power demand rises for data centers",'
        '"url":"https://example.test/power"}]}'
    )
    row[8] = (
        '{"summary":"Nuclear baseload capacity remains relevant for AI campus power.",'
        '"url_mobile":"https://m.example.test/power"}'
    )
    return tuple(row)


def _source_signal_row_with_unextractable_raw_title() -> tuple[object, ...]:
    row = list(_source_signal_row_with_raw_title())
    row[3] = (
        '{"articles":[{"url":"https://example.test/ceg",'
        '"url_mobile":"https://m.example.test/ceg"}]}'
    )
    return tuple(row)


def _market_event_row_with_unextractable_raw_display_text() -> tuple[object, ...]:
    row = list(_market_event_row_with_raw_display_text())
    row[7] = (
        '{"articles":[{"url":"https://example.test/power",'
        '"url_mobile":"https://m.example.test/power"}]}'
    )
    row[8] = '{"url":"https://example.test/power"}'
    return tuple(row)


if __name__ == "__main__":
    unittest.main()
