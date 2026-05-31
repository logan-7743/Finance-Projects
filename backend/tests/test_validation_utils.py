"""Tests for validation split utilities."""

from quant.validation import (
    make_chronological_splits,
    make_purged_folds,
    make_walk_forward_windows,
)


def test_chronological_splits_lock_final_holdout() -> None:
    timestamps = [f"2025-01-{idx + 1:02d}" for idx in range(20)]
    plan = make_chronological_splits(timestamps, train_fraction=0.5, validation_fraction=0.25)

    assert plan.train.start_index == 0
    assert plan.validation.start_index == plan.train.end_index
    assert plan.final_test.start_index == plan.validation.end_index
    assert plan.final_test_locked is True


def test_walk_forward_windows_are_chronological() -> None:
    timestamps = [f"t{idx}" for idx in range(12)]
    windows = make_walk_forward_windows(timestamps, train_size=5, test_size=2, step_size=2)

    assert len(windows) == 3
    assert windows[0].train.start_index == 0
    assert windows[0].test.start_index == 5
    assert windows[1].train.start_index == 2
    assert windows[1].test.start_index == 7


def test_purged_folds_remove_overlapping_label_windows_and_embargo() -> None:
    folds = make_purged_folds(
        sample_count=10,
        label_end_indices=[idx + 2 for idx in range(10)],
        n_splits=2,
        embargo_pct=0.1,
    )

    first = folds[0]
    assert first.test_indices == [0, 1, 2, 3, 4]
    assert 5 in first.embargoed_indices
    assert all(index not in first.train_indices for index in first.test_indices)
    assert all(index not in first.train_indices for index in first.embargoed_indices)
