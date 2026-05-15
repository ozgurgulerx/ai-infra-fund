from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
for path in (CORE_SRC,):
    sys.path.insert(0, str(path))


class MacroSeriesObservationTests(unittest.TestCase):
    def _build(self, **overrides: object):
        from ai_infra_fund_core.equity_intelligence.connectors import (
            MacroSeriesObservation,
        )

        defaults: dict[str, object] = dict(
            series_id="DFF",
            as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
            value=Decimal("5.33"),
            unit="percent",
            vintage_id="2026-05-02",
            source="fred",
            content_hash="abc123",
        )
        defaults.update(overrides)
        return MacroSeriesObservation(**defaults)

    def test_accepts_valid_observation(self) -> None:
        observation = self._build()
        self.assertEqual("DFF", observation.series_id)
        self.assertEqual(Decimal("5.33"), observation.value)
        self.assertEqual("percent", observation.unit)
        self.assertEqual("fred", observation.source)

    def test_allows_negative_value(self) -> None:
        observation = self._build(value=Decimal("-0.10"))
        self.assertEqual(Decimal("-0.10"), observation.value)

    def test_allows_missing_value(self) -> None:
        observation = self._build(value=None)
        self.assertIsNone(observation.value)

    def test_rejects_naive_datetime(self) -> None:
        with self.assertRaises(ValueError):
            self._build(as_of=datetime(2026, 5, 1))

    def test_rejects_empty_series_id(self) -> None:
        with self.assertRaises(ValueError):
            self._build(series_id="")

    def test_rejects_empty_unit(self) -> None:
        with self.assertRaises(ValueError):
            self._build(unit="")

    def test_rejects_empty_vintage_id(self) -> None:
        with self.assertRaises(ValueError):
            self._build(vintage_id="")

    def test_rejects_empty_source(self) -> None:
        with self.assertRaises(ValueError):
            self._build(source="")

    def test_rejects_empty_content_hash(self) -> None:
        with self.assertRaises(ValueError):
            self._build(content_hash="")


class StubMacroSeriesConnectorTests(unittest.TestCase):
    def test_returns_registered_observations(self) -> None:
        from ai_infra_fund_core.equity_intelligence.connectors import (
            MacroSeriesObservation,
            StubMacroSeriesConnector,
        )

        observation = MacroSeriesObservation(
            series_id="DFF",
            as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
            value=Decimal("5.33"),
            unit="percent",
            vintage_id="2026-05-02",
            source="fred",
            content_hash="hash-dff",
        )
        connector = StubMacroSeriesConnector(
            connector_id="stub-fred",
            observations={"DFF": (observation,)},
        )

        results = connector.fetch_series("DFF", since=None)
        self.assertEqual((observation,), results)

    def test_unknown_series_raises(self) -> None:
        from ai_infra_fund_core.equity_intelligence.connectors import (
            StubMacroSeriesConnector,
        )

        connector = StubMacroSeriesConnector(
            connector_id="stub-fred",
            observations={},
        )
        with self.assertRaises(KeyError):
            connector.fetch_series("UNKNOWN", since=None)

    def test_since_filters_observations(self) -> None:
        from ai_infra_fund_core.equity_intelligence.connectors import (
            MacroSeriesObservation,
            StubMacroSeriesConnector,
        )

        older = MacroSeriesObservation(
            series_id="DFF",
            as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
            value=Decimal("5.00"),
            unit="percent",
            vintage_id="2026-01-02",
            source="fred",
            content_hash="hash-old",
        )
        newer = MacroSeriesObservation(
            series_id="DFF",
            as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
            value=Decimal("5.33"),
            unit="percent",
            vintage_id="2026-05-02",
            source="fred",
            content_hash="hash-new",
        )
        connector = StubMacroSeriesConnector(
            connector_id="stub-fred",
            observations={"DFF": (older, newer)},
        )

        filtered = connector.fetch_series(
            "DFF", since=datetime(2026, 3, 1, tzinfo=timezone.utc)
        )
        self.assertEqual((newer,), filtered)


if __name__ == "__main__":
    unittest.main()
