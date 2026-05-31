"""Multi-asset strategy backtesting engine.

This is the portfolio-oriented foundation for crypto research. It requires
aligned bars across symbols and enforces next-bar-or-later execution for every
signal, so strategy code cannot fill on the same bar that generated the signal.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pydantic import BaseModel, Field

from quant.data.base import OHLCVBar
from quant.risk.costs import CostModel
from quant.strategies import BaseStrategy, Signal, SignalDirection


class MultiAssetBacktestConfig(BaseModel):
    initial_capital: float = Field(default=100_000.0, gt=1_000.0)
    execution_lag_bars: int = Field(default=1, ge=1)
    min_bars_before_signals: int = Field(default=30, ge=2)
    max_position_weight: float = Field(default=0.2, gt=0.0, le=1.0)


class MultiAssetTrade(BaseModel):
    symbol: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    net_pnl: float
    net_return_pct: float


class MultiAssetMetrics(BaseModel):
    trade_count: int
    total_return_pct: float
    max_drawdown_pct: float
    ending_equity: float
    exposure_pct: float


class MultiAssetBacktestResult(BaseModel):
    trades: list[MultiAssetTrade]
    metrics: MultiAssetMetrics
    equity_curve: list[tuple[str, float]]
    final_positions: dict[str, float]
    signal_count: int


@dataclass
class _PortfolioPosition:
    entry_time: str
    entry_price: float
    quantity: float
    entry_cost_total: float


@dataclass
class _PendingOrder:
    symbol: str
    direction: SignalDirection
    execute_at_index: int


def run_multi_asset_backtest(
    *,
    symbol_bars: dict[str, list[OHLCVBar]],
    strategies: dict[str, BaseStrategy],
    config: MultiAssetBacktestConfig | None = None,
    cost_model: CostModel | None = None,
) -> MultiAssetBacktestResult:
    cfg = config or MultiAssetBacktestConfig()
    model = cost_model or CostModel()
    _validate_inputs(symbol_bars=symbol_bars, strategies=strategies, min_bars=cfg.min_bars_before_signals)

    symbols = list(symbol_bars.keys())
    timeline = [bar.time for bar in symbol_bars[symbols[0]]]
    cash = cfg.initial_capital
    positions: dict[str, _PortfolioPosition] = {}
    pending_orders: list[_PendingOrder] = []
    trades: list[MultiAssetTrade] = []
    equity_curve: list[tuple[str, float]] = []
    signal_count = 0
    bars_with_exposure = 0

    for idx, timestamp in enumerate(timeline):
        due_orders = [order for order in pending_orders if order.execute_at_index == idx]
        pending_orders = [order for order in pending_orders if order.execute_at_index != idx]
        for order in due_orders:
            cash, trade = _execute_order(
                order=order,
                bar=symbol_bars[order.symbol][idx],
                cash=cash,
                positions=positions,
                model=model,
                max_position_value=_portfolio_equity(
                    cash=cash,
                    positions=positions,
                    symbol_bars=symbol_bars,
                    index=idx,
                    use_open=True,
                )
                * cfg.max_position_weight,
            )
            if trade is not None:
                trades.append(trade)

        if idx + 1 >= cfg.min_bars_before_signals:
            for symbol in symbols:
                signal = _latest_signal_for_time(
                    strategy=strategies[symbol],
                    symbol=symbol,
                    bars=symbol_bars[symbol],
                    index=idx,
                )
                if signal is None:
                    continue
                signal_count += 1
                execute_at = idx + cfg.execution_lag_bars
                if execute_at < len(timeline):
                    pending_orders.append(
                        _PendingOrder(
                            symbol=symbol,
                            direction=signal.direction,
                            execute_at_index=execute_at,
                        )
                    )

        if positions:
            bars_with_exposure += 1
        equity_curve.append(
            (
                timestamp,
                _portfolio_equity(
                    cash=cash,
                    positions=positions,
                    symbol_bars=symbol_bars,
                    index=idx,
                    use_open=False,
                ),
            )
        )

    final_index = len(timeline) - 1
    for symbol in list(positions):
        cash, trade = _execute_order(
            order=_PendingOrder(symbol=symbol, direction=SignalDirection.FLAT, execute_at_index=final_index),
            bar=symbol_bars[symbol][final_index],
            cash=cash,
            positions=positions,
            model=model,
            max_position_value=0.0,
        )
        if trade is not None:
            trades.append(trade)
    equity_curve[-1] = (timeline[-1], cash)

    return MultiAssetBacktestResult(
        trades=trades,
        metrics=_compute_multi_asset_metrics(
            initial_capital=cfg.initial_capital,
            ending_equity=cash,
            equity_curve=equity_curve,
            trades=trades,
            bars_with_exposure=bars_with_exposure,
        ),
        equity_curve=equity_curve,
        final_positions={symbol: position.quantity for symbol, position in positions.items()},
        signal_count=signal_count,
    )


def _validate_inputs(
    *,
    symbol_bars: dict[str, list[OHLCVBar]],
    strategies: dict[str, BaseStrategy],
    min_bars: int,
) -> None:
    if not symbol_bars:
        raise ValueError("At least one symbol is required.")
    if set(symbol_bars) != set(strategies):
        raise ValueError("Strategies must be provided for exactly the same symbols as bars.")

    timelines: list[list[str]] = []
    for symbol, bars in symbol_bars.items():
        if len(bars) < min_bars:
            raise ValueError(f"Symbol {symbol} needs at least {min_bars} bars.")
        timelines.append([bar.time for bar in bars])
    first = timelines[0]
    if any(timeline != first for timeline in timelines[1:]):
        raise ValueError("Multi-asset backtest requires aligned timestamps across symbols.")


def _latest_signal_for_time(
    *,
    strategy: BaseStrategy,
    symbol: str,
    bars: list[OHLCVBar],
    index: int,
) -> Signal | None:
    data = _bars_to_dataframe(bars[: index + 1])
    matching = [
        signal
        for signal in strategy.generate_signals(data)
        if signal.symbol == symbol and signal.timestamp == bars[index].time
    ]
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


def _execute_order(
    *,
    order: _PendingOrder,
    bar: OHLCVBar,
    cash: float,
    positions: dict[str, _PortfolioPosition],
    model: CostModel,
    max_position_value: float,
) -> tuple[float, MultiAssetTrade | None]:
    position = positions.get(order.symbol)
    fill_price = bar.open
    if order.direction == SignalDirection.LONG and position is None:
        per_unit_cost = model.estimate(fill_price, 1.0).total_per_share
        budget = min(cash, max_position_value)
        quantity = budget / (fill_price + per_unit_cost)
        if quantity <= 0:
            return cash, None
        entry_cost = model.estimate(fill_price, quantity).total
        positions[order.symbol] = _PortfolioPosition(
            entry_time=bar.time,
            entry_price=fill_price,
            quantity=quantity,
            entry_cost_total=entry_cost,
        )
        return cash - (quantity * fill_price) - entry_cost, None

    if order.direction in {SignalDirection.FLAT, SignalDirection.SHORT} and position is not None:
        exit_cost = model.estimate(fill_price, position.quantity).total
        gross_pnl = (fill_price - position.entry_price) * position.quantity
        net_pnl = gross_pnl - position.entry_cost_total - exit_cost
        del positions[order.symbol]
        return (
            cash + (position.quantity * fill_price) - exit_cost,
            MultiAssetTrade(
                symbol=order.symbol,
                entry_time=position.entry_time,
                exit_time=bar.time,
                entry_price=position.entry_price,
                exit_price=fill_price,
                quantity=position.quantity,
                gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                net_return_pct=(net_pnl / (position.entry_price * position.quantity)) * 100,
            ),
        )
    return cash, None


def _portfolio_equity(
    *,
    cash: float,
    positions: dict[str, _PortfolioPosition],
    symbol_bars: dict[str, list[OHLCVBar]],
    index: int,
    use_open: bool,
) -> float:
    equity = cash
    for symbol, position in positions.items():
        bar = symbol_bars[symbol][index]
        price = bar.open if use_open else bar.close
        equity += position.quantity * price
    return equity


def _compute_multi_asset_metrics(
    *,
    initial_capital: float,
    ending_equity: float,
    equity_curve: list[tuple[str, float]],
    trades: list[MultiAssetTrade],
    bars_with_exposure: int,
) -> MultiAssetMetrics:
    equity = pd.Series([value for _, value in equity_curve])
    running_max = equity.cummax()
    drawdowns = (equity / running_max) - 1.0
    max_drawdown = float(abs(drawdowns.min()) * 100 if not drawdowns.empty else 0.0)
    exposure = bars_with_exposure / len(equity_curve) * 100 if equity_curve else 0.0
    return MultiAssetMetrics(
        trade_count=len(trades),
        total_return_pct=((ending_equity / initial_capital) - 1.0) * 100,
        max_drawdown_pct=max_drawdown,
        ending_equity=ending_equity,
        exposure_pct=exposure,
    )
