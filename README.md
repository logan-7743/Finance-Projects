# Quant Trading Platform

A local-first, cloud-ready quant trading platform for building, testing, and eventually running multiple trading algorithms with discipline.

The guiding principle: **tell the truth**. Strategies must be evaluated with real costs: slippage, transaction fees, latency, spread, market impact, and alpha decay. No fake backtests. No speculative claims. Paper first, real money only after rigorous testing.

## Current Scope

This first foundation pass includes:

- `.cursor/rules/` — persistent agent guidance for quant rigor, architecture, coding standards, and project memory
- `context/` — living wiki for decisions, issues, features, goals, and glossary
- `backend/` — FastAPI + Python quant core
- `frontend/` — Next.js + Tailwind dashboard
- First feature: type a stock ticker and view a historical price chart via `yfinance`

## Architecture

```text
frontend/  Next.js + TypeScript + Tailwind + lightweight-charts
    |
    | local REST API
    v
backend/   FastAPI + yfinance + quant core package
```

All quant logic belongs in `backend/quant/`. The frontend is display and interaction only.

## Local Development

Run both services together:

```bash
make dev
```

This starts:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://localhost:3000`

Press `Ctrl+C` to stop both.

Manual backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e \".[dev]\"
.venv/bin/uvicorn app.main:app --reload
```

Manual frontend:

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Local Secrets

Local credentials live in ignored `.env` files. Do not commit them.

- `backend/.env` — Alpaca paper trading credentials and backend config
- `frontend/.env.local` — optional frontend overrides

## Deployment Model (Future)

This repo is **local-first right now**. No cloud setup is required for the first deliverable.

Future production target:

- UI: Vercel
- Trading engine + API: GCP Cloud Run with `min-instances=1`
- Scheduler: GCP Cloud Scheduler
- Logs/audit trail: GCP Cloud Logging
- Database: TBD (Neon Postgres or GCP Cloud SQL)

The trading engine should not run on serverless functions because trading systems need persistent websockets, predictable latency, longer-running jobs, and durable state.

## Crypto Direction

Crypto support will use exchange APIs, not `yfinance`, for serious work:

- Coinbase Advanced Trade: public WebSocket `level2`, `market_trades`, `ticker`, `candles`
- Kraken WebSocket v2: public L2 `book`, trades, checksums, optional deeper/L3 feeds

Order flow is exchange-local unless using a paid consolidated provider.

## Roadmap

See [context/goals-and-roadmap.md](context/goals-and-roadmap.md).
