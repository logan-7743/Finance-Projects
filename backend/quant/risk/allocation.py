"""Portfolio allocation and loss-budgeting rules."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AllocationInput(BaseModel):
    symbol: str
    cost_adjusted_ev_pct: float
    uncertainty_pct: float
    regime_score: float = Field(ge=0.0, le=1.0)
    liquidity_usd: float
    portfolio_equity: float
    current_drawdown_pct: float = Field(ge=0.0)


class AllocationConfig(BaseModel):
    min_ev_pct: float = 0.25
    base_risk_fraction: float = Field(default=0.01, gt=0.0, le=0.1)
    max_position_weight: float = Field(default=0.2, gt=0.0, le=1.0)
    max_liquidity_fraction: float = Field(default=0.01, gt=0.0, le=0.1)
    drawdown_throttle_start_pct: float = 5.0
    drawdown_disable_pct: float = 15.0


class AllocationDecision(BaseModel):
    symbol: str
    should_trade: bool
    target_notional: float
    max_loss_budget: float
    reasons: list[str] = Field(default_factory=list)


def size_position(
    allocation_input: AllocationInput,
    *,
    config: AllocationConfig | None = None,
) -> AllocationDecision:
    cfg = config or AllocationConfig()
    reasons: list[str] = []

    if allocation_input.cost_adjusted_ev_pct < cfg.min_ev_pct:
        reasons.append("ev_below_threshold")
    if allocation_input.current_drawdown_pct >= cfg.drawdown_disable_pct:
        reasons.append("drawdown_disable")
    if allocation_input.liquidity_usd <= 0:
        reasons.append("missing_liquidity")

    if reasons:
        return AllocationDecision(
            symbol=allocation_input.symbol,
            should_trade=False,
            target_notional=0.0,
            max_loss_budget=0.0,
            reasons=reasons,
        )

    uncertainty_penalty = 1 / (1 + max(allocation_input.uncertainty_pct, 0.0))
    drawdown_multiplier = _drawdown_multiplier(
        drawdown_pct=allocation_input.current_drawdown_pct,
        throttle_start=cfg.drawdown_throttle_start_pct,
        disable_at=cfg.drawdown_disable_pct,
    )
    risk_budget = (
        allocation_input.portfolio_equity
        * cfg.base_risk_fraction
        * allocation_input.regime_score
        * uncertainty_penalty
        * drawdown_multiplier
    )
    max_by_weight = allocation_input.portfolio_equity * cfg.max_position_weight
    max_by_liquidity = allocation_input.liquidity_usd * cfg.max_liquidity_fraction
    target = max(0.0, min(risk_budget, max_by_weight, max_by_liquidity))

    if target <= 0:
        return AllocationDecision(
            symbol=allocation_input.symbol,
            should_trade=False,
            target_notional=0.0,
            max_loss_budget=0.0,
            reasons=["target_size_zero"],
        )

    return AllocationDecision(
        symbol=allocation_input.symbol,
        should_trade=True,
        target_notional=target,
        max_loss_budget=risk_budget,
        reasons=[],
    )


def _drawdown_multiplier(*, drawdown_pct: float, throttle_start: float, disable_at: float) -> float:
    if drawdown_pct <= throttle_start:
        return 1.0
    if drawdown_pct >= disable_at:
        return 0.0
    span = disable_at - throttle_start
    return max(0.0, 1.0 - ((drawdown_pct - throttle_start) / span))
