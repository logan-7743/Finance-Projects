"""Trading cost models — slippage, fees, and latency.

These costs MUST be applied in every backtest. Ignoring them produces
results that will never hold in live trading. See 10-quant-rigor.mdc.

TODO (Phase 1): Implement realistic cost models calibrated to Alpaca's
actual fee schedule and observed slippage on target instruments.
"""

from dataclasses import dataclass


@dataclass
class CostEstimate:
    """Total estimated round-trip cost for a trade."""

    slippage_per_share: float  # Adverse price movement on fill
    commission: float  # Broker commission (can be 0 for Alpaca equities)
    spread_cost: float  # Half bid-ask spread per share
    latency_cost: float  # Estimated cost of execution delay
    total_per_share: float  # Sum of all above
    total: float  # total_per_share * quantity


class CostModel:
    """Estimates round-trip trading costs for a given order.

    TODO (Phase 1): Replace these placeholder values with a calibrated model:
    - Slippage: fit to historical Alpaca fill data vs. mid-price at signal time
    - Spread: use average bid-ask spread for target symbols/times
    - Latency: measure actual signal-to-fill latency in paper trading

    Default parameters are intentionally conservative (pessimistic).
    Better to underestimate edge than overestimate it.
    """

    def __init__(
        self,
        slippage_bps: float = 5.0,  # 5 basis points slippage per side
        commission_per_share: float = 0.0,  # Alpaca: $0 commission for equities
        spread_bps: float = 3.0,  # 3 bps half-spread
        latency_ms: float = 100.0,  # assumed 100ms signal-to-fill latency
    ):
        self.slippage_bps = slippage_bps
        self.commission_per_share = commission_per_share
        self.spread_bps = spread_bps
        self.latency_ms = latency_ms

    def estimate(self, price: float, quantity: float) -> CostEstimate:
        """Estimate costs for a single-sided order.

        Args:
            price: Expected fill price (e.g., last close or mid).
            quantity: Number of shares.

        Returns:
            CostEstimate with all cost components broken out.
        """
        slippage = price * (self.slippage_bps / 10_000)
        spread = price * (self.spread_bps / 10_000)
        # Latency cost is a function of price volatility and delay — placeholder
        # TODO: implement properly using realized volatility and latency estimate
        latency_cost = 0.0

        total_per_share = slippage + self.commission_per_share + spread + latency_cost
        return CostEstimate(
            slippage_per_share=slippage,
            commission=self.commission_per_share * quantity,
            spread_cost=spread,
            latency_cost=latency_cost,
            total_per_share=total_per_share,
            total=total_per_share * quantity,
        )
