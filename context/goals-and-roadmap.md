# Goals and Roadmap

## North-Star Goals

1. **Build an honest, math-grounded trading platform** — analytical, not speculative. Every signal has a mathematical basis and an economic rationale.
2. **Paper-first discipline** — every strategy runs on Alpaca paper trading before any real capital.
3. **Real money only after rigorous testing** — out-of-sample validation, walk-forward testing, confirmed paper performance, risk limits defined.
4. **Scale capital slowly** — real money starts small and increases only with sustained evidence.
5. **Cloud-deployed, live UI** — the platform ultimately runs on the cloud with live performance insights accessible on desktop and mobile.

## Roadmap

### Phase 0 — Foundation (current)
- [x] `.cursor/rules/` — project conscience and agent workflow
- [x] `context/` — living wiki / project memory
- [x] Backend: FastAPI + yfinance market data API
- [x] Frontend: Next.js + shadcn-style dashboard with candlestick stock chart
- [x] Full monorepo running on localhost
- [x] Market dashboard indicator engine (server-side quant math + selectable UI overlays/oscillators)

### Phase 1 — First Strategy
- [x] Backtest engine in `quant/backtesting/` with proper cost modeling
- [x] A simple baseline strategy (e.g., SMA crossover or mean reversion) implemented and backtested
- [x] Performance metrics: Sharpe, max drawdown, Calmar, net-of-cost P&L
- [x] Backtest results displayed in the UI

Progress note (2026-05-31):
- Added strategy-oriented backtest foundation (`quant/backtesting/strategy_engine.py`) with explicit execution lag and cost-aware fills.
- Added first baseline strategy scaffold (`quant/strategies/ema_crossover.py`) and backend tests.
- Added multi-asset backtest foundation, validation utilities, reusable metrics/statistics, cross-sectional momentum baseline, crypto universe filtering, allocation sizing, and execution-readiness gates.
- Added initial strategy backtest API/UI surface for the EMA baseline.
- Added dedicated `/research` cockpit for EMA baseline metrics, Gemini review, and Perplexity research.
- [x] Basic indicator-rule backtest API + dashboard runner with net-of-cost diagnostic metrics

### Phase 1b — Crypto ML Research Spine
- [x] Multi-asset aligned-bar backtest foundation
- [x] Train/validation/final-test and walk-forward split utilities
- [x] Purged/embargoed fold utilities for future-horizon labels
- [x] Statistical robustness helpers (bootstrap, permutation, probabilistic Sharpe)
- [x] Crypto universe filter scaffold (market cap, volume, venue, liquidity, risk flags)
- [x] Conservative allocation/risk-budgeting scaffold
- [x] Execution-readiness stage gates
- [x] Gemini research reviewer over structured artifacts
- [ ] Exchange-native crypto data provider (Coinbase/Kraken)
- [ ] External paper broker integration

### Phase 2 — Paper Trading
- [ ] Alpaca integration in `quant/execution/`
- [ ] Paper trading loop: signal → order → fill → position tracking
- [ ] Live position and P&L in the UI
- [ ] Alpha decay monitoring — live vs. backtest comparison

### Phase 3 — Sentiment + Research
- [ ] LLM sentiment integration (OpenAI or similar) on news/earnings
- [x] Perplexity for automated research summaries
- [x] Local Trump event corpus pull foundation (two-year trump.fm social posts + White House official transcripts/statements)
- [ ] Sentiment signals as strategy inputs or filters

Progress note (2026-05-31):
- Added `quant/events/` with streaming JSONL storage, trump.fm social-post ingestion, White House sitemap/article ingestion, merge/coverage reporting, and a CLI pull entry point.
- Pulled the current local corpus under `data/events/`: `9,840` merged events (`9,794` social posts, `46` White House records). No market labels or strategy logic yet.
- Added `/api/events/trump` and `/events` so the corpus can be browsed with source/search/date filters before labeling work begins.

### Phase 4 — Crypto
- [ ] Coinbase integration for crypto market data (candles, L2 book, market trades)
- [ ] Kraken integration for crypto order book/trade flow comparison
- [ ] First crypto strategy

### Phase 5 — Cloud Deployment
- [ ] Backend → GCP Cloud Run (`min-instances=1`)
- [ ] Frontend → Vercel
- [ ] Cloud Scheduler for strategy cron jobs
- [ ] Cloud Logging for order audit trail
- [ ] Database for trade history and equity curve (Neon or Cloud SQL)

### Phase 6 — Real Money
- [ ] All Phase 2 criteria met and sustained in paper
- [ ] Risk limits and position sizing rules defined and enforced in code
- [ ] Start with smallest viable real allocation
- [ ] Monitor closely; scale only with evidence
