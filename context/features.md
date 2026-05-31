# Features

Shipped features, how they work, and their honest current status.

---

## Market Price Chart (Equities + Crypto)

**Status:** Shipped (local-first foundation)

**What it does:** Displays a candlestick (OHLC) chart for entered equity or crypto symbols. Supports selectable date ranges (1D, 5D, 1M, 6M, 1Y, 5Y) and a line/candle toggle.

**How it works:**
1. User enters a symbol in the frontend symbol search input (e.g. `AAPL`, `BTC`, `BTC/USD`, `BTC-USD`).
2. Frontend loads cached history/quote from localStorage first (cache key includes symbol and range).
3. Frontend only calls backend automatically when required cache is missing.
4. Backend uses `yfinance` to fetch OHLCV/quote data and returns typed JSON.
5. Frontend renders the data via `lightweight-charts` v5 (TradingView) in a `PriceChart` React client component.
6. Manual refresh is explicit via a button; history refresh uses `since=<last_bar_time>` and merges new bars into existing history.
7. Backend normalizes common crypto symbol shortcuts (`BTC`, `ETH/USD`, `SOLUSD`) into Yahoo-compatible symbols (`BTC-USD`, etc.).

**Limitations (honest):**
- Data is historical only — no live/streaming quotes yet.
- `yfinance` is unofficial and can break without notice; treat as development/research data only.
- No authentication, no user state.
- Quote metadata depends on Yahoo availability and may be incomplete.
- Browser cache is per-device/per-browser and not shared across clients.
- Crypto support here is candle/quote level only; no exchange order-book or trade-flow streams yet.

---

## Market Dashboard Technical Indicators

**Status:** Shipped (v1)

**What it does:** Lets users select robust indicators directly on the market dashboard chart, tune parameters per indicator instance, and remove indicators as needed. Supports multiple instances of the same indicator (e.g., EMA 20 + EMA 50).

**Indicator pack (v1):**
- EMA
- SMA
- ATR
- ADX
- RSI
- MACD
- Bollinger Bands
- VWAP
- Stochastic Oscillator
- OBV

**How it works:**
1. Frontend stores active indicator configs in localStorage and sends them with history requests.
2. Backend parses/validates requested indicator payloads and computes all indicator math in `quant/indicators/`.
3. On incremental refresh (`since=...`), backend fetches extra warm-up history to keep rolling indicators stable.
4. Backend trims returned bars/indicator points back to the requested visible window.
5. Frontend merges incremental indicator points by timestamp and renders overlays/oscillators in `lightweight-charts`.

**Limitations (honest):**
- Indicator computations are currently based on chart bars from yfinance (research-grade data).
- Oscillators are rendered in a compressed lower region of the same chart canvas (not fully separate pane widgets).
- Backend test execution requires a configured Python environment with project dev dependencies.

---

## Indicator Rule Backtesting (Basic)

**Status:** Shipped (v1 basic diagnostics)

**What it does:** Lets users define simple indicator-based entry/exit rules in the dashboard, run a long-only backtest, and review grounded net-of-cost metrics plus recent trade outcomes.

**How it works:**
1. Frontend sends selected indicator configs and rule sets to `POST /api/market/backtest`.
2. Backend fetches history bars, computes requested indicators, and evaluates rule logic bar-by-bar.
3. Engine simulates one-position-at-a-time long entries/exits with conservative cost model deductions.
4. API returns metrics (Sharpe, max drawdown, Calmar, win rate, profit factor, exposure, returns), equity curve, and executed trade list.
5. Frontend renders a compact metrics grid and recent trade table.

**Limitations (honest):**
- This is a basic rule engine (long-only, single active position, all-rules-must-pass logic).
- No out-of-sample split, no walk-forward, no significance testing, and no regime analysis yet.
- Cost model is conservative placeholder and not yet calibrated to real fill/slippage telemetry.
- Results are useful for screening ideas, not production capital decisions.

---

## Strategy Backtesting Engine (BaseStrategy, v1)

**Status:** Shipped (foundation)

**What it does:** Backtests any `BaseStrategy` implementation with explicit signal-to-fill lag, cost-aware fills, equity curve tracking, trade ledger, and core performance metrics.

**How it works:**
1. Engine runs bar-by-bar and calls strategy signal generation on data available up to the current bar only.
2. Signals are queued and executed on a later bar (`execution_lag_bars`, default 1) to avoid same-bar execution bias.
3. Long entries consume available capital (fractional quantity optional) and deduct estimated costs from `CostModel`.
4. Exit signals close positions, realize P&L net of entry/exit costs, and append executed trade records.
5. Engine computes metrics (Sharpe, drawdown, Calmar, win rate, profit factor, exposure, returns) from the resulting equity curve and trades.

**Current baseline strategy:** `EmaCrossoverStrategy` under `quant/strategies/`.

**Limitations (honest):**
- Engine is currently long/flat oriented; shorting is not modeled as a separate borrow/margin flow.
- Validation workflow exists as backend utilities but is not wired into the strategy API/UI yet.
- Cost model remains conservative placeholder calibration, not venue-calibrated.
- API/UI supports running the EMA baseline strategy as an initial research report, but not arbitrary strategy classes yet.

---

## Crypto Research Foundation Modules

**Status:** Shipped (foundation, not production-grade)

**What it does:** Adds the first reusable backend pieces from the referenced crypto ML research plan.

**Implemented modules:**
- `quant/backtesting/engine.py` — multi-asset portfolio backtest foundation with aligned bars, signal lag, cash/positions, and cost-aware fills.
- `quant/validation/` — chronological train/validation/final-test splits, walk-forward windows, and purged/embargoed folds.
- `quant/metrics/` — reusable performance summaries, bootstrap mean intervals, permutation significance, and probabilistic Sharpe helper.
- `quant/strategies/cross_sectional_momentum.py` — simple crypto cross-sectional momentum baseline.
- `quant/universe/crypto_universe.py` — market cap, volume, venue, age, spread/depth, and risk-flag filtering.
- `quant/risk/allocation.py` — conservative EV/regime/liquidity/drawdown-based position sizing.
- `quant/execution/readiness.py` — staged execution-readiness gates before any live trading.
- `quant/research/` — structured backtest review artifacts and Gemini-backed skeptical review interface.
- `quant/research/perplexity_researcher.py` — Perplexity-backed current web research summaries with citations.
- `app/routers/backtests.py` + dashboard button — first thin strategy backtest API/UI surface for EMA baseline.
- `app/routers/research.py` + dashboard button — first Gemini review route/UI for structured baseline artifacts.

**Limitations (honest):**
- These are foundational primitives, not a complete ML pipeline.
- No exchange-native crypto market data provider is implemented yet.
- Gemini report generation exists for structured artifacts, but is not yet wired into saved backtest run history or validation reports.
- No real paper/live broker integration is implemented yet.
- Statistical tests are first-pass helpers and need stronger research-report integration before capital decisions.

---

## Gemini Research Reviewer

**Status:** Shipped (v1 reviewer, local API key required)

**What it does:** Sends structured backtest artifacts to Gemini and returns a skeptical research-review report with a verdict.

**How it works:**
1. Backend defines `BacktestReviewArtifact` with hypothesis, metrics, cost assumptions, validation notes, and risks.
2. `GeminiResearchReviewer` reads the API key from settings and calls the Google Gen AI SDK.
3. `POST /api/research/review` accepts a structured artifact and returns provider/model/verdict/report markdown.
4. Dashboard and the dedicated `/research` page can send the EMA baseline result to Gemini via **Review with Gemini**.

**Secret handling:** Real keys live only in local `.env`. `.env.example` contains placeholders. `.env` is gitignored and must not be committed.

**Limitations (honest):**
- The LLM is a reviewer only; it does not create signals or trade decisions.
- The report quality depends on the structured metrics provided.
- The reviewer does not yet include chart images, regime tables, validation folds, or persisted run artifacts.

---

## Perplexity Research Summaries

**Status:** Shipped (backend API foundation)

**What it does:** Provides a Perplexity-backed research endpoint for current, web-grounded summaries with citations.

**How it works:**
1. Backend defines `PerplexityResearchRequest` and `PerplexityResearchResult`.
2. `PerplexityResearcher` calls Perplexity `POST /chat/completions` with bearer-token auth and Sonar models.
3. `POST /api/research/perplexity` returns answer markdown plus search-result citations.
4. Frontend API typing exists via `runPerplexityResearch(...)`.
5. `/research` provides a Perplexity research panel with question input, summary output, and citations.

**Secret handling:** Real keys live only in local `.env` as `PERPLEXITY_API_KEY`. `.env.example` contains placeholders only.

**Limitations (honest):**
- This should support research summaries, not direct trading signals.
- Outputs need source review and should not be treated as market truth without verification.
- No persistence yet; summaries are not saved to a research database.

---

## Research Dashboard UI

**Status:** Shipped (v1 local research cockpit)

**Route:** `/research`

**What it does:** Provides a dedicated UI for the first research workflows: EMA baseline backtest, Gemini review, and Perplexity market research.

**How it works:**
1. User runs the EMA baseline for a selected symbol/capital/EMA configuration.
2. UI displays key metrics: return, Sharpe, drawdown, ending equity, trades, win rate, Calmar, signals.
3. User can send the structured baseline artifact to Gemini for a skeptical review.
4. User can ask Perplexity a current-market research question and inspect returned citations.

**Limitations (honest):**
- This is a control surface for early research, not a full strategy lab.
- It does not yet display validation folds, regime analysis, allocation decisions, or saved run history.
- It depends on backend API keys being configured in local `.env`.

---

## Backend Module Homes (scaffolded, not implemented)

**Status:** Partially implemented — still early

These modules now include early implementations in some areas, but are still far from production-complete.

- `quant/strategies/` — strategy base class + EMA crossover + cross-sectional momentum baseline
- `quant/backtesting/` — indicator rule backtest + strategy backtest + multi-asset engine foundation
- `quant/execution/` — broker interfaces + execution-readiness gates
- `quant/risk/` — cost models + allocation/risk-budgeting
- `quant/metrics/` — reusable performance/statistical helpers
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
