"use client";

import {
  Activity,
  BarChart3,
  Brain,
  CandlestickChart,
  Database,
  Plus,
  Server,
  X,
} from "lucide-react";
import Link from "next/link";
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
import { Input } from "@/components/ui/input";
import {
  type ChartRange,
  type ChartType,
  type BacktestResult,
  type BacktestRule,
  getHistory,
  getQuote,
  reviewBacktestArtifact,
  runEmaCrossoverBacktest,
  runIndicatorBacktest,
  type HistoryResponse,
  type IndicatorKind,
  type IndicatorRequestConfig,
  type RuleOperator,
  type QuoteResponse,
  type StrategyBacktestResult,
  type LlmReviewResult,
} from "@/lib/api";
import {
  createIndicatorConfig,
  INDICATOR_SPECS,
  INDICATOR_SPECS_BY_KIND,
} from "@/lib/indicators";
import { cn } from "@/lib/utils";

const ranges: ChartRange[] = ["1D", "5D", "1M", "6M", "1Y", "5Y"];
const stockPresets = ["AAPL", "MSFT", "NVDA"];
const cryptoPresets = ["BTC-USD", "ETH-USD", "SOL-USD"];
const HISTORY_CACHE_KEY_PREFIX = "market-history";
const QUOTE_CACHE_KEY_PREFIX = "market-quote";
const INDICATOR_CONFIG_CACHE_KEY = "market-indicators-config";
const DEFAULT_INITIAL_CAPITAL = 100_000;

const operatorOptions: Array<{ value: RuleOperator; label: string }> = [
  { value: "gt", label: ">" },
  { value: "lt", label: "<" },
  { value: "crosses_above", label: "crosses above" },
  { value: "crosses_below", label: "crosses below" },
];

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

function stableIndicatorSignature(indicators: IndicatorRequestConfig[]): string {
  const normalized = indicators
    .map((indicator) => ({
      id: indicator.id,
      kind: indicator.kind,
      params: Object.fromEntries(Object.entries(indicator.params).sort()),
    }))
    .sort((a, b) => a.id.localeCompare(b.id));
  return JSON.stringify(normalized);
}

function historyCacheKey(
  symbol: string,
  range: ChartRange,
  indicatorSignature: string,
) {
  return `${HISTORY_CACHE_KEY_PREFIX}:${symbol}:${range}:${indicatorSignature}`;
}

function quoteCacheKey(symbol: string) {
  return `${QUOTE_CACHE_KEY_PREFIX}:${symbol}`;
}

function readCache<T>(key: string): T | null {
  if (typeof window === "undefined") {
    return null;
  }
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
  if (typeof window === "undefined") {
    return;
  }
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
  const baseIndicators = baseHistory.indicators ?? [];
  const incomingIndicators = incomingHistory.indicators ?? [];
  const mergedIndicators = incomingIndicators.map((incomingIndicator) => {
    const baseIndicator = baseIndicators.find(
      (candidate) => candidate.id === incomingIndicator.id,
    );
    if (!baseIndicator) {
      return incomingIndicator;
    }
    return {
      ...incomingIndicator,
      lines: incomingIndicator.lines.map((incomingLine) => {
        const baseLine = baseIndicator.lines.find((candidate) => candidate.key === incomingLine.key);
        if (!baseLine) {
          return incomingLine;
        }
        const pointsMap = new Map(baseLine.points.map((point) => [point.time, point]));
        for (const point of incomingLine.points) {
          pointsMap.set(point.time, point);
        }
        const points = Array.from(pointsMap.values()).sort((a, b) => a.time.localeCompare(b.time));
        return {
          ...incomingLine,
          points,
        };
      }),
    };
  });
  return {
    symbol: incomingHistory.symbol,
    period: incomingHistory.period,
    interval: incomingHistory.interval,
    bars,
    indicators: mergedIndicators,
  };
}

function lineKeysForIndicator(indicator: IndicatorRequestConfig): string[] {
  const spec = INDICATOR_SPECS_BY_KIND[indicator.kind];
  return spec.lineKeys.map((line) => line.key);
}

function createDefaultRule(indicators: IndicatorRequestConfig[]): BacktestRule {
  const left = indicators[0];
  const right = indicators[1] ?? indicators[0];
  const leftLine = left ? lineKeysForIndicator(left)[0] : "ema";
  const rightLine = right ? lineKeysForIndicator(right)[0] : "ema";
  return {
    left_indicator_id: left?.id ?? "missing-left",
    left_line_key: leftLine,
    operator: "crosses_above",
    right_type: "indicator",
    right_indicator_id: right?.id ?? left?.id ?? null,
    right_line_key: rightLine,
    right_value: null,
  };
}

function normalizeRulesForIndicators(
  rules: BacktestRule[],
  indicators: IndicatorRequestConfig[],
): BacktestRule[] {
  if (indicators.length === 0) {
    return [];
  }
  const validIds = new Set(indicators.map((indicator) => indicator.id));
  const fallback = indicators[0];
  return rules.map((rule) => {
    const leftIndicator = validIds.has(rule.left_indicator_id)
      ? indicators.find((indicator) => indicator.id === rule.left_indicator_id) ?? fallback
      : fallback;
    const leftLines = lineKeysForIndicator(leftIndicator);
    const leftLine = leftLines.includes(rule.left_line_key) ? rule.left_line_key : leftLines[0];

    if (rule.right_type === "indicator") {
      const rightIndicator =
        rule.right_indicator_id && validIds.has(rule.right_indicator_id)
          ? indicators.find((indicator) => indicator.id === rule.right_indicator_id) ?? fallback
          : fallback;
      const rightLines = lineKeysForIndicator(rightIndicator);
      const rightLine = rule.right_line_key && rightLines.includes(rule.right_line_key)
        ? rule.right_line_key
        : rightLines[0];
      return {
        ...rule,
        left_indicator_id: leftIndicator.id,
        left_line_key: leftLine,
        right_indicator_id: rightIndicator.id,
        right_line_key: rightLine,
      };
    }

    return {
      ...rule,
      left_indicator_id: leftIndicator.id,
      left_line_key: leftLine,
      right_indicator_id: null,
      right_line_key: null,
      right_value: rule.right_value ?? 0,
    };
  });
}

export function MarketDashboard() {
  const [symbol, setSymbol] = useState("AAPL");
  const [range, setRange] = useState<ChartRange>("6M");
  const [chartType, setChartType] = useState<ChartType>("candles");
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [quote, setQuote] = useState<QuoteResponse | null>(null);
  const [indicatorConfigs, setIndicatorConfigs] = useState<IndicatorRequestConfig[]>(
    () => readCache<IndicatorRequestConfig[]>(INDICATOR_CONFIG_CACHE_KEY) ?? [],
  );
  const [kindToAdd, setKindToAdd] = useState<IndicatorKind>("ema");
  const [initialCapital, setInitialCapital] = useState(DEFAULT_INITIAL_CAPITAL);
  const [entryRules, setEntryRules] = useState<BacktestRule[]>([]);
  const [exitRules, setExitRules] = useState<BacktestRule[]>([]);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [isStrategyBacktesting, setIsStrategyBacktesting] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [strategyBacktestResult, setStrategyBacktestResult] =
    useState<StrategyBacktestResult | null>(null);
  const [researchReview, setResearchReview] = useState<LlmReviewResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const indicatorSignature = useMemo(
    () => stableIndicatorSignature(indicatorConfigs),
    [indicatorConfigs],
  );

  useEffect(() => {
    writeCache(INDICATOR_CONFIG_CACHE_KEY, indicatorConfigs);
  }, [indicatorConfigs]);

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
          const historyResponse = await getHistory(symbol, range, {
            since,
            indicators: indicatorConfigs,
          });
          if (requestId !== requestIdRef.current) {
            return;
          }
          nextHistory =
            options.incremental && options.baseHistory
              ? mergeHistory(options.baseHistory, historyResponse)
              : historyResponse;
          setHistory(nextHistory);
          writeCache(historyCacheKey(symbol, range, indicatorSignature), nextHistory);
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
    [indicatorConfigs, indicatorSignature, range, symbol],
  );

  useEffect(() => {
    async function loadFromCache() {
      setError(null);
      const cachedHistory = readCache<HistoryResponse>(
        historyCacheKey(symbol, range, indicatorSignature),
      );
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
  }, [fetchMarketData, indicatorSignature, range, symbol]);

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
  const indicatorsById = useMemo(
    () => new Map(indicatorConfigs.map((indicator) => [indicator.id, indicator])),
    [indicatorConfigs],
  );

  function handleAddIndicator() {
    const id = `${kindToAdd}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
    setIndicatorConfigs((current) => {
      const nextIndicators = [...current, createIndicatorConfig(kindToAdd, id)];
      setEntryRules((currentRules) => {
        if (currentRules.length === 0) {
          return [createDefaultRule(nextIndicators)];
        }
        return normalizeRulesForIndicators(currentRules, nextIndicators);
      });
      setExitRules((currentRules) => {
        if (currentRules.length === 0) {
          return [
            {
              ...createDefaultRule(nextIndicators),
              operator: "crosses_below",
            },
          ];
        }
        return normalizeRulesForIndicators(currentRules, nextIndicators);
      });
      return nextIndicators;
    });
  }

  function handleRemoveIndicator(indicatorId: string) {
    setIndicatorConfigs((current) => {
      const nextIndicators = current.filter((indicator) => indicator.id !== indicatorId);
      setEntryRules((currentRules) => normalizeRulesForIndicators(currentRules, nextIndicators));
      setExitRules((currentRules) => normalizeRulesForIndicators(currentRules, nextIndicators));
      return nextIndicators;
    });
  }

  function handleParamUpdate(indicatorId: string, key: string, value: number) {
    if (!Number.isFinite(value)) {
      return;
    }
    setIndicatorConfigs((current) =>
      current.map((indicator) =>
        indicator.id === indicatorId
          ? {
              ...indicator,
              params: {
                ...indicator.params,
                [key]: value,
              },
            }
          : indicator,
      ),
    );
  }

  function updateRule(
    side: "entry" | "exit",
    index: number,
    updater: (rule: BacktestRule) => BacktestRule,
  ) {
    const setRules = side === "entry" ? setEntryRules : setExitRules;
    setRules((current) =>
      current.map((rule, currentIndex) =>
        currentIndex === index ? updater(rule) : rule,
      ),
    );
  }

  function addRule(side: "entry" | "exit") {
    if (indicatorConfigs.length === 0) {
      return;
    }
    const setRules = side === "entry" ? setEntryRules : setExitRules;
    setRules((current) => [...current, createDefaultRule(indicatorConfigs)]);
  }

  function removeRule(side: "entry" | "exit", index: number) {
    const setRules = side === "entry" ? setEntryRules : setExitRules;
    setRules((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  async function runBacktest() {
    if (indicatorConfigs.length === 0) {
      setBacktestError("Add at least one indicator before running a backtest.");
      return;
    }
    const resolvedEntryRules = normalizeRulesForIndicators(
      entryRules.length > 0 ? entryRules : [createDefaultRule(indicatorConfigs)],
      indicatorConfigs,
    );
    const resolvedExitRules = normalizeRulesForIndicators(
      exitRules.length > 0
        ? exitRules
        : [
            {
              ...createDefaultRule(indicatorConfigs),
              operator: "crosses_below",
            },
          ],
      indicatorConfigs,
    );
    setIsBacktesting(true);
    setBacktestError(null);
    try {
      const result = await runIndicatorBacktest({
        symbol,
        range,
        indicators: indicatorConfigs,
        config: {
          initial_capital: initialCapital,
          entry_rules: resolvedEntryRules,
          exit_rules: resolvedExitRules,
        },
      });
      setBacktestResult(result);
    } catch (err) {
      setBacktestError(err instanceof Error ? err.message : "Backtest failed.");
    } finally {
      setIsBacktesting(false);
    }
  }

  async function runStrategyBaseline() {
    setIsStrategyBacktesting(true);
    setBacktestError(null);
    try {
      const result = await runEmaCrossoverBacktest({
        symbol,
        period: "1y",
        interval: "1d",
        initial_capital: initialCapital,
        fast_period: 12,
        slow_period: 26,
        execution_lag_bars: 1,
      });
      setStrategyBacktestResult(result);
      setResearchReview(null);
    } catch (err) {
      setBacktestError(err instanceof Error ? err.message : "Strategy baseline failed.");
    } finally {
      setIsStrategyBacktesting(false);
    }
  }

  async function reviewStrategyBaseline() {
    if (!strategyBacktestResult) {
      return;
    }
    setIsReviewing(true);
    setBacktestError(null);
    try {
      const firstTime = strategyBacktestResult.equity_curve[0]?.[0] ?? "unknown";
      const lastTime =
        strategyBacktestResult.equity_curve[strategyBacktestResult.equity_curve.length - 1]?.[0] ??
        "unknown";
      const review = await reviewBacktestArtifact({
        strategy_name: strategyBacktestResult.strategy_name,
        symbol: strategyBacktestResult.symbol,
        hypothesis: "A fast EMA crossing above a slow EMA captures short-term momentum.",
        data_range: `${firstTime} to ${lastTime}`,
        cost_assumptions: [
          "Uses backend CostModel defaults.",
          "Execution is delayed by one bar and filled at next bar open.",
        ],
        validation_notes: [
          "This is an in-sample baseline report.",
          "Walk-forward and final holdout validation are required before paper trading.",
        ],
        metrics: [
          { name: "Total Return %", value: strategyBacktestResult.metrics.total_return_pct },
          { name: "Sharpe", value: strategyBacktestResult.metrics.sharpe_ratio },
          { name: "Max Drawdown %", value: strategyBacktestResult.metrics.max_drawdown_pct },
          { name: "Trade Count", value: strategyBacktestResult.metrics.trade_count },
          { name: "Win Rate %", value: strategyBacktestResult.metrics.win_rate_pct },
          { name: "Ending Equity", value: strategyBacktestResult.metrics.ending_equity },
        ],
        risks: [
          "Data source may be research-grade only.",
          "No regime breakdown yet.",
          "No untouched final holdout has been run.",
        ],
      });
      setResearchReview(review);
    } catch (err) {
      setBacktestError(err instanceof Error ? err.message : "Gemini review failed.");
    } finally {
      setIsReviewing(false);
    }
  }

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
          <Link className="flex items-center gap-2 rounded-lg bg-zinc-900 px-3 py-2 text-zinc-50" href="/">
            <BarChart3 className="h-4 w-4" />
            Market Data
          </Link>
          <Link className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500" href="/research">
            <Activity className="h-4 w-4" />
            Research
          </Link>
          <Link className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500" href="/events">
            <Database className="h-4 w-4" />
            Event Corpus
          </Link>
          <span className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-600">
            <Brain className="h-4 w-4" />
            Gemini Review
          </span>
          <span className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-600">
            <Server className="h-4 w-4" />
            Execution
          </span>
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
                Historical OHLCV for equities and major crypto pairs from yfinance
                through the FastAPI backend. No trading logic runs in the browser.
              </p>
            </div>

            <SymbolSearch
              currentSymbol={symbol}
              onSubmit={setSymbol}
              disabled={isLoading || isRefreshing}
            />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-zinc-400">
            <span>Quick symbols:</span>
            {stockPresets.map((preset) => (
              <Button
                key={preset}
                variant={symbol === preset ? "default" : "secondary"}
                size="sm"
                onClick={() => setSymbol(preset)}
                disabled={isLoading || isRefreshing}
              >
                {preset}
              </Button>
            ))}
            <span className="mx-1 text-zinc-600">|</span>
            {cryptoPresets.map((preset) => (
              <Button
                key={preset}
                variant={symbol === preset ? "default" : "secondary"}
                size="sm"
                onClick={() => setSymbol(preset)}
                disabled={isLoading || isRefreshing}
              >
                {preset}
              </Button>
            ))}
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
                  {history?.interval ?? "n/a"} · Indicators: {indicatorConfigs.length}
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
              <div className="mb-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                    Indicators
                  </span>
                  <select
                    value={kindToAdd}
                    onChange={(event) => setKindToAdd(event.target.value as IndicatorKind)}
                    className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
                    disabled={isLoading || isRefreshing}
                  >
                    {INDICATOR_SPECS.map((spec) => (
                      <option key={spec.kind} value={spec.kind}>
                        {spec.label}
                      </option>
                    ))}
                  </select>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleAddIndicator}
                    disabled={isLoading || isRefreshing}
                  >
                    <Plus className="mr-1 h-3 w-3" />
                    Add
                  </Button>
                </div>

                {indicatorConfigs.length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {indicatorConfigs.map((indicator) => {
                      const spec = INDICATOR_SPECS_BY_KIND[indicator.kind];
                      return (
                        <div
                          key={indicator.id}
                          className="rounded-md border border-zinc-800 bg-zinc-900/50 p-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium text-zinc-200">{spec.label}</p>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRemoveIndicator(indicator.id)}
                              className="h-7 px-2 text-zinc-400 hover:text-zinc-100"
                              disabled={isLoading || isRefreshing}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                          {spec.params.length > 0 ? (
                            <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-4">
                              {spec.params.map((param) => (
                                <label key={param.key} className="text-xs text-zinc-400">
                                  <span>{param.label}</span>
                                  <Input
                                    type="number"
                                    value={indicator.params[param.key] ?? spec.defaults[param.key]}
                                    min={param.min}
                                    max={param.max}
                                    step={param.step}
                                    onChange={(event) =>
                                      handleParamUpdate(
                                        indicator.id,
                                        param.key,
                                        Number(event.target.value),
                                      )
                                    }
                                    className="mt-1 h-8 border-zinc-700 bg-zinc-950 text-zinc-100"
                                  />
                                </label>
                              ))}
                            </div>
                          ) : (
                            <p className="mt-2 text-xs text-zinc-500">No editable parameters.</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-zinc-500">
                    No indicators selected. Add one to overlay quant signals on the chart.
                  </p>
                )}
              </div>
              <div className="mb-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                      Basic Backtest
                    </p>
                    <p className="text-xs text-zinc-500">
                      Net-of-cost sanity checks, not institutional-grade validation.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-zinc-400">
                      Initial Capital
                      <Input
                        type="number"
                        min={10_000}
                        step={1_000}
                        value={initialCapital}
                        onChange={(event) => setInitialCapital(Number(event.target.value))}
                        className="mt-1 h-8 w-36 border-zinc-700 bg-zinc-950 text-zinc-100"
                      />
                    </label>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void runBacktest()}
                      disabled={isBacktesting || isLoading || indicatorConfigs.length === 0}
                    >
                      {isBacktesting ? "Running..." : "Run Backtest"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void runStrategyBaseline()}
                      disabled={isStrategyBacktesting || isLoading}
                    >
                      {isStrategyBacktesting ? "Running EMA..." : "Run EMA Baseline"}
                    </Button>
                  </div>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2">
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-sm font-medium text-zinc-200">Entry Rules (ALL true)</p>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => addRule("entry")}
                        className="h-7 px-2 text-zinc-400 hover:text-zinc-100"
                      >
                        <Plus className="mr-1 h-3 w-3" />
                        Add
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {entryRules.map((rule, index) => {
                        const leftIndicator = indicatorsById.get(rule.left_indicator_id);
                        const leftLineKeys = leftIndicator ? lineKeysForIndicator(leftIndicator) : [];
                        const rightIndicator =
                          rule.right_indicator_id != null
                            ? indicatorsById.get(rule.right_indicator_id)
                            : undefined;
                        const rightLineKeys = rightIndicator ? lineKeysForIndicator(rightIndicator) : [];
                        return (
                          <div key={`entry-${index}`} className="rounded border border-zinc-800 p-2">
                            <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                              <select
                                value={rule.left_indicator_id}
                                onChange={(event) =>
                                  updateRule("entry", index, (current) => {
                                    const nextIndicator = indicatorsById.get(event.target.value);
                                    const nextLine = nextIndicator
                                      ? lineKeysForIndicator(nextIndicator)[0]
                                      : current.left_line_key;
                                    return {
                                      ...current,
                                      left_indicator_id: event.target.value,
                                      left_line_key: nextLine,
                                    };
                                  })
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                {indicatorConfigs.map((indicator) => (
                                  <option key={indicator.id} value={indicator.id}>
                                    {INDICATOR_SPECS_BY_KIND[indicator.kind].label} ({indicator.id.slice(-4)})
                                  </option>
                                ))}
                              </select>
                              <select
                                value={rule.left_line_key}
                                onChange={(event) =>
                                  updateRule("entry", index, (current) => ({
                                    ...current,
                                    left_line_key: event.target.value,
                                  }))
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                {leftLineKeys.map((lineKey) => (
                                  <option key={lineKey} value={lineKey}>
                                    {lineKey}
                                  </option>
                                ))}
                              </select>
                              <select
                                value={rule.operator}
                                onChange={(event) =>
                                  updateRule("entry", index, (current) => ({
                                    ...current,
                                    operator: event.target.value as RuleOperator,
                                  }))
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                {operatorOptions.map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                              <select
                                value={rule.right_type}
                                onChange={(event) =>
                                  updateRule("entry", index, (current) => ({
                                    ...current,
                                    right_type: event.target.value as "indicator" | "value",
                                  }))
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                <option value="indicator">Indicator</option>
                                <option value="value">Constant</option>
                              </select>
                              {rule.right_type === "indicator" ? (
                                <>
                                  <select
                                    value={rule.right_indicator_id ?? ""}
                                    onChange={(event) =>
                                      updateRule("entry", index, (current) => {
                                        const nextIndicator = indicatorsById.get(event.target.value);
                                        const nextLine = nextIndicator
                                          ? lineKeysForIndicator(nextIndicator)[0]
                                          : current.right_line_key;
                                        return {
                                          ...current,
                                          right_indicator_id: event.target.value,
                                          right_line_key: nextLine ?? null,
                                        };
                                      })
                                    }
                                    className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                                  >
                                    {indicatorConfigs.map((indicator) => (
                                      <option key={indicator.id} value={indicator.id}>
                                        {INDICATOR_SPECS_BY_KIND[indicator.kind].label} ({indicator.id.slice(-4)})
                                      </option>
                                    ))}
                                  </select>
                                  <select
                                    value={rule.right_line_key ?? ""}
                                    onChange={(event) =>
                                      updateRule("entry", index, (current) => ({
                                        ...current,
                                        right_line_key: event.target.value,
                                      }))
                                    }
                                    className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                                  >
                                    {rightLineKeys.map((lineKey) => (
                                      <option key={lineKey} value={lineKey}>
                                        {lineKey}
                                      </option>
                                    ))}
                                  </select>
                                </>
                              ) : (
                                <Input
                                  type="number"
                                  value={rule.right_value ?? 0}
                                  step={0.1}
                                  onChange={(event) =>
                                    updateRule("entry", index, (current) => ({
                                      ...current,
                                      right_value: Number(event.target.value),
                                    }))
                                  }
                                  className="h-8 border-zinc-700 bg-zinc-950 text-zinc-100"
                                />
                              )}
                            </div>
                            <div className="mt-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeRule("entry", index)}
                                className="h-7 px-2 text-zinc-400 hover:text-zinc-100"
                              >
                                <X className="mr-1 h-3 w-3" />
                                Remove
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2">
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-sm font-medium text-zinc-200">Exit Rules (ALL true)</p>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => addRule("exit")}
                        className="h-7 px-2 text-zinc-400 hover:text-zinc-100"
                      >
                        <Plus className="mr-1 h-3 w-3" />
                        Add
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {exitRules.map((rule, index) => {
                        const leftIndicator = indicatorsById.get(rule.left_indicator_id);
                        const leftLineKeys = leftIndicator ? lineKeysForIndicator(leftIndicator) : [];
                        const rightIndicator =
                          rule.right_indicator_id != null
                            ? indicatorsById.get(rule.right_indicator_id)
                            : undefined;
                        const rightLineKeys = rightIndicator ? lineKeysForIndicator(rightIndicator) : [];
                        return (
                          <div key={`exit-${index}`} className="rounded border border-zinc-800 p-2">
                            <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                              <select
                                value={rule.left_indicator_id}
                                onChange={(event) =>
                                  updateRule("exit", index, (current) => {
                                    const nextIndicator = indicatorsById.get(event.target.value);
                                    const nextLine = nextIndicator
                                      ? lineKeysForIndicator(nextIndicator)[0]
                                      : current.left_line_key;
                                    return {
                                      ...current,
                                      left_indicator_id: event.target.value,
                                      left_line_key: nextLine,
                                    };
                                  })
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                {indicatorConfigs.map((indicator) => (
                                  <option key={indicator.id} value={indicator.id}>
                                    {INDICATOR_SPECS_BY_KIND[indicator.kind].label} ({indicator.id.slice(-4)})
                                  </option>
                                ))}
                              </select>
                              <select
                                value={rule.left_line_key}
                                onChange={(event) =>
                                  updateRule("exit", index, (current) => ({
                                    ...current,
                                    left_line_key: event.target.value,
                                  }))
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                {leftLineKeys.map((lineKey) => (
                                  <option key={lineKey} value={lineKey}>
                                    {lineKey}
                                  </option>
                                ))}
                              </select>
                              <select
                                value={rule.operator}
                                onChange={(event) =>
                                  updateRule("exit", index, (current) => ({
                                    ...current,
                                    operator: event.target.value as RuleOperator,
                                  }))
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                {operatorOptions.map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                              <select
                                value={rule.right_type}
                                onChange={(event) =>
                                  updateRule("exit", index, (current) => ({
                                    ...current,
                                    right_type: event.target.value as "indicator" | "value",
                                  }))
                                }
                                className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                              >
                                <option value="indicator">Indicator</option>
                                <option value="value">Constant</option>
                              </select>
                              {rule.right_type === "indicator" ? (
                                <>
                                  <select
                                    value={rule.right_indicator_id ?? ""}
                                    onChange={(event) =>
                                      updateRule("exit", index, (current) => {
                                        const nextIndicator = indicatorsById.get(event.target.value);
                                        const nextLine = nextIndicator
                                          ? lineKeysForIndicator(nextIndicator)[0]
                                          : current.right_line_key;
                                        return {
                                          ...current,
                                          right_indicator_id: event.target.value,
                                          right_line_key: nextLine ?? null,
                                        };
                                      })
                                    }
                                    className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                                  >
                                    {indicatorConfigs.map((indicator) => (
                                      <option key={indicator.id} value={indicator.id}>
                                        {INDICATOR_SPECS_BY_KIND[indicator.kind].label} ({indicator.id.slice(-4)})
                                      </option>
                                    ))}
                                  </select>
                                  <select
                                    value={rule.right_line_key ?? ""}
                                    onChange={(event) =>
                                      updateRule("exit", index, (current) => ({
                                        ...current,
                                        right_line_key: event.target.value,
                                      }))
                                    }
                                    className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                                  >
                                    {rightLineKeys.map((lineKey) => (
                                      <option key={lineKey} value={lineKey}>
                                        {lineKey}
                                      </option>
                                    ))}
                                  </select>
                                </>
                              ) : (
                                <Input
                                  type="number"
                                  value={rule.right_value ?? 0}
                                  step={0.1}
                                  onChange={(event) =>
                                    updateRule("exit", index, (current) => ({
                                      ...current,
                                      right_value: Number(event.target.value),
                                    }))
                                  }
                                  className="h-8 border-zinc-700 bg-zinc-950 text-zinc-100"
                                />
                              )}
                            </div>
                            <div className="mt-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeRule("exit", index)}
                                className="h-7 px-2 text-zinc-400 hover:text-zinc-100"
                              >
                                <X className="mr-1 h-3 w-3" />
                                Remove
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {backtestError ? (
                  <p className="mt-3 text-xs text-red-300">{backtestError}</p>
                ) : null}
              </div>
              {error ? (
                <div className="rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-200">
                  {error}
                </div>
              ) : (
                <PriceChart
                  data={history?.bars ?? []}
                  indicators={history?.indicators ?? []}
                  type={chartType}
                />
              )}
              {backtestResult ? (
                <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                  <p className="text-sm font-medium text-zinc-200">Backtest Results</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Preliminary diagnostics only. Treat as hypothesis generation, not production evidence.
                  </p>
                  <div className="mt-3 grid gap-2 text-xs md:grid-cols-4">
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Total Return</p>
                      <p className="font-semibold">{backtestResult.metrics.total_return_pct.toFixed(2)}%</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Sharpe</p>
                      <p className="font-semibold">{backtestResult.metrics.sharpe_ratio.toFixed(2)}</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Max Drawdown</p>
                      <p className="font-semibold">{backtestResult.metrics.max_drawdown_pct.toFixed(2)}%</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Trades</p>
                      <p className="font-semibold">{backtestResult.metrics.trade_count}</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Win Rate</p>
                      <p className="font-semibold">{backtestResult.metrics.win_rate_pct.toFixed(2)}%</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Calmar</p>
                      <p className="font-semibold">{backtestResult.metrics.calmar_ratio.toFixed(2)}</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Profit Factor</p>
                      <p className="font-semibold">{backtestResult.metrics.profit_factor.toFixed(2)}</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Ending Equity</p>
                      <p className="font-semibold">
                        {formatCurrency(backtestResult.metrics.ending_equity)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 max-h-56 overflow-auto rounded border border-zinc-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-zinc-900 text-zinc-400">
                        <tr>
                          <th className="px-2 py-1">Entry</th>
                          <th className="px-2 py-1">Exit</th>
                          <th className="px-2 py-1">Qty</th>
                          <th className="px-2 py-1">Net P&L</th>
                          <th className="px-2 py-1">Return</th>
                        </tr>
                      </thead>
                      <tbody>
                        {backtestResult.trades.slice(-20).map((trade, index) => (
                          <tr key={`${trade.entry_time}-${trade.exit_time}-${index}`} className="border-t border-zinc-800">
                            <td className="px-2 py-1 text-zinc-300">{trade.entry_time}</td>
                            <td className="px-2 py-1 text-zinc-300">{trade.exit_time}</td>
                            <td className="px-2 py-1 text-zinc-300">{trade.quantity.toFixed(0)}</td>
                            <td
                              className={cn(
                                "px-2 py-1",
                                trade.net_pnl >= 0 ? "text-emerald-300" : "text-red-300",
                              )}
                            >
                              {trade.net_pnl.toFixed(2)}
                            </td>
                            <td
                              className={cn(
                                "px-2 py-1",
                                trade.net_return_pct >= 0 ? "text-emerald-300" : "text-red-300",
                              )}
                            >
                              {trade.net_return_pct.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
              {strategyBacktestResult ? (
                <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                  <p className="text-sm font-medium text-zinc-200">EMA Baseline Strategy</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Simple baseline that future ML models must beat out-of-sample after costs.
                  </p>
                  <div className="mt-3 grid gap-2 text-xs md:grid-cols-4">
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Symbol</p>
                      <p className="font-semibold">{strategyBacktestResult.symbol}</p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Total Return</p>
                      <p className="font-semibold">
                        {strategyBacktestResult.metrics.total_return_pct.toFixed(2)}%
                      </p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Sharpe</p>
                      <p className="font-semibold">
                        {strategyBacktestResult.metrics.sharpe_ratio.toFixed(2)}
                      </p>
                    </div>
                    <div className="rounded border border-zinc-800 p-2">
                      <p className="text-zinc-500">Trades</p>
                      <p className="font-semibold">{strategyBacktestResult.metrics.trade_count}</p>
                    </div>
                  </div>
                  <div className="mt-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void reviewStrategyBaseline()}
                      disabled={isReviewing}
                    >
                      {isReviewing ? "Reviewing..." : "Review with Gemini"}
                    </Button>
                  </div>
                  {researchReview ? (
                    <div className="mt-3 rounded border border-zinc-800 bg-zinc-900/40 p-3 text-xs text-zinc-300">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="rounded bg-zinc-800 px-2 py-1 text-zinc-200">
                          {researchReview.provider} / {researchReview.model}
                        </span>
                        <span className="rounded bg-zinc-800 px-2 py-1 text-zinc-200">
                          verdict: {researchReview.verdict}
                        </span>
                      </div>
                      <pre className="whitespace-pre-wrap font-sans leading-relaxed">
                        {researchReview.report_markdown}
                      </pre>
                    </div>
                  ) : null}
                </div>
              ) : null}
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
