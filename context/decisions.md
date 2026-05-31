# Decisions Log

Architectural and design decisions — what was chosen and why. Append new entries at the bottom.

---

## 2026-05-30 — Monorepo with FastAPI backend + Next.js frontend seam

**Decision:** Split the platform into `backend/` (Python, FastAPI) and `frontend/` (Next.js, TypeScript) communicating over a local REST API.

**Why:** All quant math, data fetching, and order logic belongs in Python — the ecosystem (numpy, pandas, yfinance, scipy, alpaca-trade-api) is mature and unmatched. The frontend is display + interaction only. A clean REST seam means the engine can be deployed independently from the UI (Cloud Run vs Vercel), scaled independently, and tested independently.

**Alternatives rejected:** Python-only Streamlit/Dash UI — faster to start but weak for a long-term production UI, poor mobile experience, and harder to build a multi-algo dashboard.

---

## 2026-05-30 — Vercel for UI, GCP Cloud Run for backend (serverless excluded for engine)

**Decision:** Frontend deploys to Vercel. Backend (FastAPI engine) deploys to GCP Cloud Run with `min-instances=1`.

**Why:** Serverless (including Vercel Functions) is structurally incompatible with a trading engine:
- Ephemeral instances cannot hold persistent websocket connections (required for Alpaca/Coinbase live feeds)
- `maxDuration` caps prevent long-running backtests, optimization, and model training
- Cold-start latency is uncontrolled and unmeasurable — a direct violation of the project's latency-awareness principle
- No in-memory state between invocations

Vercel cron jobs (even on Pro) poll at minimum 1-minute intervals, which is acceptable only for slow/EOD strategies and explicitly not for execution-sensitive ones.

Cloud Run with a warm instance eliminates all of the above. GCP Cloud Scheduler handles cron at any frequency.

**Note:** This is a *future* deployment decision. Local development runs `uvicorn` directly on `127.0.0.1:8000`.

---

## 2026-05-30 — Database deferred behind a thin interface

**Decision:** No database chosen yet. DB access will be isolated behind a thin interface in the quant package so the choice (Neon Postgres vs GCP Cloud SQL) can be made when persistent state is actually needed (i.e., when strategies start storing trades, equity curves, and positions).

**Why:** The first deliverable (a stock chart) has no persistence requirements. Choosing a DB now would add setup friction for no immediate benefit.

---

## 2026-05-30 — TradingView lightweight-charts v5 for candlestick charting

**Decision:** Use `lightweight-charts` (TradingView) for all financial charts in the frontend.

**Why:** Industry standard for financial web charting — performant, WebGL-based, correct OHLC candlestick rendering, supports line/area/histogram overlays, mobile-friendly. The v5 API uses `chart.addSeries(CandlestickSeries, ...)`.

**Alternatives rejected:** Recharts, Chart.js — general-purpose charting libraries that lack proper financial chart primitives (candlesticks, crosshair, price scale).

---

## 2026-05-30 — Crypto market data should use exchange websockets for order flow

**Decision:** Crypto support will be added through exchange-specific data providers under `backend/quant/data/`, starting with Coinbase Advanced Trade or Kraken. Historical candles can come from REST; order book and trade-flow data should come from WebSockets.

**Why:** `yfinance` can show some crypto candles (e.g. BTC-USD), but it cannot provide true order flow. For useful crypto microstructure features we need L2 order book updates and executed trade streams. Coinbase Advanced Trade exposes public `level2`, `market_trades`, `ticker`, and `candles` channels. Kraken WebSocket v2 exposes public L2 `book` depth, trades, and checksums for book integrity.

**Caveat:** “Order flow” is exchange-local unless using a paid market data aggregator. Coinbase order flow is Coinbase flow, Kraken order flow is Kraken flow. Cross-exchange consolidated order flow requires an aggregator such as Kaiko, CoinAPI, CCData, or similar.

---

## 2026-05-31 — Cache-first dashboard with manual refresh

**Decision:** Use cache-first market-data loading in the frontend and disable automatic refresh behavior when cache exists. Data refresh happens only on explicit user action or missing cache.

**Why:** The project uses yfinance/Yahoo in Phase 0, which is rate-limited and unsuitable for frequent automatic fetches. Cache-first loading preserves responsiveness, lowers request volume, and aligns with local-dev reliability.

**Implementation detail:** Manual refresh requests incremental history via a `since` cursor and merges new bars client-side, rather than re-downloading full history each time.

---

## 2026-05-31 — Technical indicators computed server-side in quant layer

**Decision:** Compute market dashboard technical indicators in backend `quant/indicators/` and return indicator series through `/api/market/history`, instead of calculating indicators in the frontend.

**Why:** Keeps quant math in one place, aligns with architecture boundaries (routers thin, frontend display-only), and makes indicator logic reusable for future backtesting/strategy workflows. This also centralizes parameter validation and avoids divergent formulas between UI and quant engine.

**Implementation detail:** For incremental refresh requests with `since`, backend estimates and fetches a warm-up window before computing indicators, then trims output back to the visible window to preserve indicator correctness.

---

## 2026-05-31 — Backtesting v1 uses explicit indicator-rule definitions via API

**Decision:** Implement first backtesting UI/API as explicit indicator-rule definitions (left series, operator, right series/constant) rather than introducing a full strategy DSL or auto-generated strategy classes.

**Why:** Fastest path to honest diagnostics for many indicator combinations while keeping quant math in backend Python and frontend as control surface. It allows early idea triage and metric reporting without over-investing in architecture before validation workflows mature.

**Implementation detail:** `POST /api/market/backtest` receives indicator configs + entry/exit rules + initial capital, runs a long-only net-of-cost simulation, and returns metrics/trades/equity data.

---

## 2026-05-31 — Strategy backtesting enforces explicit signal-to-fill lag

**Decision:** Add a strategy-oriented backtesting engine (`quant/backtesting/strategy_engine.py`) that runs `BaseStrategy` implementations with a strict timing contract: signals are generated from data up to bar `t`, then executed no earlier than bar `t + lag` (default one bar) at bar open.

**Why:** The project direction is shifting from ad-hoc indicator-rule testing toward reusable strategy classes. Enforcing execution lag at the engine level prevents same-bar fill bias and reduces accidental look-ahead assumptions in strategy code.

**Implementation detail:** Engine tracks cash/positions/trades/equity, applies `CostModel` on entry and exit, and computes core net-of-cost metrics. First baseline strategy added: EMA crossover under `quant/strategies/ema_crossover.py`.

---

## 2026-05-31 — Crypto ML research foundation prioritized over live execution

**Decision:** Implement foundational research modules first: multi-asset backtesting, validation splits, statistical helpers, universe filtering, allocation sizing, and execution-readiness gates before exchange live trading or Gemini reviews.

**Why:** The user's repo direction is now a rigorous small/mid-cap crypto ML portfolio research platform. The highest-risk failure mode is not coding difficulty; it is false confidence from leakage, overfitting, weak universe selection, or unsafe sizing. These foundations make future strategy results harder to fool.

**Implementation detail:** Initial production-facing surface is intentionally narrow: an EMA baseline strategy API/UI report. More complex ML and Gemini report generation should consume structured artifacts from these modules rather than bypass them.

---

## 2026-05-31 — Gemini is the first LLM reviewer provider

**Decision:** Use Gemini through the current `google-genai` Python SDK as the first LLM reviewer provider, behind a small reviewer interface.

**Why:** The user wants Gemini for backtest report review. Keeping it behind `LlmReviewer` lets the platform switch or add providers later without changing research artifacts or strategy code.

**Implementation detail:** API keys are read from `GEMINI_API_KEY` in local `.env`; committed files only contain placeholders. The reviewer accepts structured `BacktestReviewArtifact` inputs and is explicitly report-only, never a signal generator.

---

## 2026-05-31 — Perplexity is used for current research summaries

**Decision:** Add Perplexity as the first current-web research provider using its bearer-token chat completions API.

**Why:** Gemini is used for reviewing structured backtest artifacts. Perplexity is better suited for current market/research summaries because it returns web-grounded answers with citations. Keeping the roles separate reduces the chance that external research text becomes an unvetted trading signal.

**Implementation detail:** `PerplexityResearcher` calls `https://api.perplexity.ai/chat/completions` with a configured Sonar model. API keys are read from `PERPLEXITY_API_KEY`; committed files only contain placeholders.
