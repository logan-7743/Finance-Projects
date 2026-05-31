"""Strategy-based backtesting engine with explicit execution lag.

This module backtests any BaseStrategy implementation while enforcing a strict
timing contract:
- Signals are generated from data available up to bar t.
- Orders execute no earlier than bar t + execution_lag_bars.

The default configuration uses a 1-bar lag, which avoids same-bar fill bias.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
from pydantic import BaseModel, Field

from quant.data.base import OHLCVBar
from quant.risk.costs import CostModel
from quant.strategies import BaseStrategy, Signal, SignalDirection


class StrategyBacktestConfig(BaseModel):
    initial_capital: float = Field(default=100_000.0, gt=1_000.0)
    execution_lag_bars: int = Field(default=1, ge=1)
    min_bars_before_signals: int = Field(default=30, ge=2)
    allow_fractional_quantity: bool = True


class StrategyExecutedTrade(BaseModel):
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    net_pnl: float
    net_return_pct: float


class StrategyBacktestMetrics(BaseModel):
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


class StrategyBacktestResult(BaseModel):
    strategy_name: str
    symbol: str
    trades: list[StrategyExecutedTrade]
    metrics: StrategyBacktestMetrics
    equity_curve: list[tuple[str, float]]
    signal_count: int


@dataclass
class _Position:
    entry_time: str
    entry_price: float
    quantity: float
    entry_cost_total: float


@dataclass
class _PendingDirection:
    direction: SignalDirection
    execute_at_index: int


def run_strategy_backtest(
    *,
    symbol: str,
    bars: list[OHLCVBar],
    strategy: BaseStrategy,
    config: StrategyBacktestConfig | None = None,
    cost_model: CostModel | None = None,
) -> StrategyBacktestResult:
    cfg = config or StrategyBacktestConfig()
    model = cost_model or CostModel()

    if len(bars) < cfg.min_bars_before_signals:
        raise ValueError(
            f"Need at least {cfg.min_bars_before_signals} bars to run strategy backtest."
        )

    cash = cfg.initial_capital
    position: _Position | None = None
    trades: list[StrategyExecutedTrade] = []
    equity_curve: list[tuple[str, float]] = []
    pending: _PendingDirection | None = None
    signal_count = 0
    bars_in_position = 0

    for idx, bar in enumerate(bars):
        if pending is not None and pending.execute_at_index == idx:
            cash, position, trade = _execute_direction(
                direction=pending.direction,
                bar=bar,
                cash=cash,
                position=position,
                model=model,
                allow_fractional_quantity=cfg.allow_fractional_quantity,
            )
            if trade is not None:
                trades.append(trade)
            pending = None

        if idx + 1 >= cfg.min_bars_before_signals:
            signal = _latest_signal_for_time(
                strategy=strategy,
                symbol=symbol,
                bars=bars,
                index=idx,
            )
            if signal is not None:
                signal_count += 1
                execute_at = idx + cfg.execution_lag_bars
                if execute_at < len(bars):
                    pending = _PendingDirection(direction=signal.direction, execute_at_index=execute_at)

        if position is not None:
            bars_in_position += 1
            equity = cash + (position.quantity * bar.close)
        else:
            equity = cash
        equity_curve.append((bar.time, equity))

    if position is not None:
        final_bar = bars[-1]
        cash, _, trade = _execute_direction(
            direction=SignalDirection.FLAT,
            bar=final_bar,
            cash=cash,
            position=position,
            model=model,
            allow_fractional_quantity=cfg.allow_fractional_quantity,
        )
        if trade is not None:
            trades.append(trade)
        equity_curve[-1] = (final_bar.time, cash)

    metrics = _compute_metrics(
        bars=bars,
        initial_capital=cfg.initial_capital,
        ending_equity=cash,
        trades=trades,
        equity_curve=equity_curve,
        bars_in_position=bars_in_position,
    )
    return StrategyBacktestResult(
        strategy_name=strategy.name,
        symbol=symbol,
        trades=trades,
        metrics=metrics,
        equity_curve=equity_curve,
        signal_count=signal_count,
    )


def _latest_signal_for_time(
    *,
    strategy: BaseStrategy,
    symbol: str,
    bars: list[OHLCVBar],
    index: int,
) -> Signal | None:
    data = _bars_to_dataframe(bars[: index + 1])
    signals = strategy.generate_signals(data)
    if not signals:
        return None
    bar_time = bars[index].time
    matching = [sig for sig in signals if sig.symbol == symbol and sig.timestamp == bar_time]
    return matching[-1] if matching else None


def _bars_to_dataframe(bars: list[OHLCVBar]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "open": [bar.open for bar in bars],
            "high": [bar.high for bar in bars],
            "low": [bar.low for bar in bars],
            "close": [bar.close for bar in bars],
            "volume": [bar.volume for bar in bars],
        },
        index=[bar.time for bar in bars],
    )
    frame.index.name = "time"
    return frame


def _execute_direction(
    *,
    direction: SignalDirection,
    bar: OHLCVBar,
    cash: float,
    position: _Position | None,
    model: CostModel,
    allow_fractional_quantity: bool,
) -> tuple[float, _Position | None, StrategyExecutedTrade | None]:
    fill_price = bar.open
    trade: StrategyExecutedTrade | None = None

    if direction == SignalDirection.LONG and position is None:
        per_share_cost = model.estimate(fill_price, 1.0).total_per_share
        denom = fill_price + per_share_cost
        if denom <= 0:
            return cash, position, None
        quantity = cash / denom
        if not allow_fractional_quantity:
            quantity = math.floor(quantity)
        if quantity <= 0:
            return cash, position, None
        entry_cost = model.estimate(fill_price, quantity).total
        cash -= (quantity * fill_price) + entry_cost
        return (
            cash,
            _Position(
                entry_time=bar.time,
                entry_price=fill_price,
                quantity=quantity,
                entry_cost_total=entry_cost,
            ),
            None,
        )

    if direction in {SignalDirection.FLAT, SignalDirection.SHORT} and position is not None:
        exit_cost = model.estimate(fill_price, position.quantity).total
        gross_pnl = (fill_price - position.entry_price) * position.quantity
        net_pnl = gross_pnl - position.entry_cost_total - exit_cost
        cash += (position.quantity * fill_price) - exit_cost
        trade = StrategyExecutedTrade(
            entry_time=position.entry_time,
            exit_time=bar.time,
            entry_price=position.entry_price,
            exit_price=fill_price,
            quantity=position.quantity,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            net_return_pct=(net_pnl / (position.entry_price * position.quantity)) * 100,
        )
        return cash, None, trade

    return cash, position, trade


def _compute_metrics(
    *,
    bars: list[OHLCVBar],
    initial_capital: float,
    ending_equity: float,
    trades: list[StrategyExecutedTrade],
    equity_curve: list[tuple[str, float]],
    bars_in_position: int,
) -> StrategyBacktestMetrics:
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
    avg_trade_return = sum(trade.net_return_pct for trade in trades) / len(trades) if trades else 0.0
    gross_profit = sum(trade.net_pnl for trade in wins)
    gross_loss = abs(sum(trade.net_pnl for trade in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    exposure = (bars_in_position / len(bars) * 100) if bars else 0.0

    return StrategyBacktestMetrics(
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
