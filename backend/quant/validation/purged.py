"""Purged and embargoed folds for financial ML labels.

Each sample has a trade time index and an event/end index where the label is
resolved. Purging removes train samples whose label window overlaps a test
window. Embargo removes a buffer after the test fold.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Sequence


@dataclass(frozen=True)
class PurgedFold:
    fold: int
    train_indices: list[int]
    test_indices: list[int]
    purged_indices: list[int]
    embargoed_indices: list[int]


def make_purged_folds(
    *,
    sample_count: int,
    label_end_indices: Sequence[int],
    n_splits: int,
    embargo_pct: float = 0.0,
) -> list[PurgedFold]:
    if sample_count <= 0:
        raise ValueError("sample_count must be positive.")
    if len(label_end_indices) != sample_count:
        raise ValueError("label_end_indices length must match sample_count.")
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2.")
    if not 0 <= embargo_pct < 1:
        raise ValueError("embargo_pct must be in [0, 1).")

    fold_size = ceil(sample_count / n_splits)
    folds: list[PurgedFold] = []
    for fold in range(n_splits):
        test_start = fold * fold_size
        test_end = min(sample_count, test_start + fold_size)
        if test_start >= test_end:
            continue
        test_indices = list(range(test_start, test_end))
        embargo_size = ceil(sample_count * embargo_pct)
        embargo_start = test_end
        embargo_end = min(sample_count, test_end + embargo_size)

        purged: list[int] = []
        embargoed = list(range(embargo_start, embargo_end))
        train: list[int] = []
        for idx in range(sample_count):
            if test_start <= idx < test_end:
                continue
            if embargo_start <= idx < embargo_end:
                continue
            if _overlaps_test_window(idx, label_end_indices[idx], test_start, test_end - 1):
                purged.append(idx)
                continue
            train.append(idx)

        folds.append(
            PurgedFold(
                fold=fold + 1,
                train_indices=train,
                test_indices=test_indices,
                purged_indices=purged,
                embargoed_indices=embargoed,
            )
        )
    return folds


def _overlaps_test_window(
    sample_start: int,
    sample_end: int,
    test_start: int,
    test_end: int,
) -> bool:
    return sample_start <= test_end and sample_end >= test_start
