"""Tests for quant indicator calculations and request validation."""

from quant.data.base import OHLCVBar
from quant.indicators import (
    compute_indicators,
    estimate_warmup_start,
    parse_indicator_requests,
    required_warmup_bars,
)


def _sample_bars(count: int = 80) -> list[OHLCVBar]:
    bars: list[OHLCVBar] = []
    base_price = 100.0
    for idx in range(count):
        close = base_price + (idx * 0.7)
        bars.append(
            OHLCVBar(
                time=f"2026-01-{(idx % 28) + 1:02d}",
                open=close - 0.8,
                high=close + 1.5,
                low=close - 1.2,
                close=close,
                volume=10_000 + (idx * 25),
            )
        )
    return bars


def test_parse_indicator_requests_valid_payload() -> None:
    requests = parse_indicator_requests(
        '[{"id":"ema_20","kind":"ema","params":{"period":20}},'
        '{"id":"macd_1","kind":"macd","params":{"fast":12,"slow":26,"signal":9}}]'
    )
    assert len(requests) == 2
    assert requests[0].kind == "ema"
    assert requests[1].params["slow"] == 26


def test_parse_indicator_requests_rejects_bad_payload() -> None:
    try:
        parse_indicator_requests('{"kind":"ema"}')
    except ValueError as exc:
        assert "expected JSON array" in str(exc)
    else:
        raise AssertionError("Expected invalid payload to raise ValueError.")


def test_compute_indicators_returns_requested_series() -> None:
    bars = _sample_bars()
    requests = parse_indicator_requests(
        '[{"id":"ema_20","kind":"ema","params":{"period":20}},'
        '{"id":"rsi_14","kind":"rsi","params":{"period":14}},'
        '{"id":"macd_12_26_9","kind":"macd","params":{"fast":12,"slow":26,"signal":9}}]'
    )
    indicators = compute_indicators(bars=bars, requests=requests, since=None)
    by_id = {indicator.id: indicator for indicator in indicators}

    assert len(indicators) == 3
    assert by_id["ema_20"].pane == "overlay"
    assert by_id["rsi_14"].pane == "oscillator"
    assert {line.key for line in by_id["macd_12_26_9"].lines} == {
        "macd",
        "signal",
        "histogram",
    }
    assert len(by_id["ema_20"].lines[0].points) > 10


def test_compute_indicators_trims_points_for_since_cursor() -> None:
    bars = _sample_bars()
    requests = parse_indicator_requests('[{"id":"sma_5","kind":"sma","params":{"period":5}}]')
    indicators = compute_indicators(bars=bars, requests=requests, since="2026-01-15")

    assert len(indicators) == 1
    assert indicators[0].lines[0].points
    assert all(point.time >= "2026-01-15" for point in indicators[0].lines[0].points)


def test_required_warmup_bars_respects_longest_indicator() -> None:
    requests = parse_indicator_requests(
        '[{"id":"ema_100","kind":"ema","params":{"period":100}},'
        '{"id":"macd_1","kind":"macd","params":{"fast":12,"slow":26,"signal":9}}]'
    )
    warmup = required_warmup_bars(requests)
    assert warmup >= 105


def test_estimate_warmup_start_backtracks_for_interval() -> None:
    start = estimate_warmup_start(since="2026-05-20", interval="1d", warmup_bars=20)
    assert start is not None
    assert start < "2026-05-20"
