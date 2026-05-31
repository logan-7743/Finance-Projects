"""Statistical robustness helpers for strategy research."""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import NormalDist, mean


@dataclass(frozen=True)
class BootstrapInterval:
    lower: float
    median: float
    upper: float
    samples: int


def bootstrap_mean_interval(
    values: list[float],
    *,
    samples: int = 1_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> BootstrapInterval:
    if not values:
        raise ValueError("values cannot be empty.")
    if samples <= 0:
        raise ValueError("samples must be positive.")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1.")

    rng = random.Random(seed)
    estimates = sorted(mean(rng.choice(values) for _ in values) for _ in range(samples))
    lower_idx = int(((1 - confidence) / 2) * samples)
    upper_idx = min(samples - 1, int((1 - (1 - confidence) / 2) * samples))
    median_idx = samples // 2
    return BootstrapInterval(
        lower=estimates[lower_idx],
        median=estimates[median_idx],
        upper=estimates[upper_idx],
        samples=samples,
    )


def permutation_significance(
    signal_returns: list[float],
    *,
    benchmark: float = 0.0,
    permutations: int = 1_000,
    seed: int = 42,
) -> float:
    """Return one-sided p-value that mean signal return beats benchmark.

    The null randomly flips return signs, preserving magnitudes while destroying
    directional edge.
    """

    if not signal_returns:
        raise ValueError("signal_returns cannot be empty.")
    observed = mean(signal_returns) - benchmark
    rng = random.Random(seed)
    count_at_least_observed = 0
    for _ in range(permutations):
        permuted = [value if rng.random() >= 0.5 else -value for value in signal_returns]
        if mean(permuted) - benchmark >= observed:
            count_at_least_observed += 1
    return (count_at_least_observed + 1) / (permutations + 1)


def probabilistic_sharpe_ratio(
    *,
    observed_sharpe: float,
    benchmark_sharpe: float,
    sample_count: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    if sample_count <= 1:
        raise ValueError("sample_count must be > 1.")
    denominator = (1 - skew * observed_sharpe + ((kurtosis - 1) / 4) * observed_sharpe**2)
    if denominator <= 0:
        return 0.0
    z_score = ((observed_sharpe - benchmark_sharpe) * (sample_count - 1) ** 0.5) / denominator**0.5
    return NormalDist().cdf(z_score)
