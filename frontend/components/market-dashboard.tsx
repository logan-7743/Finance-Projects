"use client";

import { Activity, BarChart3, Brain, CandlestickChart, Server } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PriceChart } from "@/components/price-chart";
import { SymbolSearch } from "@/components/symbol-search";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartRange,
  type ChartType,
  getHistory,
  getQuote,
  type HistoryResponse,
  type QuoteResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const ranges: ChartRange[] = ["1D", "5D", "1M", "6M", "1Y", "5Y"];
const HISTORY_CACHE_KEY_PREFIX = "market-history";
const QUOTE_CACHE_KEY_PREFIX = "market-quote";

interface CachedValue<T> {
  data: T;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatLargeNumber(value: number | null) {
  if (value === null) {
    return "n/a";
  }

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function historyCacheKey(symbol: string, range: ChartRange) {
  return `${HISTORY_CACHE_KEY_PREFIX}:${symbol}:${range}`;
}

function quoteCacheKey(symbol: string) {
  return `${QUOTE_CACHE_KEY_PREFIX}:${symbol}`;
}

function readCache<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CachedValue<T>;
    return parsed.data;
  } catch {
    return null;
  }
}

function writeCache<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify({ data: value } as CachedValue<T>));
}

function mergeHistory(
  baseHistory: HistoryResponse | null,
  incomingHistory: HistoryResponse,
): HistoryResponse {
  if (!baseHistory) {
    return incomingHistory;
  }
  const map = new Map(baseHistory.bars.map((bar) => [bar.time, bar]));
  for (const bar of incomingHistory.bars) {
    map.set(bar.time, bar);
  }
  const bars = Array.from(map.values()).sort((a, b) => a.time.localeCompare(b.time));
  return {
    symbol: incomingHistory.symbol,
    period: incomingHistory.period,
    interval: incomingHistory.interval,
    bars,
  };
}

export function MarketDashboard() {
  const [symbol, setSymbol] = useState("AAPL");
  const [range, setRange] = useState<ChartRange>("6M");
  const [chartType, setChartType] = useState<ChartType>("candles");
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [quote, setQuote] = useState<QuoteResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const fetchMarketData = useCallback(
    async (options: {
      fetchHistory: boolean;
      fetchQuote: boolean;
      incremental: boolean;
      baseHistory: HistoryResponse | null;
      source: "initial" | "manual";
    }) => {
      const requestId = ++requestIdRef.current;
      if (options.source === "initial") {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setError(null);

      let nextHistory = options.baseHistory;
      let historyFailure: Error | null = null;

      if (options.fetchHistory) {
        const since = options.incremental ? options.baseHistory?.bars.at(-1)?.time : undefined;
        try {
          const historyResponse = await getHistory(symbol, range, { since });
          if (requestId !== requestIdRef.current) {
            return;
          }
          nextHistory =
            options.incremental && options.baseHistory
              ? mergeHistory(options.baseHistory, historyResponse)
              : historyResponse;
          setHistory(nextHistory);
          writeCache(historyCacheKey(symbol, range), nextHistory);
        } catch (err) {
          historyFailure = err instanceof Error ? err : new Error("Failed to load market data.");
        }
      }

      if (options.fetchQuote) {
        try {
          const quoteResponse = await getQuote(symbol);
          if (requestId !== requestIdRef.current) {
            return;
          }
          setQuote(quoteResponse);
          writeCache(quoteCacheKey(symbol), quoteResponse);
        } catch {
          // Keep stale quote if refresh fails.
        }
      }

      if (requestId !== requestIdRef.current) {
        return;
      }

      if (historyFailure) {
        setError(historyFailure.message);
      }
      setIsLoading(false);
      setIsRefreshing(false);
    },
    [range, symbol],
  );

  useEffect(() => {
    async function loadFromCache() {
      setError(null);
      const cachedHistory = readCache<HistoryResponse>(historyCacheKey(symbol, range));
      const cachedQuote = readCache<QuoteResponse>(quoteCacheKey(symbol));
      setHistory(cachedHistory);
      setQuote(cachedQuote);

      const needsHistory = cachedHistory === null;
      const needsQuote = cachedQuote === null;
      if (!needsHistory && !needsQuote) {
        setIsLoading(false);
        return;
      }

      await fetchMarketData({
        fetchHistory: needsHistory,
        fetchQuote: needsQuote,
        incremental: false,
        baseHistory: cachedHistory,
        source: "initial",
      });
    }

    void loadFromCache();
  }, [fetchMarketData, range, symbol]);

  async function refreshData() {
    await fetchMarketData({
      fetchHistory: true,
      fetchQuote: true,
      incremental: true,
      baseHistory: history,
      source: "manual",
    });
  }

  const latestClose = useMemo(() => {
    const bars = history?.bars ?? [];
    return bars.length > 0 ? bars[bars.length - 1].close : null;
  }, [history]);

  const changeIsPositive = (quote?.change ?? 0) >= 0;

  return (
    <div className="min-h-screen bg-black text-zinc-50">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-zinc-900 bg-zinc-950/80 p-6 lg:block">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-zinc-100 p-2 text-zinc-950">
            <CandlestickChart className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold">Quant Platform</p>
            <p className="text-xs text-zinc-500">Local research mode</p>
          </div>
        </div>

        <nav className="mt-10 space-y-2 text-sm">
          <a className="flex items-center gap-2 rounded-lg bg-zinc-900 px-3 py-2 text-zinc-50">
            <BarChart3 className="h-4 w-4" />
            Market Data
          </a>
          <a className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500">
            <Activity className="h-4 w-4" />
            Strategies
          </a>
          <a className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500">
            <Brain className="h-4 w-4" />
            Sentiment
          </a>
          <a className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500">
            <Server className="h-4 w-4" />
            Execution
          </a>
        </nav>
      </aside>

      <main className="lg:pl-64">
        <section className="border-b border-zinc-900 px-6 py-6 sm:px-8">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm text-zinc-500">Localhost foundation</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight">
                Market Data Dashboard
              </h1>
              <p className="mt-2 max-w-2xl text-sm text-zinc-400">
                First live panel: historical OHLCV from yfinance through the
                FastAPI backend. No trading logic runs in the browser.
              </p>
            </div>

            <SymbolSearch
              currentSymbol={symbol}
              onSubmit={setSymbol}
              disabled={isLoading || isRefreshing}
            />
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-4 px-6 py-6 sm:px-8 md:grid-cols-4">
          <Card>
            <CardHeader>
              <CardDescription>Symbol</CardDescription>
              <CardTitle>{quote?.symbol ?? symbol}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-zinc-400">
              {quote?.name ?? "Awaiting quote"}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Last Price</CardDescription>
              <CardTitle>
                {latestClose !== null ? formatCurrency(latestClose) : "n/a"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-zinc-400">
              Source: yfinance
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Change</CardDescription>
              <CardTitle
                className={cn(
                  changeIsPositive ? "text-emerald-400" : "text-red-400",
                )}
              >
                {quote ? `${quote.change.toFixed(2)} (${quote.change_pct.toFixed(2)}%)` : "n/a"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-zinc-400">
              vs previous close
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Market Cap</CardDescription>
              <CardTitle>{formatLargeNumber(quote?.market_cap ?? null)}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-zinc-400">
              Quote metadata
            </CardContent>
          </Card>
        </section>

        <section className="mx-auto max-w-7xl px-6 pb-10 sm:px-8">
          <Card>
            <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle>{symbol} Price Chart</CardTitle>
                <CardDescription>
                  Range: {range} · Bars: {history?.bars.length ?? 0} · Interval:{" "}
                  {history?.interval ?? "n/a"}
                </CardDescription>
              </div>

              <div className="flex flex-wrap gap-2">
                {ranges.map((item) => (
                  <Button
                    key={item}
                    variant={item === range ? "default" : "secondary"}
                    size="sm"
                    onClick={() => setRange(item)}
                    disabled={isLoading}
                  >
                    {item}
                  </Button>
                ))}
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => void refreshData()}
                  disabled={isLoading || isRefreshing}
                >
                  {isRefreshing ? "Refreshing..." : "Refresh"}
                </Button>
                <Button
                  variant={chartType === "candles" ? "default" : "secondary"}
                  size="sm"
                  onClick={() =>
                    setChartType((current) =>
                      current === "candles" ? "line" : "candles",
                    )
                  }
                >
                  {chartType === "candles" ? "Candles" : "Line"}
                </Button>
              </div>
            </CardHeader>

            <CardContent>
              {error ? (
                <div className="rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-200">
                  {error}
                </div>
              ) : (
                <PriceChart data={history?.bars ?? []} type={chartType} />
              )}
              {isLoading ? (
                <p className="mt-3 text-sm text-zinc-500">Loading market data...</p>
              ) : null}
              {isRefreshing ? (
                <p className="mt-3 text-sm text-zinc-500">Refreshing latest bars...</p>
              ) : null}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
