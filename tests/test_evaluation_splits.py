from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.evaluation.splits import (  # noqa: E402
    PurgedSplit,
    WalkForwardSplit,
    make_purged_cv_splits,
    make_walk_forward_splits,
)


class Phase7WalkForwardSplitTests(unittest.TestCase):
    def test_walk_forward_splits_preserve_chronological_order(self) -> None:
        periods = tuple(date(2026, 1, 1) + timedelta(days=offset) for offset in range(10))

        splits = make_walk_forward_splits(
            periods,
            train_size=4,
            test_size=2,
            step_size=2,
        )

        self.assertEqual(
            (
                WalkForwardSplit(train_indices=(0, 1, 2, 3), test_indices=(4, 5)),
                WalkForwardSplit(train_indices=(0, 1, 2, 3, 4, 5), test_indices=(6, 7)),
                WalkForwardSplit(train_indices=(0, 1, 2, 3, 4, 5, 6, 7), test_indices=(8, 9)),
            ),
            splits,
        )
        for split in splits:
            self.assertLess(max(split.train_indices), min(split.test_indices))

    def test_walk_forward_supports_rolling_train_window(self) -> None:
        periods = tuple(date(2026, 1, 1) + timedelta(days=offset) for offset in range(9))

        splits = make_walk_forward_splits(
            periods,
            train_size=4,
            test_size=2,
            step_size=2,
            expanding=False,
        )

        self.assertEqual(
            (
                WalkForwardSplit(train_indices=(0, 1, 2, 3), test_indices=(4, 5)),
                WalkForwardSplit(train_indices=(2, 3, 4, 5), test_indices=(6, 7)),
            ),
            splits,
        )

    def test_walk_forward_embargo_removes_overlapping_labels(self) -> None:
        periods = tuple(date(2026, 1, 1) + timedelta(days=offset) for offset in range(10))

        splits = make_walk_forward_splits(
            periods,
            train_size=5,
            test_size=2,
            step_size=2,
            label_horizon=3,
            embargo=1,
        )

        self.assertEqual(
            (
                WalkForwardSplit(train_indices=(0, 1), test_indices=(5, 6)),
                WalkForwardSplit(train_indices=(0, 1, 2, 3), test_indices=(7, 8)),
            ),
            splits,
        )

    def test_walk_forward_rejects_unsorted_periods(self) -> None:
        with self.assertRaises(ValueError):
            make_walk_forward_splits(
                (date(2026, 1, 2), date(2026, 1, 1)),
                train_size=1,
                test_size=1,
            )


class Phase7PurgedCvSplitTests(unittest.TestCase):
    def test_purged_cv_excludes_label_leakage_windows(self) -> None:
        periods = tuple(date(2026, 1, 1) + timedelta(days=offset) for offset in range(12))

        splits = make_purged_cv_splits(
            periods,
            folds=3,
            label_horizon=2,
            embargo=1,
        )

        self.assertEqual(
            (
                PurgedSplit(train_indices=(6, 7, 8, 9, 10, 11), test_indices=(0, 1, 2, 3)),
                PurgedSplit(train_indices=(0, 1, 10, 11), test_indices=(4, 5, 6, 7)),
                PurgedSplit(train_indices=(0, 1, 2, 3, 4, 5), test_indices=(8, 9, 10, 11)),
            ),
            splits,
        )
        for split in splits:
            self.assertTrue(set(split.train_indices).isdisjoint(split.test_indices))

    def test_purged_cv_rejects_invalid_fold_count(self) -> None:
        with self.assertRaises(ValueError):
            make_purged_cv_splits(
                (date(2026, 1, 1), date(2026, 1, 2)),
                folds=3,
                label_horizon=1,
            )


if __name__ == "__main__":
    unittest.main()
