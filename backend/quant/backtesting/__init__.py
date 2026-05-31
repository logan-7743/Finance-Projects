"""Backtesting package."""

from quant.backtesting.indicator_rules import (
    BacktestConfig,
    BacktestMetrics,
    BacktestResult,
    BacktestRule,
    ExecutedTrade,
    run_indicator_rules_backtest,
)
from quant.backtesting.engine import (
    MultiAssetBacktestConfig,
    MultiAssetBacktestResult,
    MultiAssetMetrics,
    MultiAssetTrade,
    run_multi_asset_backtest,
)
from quant.backtesting.strategy_engine import (
    StrategyBacktestConfig,
    StrategyBacktestMetrics,
    StrategyBacktestResult,
    StrategyExecutedTrade,
    run_strategy_backtest,
)

__all__ = [
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestResult",
    "BacktestRule",
    "ExecutedTrade",
    "run_indicator_rules_backtest",
    "MultiAssetBacktestConfig",
    "MultiAssetBacktestResult",
    "MultiAssetMetrics",
    "MultiAssetTrade",
    "run_multi_asset_backtest",
    "StrategyBacktestConfig",
    "StrategyBacktestMetrics",
    "StrategyBacktestResult",
    "StrategyExecutedTrade",
    "run_strategy_backtest",
]
