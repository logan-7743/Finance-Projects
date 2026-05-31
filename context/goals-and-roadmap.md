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

### Phase 1 — First Strategy
- [ ] Backtest engine in `quant/backtesting/` with proper cost modeling
- [ ] A simple baseline strategy (e.g., SMA crossover or mean reversion) implemented and backtested
- [ ] Performance metrics: Sharpe, max drawdown, Calmar, net-of-cost P&L
- [ ] Backtest results displayed in the UI

### Phase 2 — Paper Trading
- [ ] Alpaca integration in `quant/execution/`
- [ ] Paper trading loop: signal → order → fill → position tracking
- [ ] Live position and P&L in the UI
- [ ] Alpha decay monitoring — live vs. backtest comparison

### Phase 3 — Sentiment + Research
- [ ] LLM sentiment integration (OpenAI or similar) on news/earnings
- [ ] Perplexity for automated research summaries
- [ ] Sentiment signals as strategy inputs or filters

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
