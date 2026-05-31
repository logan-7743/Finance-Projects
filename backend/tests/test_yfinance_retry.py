"""Tests for yfinance retry helpers."""

import pytest
from yfinance.exceptions import YFRateLimitError

from quant.data.yfinance_retry import is_rate_limited_error, with_yfinance_retries


def test_is_rate_limited_error_detects_yfinance_exception() -> None:
    assert is_rate_limited_error(YFRateLimitError())


def test_is_rate_limited_error_detects_message() -> None:
    assert is_rate_limited_error(RuntimeError("Too Many Requests. Rate limited."))


def test_with_yfinance_retries_eventually_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("quant.data.yfinance_retry.time.sleep", sleeps.append)

    attempts = {"count": 0}

    def fn() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise YFRateLimitError()
        return "ok"

    assert with_yfinance_retries(fn, delays_seconds=(0.0, 0.0)) == "ok"
    assert attempts["count"] == 3
    assert sleeps == [0.0, 0.0]
