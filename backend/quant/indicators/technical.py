"""Technical indicator computation for market dashboard overlays."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from quant.data.base import OHLCVBar

IndicatorKind = Literal[
    "ema",
    "sma",
    "atr",
    "adx",
    "rsi",
    "macd",
    "bollinger",
    "vwap",
    "stochastic",
    "obv",
]
IndicatorPane = Literal["overlay", "oscillator"]
LineStyle = Literal["line", "histogram"]


class IndicatorRequest(BaseModel):
    """Requested indicator instance from the frontend."""

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    kind: IndicatorKind
    params: dict[str, float | int] = Field(default_factory=dict)


class IndicatorPoint(BaseModel):
    time: str
    value: float


class IndicatorLine(BaseModel):
    key: str
    label: str
    color: str
    style: LineStyle = "line"
    points: list[IndicatorPoint]


class IndicatorSeries(BaseModel):
    id: str
    kind: IndicatorKind
    name: str
    pane: IndicatorPane
    lines: list[IndicatorLine]


_REQUESTS_ADAPTER = TypeAdapter(list[IndicatorRequest])
_INTERVAL_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "1d": 60 * 24,
    "1wk": 60 * 24 * 7,
    "1mo": 60 * 24 * 30,
}


def parse_indicator_requests(raw: str | None) -> list[IndicatorRequest]:
    """Parse and validate indicator request JSON payload."""
    if raw is None or raw.strip() == "":
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid indicators payload: expected JSON array.") from exc
    try:
        return _REQUESTS_ADAPTER.validate_python(parsed)
    except ValidationError as exc:
        raise ValueError(f"Invalid indicators payload: {exc}") from exc


def required_warmup_bars(indicators: list[IndicatorRequest]) -> int:
    """Estimate lookback bars needed for stable indicator values."""
    if not indicators:
        return 0
    max_bars = 1
    for indicator in indicators:
        params = indicator.params
        kind = indicator.kind
        if kind in ("ema", "sma", "atr", "adx", "rsi", "bollinger"):
            period = _int_param(params, "period", default=14, minimum=2, maximum=500)
            max_bars = max(max_bars, period + 5)
        elif kind == "macd":
            fast = _int_param(params, "fast", default=12, minimum=2, maximum=200)
            slow = _int_param(params, "slow", default=26, minimum=3, maximum=300)
            signal = _int_param(params, "signal", default=9, minimum=2, maximum=100)
            max_bars = max(max_bars, slow + signal + 5)
        elif kind == "stochastic":
            period = _int_param(params, "period", default=14, minimum=2, maximum=200)
            smooth = _int_param(params, "smooth", default=3, minimum=1, maximum=50)
            max_bars = max(max_bars, period + smooth + 5)
        elif kind in ("vwap", "obv"):
            max_bars = max(max_bars, 3)
    return max_bars


def estimate_warmup_start(
    *,
    since: str | None,
    interval: str,
    warmup_bars: int,
) -> str | None:
    """Estimate a start cursor that includes enough bars for indicator warm-up."""
    if since is None or warmup_bars <= 0:
        return since

    since_dt = _parse_time(since)
    if since_dt is None:
        return since

    minutes = _INTERVAL_MINUTES.get(interval)
    if minutes is None:
        return since

    # Use a conservative multiplier to account for market-closed periods.
    warmup_minutes = minutes * warmup_bars * 3
    start_dt = since_dt - timedelta(minutes=warmup_minutes)

    if "T" in since:
        return start_dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return start_dt.date().isoformat()


def is_on_or_after(time_value: str, cursor: str) -> bool:
    """Compare two bar timestamps safely."""
    value_dt = _parse_time(time_value)
    cursor_dt = _parse_time(cursor)
    if value_dt is None or cursor_dt is None:
        return time_value >= cursor
    return value_dt >= cursor_dt


def compute_indicators(
    *,
    bars: list[OHLCVBar],
    requests: list[IndicatorRequest],
    since: str | None = None,
) -> list[IndicatorSeries]:
    """Compute requested indicators for a bar series."""
    if not bars or not requests:
        return []

    frame = pd.DataFrame(
        {
            "time": [bar.time for bar in bars],
            "open": [bar.open for bar in bars],
            "high": [bar.high for bar in bars],
            "low": [bar.low for bar in bars],
            "close": [bar.close for bar in bars],
            "volume": [bar.volume for bar in bars],
        }
    )

    computed: list[IndicatorSeries] = []
    for request in requests:
        computed.append(_compute_indicator(frame=frame, request=request))

    if since is None:
        return computed
    return [_trim_series(series, since=since) for series in computed]


def _compute_indicator(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    kind = request.kind
    if kind == "ema":
        return _ema(frame=frame, request=request)
    if kind == "sma":
        return _sma(frame=frame, request=request)
    if kind == "atr":
        return _atr(frame=frame, request=request)
    if kind == "adx":
        return _adx(frame=frame, request=request)
    if kind == "rsi":
        return _rsi(frame=frame, request=request)
    if kind == "macd":
        return _macd(frame=frame, request=request)
    if kind == "bollinger":
        return _bollinger(frame=frame, request=request)
    if kind == "vwap":
        return _vwap(frame=frame, request=request)
    if kind == "stochastic":
        return _stochastic(frame=frame, request=request)
    if kind == "obv":
        return _obv(frame=frame, request=request)
    raise ValueError(f"Unsupported indicator kind: {kind}")


def _sma(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    period = _int_param(request.params, "period", default=20, minimum=2, maximum=500)
    series = frame["close"].rolling(window=period, min_periods=period).mean()
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"SMA ({period})",
        pane="overlay",
        lines=[
            IndicatorLine(
                key="sma",
                label=f"SMA {period}",
                color="#eab308",
                points=_points(frame["time"], series),
            )
        ],
    )


def _ema(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    period = _int_param(request.params, "period", default=20, minimum=2, maximum=500)
    series = frame["close"].ewm(span=period, adjust=False).mean()
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"EMA ({period})",
        pane="overlay",
        lines=[
            IndicatorLine(
                key="ema",
                label=f"EMA {period}",
                color="#f97316",
                points=_points(frame["time"], series),
            )
        ],
    )


def _atr(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    period = _int_param(request.params, "period", default=14, minimum=2, maximum=300)
    tr = _true_range(frame)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"ATR ({period})",
        pane="oscillator",
        lines=[
            IndicatorLine(
                key="atr",
                label=f"ATR {period}",
                color="#22d3ee",
                points=_points(frame["time"], atr),
            )
        ],
    )


def _adx(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    period = _int_param(request.params, "period", default=14, minimum=2, maximum=300)
    high = frame["high"]
    low = frame["low"]
    close = frame["close"]

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = _true_range(frame)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean().replace(0, pd.NA)

    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    di_sum = (plus_di + minus_di).replace(0, pd.NA)
    dx = 100 * ((plus_di - minus_di).abs() / di_sum)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()

    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"ADX ({period})",
        pane="oscillator",
        lines=[
            IndicatorLine(
                key="adx",
                label=f"ADX {period}",
                color="#c084fc",
                points=_points(frame["time"], adx),
            ),
            IndicatorLine(
                key="plus_di",
                label="+DI",
                color="#22c55e",
                points=_points(frame["time"], plus_di),
            ),
            IndicatorLine(
                key="minus_di",
                label="-DI",
                color="#ef4444",
                points=_points(frame["time"], minus_di),
            ),
        ],
    )


def _rsi(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    period = _int_param(request.params, "period", default=14, minimum=2, maximum=300)
    delta = frame["close"].diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"RSI ({period})",
        pane="oscillator",
        lines=[
            IndicatorLine(
                key="rsi",
                label=f"RSI {period}",
                color="#38bdf8",
                points=_points(frame["time"], rsi),
            )
        ],
    )


def _macd(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    fast = _int_param(request.params, "fast", default=12, minimum=2, maximum=200)
    slow = _int_param(request.params, "slow", default=26, minimum=3, maximum=300)
    signal = _int_param(request.params, "signal", default=9, minimum=2, maximum=100)
    if fast >= slow:
        raise ValueError("MACD requires fast < slow.")

    ema_fast = frame["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = frame["close"].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line

    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"MACD ({fast},{slow},{signal})",
        pane="oscillator",
        lines=[
            IndicatorLine(
                key="macd",
                label="MACD",
                color="#facc15",
                points=_points(frame["time"], macd),
            ),
            IndicatorLine(
                key="signal",
                label="Signal",
                color="#38bdf8",
                points=_points(frame["time"], signal_line),
            ),
            IndicatorLine(
                key="histogram",
                label="Histogram",
                color="#94a3b8",
                style="histogram",
                points=_points(frame["time"], histogram),
            ),
        ],
    )


def _bollinger(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    period = _int_param(request.params, "period", default=20, minimum=2, maximum=300)
    stddev = _float_param(request.params, "stddev", default=2.0, minimum=0.1, maximum=6.0)
    basis = frame["close"].rolling(window=period, min_periods=period).mean()
    spread = frame["close"].rolling(window=period, min_periods=period).std(ddof=0)
    upper = basis + (spread * stddev)
    lower = basis - (spread * stddev)
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"Bollinger ({period},{stddev:g})",
        pane="overlay",
        lines=[
            IndicatorLine(
                key="upper",
                label="Upper",
                color="#60a5fa",
                points=_points(frame["time"], upper),
            ),
            IndicatorLine(
                key="basis",
                label="Basis",
                color="#eab308",
                points=_points(frame["time"], basis),
            ),
            IndicatorLine(
                key="lower",
                label="Lower",
                color="#60a5fa",
                points=_points(frame["time"], lower),
            ),
        ],
    )


def _vwap(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    typical_price = (frame["high"] + frame["low"] + frame["close"]) / 3
    cum_vol = frame["volume"].cumsum().replace(0, pd.NA)
    vwap = (typical_price * frame["volume"]).cumsum() / cum_vol
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name="VWAP",
        pane="overlay",
        lines=[
            IndicatorLine(
                key="vwap",
                label="VWAP",
                color="#a78bfa",
                points=_points(frame["time"], vwap),
            )
        ],
    )


def _stochastic(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    period = _int_param(request.params, "period", default=14, minimum=2, maximum=300)
    smooth = _int_param(request.params, "smooth", default=3, minimum=1, maximum=50)
    lowest_low = frame["low"].rolling(window=period, min_periods=period).min()
    highest_high = frame["high"].rolling(window=period, min_periods=period).max()
    denominator = (highest_high - lowest_low).replace(0, pd.NA)
    k = 100 * ((frame["close"] - lowest_low) / denominator)
    d = k.rolling(window=smooth, min_periods=smooth).mean()
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name=f"Stochastic ({period},{smooth})",
        pane="oscillator",
        lines=[
            IndicatorLine(
                key="k",
                label="%K",
                color="#f59e0b",
                points=_points(frame["time"], k),
            ),
            IndicatorLine(
                key="d",
                label="%D",
                color="#38bdf8",
                points=_points(frame["time"], d),
            ),
        ],
    )


def _obv(*, frame: pd.DataFrame, request: IndicatorRequest) -> IndicatorSeries:
    direction = frame["close"].diff().fillna(0).map(
        lambda delta: 1.0 if delta > 0 else -1.0 if delta < 0 else 0.0
    )
    obv = (direction * frame["volume"]).cumsum()
    return IndicatorSeries(
        id=request.id,
        kind=request.kind,
        name="OBV",
        pane="oscillator",
        lines=[
            IndicatorLine(
                key="obv",
                label="OBV",
                color="#34d399",
                points=_points(frame["time"], obv),
            )
        ],
    )


def _true_range(frame: pd.DataFrame) -> pd.Series:
    high = frame["high"]
    low = frame["low"]
    close = frame["close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _points(time_series: pd.Series, value_series: pd.Series) -> list[IndicatorPoint]:
    points: list[IndicatorPoint] = []
    for time_value, raw_value in zip(time_series, value_series, strict=True):
        if raw_value is None:
            continue
        if pd.isna(raw_value):
            continue
        value = float(raw_value)
        if not math.isfinite(value):
            continue
        points.append(IndicatorPoint(time=str(time_value), value=value))
    return points


def _trim_series(series: IndicatorSeries, *, since: str) -> IndicatorSeries:
    trimmed_lines = []
    for line in series.lines:
        trimmed_points = [point for point in line.points if is_on_or_after(point.time, since)]
        trimmed_lines.append(line.model_copy(update={"points": trimmed_points}))
    return series.model_copy(update={"lines": trimmed_lines})


def _int_param(
    params: dict[str, float | int],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = params.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid '{key}' value: expected integer.") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"Invalid '{key}' value: expected {minimum} <= value <= {maximum}.")
    return value


def _float_param(
    params: dict[str, float | int],
    key: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = params.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid '{key}' value: expected numeric.") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"Invalid '{key}' value: expected {minimum} <= value <= {maximum}.")
    return value


def _parse_time(value: str) -> datetime | None:
    try:
        if "T" in value:
            cleaned = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
        else:
            dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
