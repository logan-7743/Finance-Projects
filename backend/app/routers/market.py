"""Market data API routes.

All data fetching delegates to the quant.data layer. Routers are thin:
validate inputs → call quant → return shaped Pydantic response.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from yfinance.exceptions import YFRateLimitError

from quant.backtesting import BacktestConfig, BacktestResult, run_indicator_rules_backtest
from quant.data import OHLCVBar, QuoteData, YFinanceSource
from quant.data.yfinance_retry import is_rate_limited_error
from quant.indicators import (
    IndicatorRequest,
    IndicatorSeries,
    compute_indicators,
    estimate_warmup_start,
    is_on_or_after,
    parse_indicator_requests,
    required_warmup_bars,
)

router = APIRouter()
_source = YFinanceSource()

CRYPTO_BASE_ASSETS = {
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "LTC",
    "AVAX",
    "DOT",
    "LINK",
    "MATIC",
    "BCH",
    "ATOM",
}


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.upper().strip().replace("/", "-")
    if normalized in CRYPTO_BASE_ASSETS:
        return f"{normalized}-USD"
    if normalized.endswith("USD") and "-" not in normalized:
        base = normalized[:-3]
        if base in CRYPTO_BASE_ASSETS:
            return f"{base}-USD"
    return normalized


def _raise_for_fetch_error(symbol: str, resource: str, exc: Exception) -> None:
    if isinstance(exc, YFRateLimitError) or is_rate_limited_error(exc):
        raise HTTPException(
            status_code=429,
            detail=(
                f"Yahoo Finance rate limit while fetching {resource} for '{symbol}'. "
                "Wait a minute and retry — repeated refreshes make this worse."
            ),
        ) from exc
    raise HTTPException(
        status_code=502,
        detail=f"Failed to fetch {resource} for '{symbol}': {exc}",
    ) from exc

# Valid period and interval options (subset of what yfinance supports)
PeriodType = Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
IntervalType = Literal[
    "1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"
]

RANGE_TO_PERIOD: dict[str, tuple[str, str]] = {
    "1D": ("5d", "5m"),
    "5D": ("5d", "1h"),
    "1M": ("1mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
}


class OHLCVBarResponse(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoryResponse(BaseModel):
    symbol: str
    period: str
    interval: str
    bars: list[OHLCVBarResponse]
    indicators: list[IndicatorSeries] = Field(default_factory=list)


class QuoteResponse(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: float
    market_cap: float | None
    name: str | None


class BacktestRequest(BaseModel):
    symbol: str
    range: str = "6M"
    period: str | None = None
    interval: str | None = None
    indicators: list[IndicatorRequest] = Field(default_factory=list)
    config: BacktestConfig


def _bar_to_response(bar: OHLCVBar) -> OHLCVBarResponse:
    return OHLCVBarResponse(
        time=bar.time,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
    )


def _resolve_period_interval(
    *,
    range: str,
    period: str | None,
    interval: str | None,
) -> tuple[str, str]:
    if period is None or interval is None:
        if range not in RANGE_TO_PERIOD:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid range '{range}'. Valid: {list(RANGE_TO_PERIOD.keys())}",
            )
        return RANGE_TO_PERIOD[range]
    return period, interval


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL or BTC-USD"),
    range: str = Query("6M", description="UI range: 1D, 5D, 1M, 6M, 1Y, 5Y"),
    period: str | None = Query(None, description="yfinance period override, e.g. 6mo"),
    interval: str | None = Query(None, description="yfinance interval override, e.g. 1d"),
    since: str | None = Query(
        None, description="Optional ISO date/datetime cursor for incremental fetches."
    ),
    indicators: str | None = Query(
        None,
        description=(
            "Optional JSON array of indicator configs "
            '(e.g. [{"id":"ema_1","kind":"ema","params":{"period":20}}]).'
        ),
    ),
) -> HistoryResponse:
    """Return OHLCV history for a symbol.

    Accepts either a UI range shorthand (1D, 5D, 1M, 6M, 1Y, 5Y) or
    explicit yfinance period/interval parameters.
    """
    symbol = _normalize_symbol(symbol)
    indicator_requests: list[IndicatorRequest] = []
    try:
        indicator_requests = parse_indicator_requests(indicators)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resolved_period, resolved_interval = _resolve_period_interval(
        range=range,
        period=period,
        interval=interval,
    )

    history_start = since
    if since is not None and indicator_requests:
        warmup_bars = required_warmup_bars(indicator_requests)
        history_start = estimate_warmup_start(
            since=since,
            interval=resolved_interval,
            warmup_bars=warmup_bars,
        )

    try:
        bars = _source.get_history(
            symbol,
            period=resolved_period,
            interval=resolved_interval,
            start=history_start,
        )
    except Exception as exc:
        _raise_for_fetch_error(symbol, "history", exc)

    if not bars:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for symbol '{symbol}'. Check the ticker is valid.",
        )

    response_bars = bars
    if since is not None and history_start != since:
        response_bars = [bar for bar in bars if is_on_or_after(bar.time, since)]

    try:
        indicator_series = compute_indicators(
            bars=bars,
            requests=indicator_requests,
            since=since,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return HistoryResponse(
        symbol=symbol,
        period=resolved_period,
        interval=resolved_interval,
        bars=[_bar_to_response(b) for b in response_bars],
        indicators=indicator_series,
    )


@router.post("/backtest", response_model=BacktestResult)
async def run_backtest(payload: BacktestRequest) -> BacktestResult:
    symbol = _normalize_symbol(payload.symbol)
    if not payload.indicators:
        raise HTTPException(status_code=400, detail="At least one indicator is required.")

    resolved_period, resolved_interval = _resolve_period_interval(
        range=payload.range,
        period=payload.period,
        interval=payload.interval,
    )
    try:
        bars = _source.get_history(
            symbol,
            period=resolved_period,
            interval=resolved_interval,
            start=None,
        )
    except Exception as exc:
        _raise_for_fetch_error(symbol, "history", exc)

    if not bars:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for symbol '{symbol}'. Check the ticker is valid.",
        )
    try:
        return run_indicator_rules_backtest(
            bars=bars,
            indicator_requests=payload.indicators,
            config=payload.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/quote", response_model=QuoteResponse)
async def get_quote(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL or BTC-USD"),
) -> QuoteResponse:
    """Return the latest quote snapshot for a symbol."""
    symbol = _normalize_symbol(symbol)

    try:
        quote: QuoteData = _source.get_quote(symbol)
    except Exception as exc:
        _raise_for_fetch_error(symbol, "quote", exc)

    return QuoteResponse(
        symbol=quote.symbol,
        price=quote.price,
        change=quote.change,
        change_pct=quote.change_pct,
        volume=quote.volume,
        market_cap=quote.market_cap,
        name=quote.name,
    )
