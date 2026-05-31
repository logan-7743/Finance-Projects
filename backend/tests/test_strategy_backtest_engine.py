"""Unit tests for strategy-based backtesting engine."""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from quant.backtesting import StrategyBacktestConfig, run_strategy_backtest
from quant.data.base import OHLCVBar
from quant.strategies import BaseStrategy, EmaCrossoverStrategy, Signal, SignalDirection


def _bars(count: int = 18) -> list[OHLCVBar]:
    base_pattern = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 104.0, 103.0, 102.0]
    bars: list[OHLCVBar] = []
    start = date(2025, 1, 1)
    for idx in range(count):
        price = base_pattern[idx % len(base_pattern)]
        timestamp = (start + timedelta(days=idx)).isoformat()
        bars.append(
            OHLCVBar(
                time=timestamp,
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.2,
                volume=100_000 + idx * 500,
            )
        )
    return bars


@dataclass
class _ScheduledSignalStrategy(BaseStrategy):
    symbol: str
    schedule: dict[str, SignalDirection]
    name: str = "scheduled_signal_strategy"

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        timestamp = str(data.index[-1])
        direction = self.schedule.get(timestamp)
        if direction is None:
            return []
        return [
            Signal(
                symbol=self.symbol,
                direction=direction,
                strength=1.0,
                timestamp=timestamp,
            )
        ]


def test_engine_executes_on_next_bar_open() -> None:
    bars = _bars()
    strategy = _ScheduledSignalStrategy(
        symbol="BTC-USD",
        schedule={
            bars[2].time: SignalDirection.LONG,
            bars[4].time: SignalDirection.FLAT,
        },
    )
    result = run_strategy_backtest(
        symbol="BTC-USD",
        bars=bars,
        strategy=strategy,
        config=StrategyBacktestConfig(
            initial_capital=10_000,
            min_bars_before_signals=2,
            execution_lag_bars=1,
        ),
    )

    assert result.metrics.trade_count == 1
    trade = result.trades[0]
    assert trade.entry_time == bars[3].time
    assert trade.entry_price == bars[3].open
    assert trade.exit_time == bars[5].time
    assert trade.exit_price == bars[5].open


def test_engine_ignores_signal_if_no_future_bar_to_execute() -> None:
    bars = _bars()
    strategy = _ScheduledSignalStrategy(
        symbol="BTC-USD",
        schedule={bars[-1].time: SignalDirection.LONG},
    )
    result = run_strategy_backtest(
        symbol="BTC-USD",
        bars=bars,
        strategy=strategy,
        config=StrategyBacktestConfig(
            initial_capital=10_000,
            min_bars_before_signals=2,
            execution_lag_bars=1,
        ),
    )

    assert result.metrics.trade_count == 0
    assert result.metrics.ending_equity == 10_000


def test_ema_crossover_strategy_backtest_runs() -> None:
    bars = _bars(count=120)
    strategy = EmaCrossoverStrategy(symbol="BTC-USD", fast_period=3, slow_period=6)
    result = run_strategy_backtest(
        symbol="BTC-USD",
        bars=bars,
        strategy=strategy,
        config=StrategyBacktestConfig(
            initial_capital=50_000,
            min_bars_before_signals=10,
            execution_lag_bars=1,
        ),
    )

    assert result.strategy_name == "ema_crossover"
    assert len(result.equity_curve) == len(bars)
    assert result.metrics.ending_equity > 0
