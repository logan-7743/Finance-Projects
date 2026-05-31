"""Reusable performance metrics computed on net-of-cost equity curves."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PerformanceSummary:
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    annualized_return_pct: float


def summarize_equity_curve(
    equity_values: list[float],
    *,
    periods_per_year: int,
) -> PerformanceSummary:
    if len(equity_values) < 2:
        raise ValueError("Need at least two equity values.")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive.")

    equity = pd.Series(equity_values, dtype="float64")
    total_return = (float(equity.iloc[-1]) / float(equity.iloc[0])) - 1.0
    periods = max(len(equity_values) - 1, 1)
    annualized = ((1 + total_return) ** (periods_per_year / periods)) - 1.0

    returns = equity.pct_change().dropna()
    sharpe = 0.0
    if not returns.empty and returns.std() > 0:
        sharpe = float((returns.mean() / returns.std()) * math.sqrt(periods_per_year))

    running_max = equity.cummax()
    drawdowns = (equity / running_max) - 1.0
    max_drawdown = float(abs(drawdowns.min()) if not drawdowns.empty else 0.0)
    calmar = annualized / max_drawdown if max_drawdown > 0 else 0.0

    return PerformanceSummary(
        total_return_pct=total_return * 100,
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_drawdown * 100,
        calmar_ratio=calmar,
        annualized_return_pct=annualized * 100,
    )


def trade_expectancy(net_pnls: list[float]) -> float:
    if not net_pnls:
        return 0.0
    return sum(net_pnls) / len(net_pnls)
