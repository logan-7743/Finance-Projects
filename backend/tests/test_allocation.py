"""Tests for risk-budgeted allocation sizing."""

from quant.risk import AllocationConfig, AllocationInput, size_position


def test_allocation_rejects_low_ev() -> None:
    decision = size_position(
        AllocationInput(
            symbol="SOL-USD",
            cost_adjusted_ev_pct=0.1,
            uncertainty_pct=0.2,
            regime_score=1.0,
            liquidity_usd=10_000_000,
            portfolio_equity=100_000,
            current_drawdown_pct=0,
        ),
        config=AllocationConfig(min_ev_pct=0.25),
    )

    assert decision.should_trade is False
    assert "ev_below_threshold" in decision.reasons


def test_allocation_sizes_with_liquidity_and_drawdown_caps() -> None:
    decision = size_position(
        AllocationInput(
            symbol="SOL-USD",
            cost_adjusted_ev_pct=1.0,
            uncertainty_pct=0.5,
            regime_score=0.8,
            liquidity_usd=1_000_000,
            portfolio_equity=100_000,
            current_drawdown_pct=6,
        ),
        config=AllocationConfig(base_risk_fraction=0.05, max_liquidity_fraction=0.01),
    )

    assert decision.should_trade is True
    assert 0 < decision.target_notional <= 10_000


def test_allocation_disables_at_drawdown_limit() -> None:
    decision = size_position(
        AllocationInput(
            symbol="SOL-USD",
            cost_adjusted_ev_pct=1.0,
            uncertainty_pct=0.2,
            regime_score=1.0,
            liquidity_usd=10_000_000,
            portfolio_equity=100_000,
            current_drawdown_pct=20,
        )
    )

    assert decision.should_trade is False
    assert "drawdown_disable" in decision.reasons
