# Quant Trading Frontend

Next.js dashboard for the local quant trading platform.

## Local Development

Create `.env.local` from `.env.example` if you need to override the backend URL:

```bash
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The frontend calls the FastAPI backend at `NEXT_PUBLIC_API_URL` (defaults to `http://127.0.0.1:8000`).

## Current Feature

- Market data dashboard
- Ticker search
- Range selector
- Candlestick / line toggle
- TradingView `lightweight-charts` renderer

## Commands

```bash
npm run lint
npm run build
```

## Boundary

The frontend is display and interaction only. No trading strategy, data fetching from providers, or order execution logic belongs here. All quant work lives in `backend/quant/` and is exposed through the FastAPI backend.

## Future Deploy

This app is designed to deploy to Vercel later. The trading engine should remain on an always-on backend (future: GCP Cloud Run), not in Vercel serverless functions.
