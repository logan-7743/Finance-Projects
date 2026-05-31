"""Chronological train/validation/final-test split helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class DatasetSplit:
    name: str
    start_index: int
    end_index: int
    start_time: str
    end_time: str

    @property
    def length(self) -> int:
        return self.end_index - self.start_index


@dataclass(frozen=True)
class SplitPlan:
    train: DatasetSplit
    validation: DatasetSplit
    final_test: DatasetSplit
    final_test_locked: bool = True


def make_chronological_splits(
    timestamps: Sequence[str],
    *,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> SplitPlan:
    if len(timestamps) < 10:
        raise ValueError("Need at least 10 timestamps to create research splits.")
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1.")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1.")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train + validation fractions must leave room for final test.")

    train_end = int(len(timestamps) * train_fraction)
    validation_end = int(len(timestamps) * (train_fraction + validation_fraction))
    if train_end == 0 or validation_end <= train_end or validation_end >= len(timestamps):
        raise ValueError("Split fractions produced an empty split.")

    return SplitPlan(
        train=_split("train", timestamps, 0, train_end),
        validation=_split("validation", timestamps, train_end, validation_end),
        final_test=_split("final_test", timestamps, validation_end, len(timestamps)),
    )


def _split(name: str, timestamps: Sequence[str], start: int, end: int) -> DatasetSplit:
    return DatasetSplit(
        name=name,
        start_index=start,
        end_index=end,
        start_time=timestamps[start],
        end_time=timestamps[end - 1],
    )
