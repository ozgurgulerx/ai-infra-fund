from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.evaluation.bias_checks import (  # noqa: E402
    check_lookahead_bias,
    check_recursive_indicator_consistency,
)


def ts(hour: int) -> datetime:
    return datetime(2026, 5, 14, hour, 0, tzinfo=timezone.utc)


class Phase7LookaheadBiasCheckTests(unittest.TestCase):
    def test_lookahead_check_passes_when_features_are_available_by_prediction_as_of(self) -> None:
        result = check_lookahead_bias(
            features=(
                {"feature_id": "f1", "available_at": ts(9)},
                {"feature_id": "f2", "available_at": ts(10)},
            ),
            predictions=(
                {"prediction_id": "p1", "feature_ids": ("f1",), "as_of": ts(10)},
                {"prediction_id": "p2", "feature_ids": ("f1", "f2"), "as_of": ts(11)},
            ),
        )

        self.assertTrue(result.passed)
        self.assertEqual((), result.violations)

    def test_lookahead_check_fails_when_feature_is_available_after_prediction_as_of(self) -> None:
        result = check_lookahead_bias(
            features=(
                {"feature_id": "f1", "available_at": ts(12)},
            ),
            predictions=(
                {"prediction_id": "p1", "feature_ids": ("f1",), "as_of": ts(11)},
            ),
        )

        self.assertFalse(result.passed)
        self.assertEqual(
            (
                "prediction p1 used feature f1 available at 2026-05-14T12:00:00+00:00 "
                "after prediction as_of 2026-05-14T11:00:00+00:00",
            ),
            result.violations,
        )

    def test_lookahead_check_requires_timezone_aware_datetimes(self) -> None:
        with self.assertRaises(ValueError):
            check_lookahead_bias(
                features=({"feature_id": "f1", "available_at": datetime(2026, 5, 14, 12, 0)},),
                predictions=({"prediction_id": "p1", "feature_ids": ("f1",), "as_of": ts(11)},),
            )


class Phase7RecursiveIndicatorConsistencyTests(unittest.TestCase):
    def test_recursive_indicator_check_passes_for_stable_prefix_outputs(self) -> None:
        result = check_recursive_indicator_consistency(
            baseline=(1.0, 1.5, 2.0),
            recomputed=(1.0, 1.5, 2.0, 2.5),
        )

        self.assertTrue(result.passed)
        self.assertEqual((), result.violations)

    def test_recursive_indicator_check_detects_unstable_recursive_output(self) -> None:
        result = check_recursive_indicator_consistency(
            baseline=(1.0, 1.5, 2.0),
            recomputed=(1.0, 1.6, 2.0, 2.5),
            tolerance=0.0,
        )

        self.assertFalse(result.passed)
        self.assertEqual(("indicator changed at index 1: baseline=1.5 recomputed=1.6",), result.violations)

    def test_recursive_indicator_check_allows_configured_tolerance(self) -> None:
        result = check_recursive_indicator_consistency(
            baseline=(1.0, 1.5, 2.0),
            recomputed=(1.0, 1.50001, 2.0),
            tolerance=0.0001,
        )

        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
