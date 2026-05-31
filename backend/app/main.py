from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import backtests, events, market, research


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Quant Trading Platform API",
    description="Market data, strategy signals, and trading engine.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(backtests.router, prefix="/api/backtests", tags=["backtests"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(events.router, prefix="/api/events", tags=["events"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
