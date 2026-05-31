"""Tests for reusable performance/statistical metrics."""

from quant.metrics import (
    bootstrap_mean_interval,
    permutation_significance,
    probabilistic_sharpe_ratio,
    summarize_equity_curve,
    trade_expectancy,
)


def test_summarize_equity_curve_reports_drawdown_and_return() -> None:
    summary = summarize_equity_curve([100.0, 110.0, 105.0, 120.0], periods_per_year=365)

    assert round(summary.total_return_pct, 6) == 20.0
    assert summary.max_drawdown_pct > 0
    assert summary.annualized_return_pct > 0


def test_trade_expectancy_uses_net_pnl() -> None:
    assert trade_expectancy([10.0, -5.0, 4.0]) == 3.0


def test_bootstrap_interval_is_reproducible() -> None:
    interval = bootstrap_mean_interval([1.0, 2.0, 3.0], samples=100, seed=7)

    assert interval.samples == 100
    assert interval.lower <= interval.median <= interval.upper


def test_permutation_significance_returns_probability() -> None:
    p_value = permutation_significance([1.0, 1.5, 2.0, -0.2], permutations=100, seed=7)

    assert 0 <= p_value <= 1


def test_probabilistic_sharpe_ratio_bounds() -> None:
    value = probabilistic_sharpe_ratio(
        observed_sharpe=1.2,
        benchmark_sharpe=0.0,
        sample_count=100,
    )

    assert 0 <= value <= 1
