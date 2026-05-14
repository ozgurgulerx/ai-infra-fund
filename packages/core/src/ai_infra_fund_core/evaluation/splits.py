from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class WalkForwardSplit:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "train_indices", _normalize_indices(self.train_indices, "train_indices"))
        object.__setattr__(self, "test_indices", _normalize_indices(self.test_indices, "test_indices"))


@dataclass(frozen=True, slots=True)
class PurgedSplit:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "train_indices", _normalize_indices(self.train_indices, "train_indices"))
        object.__setattr__(self, "test_indices", _normalize_indices(self.test_indices, "test_indices"))


def make_walk_forward_splits(
    periods: Sequence[T],
    *,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
    expanding: bool = True,
    label_horizon: int = 1,
    embargo: int = 0,
) -> tuple[WalkForwardSplit, ...]:
    ordered_periods = _validate_periods(periods)
    step = test_size if step_size is None else step_size
    _require_positive_int(train_size, "train_size")
    _require_positive_int(test_size, "test_size")
    _require_positive_int(step, "step_size")
    _require_positive_int(label_horizon, "label_horizon")
    _require_non_negative_int(embargo, "embargo")

    if train_size + test_size > len(ordered_periods):
        raise ValueError("periods must contain at least train_size + test_size rows")

    splits: list[WalkForwardSplit] = []
    test_start = train_size
    while test_start + test_size <= len(ordered_periods):
        test_end = test_start + test_size - 1
        if expanding:
            train_candidates = range(0, test_start)
        else:
            train_candidates = range(test_start - train_size, test_start)

        train_indices = _purge_indices(
            train_candidates,
            test_start=test_start,
            test_end=test_end,
            label_horizon=label_horizon,
            embargo=embargo,
            row_count=len(ordered_periods),
        )
        splits.append(
            WalkForwardSplit(
                train_indices=train_indices,
                test_indices=tuple(range(test_start, test_start + test_size)),
            )
        )
        test_start += step

    return tuple(splits)


def make_purged_cv_splits(
    periods: Sequence[T],
    *,
    folds: int,
    label_horizon: int,
    embargo: int = 0,
) -> tuple[PurgedSplit, ...]:
    ordered_periods = _validate_periods(periods)
    _require_positive_int(folds, "folds")
    _require_positive_int(label_horizon, "label_horizon")
    _require_non_negative_int(embargo, "embargo")
    if folds < 2:
        raise ValueError("folds must be at least 2")
    if folds > len(ordered_periods):
        raise ValueError("folds must not exceed period count")

    splits: list[PurgedSplit] = []
    start = 0
    for fold_size in _fold_sizes(len(ordered_periods), folds):
        test_start = start
        test_end = start + fold_size - 1
        train_indices = _purge_indices(
            range(0, len(ordered_periods)),
            test_start=test_start,
            test_end=test_end,
            label_horizon=label_horizon,
            embargo=embargo,
            row_count=len(ordered_periods),
        )
        splits.append(
            PurgedSplit(
                train_indices=train_indices,
                test_indices=tuple(range(test_start, test_end + 1)),
            )
        )
        start += fold_size

    return tuple(splits)


def _purge_indices(
    candidate_indices: range,
    *,
    test_start: int,
    test_end: int,
    label_horizon: int,
    embargo: int,
    row_count: int,
) -> tuple[int, ...]:
    leakage_start = max(0, test_start - label_horizon - embargo + 1)
    leakage_end = min(row_count - 1, test_end + label_horizon + embargo - 1)
    return tuple(index for index in candidate_indices if index < leakage_start or index > leakage_end)


def _fold_sizes(row_count: int, folds: int) -> tuple[int, ...]:
    base_size = row_count // folds
    remainder = row_count % folds
    return tuple(base_size + (1 if fold_index < remainder else 0) for fold_index in range(folds))


def _validate_periods(periods: Sequence[T]) -> tuple[T, ...]:
    ordered_periods = tuple(periods)
    if not ordered_periods:
        raise ValueError("periods must not be empty")
    for previous, current in zip(ordered_periods, ordered_periods[1:]):
        if previous > current:  # type: ignore[operator]
            raise ValueError("periods must be sorted in chronological order")
    return ordered_periods


def _normalize_indices(indices: tuple[int, ...], field_name: str) -> tuple[int, ...]:
    normalized = tuple(indices)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if any(index < 0 for index in normalized):
        raise ValueError(f"{field_name} must not contain negative indices")
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} must be sorted and unique")
    return normalized


def _require_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
