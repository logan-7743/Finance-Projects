"""Tests for crypto universe filtering."""

from quant.universe import CryptoAssetCandidate, CryptoUniverseFilterConfig, filter_crypto_universe


def test_crypto_universe_filters_liquidity_and_risk() -> None:
    result = filter_crypto_universe(
        [
            CryptoAssetCandidate(
                symbol="SOL-USD",
                market_cap_usd=5_000_000_000,
                volume_24h_usd=100_000_000,
                age_days=1_500,
                venues=["coinbase", "kraken"],
                spread_bps=10,
                depth_1pct_usd=2_000_000,
            ),
            CryptoAssetCandidate(
                symbol="RUG-USD",
                market_cap_usd=5_000_000,
                volume_24h_usd=25_000,
                age_days=3,
                venues=["unknown"],
                spread_bps=500,
                depth_1pct_usd=100,
                known_risk_flags=["honeypot_warning"],
            ),
        ],
        config=CryptoUniverseFilterConfig(),
        point_in_time="2026-05-31T00:00:00Z",
    )

    assert [asset.symbol for asset in result.selected] == ["SOL-USD"]
    assert "RUG-USD" in result.rejected
    assert "market_cap_too_small" in result.rejected["RUG-USD"]
    assert "known_risk_flags" in result.rejected["RUG-USD"]
