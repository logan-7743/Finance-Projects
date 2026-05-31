# Quant Trading Backend

FastAPI backend and Python quant core for the platform.

## Local Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload
```

API will run at `http://127.0.0.1:8000`.

## Endpoints

- `GET /health`
- `GET /api/market/history?symbol=AAPL&range=6M`
- `GET /api/market/quote?symbol=AAPL`

## Quant Package

All trading logic belongs under `quant/`:

- `quant/data/` — market data sources (`YFinanceSource` implemented)
- `quant/strategies/` — strategy interfaces
- `quant/backtesting/` — future backtest engine
- `quant/execution/` — future broker interfaces
- `quant/risk/` — cost models for fees, slippage, spread, latency
- `quant/metrics/` — future performance metrics
- `quant/sentiment/` — future LLM / Perplexity sentiment inputs

## Warning

`yfinance` is fine for local research and historical charting, but it is not a production-grade live trading data feed.
