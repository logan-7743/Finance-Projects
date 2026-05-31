"""Walk-forward validation windows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from quant.validation.splits import DatasetSplit


@dataclass(frozen=True)
class WalkForwardWindow:
    fold: int
    train: DatasetSplit
    test: DatasetSplit


def make_walk_forward_windows(
    timestamps: Sequence[str],
    *,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> list[WalkForwardWindow]:
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive.")
    step = step_size or test_size
    if step <= 0:
        raise ValueError("step_size must be positive.")

    windows: list[WalkForwardWindow] = []
    start = 0
    fold = 1
    while start + train_size + test_size <= len(timestamps):
        train_start = start
        train_end = start + train_size
        test_end = train_end + test_size
        windows.append(
            WalkForwardWindow(
                fold=fold,
                train=_split("train", timestamps, train_start, train_end),
                test=_split("test", timestamps, train_end, test_end),
            )
        )
        fold += 1
        start += step

    if not windows:
        raise ValueError("No walk-forward windows fit the provided timestamps.")
    return windows


def _split(name: str, timestamps: Sequence[str], start: int, end: int) -> DatasetSplit:
    return DatasetSplit(
        name=name,
        start_index=start,
        end_index=end,
        start_time=timestamps[start],
        end_time=timestamps[end - 1],
    )
