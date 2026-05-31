"""Simple indicator rule backtesting engine (long-only, net-of-cost)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from quant.data.base import OHLCVBar
from quant.indicators import IndicatorRequest, IndicatorSeries, compute_indicators
from quant.risk.costs import CostModel

RuleOperator = Literal["gt", "lt", "crosses_above", "crosses_below"]
RuleRightType = Literal["indicator", "value"]


class BacktestRule(BaseModel):
    left_indicator_id: str
    left_line_key: str
    operator: RuleOperator
    right_type: RuleRightType
    right_indicator_id: str | None = None
    right_line_key: str | None = None
    right_value: float | None = None


class BacktestConfig(BaseModel):
    initial_capital: float = Field(default=100_000, gt=1_000)
    entry_rules: list[BacktestRule]
    exit_rules: list[BacktestRule]


class ExecutedTrade(BaseModel):
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    net_pnl: float
    net_return_pct: float


class BacktestMetrics(BaseModel):
    trade_count: int
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    win_rate_pct: float
    avg_trade_return_pct: float
    exposure_pct: float
    profit_factor: float
    ending_equity: float


class BacktestResult(BaseModel):
    indicators: list[IndicatorSeries]
    trades: list[ExecutedTrade]
    metrics: BacktestMetrics
    equity_curve: list[tuple[str, float]]


@dataclass
class _Position:
    entry_time: str
    entry_price: float
    quantity: float
    entry_cost: float
    bars_held: int = 0


def run_indicator_rules_backtest(
    *,
    bars: list[OHLCVBar],
    indicator_requests: list[IndicatorRequest],
    config: BacktestConfig,
    cost_model: CostModel | None = None,
) -> BacktestResult:
    if len(bars) < 30:
        raise ValueError("Need at least 30 bars to run backtest.")
    if not config.entry_rules:
        raise ValueError("At least one entry rule is required.")
    if not config.exit_rules:
        raise ValueError("At least one exit rule is required.")

    model = cost_model or CostModel()
    indicators = compute_indicators(bars=bars, requests=indicator_requests, since=None)
    value_map = _build_value_map(indicators)

    position: _Position | None = None
    cash = config.initial_capital
    trades: list[ExecutedTrade] = []
    equity_curve: list[tuple[str, float]] = []
    bars_in_position = 0

    for idx, bar in enumerate(bars):
        current_values = value_map.get(bar.time, {})
        close_price = bar.close

        if position is not None:
            position.bars_held += 1
            bars_in_position += 1
            should_exit = _evaluate_rules(
                rules=config.exit_rules,
                values=value_map,
                bars=bars,
                index=idx,
            )
            if should_exit:
                exit_cost = model.estimate(close_price, position.quantity).total
                gross_pnl = (close_price - position.entry_price) * position.quantity
                net_pnl = gross_pnl - position.entry_cost - exit_cost
                cash += (position.quantity * close_price) - exit_cost
                trade = ExecutedTrade(
                    entry_time=position.entry_time,
                    exit_time=bar.time,
                    entry_price=position.entry_price,
                    exit_price=close_price,
                    quantity=position.quantity,
                    gross_pnl=gross_pnl,
                    net_pnl=net_pnl,
                    net_return_pct=(net_pnl / (position.entry_price * position.quantity)) * 100,
                )
                trades.append(trade)
                position = None
        else:
            should_enter = _evaluate_rules(
                rules=config.entry_rules,
                values=value_map,
                bars=bars,
                index=idx,
            )
            if should_enter:
                quantity = math.floor(cash / close_price)
                if quantity > 0:
                    entry_cost = model.estimate(close_price, quantity).total
                    cash -= (quantity * close_price) + entry_cost
                    position = _Position(
                        entry_time=bar.time,
                        entry_price=close_price,
                        quantity=quantity,
                        entry_cost=entry_cost,
                    )

        equity = cash if position is None else cash + (position.quantity * close_price)
        equity_curve.append((bar.time, equity))

        # If the indicator map is sparse, keep processing bars; rule evaluation handles missing.
        _ = current_values

    if position is not None:
        final_price = bars[-1].close
        exit_cost = model.estimate(final_price, position.quantity).total
        gross_pnl = (final_price - position.entry_price) * position.quantity
        net_pnl = gross_pnl - position.entry_cost - exit_cost
        cash += (position.quantity * final_price) - exit_cost
        trades.append(
            ExecutedTrade(
                entry_time=position.entry_time,
                exit_time=bars[-1].time,
                entry_price=position.entry_price,
                exit_price=final_price,
                quantity=position.quantity,
                gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                net_return_pct=(net_pnl / (position.entry_price * position.quantity)) * 100,
            )
        )
        equity_curve[-1] = (bars[-1].time, cash)

    metrics = _compute_metrics(
        bars=bars,
        initial_capital=config.initial_capital,
        ending_equity=cash,
        trades=trades,
        equity_curve=equity_curve,
        bars_in_position=bars_in_position,
    )
    return BacktestResult(
        indicators=indicators,
        trades=trades,
        metrics=metrics,
        equity_curve=equity_curve,
    )


def _build_value_map(indicators: list[IndicatorSeries]) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, float]] = {}
    for indicator in indicators:
        for line in indicator.lines:
            key = f"{indicator.id}:{line.key}"
            for point in line.points:
                if point.time not in values:
                    values[point.time] = {}
                values[point.time][key] = point.value
    return values


def _evaluate_rules(
    *,
    rules: list[BacktestRule],
    values: dict[str, dict[str, float]],
    bars: list[OHLCVBar],
    index: int,
) -> bool:
    if index <= 0:
        return False
    for rule in rules:
        if not _evaluate_rule(rule=rule, values=values, bars=bars, index=index):
            return False
    return True


def _evaluate_rule(
    *,
    rule: BacktestRule,
    values: dict[str, dict[str, float]],
    bars: list[OHLCVBar],
    index: int,
) -> bool:
    current_time = bars[index].time
    prev_time = bars[index - 1].time
    current = values.get(current_time, {})
    previous = values.get(prev_time, {})
    left_key = f"{rule.left_indicator_id}:{rule.left_line_key}"
    left_now = current.get(left_key)
    left_prev = previous.get(left_key)
    if left_now is None:
        return False

    right_now, right_prev = _resolve_right_values(rule=rule, current=current, previous=previous)
    if right_now is None:
        return False

    if rule.operator == "gt":
        return left_now > right_now
    if rule.operator == "lt":
        return left_now < right_now
    if left_prev is None or right_prev is None:
        return False
    if rule.operator == "crosses_above":
        return left_prev <= right_prev and left_now > right_now
    if rule.operator == "crosses_below":
        return left_prev >= right_prev and left_now < right_now
    return False


def _resolve_right_values(
    *,
    rule: BacktestRule,
    current: dict[str, float],
    previous: dict[str, float],
) -> tuple[float | None, float | None]:
    if rule.right_type == "value":
        if rule.right_value is None:
            return None, None
        return float(rule.right_value), float(rule.right_value)
    if rule.right_indicator_id is None or rule.right_line_key is None:
        return None, None
    key = f"{rule.right_indicator_id}:{rule.right_line_key}"
    return current.get(key), previous.get(key)


def _compute_metrics(
    *,
    bars: list[OHLCVBar],
    initial_capital: float,
    ending_equity: float,
    trades: list[ExecutedTrade],
    equity_curve: list[tuple[str, float]],
    bars_in_position: int,
) -> BacktestMetrics:
    total_return_pct = ((ending_equity / initial_capital) - 1.0) * 100
    years = _estimate_years(bars)
    annualized_return = (
        ((ending_equity / initial_capital) ** (1 / years) - 1.0) * 100 if years > 0 else 0.0
    )

    equity = pd.Series([value for _, value in equity_curve])
    returns = equity.pct_change().dropna()
    sharpe = 0.0
    if not returns.empty and returns.std() > 0:
        periods_per_year = max(1, round(len(bars) / max(years, 1e-9)))
        sharpe = float((returns.mean() / returns.std()) * math.sqrt(periods_per_year))

    running_max = equity.cummax()
    drawdowns = (equity / running_max) - 1.0
    max_drawdown = float(abs(drawdowns.min()) * 100 if not drawdowns.empty else 0.0)
    calmar = annualized_return / max_drawdown if max_drawdown > 0 else 0.0

    wins = [trade for trade in trades if trade.net_pnl > 0]
    losses = [trade for trade in trades if trade.net_pnl < 0]
    win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
    avg_trade_return = (
        sum(trade.net_return_pct for trade in trades) / len(trades) if trades else 0.0
    )
    gross_profit = sum(trade.net_pnl for trade in wins)
    gross_loss = abs(sum(trade.net_pnl for trade in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    exposure = (bars_in_position / len(bars) * 100) if bars else 0.0

    return BacktestMetrics(
        trade_count=len(trades),
        total_return_pct=total_return_pct,
        annualized_return_pct=annualized_return,
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_drawdown,
        calmar_ratio=calmar,
        win_rate_pct=win_rate,
        avg_trade_return_pct=avg_trade_return,
        exposure_pct=exposure,
        profit_factor=profit_factor,
        ending_equity=ending_equity,
    )


def _estimate_years(bars: list[OHLCVBar]) -> float:
    if len(bars) < 2:
        return 0.0
    start = _parse_time(bars[0].time)
    end = _parse_time(bars[-1].time)
    delta_days = max((end - start).days, 1)
    return delta_days / 365.25


def _parse_time(value: str) -> datetime:
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
