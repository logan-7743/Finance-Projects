"""Abstract base class for all trading strategies.

Every strategy in this platform must subclass BaseStrategy and implement
generate_signals(). This enforces a consistent interface and ensures
strategies can be run through the backtest engine and live execution loop
interchangeably.

IMPORTANT (from 10-quant-rigor):
- Strategies must have a mathematical basis and an economic rationale.
- No overfitting. Fewer parameters are better.
- Always account for costs (slippage, fees, latency) when evaluating performance.
- Monitor for alpha decay in live trading.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd


class SignalDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class Signal:
    """A trading signal produced by a strategy."""

    symbol: str
    direction: SignalDirection
    strength: float  # 0.0–1.0; confidence or normalized score
    timestamp: str
    metadata: dict = field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract base for all trading strategies.

    Subclass this and implement generate_signals(). Add strategy-specific
    parameters to __init__ and document their economic rationale.
    """

    name: str = "unnamed_strategy"

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate trading signals from OHLCV data.

        Args:
            data: DataFrame with columns [open, high, low, close, volume]
                  indexed by timestamp. Data is adjusted for splits/dividends.

        Returns:
            List of Signal instances. Empty list means no signal.
        """
        ...

    def describe(self) -> dict:
        """Return a human-readable description of the strategy parameters."""
        return {"name": self.name}
