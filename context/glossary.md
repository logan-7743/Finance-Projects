# Glossary

Quant/domain terms and project-specific vocabulary. Add new terms as they come up.

---

## Alpha
The excess return of a strategy above a benchmark (typically the market). A strategy with positive alpha generates returns that cannot be explained by market exposure alone.

## Alpha Decay
The degradation of a strategy's edge over time. As more market participants discover and trade a signal, its profitability diminishes. All live strategies must be monitored for decay vs. their backtest performance.

## Backtest
A simulation of a strategy on historical data. **Net-of-cost backtests** subtract slippage, fees, and latency effects. Backtests are hypothetical — live performance will differ. See `10-quant-rigor.mdc` for requirements.

## Bid-Ask Spread
The difference between the best price a buyer will pay (bid) and the best price a seller will accept (ask). A real transaction cost even on "commission-free" platforms.

## Calmar Ratio
Annualized return divided by maximum drawdown. A measure of return relative to worst-case loss. Higher is better.

## Drawdown
The peak-to-trough decline in portfolio value over a period. **Maximum drawdown** is the largest such decline in the backtest/live window.

## Execution
The process of submitting and filling orders with a broker. In this project: Alpaca for equities (paper + live), Coinbase for crypto.

## Latency
The time between a trading signal being generated and the order being filled. Includes: computation time, network round-trip, exchange matching latency, and fill confirmation. Uncontrolled latency inflates slippage and erodes edge.

## Look-Ahead Bias
Using data in a backtest that would not have been available at the time of the simulated trade. A subtle and common source of inflated backtest results (e.g., using today's close price to make a decision that is supposed to happen intraday).

## Market Impact
The effect of a trade on the market price itself. Large orders move the market against the trader. More significant for illiquid instruments or large position sizes.

## OHLCV
Open, High, Low, Close, Volume — the standard representation of a price bar over a time period.

## L2 Order Book
Aggregated bid/ask liquidity by price level. L2 does not show every individual order, but it is enough for spread, depth, imbalance, liquidity, and market impact estimates.

## L3 Order Book
Individual order-level book data. More detailed than L2 and useful for queue-position analytics, but harder to maintain and often authenticated or paid.

## Order Flow
The stream of order book updates and executed trades on a venue. In crypto, order flow is usually **exchange-local** unless using a paid consolidated data provider.

## Out-of-Sample (OOS)
Data that was held back from strategy development/optimization and used only for validation. A strategy that performs well in-sample but poorly out-of-sample is likely overfit.

## Final Holdout
The final untouched test period reserved before strategy development. It should only be run after the strategy configuration is frozen. Repeatedly checking it turns it into another validation set.

## Overfitting
When a strategy is tuned so precisely to historical data that it captures noise rather than signal. Symptoms: excellent backtest, poor live performance. Cure: fewer parameters, OOS validation, walk-forward testing.

## Paper Trading
Simulated live trading using real market data and a paper (fake) account. The bridge between backtesting and real money. Required before any real capital commitment in this project.

## Point-in-Time Universe
A tradable universe built using only information available at the historical timestamp being tested. This avoids selecting today's survivors and accidentally introducing survivorship or look-ahead bias.

## Purging
Removing training samples whose label/event horizon overlaps a test fold. Used in financial ML because labels often depend on future price paths.

## Embargoing
Dropping a buffer of training samples immediately after a test fold to reduce serial-correlation leakage across the train/test boundary.

## Probabilistic Sharpe Ratio
A probability-style Sharpe significance estimate that accounts for sample size and non-normal return characteristics. Useful as an early robustness check.

## Deflated Sharpe Ratio
A stricter Sharpe significance adjustment that accounts for non-normal returns and multiple trials/selection bias. Intended to reduce false positives after testing many strategies or parameter sets.

## White's Reality Check / Hansen SPA
Multiple-testing/data-snooping tests that evaluate whether the best strategy from a searched family truly outperforms a benchmark. Relevant when many strategy variants were tried.

## Cost-Adjusted EV
Expected value after subtracting estimated transaction costs, spread, slippage, latency, and market impact. Signals should be sized or rejected based on cost-adjusted EV, not raw model confidence.

## Regime
A market state such as trend, chop, high volatility, low liquidity, or correlation compression. Strategy performance must be reported by regime because aggregate results can hide fragility.

## Sharpe Ratio
(Return - Risk-free rate) / Standard deviation of returns. The most common risk-adjusted return measure. Higher is better. Generally: <1 poor, 1–2 acceptable, >2 good. Always compute on net-of-cost returns.

## Slippage
The difference between the expected fill price (e.g., last trade price or mid price) and the actual execution price. Affected by order size, liquidity, and market conditions. Must be modeled conservatively in backtests.

## Survivorship Bias
Using a dataset that only includes securities that survived to the present (e.g., only currently listed stocks). This overstates historical performance because failed/delisted companies are excluded.

## Transaction Costs
All costs of executing a trade: commissions, exchange fees, spread, and slippage. Even "commission-free" brokers have spread costs and potential payment-for-order-flow effects.

## Walk-Forward Testing
A method of validating a strategy across multiple time periods: repeatedly optimize on a trailing window, then test on the next out-of-sample period, rolling forward. More robust than a single in-sample/out-of-sample split.

## yfinance
An unofficial Python library that fetches historical market data from Yahoo Finance. Used in this project for development and research. **Not production-grade** — subject to API changes and rate limits. Will be supplemented/replaced with Alpaca data for live trading.
