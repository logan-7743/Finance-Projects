"""Backtesting engine — TODO: implement in Phase 1.

The engine will:
1. Feed historical OHLCV data bar-by-bar to a strategy's generate_signals().
2. Convert signals to simulated orders using the cost models in quant.risk.
3. Track positions, cash, and equity curve.
4. Compute performance metrics via quant.metrics.

IMPORTANT: All backtests must be net-of-cost. See quant/risk/costs.py for the
cost model interface and 10-quant-rigor.mdc for requirements.
"""
