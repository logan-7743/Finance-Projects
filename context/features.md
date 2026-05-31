# Features

Shipped features, how they work, and their honest current status.

---

## Stock Price Chart

**Status:** Shipped (local-first foundation)

**What it does:** Displays a candlestick (OHLC) chart for any entered stock ticker. Supports selectable date ranges (1D, 5D, 1M, 6M, 1Y, 5Y) and a line/candle toggle.

**How it works:**
1. User enters a ticker symbol in the frontend symbol search input.
2. Frontend loads cached history/quote from localStorage first (cache key includes symbol and range).
3. Frontend only calls backend automatically when required cache is missing.
4. Backend uses `yfinance` to fetch OHLCV/quote data and returns typed JSON.
5. Frontend renders the data via `lightweight-charts` v5 (TradingView) in a `PriceChart` React client component.
6. Manual refresh is explicit via a button; history refresh uses `since=<last_bar_time>` and merges new bars into existing history.

**Limitations (honest):**
- Data is historical only — no live/streaming quotes yet.
- `yfinance` is unofficial and can break without notice; treat as development/research data only.
- No authentication, no user state.
- Quote metadata depends on Yahoo availability and may be incomplete.
- Browser cache is per-device/per-browser and not shared across clients.

---

## Backend Module Homes (scaffolded, not implemented)

**Status:** Scaffolded — interfaces only, no strategy/backtest logic

These modules exist as empty homes with abstract base classes and clear TODOs. They are NOT implemented yet.

- `quant/strategies/` — strategy base class
- `quant/backtesting/` — backtest engine
- `quant/execution/` — broker interfaces (Alpaca, paper)
- `quant/risk/` — cost models (fees, slippage, latency)
- `quant/metrics/` — performance metrics
- `quant/sentiment/` — LLM/Perplexity sentiment

---

## Crypto Order-Flow Direction

**Status:** Documented — not implemented

Crypto support will use exchange-specific providers under `backend/quant/data/`. For order-flow style data, the first realistic APIs are Coinbase Advanced Trade or Kraken WebSocket v2.

**Honest limitation:** Each exchange only shows its own order flow. Cross-exchange consolidated crypto order flow needs a paid aggregator.

---

## Local Dev Runner

**Status:** Shipped

**What it does:** Runs the FastAPI backend and Next.js frontend together from the repo root.

**Command:**

```bash
make dev
```

**How it works:** `Makefile` delegates to `scripts/dev.sh`, which starts:
- backend: `http://127.0.0.1:8000`
- frontend: `http://localhost:3000`

Pressing `Ctrl+C` stops both child processes.

**Limitations (honest):** This is a local development helper only. It is not a production process manager.
