"""EMA crossover baseline strategy.

Economic rationale:
- Short-term momentum can persist over brief horizons.
- A fast EMA crossing above a slow EMA indicates strengthening trend.
- A cross below indicates trend deterioration and exits to flat.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant.strategies.base import BaseStrategy, Signal, SignalDirection


@dataclass
class EmaCrossoverStrategy(BaseStrategy):
    symbol: str
    fast_period: int = 12
    slow_period: int = 26
    name: str = "ema_crossover"

    def __post_init__(self) -> None:
        if self.fast_period <= 1:
            raise ValueError("fast_period must be > 1.")
        if self.slow_period <= 1:
            raise ValueError("slow_period must be > 1.")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be smaller than slow_period.")

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        if len(data) < self.slow_period + 1:
            return []

        close = data["close"]
        ema_fast = close.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_period, adjust=False).mean()

        now_fast = float(ema_fast.iloc[-1])
        prev_fast = float(ema_fast.iloc[-2])
        now_slow = float(ema_slow.iloc[-1])
        prev_slow = float(ema_slow.iloc[-2])
        timestamp = str(data.index[-1])

        if prev_fast <= prev_slow and now_fast > now_slow:
            return [
                Signal(
                    symbol=self.symbol,
                    direction=SignalDirection.LONG,
                    strength=1.0,
                    timestamp=timestamp,
                    metadata={
                        "fast_ema": now_fast,
                        "slow_ema": now_slow,
                        "event": "crosses_above",
                    },
                )
            ]

        if prev_fast >= prev_slow and now_fast < now_slow:
            return [
                Signal(
                    symbol=self.symbol,
                    direction=SignalDirection.FLAT,
                    strength=1.0,
                    timestamp=timestamp,
                    metadata={
                        "fast_ema": now_fast,
                        "slow_ema": now_slow,
                        "event": "crosses_below",
                    },
                )
            ]

        return []
