"""Strategy backtest API routes.

Routers stay thin: validate request, fetch data, call quant layer, return result.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from quant.backtesting import StrategyBacktestConfig, StrategyBacktestResult, run_strategy_backtest
from quant.data import YFinanceSource
from quant.strategies import EmaCrossoverStrategy

router = APIRouter()


class EmaCrossoverBacktestRequest(BaseModel):
    symbol: str
    period: str = "1y"
    interval: str = "1d"
    initial_capital: float = Field(default=100_000, gt=1_000)
    fast_period: int = Field(default=12, gt=1)
    slow_period: int = Field(default=26, gt=2)
    execution_lag_bars: int = Field(default=1, ge=1)


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.upper().strip().replace("/", "-")
    if normalized.endswith("USD") and "-" not in normalized:
        return f"{normalized[:-3]}-USD"
    if "-" not in normalized and normalized in {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"}:
        return f"{normalized}-USD"
    return normalized


@router.post("/ema-crossover", response_model=StrategyBacktestResult)
async def run_ema_crossover_backtest(
    payload: EmaCrossoverBacktestRequest,
) -> StrategyBacktestResult:
    if YFinanceSource is None:
        raise HTTPException(status_code=503, detail="YFinanceSource is unavailable in this environment.")

    symbol = _normalize_symbol(payload.symbol)
    source = YFinanceSource()
    try:
        bars = source.get_history(symbol, period=payload.period, interval=payload.interval)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}: {exc}") from exc
    if not bars:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}.")

    try:
        return run_strategy_backtest(
            symbol=symbol,
            bars=bars,
            strategy=EmaCrossoverStrategy(
                symbol=symbol,
                fast_period=payload.fast_period,
                slow_period=payload.slow_period,
            ),
            config=StrategyBacktestConfig(
                initial_capital=payload.initial_capital,
                execution_lag_bars=payload.execution_lag_bars,
                min_bars_before_signals=max(payload.slow_period + 1, 30),
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
