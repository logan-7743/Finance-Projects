"""Crypto universe filters for small/mid-cap research."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CryptoAssetCandidate(BaseModel):
    symbol: str
    name: str | None = None
    market_cap_usd: float | None = None
    volume_24h_usd: float | None = None
    age_days: int | None = None
    venues: list[str] = Field(default_factory=list)
    spread_bps: float | None = None
    depth_1pct_usd: float | None = None
    is_stablecoin: bool = False
    is_wrapped: bool = False
    is_leveraged_token: bool = False
    known_risk_flags: list[str] = Field(default_factory=list)


class CryptoUniverseFilterConfig(BaseModel):
    min_market_cap_usd: float = 100_000_000
    max_market_cap_usd: float = 10_000_000_000
    min_volume_24h_usd: float = 5_000_000
    min_age_days: int = 365
    allowed_venues: set[str] = Field(default_factory=lambda: {"coinbase", "kraken"})
    max_spread_bps: float = 75.0
    min_depth_1pct_usd: float = 100_000
    exclude_risk_flagged: bool = True


class CryptoUniverseResult(BaseModel):
    selected: list[CryptoAssetCandidate]
    rejected: dict[str, list[str]]
    warnings: list[str] = Field(default_factory=list)


def filter_crypto_universe(
    candidates: list[CryptoAssetCandidate],
    *,
    config: CryptoUniverseFilterConfig | None = None,
    point_in_time: str | None = None,
) -> CryptoUniverseResult:
    cfg = config or CryptoUniverseFilterConfig()
    selected: list[CryptoAssetCandidate] = []
    rejected: dict[str, list[str]] = {}
    warnings: list[str] = []

    if point_in_time is None:
        warnings.append("Universe was filtered without an explicit point_in_time timestamp.")

    for asset in candidates:
        reasons = _rejection_reasons(asset, cfg)
        if reasons:
            rejected[asset.symbol] = reasons
        else:
            selected.append(asset)

    return CryptoUniverseResult(selected=selected, rejected=rejected, warnings=warnings)


def _rejection_reasons(
    asset: CryptoAssetCandidate,
    config: CryptoUniverseFilterConfig,
) -> list[str]:
    reasons: list[str] = []
    if asset.market_cap_usd is None:
        reasons.append("missing_market_cap")
    elif asset.market_cap_usd < config.min_market_cap_usd:
        reasons.append("market_cap_too_small")
    elif asset.market_cap_usd > config.max_market_cap_usd:
        reasons.append("market_cap_too_large")

    if asset.volume_24h_usd is None:
        reasons.append("missing_volume")
    elif asset.volume_24h_usd < config.min_volume_24h_usd:
        reasons.append("volume_too_low")

    if asset.age_days is None:
        reasons.append("missing_age")
    elif asset.age_days < config.min_age_days:
        reasons.append("too_new")

    venue_overlap = {venue.lower() for venue in asset.venues} & {
        venue.lower() for venue in config.allowed_venues
    }
    if not venue_overlap:
        reasons.append("no_allowed_venue")

    if asset.spread_bps is None:
        reasons.append("missing_spread")
    elif asset.spread_bps > config.max_spread_bps:
        reasons.append("spread_too_wide")

    if asset.depth_1pct_usd is None:
        reasons.append("missing_depth")
    elif asset.depth_1pct_usd < config.min_depth_1pct_usd:
        reasons.append("depth_too_thin")

    if asset.is_stablecoin:
        reasons.append("stablecoin")
    if asset.is_wrapped:
        reasons.append("wrapped_asset")
    if asset.is_leveraged_token:
        reasons.append("leveraged_token")
    if config.exclude_risk_flagged and asset.known_risk_flags:
        reasons.append("known_risk_flags")
    return reasons
