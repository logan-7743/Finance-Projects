"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Activity, BarChart3, Brain, CandlestickChart, Search, Server } from "lucide-react";

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
  reviewBacktestArtifact,
  runEmaCrossoverBacktest,
  runPerplexityResearch,
  type LlmReviewResult,
  type PerplexityResearchResult,
  type StrategyBacktestResult,
} from "@/lib/api";
import { cn } from "@/lib/utils";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number) {
  return `${value.toFixed(2)}%`;
}

function metricClass(value: number) {
  return value >= 0 ? "text-emerald-300" : "text-red-300";
}

export function ResearchDashboard() {
  const [symbol, setSymbol] = useState("BTC-USD");
  const [initialCapital, setInitialCapital] = useState(100_000);
  const [fastPeriod, setFastPeriod] = useState(12);
  const [slowPeriod, setSlowPeriod] = useState(26);
  const [isRunningBaseline, setIsRunningBaseline] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isResearching, setIsResearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [baseline, setBaseline] = useState<StrategyBacktestResult | null>(null);
  const [review, setReview] = useState<LlmReviewResult | null>(null);
  const [question, setQuestion] = useState(
    "What are the current liquidity and market-structure risks for small and mid-cap crypto assets?",
  );
  const [perplexityResult, setPerplexityResult] =
    useState<PerplexityResearchResult | null>(null);

  const dataRange = useMemo(() => {
    if (!baseline?.equity_curve.length) {
      return "unknown";
    }
    const first = baseline.equity_curve[0]?.[0] ?? "unknown";
    const last = baseline.equity_curve[baseline.equity_curve.length - 1]?.[0] ?? "unknown";
    return `${first} to ${last}`;
  }, [baseline]);

  async function runBaseline() {
    setIsRunningBaseline(true);
    setError(null);
    setReview(null);
    try {
      const result = await runEmaCrossoverBacktest({
        symbol,
        period: "1y",
        interval: "1d",
        initial_capital: initialCapital,
        fast_period: fastPeriod,
        slow_period: slowPeriod,
        execution_lag_bars: 1,
      });
      setBaseline(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run baseline.");
    } finally {
      setIsRunningBaseline(false);
    }
  }

  async function reviewBaseline() {
    if (!baseline) {
      return;
    }
    setIsReviewing(true);
    setError(null);
    try {
      const result = await reviewBacktestArtifact({
        strategy_name: baseline.strategy_name,
        symbol: baseline.symbol,
        hypothesis: "A fast EMA crossing above a slow EMA captures short-term momentum.",
        data_range: dataRange,
        cost_assumptions: [
          "Uses backend CostModel defaults.",
          "Execution is delayed by one bar and filled at next bar open.",
        ],
        validation_notes: [
          "This is an in-sample baseline report.",
          "Walk-forward and final holdout validation are required before paper trading.",
        ],
        metrics: [
          { name: "Total Return %", value: baseline.metrics.total_return_pct },
          { name: "Sharpe", value: baseline.metrics.sharpe_ratio },
          { name: "Max Drawdown %", value: baseline.metrics.max_drawdown_pct },
          { name: "Trade Count", value: baseline.metrics.trade_count },
          { name: "Win Rate %", value: baseline.metrics.win_rate_pct },
          { name: "Ending Equity", value: baseline.metrics.ending_equity },
        ],
        risks: [
          "Data source may be research-grade only.",
          "No regime breakdown yet.",
          "No untouched final holdout has been run.",
        ],
      });
      setReview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gemini review failed.");
    } finally {
      setIsReviewing(false);
    }
  }

  async function runResearch() {
    setIsResearching(true);
    setError(null);
    try {
      const result = await runPerplexityResearch({
        question,
        max_tokens: 1_200,
        temperature: 0.2,
      });
      setPerplexityResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Perplexity research failed.");
    } finally {
      setIsResearching(false);
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
            <p className="text-xs text-zinc-500">Research mode</p>
          </div>
        </div>

        <nav className="mt-10 space-y-2 text-sm">
          <Link className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500" href="/">
            <BarChart3 className="h-4 w-4" />
            Market Data
          </Link>
          <Link
            className="flex items-center gap-2 rounded-lg bg-zinc-900 px-3 py-2 text-zinc-50"
            href="/research"
          >
            <Activity className="h-4 w-4" />
            Research
          </Link>
          <span className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-600">
            <Brain className="h-4 w-4" />
            Gemini Review
          </span>
          <span className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-600">
            <Server className="h-4 w-4" />
            Execution Gates
          </span>
        </nav>
      </aside>

      <main className="lg:pl-64">
        <section className="mx-auto max-w-7xl px-6 py-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-zinc-500">Research cockpit</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight">
                Crypto Strategy Research
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-zinc-400">
                Run a baseline, send structured results to Gemini for a skeptical review,
                and use Perplexity for current market research. This is research support,
                not live trading.
              </p>
            </div>
            <Link className="text-sm text-zinc-400 hover:text-zinc-100" href="/">
              Back to market dashboard
            </Link>
          </div>

          {error ? (
            <div className="mb-4 rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <Card>
              <CardHeader>
                <CardTitle>Baseline Backtest</CardTitle>
                <CardDescription>
                  EMA crossover is the first baseline future ML models must beat after costs.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-4">
                  <label className="text-xs text-zinc-400">
                    Symbol
                    <Input
                      value={symbol}
                      onChange={(event) => setSymbol(event.target.value.toUpperCase())}
                      className="mt-1 border-zinc-700 bg-zinc-950 text-zinc-100"
                    />
                  </label>
                  <label className="text-xs text-zinc-400">
                    Initial Capital
                    <Input
                      type="number"
                      value={initialCapital}
                      onChange={(event) => setInitialCapital(Number(event.target.value))}
                      className="mt-1 border-zinc-700 bg-zinc-950 text-zinc-100"
                    />
                  </label>
                  <label className="text-xs text-zinc-400">
                    Fast EMA
                    <Input
                      type="number"
                      value={fastPeriod}
                      onChange={(event) => setFastPeriod(Number(event.target.value))}
                      className="mt-1 border-zinc-700 bg-zinc-950 text-zinc-100"
                    />
                  </label>
                  <label className="text-xs text-zinc-400">
                    Slow EMA
                    <Input
                      type="number"
                      value={slowPeriod}
                      onChange={(event) => setSlowPeriod(Number(event.target.value))}
                      className="mt-1 border-zinc-700 bg-zinc-950 text-zinc-100"
                    />
                  </label>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Button onClick={() => void runBaseline()} disabled={isRunningBaseline}>
                    {isRunningBaseline ? "Running..." : "Run EMA Baseline"}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => void reviewBaseline()}
                    disabled={!baseline || isReviewing}
                  >
                    {isReviewing ? "Reviewing..." : "Review with Gemini"}
                  </Button>
                </div>

                {baseline ? (
                  <div className="mt-4">
                    <div className="grid gap-2 text-xs md:grid-cols-4">
                      <Metric label="Total Return" value={formatPercent(baseline.metrics.total_return_pct)} valueClass={metricClass(baseline.metrics.total_return_pct)} />
                      <Metric label="Sharpe" value={baseline.metrics.sharpe_ratio.toFixed(2)} />
                      <Metric label="Max Drawdown" value={formatPercent(baseline.metrics.max_drawdown_pct)} valueClass="text-red-300" />
                      <Metric label="Ending Equity" value={formatCurrency(baseline.metrics.ending_equity)} />
                      <Metric label="Trades" value={String(baseline.metrics.trade_count)} />
                      <Metric label="Win Rate" value={formatPercent(baseline.metrics.win_rate_pct)} />
                      <Metric label="Calmar" value={baseline.metrics.calmar_ratio.toFixed(2)} />
                      <Metric label="Signals" value={String(baseline.signal_count)} />
                    </div>
                  </div>
                ) : (
                  <p className="mt-4 text-sm text-zinc-500">
                    No baseline run yet. Start with BTC-USD, ETH-USD, or SOL-USD.
                  </p>
                )}

                {review ? (
                  <ReportBlock
                    title={`Gemini Review (${review.verdict})`}
                    subtitle={`${review.provider} / ${review.model}`}
                    body={review.report_markdown}
                  />
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Perplexity Research
                </CardTitle>
                <CardDescription>
                  Use current web research for market context. Do not treat this as a signal.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  className="min-h-32 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-zinc-500"
                />
                <div className="mt-3">
                  <Button
                    variant="secondary"
                    onClick={() => void runResearch()}
                    disabled={isResearching || question.trim().length === 0}
                  >
                    {isResearching ? "Researching..." : "Run Perplexity Research"}
                  </Button>
                </div>

                {perplexityResult ? (
                  <div className="mt-4 space-y-3">
                    <ReportBlock
                      title="Research Summary"
                      subtitle={`${perplexityResult.provider} / ${perplexityResult.model}`}
                      body={perplexityResult.answer_markdown}
                    />
                    {perplexityResult.citations.length > 0 ? (
                      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
                        <p className="text-sm font-medium text-zinc-200">Citations</p>
                        <ul className="mt-2 space-y-2 text-xs text-zinc-400">
                          {perplexityResult.citations.map((citation) => (
                            <li key={citation.url}>
                              <a
                                className="text-zinc-300 underline-offset-4 hover:text-zinc-50 hover:underline"
                                href={citation.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {citation.title}
                              </a>
                              {citation.date ? (
                                <span className="ml-2 text-zinc-600">{citation.date}</span>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded border border-zinc-800 bg-zinc-900/40 p-2">
      <p className="text-zinc-500">{label}</p>
      <p className={cn("font-semibold text-zinc-100", valueClass)}>{value}</p>
    </div>
  );
}

function ReportBlock({
  title,
  subtitle,
  body,
}: {
  title: string;
  subtitle: string;
  body: string;
}) {
  return (
    <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-xs text-zinc-300">
      <div className="mb-2">
        <p className="text-sm font-medium text-zinc-200">{title}</p>
        <p className="text-xs text-zinc-500">{subtitle}</p>
      </div>
      <pre className="whitespace-pre-wrap font-sans leading-relaxed">{body}</pre>
    </div>
  );
}
