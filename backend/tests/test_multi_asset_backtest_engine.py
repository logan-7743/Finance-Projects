"""Tests for the portfolio-oriented multi-asset backtest engine."""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from quant.backtesting import MultiAssetBacktestConfig, run_multi_asset_backtest
from quant.data.base import OHLCVBar
from quant.strategies import BaseStrategy, Signal, SignalDirection


@dataclass
class _ScheduledStrategy(BaseStrategy):
    symbol: str
    schedule: dict[str, SignalDirection]
    name: str = "scheduled"

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        timestamp = str(data.index[-1])
        direction = self.schedule.get(timestamp)
        if direction is None:
            return []
        return [Signal(symbol=self.symbol, direction=direction, strength=1.0, timestamp=timestamp)]


def _bars(offset: float = 0.0, count: int = 12) -> list[OHLCVBar]:
    start = date(2025, 1, 1)
    bars: list[OHLCVBar] = []
    for idx in range(count):
        price = 100.0 + offset + idx
        bars.append(
            OHLCVBar(
                time=(start + timedelta(days=idx)).isoformat(),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.5,
                volume=100_000,
            )
        )
    return bars


def test_multi_asset_engine_tracks_positions_and_next_bar_execution() -> None:
    btc = _bars()
    eth = _bars(offset=50)
    result = run_multi_asset_backtest(
        symbol_bars={"BTC-USD": btc, "ETH-USD": eth},
        strategies={
            "BTC-USD": _ScheduledStrategy(
                symbol="BTC-USD",
                schedule={btc[2].time: SignalDirection.LONG, btc[5].time: SignalDirection.FLAT},
            ),
            "ETH-USD": _ScheduledStrategy(
                symbol="ETH-USD",
                schedule={eth[3].time: SignalDirection.LONG, eth[6].time: SignalDirection.FLAT},
            ),
        },
        config=MultiAssetBacktestConfig(
            initial_capital=100_000,
            min_bars_before_signals=2,
            execution_lag_bars=1,
            max_position_weight=0.25,
        ),
    )

    assert result.metrics.trade_count == 2
    assert result.trades[0].entry_time == btc[3].time
    assert result.trades[0].exit_time == btc[6].time
    assert result.trades[1].entry_time == eth[4].time
    assert result.trades[1].exit_time == eth[7].time
    assert result.final_positions == {}
    assert result.metrics.ending_equity > 0


def test_multi_asset_engine_rejects_unaligned_bars() -> None:
    btc = _bars()
    eth = _bars()
    eth[-1] = OHLCVBar(time="2030-01-01", open=1, high=1, low=1, close=1, volume=1)
    try:
        run_multi_asset_backtest(
            symbol_bars={"BTC-USD": btc, "ETH-USD": eth},
            strategies={
                "BTC-USD": _ScheduledStrategy(symbol="BTC-USD", schedule={}),
                "ETH-USD": _ScheduledStrategy(symbol="ETH-USD", schedule={}),
            },
            config=MultiAssetBacktestConfig(min_bars_before_signals=2),
        )
    except ValueError as exc:
        assert "aligned" in str(exc).lower()
    else:
        raise AssertionError("Expected unaligned bars to fail.")
