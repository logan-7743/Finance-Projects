"""Tests for symbol normalization in market routes."""

from app.routers.market import _normalize_symbol


def test_normalize_symbol_keeps_equity_ticker() -> None:
    assert _normalize_symbol("aapl") == "AAPL"


def test_normalize_symbol_converts_crypto_base_to_usd_pair() -> None:
    assert _normalize_symbol("btc") == "BTC-USD"


def test_normalize_symbol_converts_slash_notation() -> None:
    assert _normalize_symbol("eth/usd") == "ETH-USD"


def test_normalize_symbol_converts_compact_crypto_usd() -> None:
    assert _normalize_symbol("solusd") == "SOL-USD"
