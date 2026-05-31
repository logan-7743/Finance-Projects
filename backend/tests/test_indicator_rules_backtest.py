"""Unit tests for indicator rule backtesting engine."""

from quant.backtesting import BacktestConfig, BacktestRule, run_indicator_rules_backtest
from quant.indicators import parse_indicator_requests
from quant.data.base import OHLCVBar


def _bars(count: int = 180) -> list[OHLCVBar]:
    bars: list[OHLCVBar] = []
    price = 100.0
    for idx in range(count):
        # Alternate trend regimes so crosses can happen.
        drift = 0.35 if idx < count // 2 else -0.2
        price += drift
        bars.append(
            OHLCVBar(
                time=f"2025-01-{(idx % 28) + 1:02d}",
                open=price - 0.5,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=100_000 + idx * 500,
            )
        )
    return bars


def test_backtest_runs_and_returns_metrics() -> None:
    bars = _bars()
    indicators = parse_indicator_requests(
        '[{"id":"ema_fast","kind":"ema","params":{"period":10}},'
        '{"id":"ema_slow","kind":"ema","params":{"period":30}}]'
    )
    config = BacktestConfig(
        initial_capital=100_000,
        entry_rules=[
            BacktestRule(
                left_indicator_id="ema_fast",
                left_line_key="ema",
                operator="crosses_above",
                right_type="indicator",
                right_indicator_id="ema_slow",
                right_line_key="ema",
            )
        ],
        exit_rules=[
            BacktestRule(
                left_indicator_id="ema_fast",
                left_line_key="ema",
                operator="crosses_below",
                right_type="indicator",
                right_indicator_id="ema_slow",
                right_line_key="ema",
            )
        ],
    )
    result = run_indicator_rules_backtest(
        bars=bars,
        indicator_requests=indicators,
        config=config,
    )
    assert result.metrics.trade_count >= 0
    assert result.metrics.ending_equity > 0
    assert len(result.equity_curve) == len(bars)
    assert len(result.indicators) == 2


def test_backtest_requires_entry_and_exit_rules() -> None:
    bars = _bars()
    indicators = parse_indicator_requests('[{"id":"rsi","kind":"rsi","params":{"period":14}}]')
    try:
        run_indicator_rules_backtest(
            bars=bars,
            indicator_requests=indicators,
            config=BacktestConfig(initial_capital=100_000, entry_rules=[], exit_rules=[]),
        )
    except ValueError as exc:
        assert "entry rule" in str(exc).lower()
    else:
        raise AssertionError("Expected missing-rule configuration to raise ValueError.")
