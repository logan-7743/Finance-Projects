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
