"""Tests for the cross-sectional momentum baseline."""

from quant.data.base import OHLCVBar
from quant.strategies import CrossSectionalMomentumConfig, rank_cross_sectional_momentum


def _bars(start: float, step: float, count: int = 20) -> list[OHLCVBar]:
    return [
        OHLCVBar(
            time=f"t{idx}",
            open=start + idx * step,
            high=start + idx * step + 1,
            low=start + idx * step - 1,
            close=start + idx * step,
            volume=100_000,
        )
        for idx in range(count)
    ]


def test_cross_sectional_momentum_ranks_symbols() -> None:
    signals = rank_cross_sectional_momentum(
        {
            "BTC-USD": _bars(100, 1),
            "SOL-USD": _bars(50, 3),
            "ETH-USD": _bars(200, -1),
        },
        as_of_index=12,
        config=CrossSectionalMomentumConfig(lookback_bars=6, top_n=1),
    )

    assert signals[0].symbol == "SOL-USD"
    assert signals[0].selected is True
    assert [signal.selected for signal in signals].count(True) == 1
