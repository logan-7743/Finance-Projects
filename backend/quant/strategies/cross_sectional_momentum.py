"""Cross-sectional momentum baseline for crypto portfolios."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from quant.data.base import OHLCVBar


class RankedMomentumSignal(BaseModel):
    symbol: str
    momentum_return: float
    rank: int
    selected: bool


@dataclass(frozen=True)
class CrossSectionalMomentumConfig:
    lookback_bars: int = 12
    top_n: int = 3
    min_return_threshold: float = 0.0

    def __post_init__(self) -> None:
        if self.lookback_bars <= 0:
            raise ValueError("lookback_bars must be positive.")
        if self.top_n <= 0:
            raise ValueError("top_n must be positive.")


def rank_cross_sectional_momentum(
    symbol_bars: dict[str, list[OHLCVBar]],
    *,
    as_of_index: int,
    config: CrossSectionalMomentumConfig | None = None,
) -> list[RankedMomentumSignal]:
    cfg = config or CrossSectionalMomentumConfig()
    if as_of_index < cfg.lookback_bars:
        raise ValueError("as_of_index must be at least lookback_bars.")

    raw: list[tuple[str, float]] = []
    for symbol, bars in symbol_bars.items():
        if as_of_index >= len(bars):
            raise ValueError(f"as_of_index is out of range for {symbol}.")
        past = bars[as_of_index - cfg.lookback_bars].close
        current = bars[as_of_index].close
        if past <= 0:
            continue
        raw.append((symbol, (current / past) - 1.0))

    ranked = sorted(raw, key=lambda item: item[1], reverse=True)
    signals: list[RankedMomentumSignal] = []
    for idx, (symbol, momentum_return) in enumerate(ranked, start=1):
        selected = idx <= cfg.top_n and momentum_return > cfg.min_return_threshold
        signals.append(
            RankedMomentumSignal(
                symbol=symbol,
                momentum_return=momentum_return,
                rank=idx,
                selected=selected,
            )
        )
    return signals
